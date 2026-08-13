import base64
import json
from html import escape
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from app.config import settings


class AzureDevOpsNotConfiguredError(RuntimeError):
    """The support integration is missing its server-side configuration."""


class AzureDevOpsRequestError(RuntimeError):
    """Azure DevOps rejected or could not complete a work-item request."""


CUSTOMER_COMMENT_PREFIX = "**Customer reply via DPP:**\n\n"


def _authorization_header() -> str:
    """Build the Basic authorization value without exposing the PAT."""

    if settings.azure_devops_pat is None:
        raise AzureDevOpsNotConfiguredError
    pat = settings.azure_devops_pat.get_secret_value()
    encoded = base64.b64encode(f":{pat}".encode()).decode()
    return f"Basic {encoded}"


def support_ticket_is_enabled(
    area_path: str | None,
    work_item_type: str,
) -> bool:
    """Tell clients whether both routing and secret configuration are present."""

    return (
        area_path is not None
        and bool(work_item_type)
        and settings.azure_devops_pat is not None
    )


def create_support_work_item(
    *,
    area_path: str | None,
    work_item_type: str,
    requester_name: str,
    requester_email: str,
    subject: str,
    message: str,
    manufacturer_name: str,
    category_name: str,
    model_code: str,
    model_name: str,
    serial_number: str,
    public_id: str,
    passport_url: str,
) -> tuple[int, str | None]:
    """Create one Azure DevOps Customer Support work item."""

    if area_path is None or not work_item_type or settings.azure_devops_pat is None:
        raise AzureDevOpsNotConfiguredError

    encoded_work_item_type = quote(work_item_type, safe="")
    url = (
        f"{settings.azure_devops_project_url}/_apis/wit/workitems/"
        f"${encoded_work_item_type}?api-version=7.1"
    )
    title = f"[DPP Support] {model_name} / {serial_number}: {subject}"[:255]
    description = _build_description(
        requester_name=requester_name,
        requester_email=requester_email,
        message=message,
        manufacturer_name=manufacturer_name,
        category_name=category_name,
        model_code=model_code,
        model_name=model_name,
        serial_number=serial_number,
        public_id=public_id,
        passport_url=passport_url,
    )
    patch_document = [
        {"op": "add", "path": "/fields/System.Title", "value": title},
        {
            "op": "add",
            "path": "/fields/System.Description",
            "value": description,
        },
        {
            "op": "add",
            "path": "/fields/System.AreaPath",
            "value": area_path,
        },
    ]
    request = Request(
        url,
        data=json.dumps(patch_document).encode(),
        headers={
            "Accept": "application/json",
            "Authorization": _authorization_header(),
            "Content-Type": "application/json-patch+json",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=10) as response:
            result = json.load(response)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
        # Never include the request or authorization header in the public error.
        raise AzureDevOpsRequestError from error

    ticket_id = result.get("id")
    if not isinstance(ticket_id, int):
        raise AzureDevOpsRequestError
    ticket_url = result.get("_links", {}).get("html", {}).get("href")
    if not isinstance(ticket_url, str):
        ticket_url = None
    return ticket_id, ticket_url


def get_support_work_item(ticket_id: int) -> dict[str, object]:
    """Load the small Azure field subset used by the customer tracking page."""

    fields = quote(
        "System.State,System.CreatedDate,System.ChangedDate",
        safe=",",
    )
    url = (
        f"{settings.azure_devops_project_url}/_apis/wit/workitems/{ticket_id}"
        f"?fields={fields}&api-version=7.1"
    )
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "Authorization": _authorization_header(),
            "Cache-Control": "no-cache",
        },
        method="GET",
    )
    try:
        with urlopen(request, timeout=10) as response:
            result = json.load(response)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
        raise AzureDevOpsRequestError from error

    fields_result = result.get("fields")
    if not isinstance(fields_result, dict):
        raise AzureDevOpsRequestError
    return fields_result


def get_support_work_item_comments(ticket_id: int) -> list[dict[str, object]]:
    """Load the latest Azure comments used as the customer conversation."""

    query = urlencode(
        {
            "$top": 100,
            "order": "asc",
            "api-version": "7.1-preview.4",
        },
    )
    url = (
        f"{settings.azure_devops_project_url}/_apis/wit/workItems/{ticket_id}"
        f"/comments?{query}"
    )
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "Authorization": _authorization_header(),
            "Cache-Control": "no-cache",
        },
        method="GET",
    )
    try:
        with urlopen(request, timeout=10) as response:
            result = json.load(response)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
        raise AzureDevOpsRequestError from error

    comments = result.get("comments", result.get("value"))
    if not isinstance(comments, list):
        raise AzureDevOpsRequestError
    return comments


def add_support_work_item_comment(*, ticket_id: int, message: str) -> None:
    """Add a clearly labelled customer reply to an Azure work item."""

    query = urlencode({"format": "markdown", "api-version": "7.1-preview.4"})
    url = (
        f"{settings.azure_devops_project_url}/_apis/wit/workItems/{ticket_id}"
        f"/comments?{query}"
    )
    request = Request(
        url,
        data=json.dumps({"text": f"{CUSTOMER_COMMENT_PREFIX}{message}"}).encode(),
        headers={
            "Accept": "application/json",
            "Authorization": _authorization_header(),
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=10):
            return
    except (HTTPError, URLError, TimeoutError) as error:
        raise AzureDevOpsRequestError from error


def customer_safe_comment(comment: dict[str, object]) -> dict[str, object] | None:
    """Reduce one Azure comment to plain text and a generic public author."""

    text = comment.get("text")
    created_at = comment.get("createdDate")
    comment_id = comment.get("id")
    if not isinstance(text, str) or not isinstance(created_at, str):
        return None

    is_customer = text.startswith(CUSTOMER_COMMENT_PREFIX)
    if is_customer:
        text = text.removeprefix(CUSTOMER_COMMENT_PREFIX)
    text = _plain_text(text).strip()
    if not text:
        return None
    return {
        "id": comment_id if isinstance(comment_id, int) else 0,
        "author": "Customer" if is_customer else "Support",
        "message": text,
        "created_at": created_at,
    }


def upload_work_item_attachment(
    *,
    file_data: bytes,
    filename: str,
    area_path: str,
) -> str:
    """Upload validated bytes and return Azure's private attachment URL."""

    query = urlencode(
        {
            "fileName": filename,
            "areaPath": area_path,
            "api-version": "7.1",
        },
    )
    url = f"{settings.azure_devops_project_url}/_apis/wit/attachments?{query}"
    request = Request(
        url,
        data=file_data,
        headers={
            "Accept": "application/json",
            "Authorization": _authorization_header(),
            "Content-Type": "application/octet-stream",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=15) as response:
            result = json.load(response)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
        raise AzureDevOpsRequestError from error

    attachment_url = result.get("url")
    if not isinstance(attachment_url, str):
        raise AzureDevOpsRequestError
    return attachment_url


def add_work_item_attachment(
    *,
    ticket_id: int,
    attachment_url: str,
) -> None:
    """Link one previously uploaded attachment to an Azure work item."""

    url = (
        f"{settings.azure_devops_project_url}/_apis/wit/workitems/{ticket_id}"
        "?api-version=7.1"
    )
    patch_document = [
        {
            "op": "add",
            "path": "/relations/-",
            "value": {
                "rel": "AttachedFile",
                "url": attachment_url,
                "attributes": {"comment": "Screenshot submitted by customer"},
            },
        },
    ]
    request = Request(
        url,
        data=json.dumps(patch_document).encode(),
        headers={
            "Accept": "application/json",
            "Authorization": _authorization_header(),
            "Content-Type": "application/json-patch+json",
        },
        method="PATCH",
    )
    try:
        with urlopen(request, timeout=10):
            return
    except (HTTPError, URLError, TimeoutError) as error:
        raise AzureDevOpsRequestError from error


def _build_description(**values: str) -> str:
    """Build escaped HTML accepted by Azure DevOps rich-text descriptions."""

    safe = {key: escape(value) for key, value in values.items()}
    message = safe["message"].replace("\n", "<br>")
    return (
        f"<p><strong>Requester:</strong> {safe['requester_name']} "
        f"({safe['requester_email']})</p>"
        f"<p><strong>Message:</strong><br>{message}</p>"
        "<hr>"
        "<p><strong>Product passport</strong></p>"
        "<ul>"
        f"<li>Manufacturer: {safe['manufacturer_name']}</li>"
        f"<li>Category: {safe['category_name']}</li>"
        f"<li>Model: {safe['model_name']} ({safe['model_code']})</li>"
        f"<li>Serial number: {safe['serial_number']}</li>"
        f"<li>Public passport ID: {safe['public_id']}</li>"
        f"<li>Passport: <a href=\"{safe['passport_url']}\">"
        f"{safe['passport_url']}</a></li>"
        "</ul>"
    )


class _PlainTextParser(HTMLParser):
    """Extract readable text without rendering Azure-provided HTML."""

    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def _plain_text(value: str) -> str:
    parser = _PlainTextParser()
    parser.feed(value)
    return "".join(parser.parts)
