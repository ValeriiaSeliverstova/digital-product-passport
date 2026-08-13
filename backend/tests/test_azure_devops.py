import base64
import io
import json

from pydantic import SecretStr
from pytest import MonkeyPatch

from app.azure_devops import (
    add_support_work_item_comment,
    add_work_item_attachment,
    customer_safe_comment,
    create_support_work_item,
    get_support_work_item,
    get_support_work_item_comments,
    upload_work_item_attachment,
)
from app.config import settings


def test_azure_devops_request_uses_pat_and_escaped_json_patch(
    monkeypatch: MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    response = io.BytesIO(
        json.dumps(
            {
                "id": 91,
                "_links": {"html": {"href": "https://dev.azure.com/ticket/91"}},
            },
        ).encode(),
    )

    def fake_urlopen(request: object, timeout: int) -> io.BytesIO:
        captured["request"] = request
        captured["timeout"] = timeout
        return response

    monkeypatch.setattr(settings, "azure_devops_pat", SecretStr("test-pat-value"))
    monkeypatch.setattr("app.azure_devops.urlopen", fake_urlopen)

    ticket_id, ticket_url = create_support_work_item(
        area_path="Students\\Institute",
        work_item_type="Customer Support",
        requester_name="<Taylor>",
        requester_email="taylor@example.com",
        subject="Broken lock",
        message="The <lock> is broken.\nPlease help.",
        manufacturer_name="Example Ltd.",
        category_name="Safes",
        model_code="SAFE-1",
        model_name="Example Safe",
        serial_number="SN-100",
        public_id="public-id",
        passport_url="http://localhost:5173/passport/public-id",
    )

    request = captured["request"]
    patch_document = json.loads(request.data)
    expected_auth = base64.b64encode(b":test-pat-value").decode()
    assert request.full_url.endswith(
        "/_apis/wit/workitems/$Customer%20Support?api-version=7.1",
    )
    assert request.get_header("Authorization") == f"Basic {expected_auth}"
    assert request.get_header("Content-type") == "application/json-patch+json"
    assert patch_document[2]["value"] == "Students\\Institute"
    assert "&lt;Taylor&gt;" in patch_document[1]["value"]
    assert "&lt;lock&gt;" in patch_document[1]["value"]
    assert "<Taylor>" not in patch_document[1]["value"]
    assert captured["timeout"] == 10
    assert ticket_id == 91
    assert ticket_url == "https://dev.azure.com/ticket/91"


def test_get_support_work_item_requests_only_customer_status_fields(
    monkeypatch: MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    response = io.BytesIO(
        json.dumps(
            {
                "id": 91,
                "fields": {
                    "System.State": "Active",
                    "System.CreatedDate": "2026-08-13T12:00:00Z",
                    "System.ChangedDate": "2026-08-13T14:30:00Z",
                },
            },
        ).encode(),
    )

    def fake_urlopen(request: object, timeout: int) -> io.BytesIO:
        captured["request"] = request
        captured["timeout"] = timeout
        return response

    monkeypatch.setattr(settings, "azure_devops_pat", SecretStr("test-pat-value"))
    monkeypatch.setattr("app.azure_devops.urlopen", fake_urlopen)

    result = get_support_work_item(91)

    request = captured["request"]
    assert request.method == "GET"
    assert "/_apis/wit/workitems/91?fields=" in request.full_url
    assert "System.State" in request.full_url
    assert "System.Description" not in request.full_url
    assert request.get_header("Cache-control") == "no-cache"
    assert result["System.State"] == "Active"
    assert captured["timeout"] == 10


def test_upload_and_link_work_item_attachment(monkeypatch: MonkeyPatch) -> None:
    requests: list[object] = []
    responses = iter(
        [
            io.BytesIO(
                json.dumps(
                    {"url": "https://dev.azure.com/example/attachment/1"},
                ).encode(),
            ),
            io.BytesIO(b"{}"),
        ],
    )

    def fake_urlopen(request: object, timeout: int) -> io.BytesIO:
        requests.append(request)
        assert timeout in {10, 15}
        return next(responses)

    monkeypatch.setattr(settings, "azure_devops_pat", SecretStr("test-pat-value"))
    monkeypatch.setattr("app.azure_devops.urlopen", fake_urlopen)

    attachment_url = upload_work_item_attachment(
        file_data=b"image-bytes",
        filename="support-91-abcd1234.png",
        area_path="Students\\Support",
    )
    add_work_item_attachment(ticket_id=91, attachment_url=attachment_url)

    upload_request, link_request = requests
    assert upload_request.method == "POST"
    assert upload_request.data == b"image-bytes"
    assert "fileName=support-91-abcd1234.png" in upload_request.full_url
    assert "areaPath=Students%5CSupport" in upload_request.full_url
    assert upload_request.get_header("Content-type") == "application/octet-stream"
    assert link_request.method == "PATCH"
    relation = json.loads(link_request.data)[0]
    assert relation["path"] == "/relations/-"
    assert relation["value"]["rel"] == "AttachedFile"
    assert relation["value"]["url"] == attachment_url


def test_get_and_add_work_item_comments(monkeypatch: MonkeyPatch) -> None:
    requests: list[object] = []
    responses = iter(
        [
            io.BytesIO(
                json.dumps(
                    {
                        "comments": [
                            {
                                "id": 5,
                                "text": "Please restart the device.",
                                "createdDate": "2026-08-13T14:00:00Z",
                            },
                        ],
                    },
                ).encode(),
            ),
            io.BytesIO(b"{}"),
        ],
    )

    def fake_urlopen(request: object, timeout: int) -> io.BytesIO:
        requests.append(request)
        assert timeout == 10
        return next(responses)

    monkeypatch.setattr(settings, "azure_devops_pat", SecretStr("test-pat-value"))
    monkeypatch.setattr("app.azure_devops.urlopen", fake_urlopen)

    comments = get_support_work_item_comments(91)
    add_support_work_item_comment(ticket_id=91, message="It still does not work.")

    get_request, add_request = requests
    assert get_request.method == "GET"
    assert "/workItems/91/comments?" in get_request.full_url
    assert "%24top=100" in get_request.full_url
    assert comments[0]["id"] == 5
    assert add_request.method == "POST"
    assert "format=markdown" in add_request.full_url
    assert json.loads(add_request.data) == {
        "text": "**Customer reply via DPP:**\n\nIt still does not work.",
    }


def test_customer_safe_comment_requires_tag_and_hides_azure_identity() -> None:
    result = customer_safe_comment(
        {
            "id": 5,
            "text": (
                "<div>@customer</div>"
                "<div>Hello <strong>customer</strong>.<br>Please update.</div>"
            ),
            "createdDate": "2026-08-13T14:00:00Z",
            "createdBy": {"displayName": "Private Engineer Name"},
        },
    )

    assert result == {
        "id": 5,
        "author": "Support",
        "message": "Hello customer.\nPlease update.",
        "created_at": "2026-08-13T14:00:00Z",
    }

    assert customer_safe_comment(
        {
            "id": 6,
            "text": "Internal note: do not expose this",
            "createdDate": "2026-08-13T14:10:00Z",
        },
    ) is None
