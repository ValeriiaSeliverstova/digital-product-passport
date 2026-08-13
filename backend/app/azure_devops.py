import base64
import json
from html import escape
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from app.config import settings


class AzureDevOpsNotConfiguredError(RuntimeError):
    """The support integration is missing its server-side configuration."""


class AzureDevOpsRequestError(RuntimeError):
    """Azure DevOps rejected or could not complete a work-item request."""


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
