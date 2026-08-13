import base64
import io
import json

from pydantic import SecretStr
from pytest import MonkeyPatch

from app.azure_devops import create_support_work_item, get_support_work_item
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
    assert result["System.State"] == "Active"
    assert captured["timeout"] == 10
