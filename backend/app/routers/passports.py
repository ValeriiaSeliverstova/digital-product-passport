import hashlib
import json
import secrets
from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Header,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.database import get_db
from app.azure_devops import (
    AzureDevOpsNotConfiguredError,
    AzureDevOpsRequestError,
    add_work_item_attachment,
    create_support_work_item,
    support_ticket_is_enabled,
    upload_work_item_attachment,
)
from app.config import settings
from app.email_delivery import (
    EmailDeliveryError,
    EmailNotConfiguredError,
    send_tracking_email,
    tracking_email_is_configured,
)
from app.models import (
    Organization,
    PassportTemplate,
    ProductItem,
    ProductModel,
    SupportTicket,
)
from app.image_storage import detect_image_content_type
from app.schemas.public_passport import (
    PublicLifecycleEvent,
    PublicPassportField,
    PublicPassportResponse,
)
from app.schemas.support_ticket import (
    SupportTicketCreate,
    SupportTicketResponse,
)
from app.support_ticket_protection import (
    IdempotencyConflictError,
    IdempotencyInProgressError,
    SupportTicketRateLimitError,
    support_ticket_guard,
)


router = APIRouter(prefix="/api/passports", tags=["public passports"])

DatabaseSession = Annotated[Session, Depends(get_db)]

MAX_SUPPORT_ATTACHMENT_BYTES = 5 * 1024 * 1024
SUPPORT_ATTACHMENT_EXTENSIONS = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
}


def support_ticket_from_form(
    requester_name: Annotated[str, Form()],
    requester_email: Annotated[str, Form()],
    subject: Annotated[str, Form()],
    message: Annotated[str, Form()],
) -> SupportTicketCreate:
    """Build the validated ticket schema from a multipart form."""

    try:
        return SupportTicketCreate(
            requester_name=requester_name,
            requester_email=requester_email,
            subject=subject,
            message=message,
        )
    except ValidationError as error:
        raise RequestValidationError(error.errors()) from error


@router.get("/{public_id}", response_model=PublicPassportResponse)
def get_public_passport(
    public_id: UUID,
    db: DatabaseSession,
) -> PublicPassportResponse:
    """Return public fields for one published product passport."""

    product_item = get_published_product_item(db, public_id)
    if product_item is None:
        # The same response hides missing, Draft, and Retired passports.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Published passport not found",
        )

    product_model = product_item.product_model
    template = product_model.template
    organization = product_item.organization
    public_fields = [
        PublicPassportField(
            code=field.code,
            label=field.label,
            data_type=field.data_type,
            value=product_item.passport_data[field.code],
        )
        for field in template.fields
        if field.access_level == "public"
        and field.code in product_item.passport_data
        and product_item.passport_data[field.code] is not None
    ]
    public_events = [
        PublicLifecycleEvent.model_validate(event, from_attributes=True)
        for event in sorted(
            product_item.lifecycle_events,
            key=lambda lifecycle_event: lifecycle_event.occurred_at,
            reverse=True,
        )
        if event.access_level == "public"
    ]

    return PublicPassportResponse(
        public_id=product_item.public_id,
        manufacturer_name=organization.name,
        manufacturer_logo_path=get_logo_path(organization),
        support_email=organization.contact_email,
        support_phone=organization.phone,
        support_website=organization.website,
        support_ticket_enabled=support_ticket_is_enabled(
            organization.azure_devops_area_path,
            organization.azure_devops_work_item_type,
        )
        and tracking_email_is_configured(),
        category_name=product_model.category.name,
        model_code=product_model.model_code,
        model_name=product_model.name,
        model_description=product_model.description,
        model_image_path=get_product_model_image_path(product_model),
        template_name=template.name,
        template_version=template.version,
        serial_number=product_item.serial_number,
        manufacture_date=product_item.manufacture_date,
        fields=public_fields,
        lifecycle_events=public_events,
    )


@router.post(
    "/{public_id}/support-tickets",
    response_model=SupportTicketResponse,
    status_code=status.HTTP_201_CREATED,
)
def submit_support_ticket(
    public_id: UUID,
    data: Annotated[SupportTicketCreate, Depends(support_ticket_from_form)],
    request: Request,
    db: DatabaseSession,
    idempotency_key: Annotated[
        str,
        Header(alias="Idempotency-Key", min_length=8, max_length=128),
    ],
    attachment: Annotated[UploadFile | None, File()] = None,
) -> SupportTicketResponse:
    """Create an Azure DevOps ticket for one published product passport."""

    passport_id = str(public_id)
    client_host = request.client.host if request.client is not None else "unknown"
    attachment_data, attachment_content_type = _validate_support_attachment(
        attachment,
    )
    attachment_digest = (
        hashlib.sha256(attachment_data).hexdigest()
        if attachment_data is not None
        else None
    )
    fingerprint_data = data.model_dump(mode="json")
    fingerprint_data["attachment_sha256"] = attachment_digest
    fingerprint = hashlib.sha256(
        json.dumps(
            fingerprint_data,
            sort_keys=True,
            separators=(",", ":"),
        ).encode(),
    ).hexdigest()
    try:
        cached_ticket_id = support_ticket_guard.begin(
            rate_limit_key=f"{client_host}:{passport_id}",
            passport_id=passport_id,
            idempotency_key=idempotency_key,
            fingerprint=fingerprint,
        )
    except SupportTicketRateLimitError as error:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many support ticket requests. Please try again later.",
            headers={"Retry-After": str(error.retry_after)},
        ) from error
    except IdempotencyConflictError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Idempotency key was already used for different ticket data",
        ) from error
    except IdempotencyInProgressError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A support ticket with this idempotency key is being submitted",
        ) from error

    if cached_ticket_id is not None:
        return SupportTicketResponse(ticket_id=cached_ticket_id)

    product_item = get_published_product_item(db, public_id)
    if product_item is None:
        support_ticket_guard.abort(
            passport_id=passport_id,
            idempotency_key=idempotency_key,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Published passport not found",
        )

    product_model = product_item.product_model
    organization = product_item.organization
    if not tracking_email_is_configured():
        support_ticket_guard.abort(
            passport_id=passport_id,
            idempotency_key=idempotency_key,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Support ticket email service is not configured",
        )

    existing_ticket = db.scalar(
        select(SupportTicket).where(
            SupportTicket.idempotency_key == idempotency_key,
            SupportTicket.product_item_id == product_item.id,
        ),
    )
    if existing_ticket is not None:
        if existing_ticket.request_fingerprint != fingerprint:
            support_ticket_guard.abort(
                passport_id=passport_id,
                idempotency_key=idempotency_key,
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Idempotency key was already used for different ticket data",
            )
        if attachment_data is not None and not existing_ticket.attachment_added:
            _add_attachment_to_ticket(
                db=db,
                support_ticket=existing_ticket,
                attachment_data=attachment_data,
                attachment_content_type=attachment_content_type,
                area_path=organization.azure_devops_area_path,
                passport_id=passport_id,
                idempotency_key=idempotency_key,
            )
        if not existing_ticket.tracking_email_sent:
            _send_new_tracking_code(
                db=db,
                support_ticket=existing_ticket,
                recipient=data.requester_email,
                manufacturer_name=organization.name,
                organization_logo_url=organization.logo_url,
                passport_id=passport_id,
                idempotency_key=idempotency_key,
            )
        support_ticket_guard.complete(
            passport_id=passport_id,
            idempotency_key=idempotency_key,
            ticket_id=existing_ticket.azure_ticket_id,
        )
        return SupportTicketResponse(ticket_id=existing_ticket.azure_ticket_id)

    try:
        ticket_id, _ticket_url = create_support_work_item(
            area_path=organization.azure_devops_area_path,
            work_item_type=organization.azure_devops_work_item_type,
            requester_name=data.requester_name,
            requester_email=data.requester_email,
            subject=data.subject,
            message=data.message,
            manufacturer_name=organization.name,
            category_name=product_model.category.name,
            model_code=product_model.model_code,
            model_name=product_model.name,
            serial_number=product_item.serial_number,
            public_id=str(product_item.public_id),
            passport_url=(
                f"{settings.frontend_origin}/passport/{product_item.public_id}"
            ),
        )
    except AzureDevOpsNotConfiguredError as error:
        support_ticket_guard.abort(
            passport_id=passport_id,
            idempotency_key=idempotency_key,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Support ticket service is not configured",
        ) from error
    except AzureDevOpsRequestError as error:
        support_ticket_guard.abort(
            passport_id=passport_id,
            idempotency_key=idempotency_key,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Support ticket could not be submitted",
        ) from error

    tracking_code = secrets.token_urlsafe(12)
    support_ticket = SupportTicket(
        organization_id=organization.id,
        product_item_id=product_item.id,
        azure_ticket_id=ticket_id,
        idempotency_key=idempotency_key,
        request_fingerprint=fingerprint,
        subject=data.subject,
        tracking_code_hash=_hash_tracking_code(tracking_code),
        attachment_added=attachment_data is None,
    )
    db.add(support_ticket)
    db.commit()
    if attachment_data is not None:
        _add_attachment_to_ticket(
            db=db,
            support_ticket=support_ticket,
            attachment_data=attachment_data,
            attachment_content_type=attachment_content_type,
            area_path=organization.azure_devops_area_path,
            passport_id=passport_id,
            idempotency_key=idempotency_key,
        )
    try:
        send_tracking_email(
            recipient=data.requester_email,
            ticket_id=ticket_id,
            tracking_code=tracking_code,
            subject=data.subject,
            manufacturer_name=organization.name,
            organization_logo_url=organization.logo_url,
        )
    except (EmailNotConfiguredError, EmailDeliveryError) as error:
        support_ticket_guard.abort(
            passport_id=passport_id,
            idempotency_key=idempotency_key,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "Support ticket was created, but its tracking email could not be "
                "sent. Please retry the submission."
            ),
        ) from error

    support_ticket.tracking_email_sent = True
    db.commit()

    support_ticket_guard.complete(
        passport_id=passport_id,
        idempotency_key=idempotency_key,
        ticket_id=ticket_id,
    )
    return SupportTicketResponse(ticket_id=ticket_id)


def _validate_support_attachment(
    attachment: UploadFile | None,
) -> tuple[bytes | None, str | None]:
    """Accept one small raster image based on its bytes, not its filename."""

    if attachment is None:
        return None, None

    attachment_data = attachment.file.read(MAX_SUPPORT_ATTACHMENT_BYTES + 1)
    if len(attachment_data) > MAX_SUPPORT_ATTACHMENT_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="Support ticket attachment must not exceed 5 MB",
        )
    content_type = detect_image_content_type(attachment_data)
    if content_type not in SUPPORT_ATTACHMENT_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Support ticket attachment must be a PNG, JPEG, or WebP image",
        )
    return attachment_data, content_type


def _add_attachment_to_ticket(
    *,
    db: Session,
    support_ticket: SupportTicket,
    attachment_data: bytes,
    attachment_content_type: str | None,
    area_path: str | None,
    passport_id: str,
    idempotency_key: str,
) -> None:
    """Upload one validated screenshot and link it to an existing Azure ticket."""

    if attachment_content_type is None or area_path is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Support ticket attachment service is not configured",
        )
    safe_filename = (
        f"support-{support_ticket.azure_ticket_id}-{secrets.token_hex(4)}"
        f"{SUPPORT_ATTACHMENT_EXTENSIONS[attachment_content_type]}"
    )
    try:
        attachment_url = upload_work_item_attachment(
            file_data=attachment_data,
            filename=safe_filename,
            area_path=area_path,
        )
        add_work_item_attachment(
            ticket_id=support_ticket.azure_ticket_id,
            attachment_url=attachment_url,
        )
    except AzureDevOpsRequestError as error:
        support_ticket_guard.abort(
            passport_id=passport_id,
            idempotency_key=idempotency_key,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "Support ticket was created, but its attachment could not be "
                "uploaded. Please retry the submission."
            ),
        ) from error

    support_ticket.attachment_added = True
    db.commit()


def _send_new_tracking_code(
    *,
    db: Session,
    support_ticket: SupportTicket,
    recipient: str,
    manufacturer_name: str,
    organization_logo_url: str | None,
    passport_id: str,
    idempotency_key: str,
) -> None:
    """Retry email delivery for a ticket already created in Azure DevOps."""

    tracking_code = secrets.token_urlsafe(12)
    support_ticket.tracking_code_hash = _hash_tracking_code(tracking_code)
    db.commit()
    try:
        send_tracking_email(
            recipient=recipient,
            ticket_id=support_ticket.azure_ticket_id,
            tracking_code=tracking_code,
            subject=support_ticket.subject,
            manufacturer_name=manufacturer_name,
            organization_logo_url=organization_logo_url,
        )
    except (EmailNotConfiguredError, EmailDeliveryError) as error:
        support_ticket_guard.abort(
            passport_id=passport_id,
            idempotency_key=idempotency_key,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "Support ticket was created, but its tracking email could not be "
                "sent. Please retry the submission."
            ),
        ) from error

    support_ticket.tracking_email_sent = True
    db.commit()


def _hash_tracking_code(tracking_code: str) -> str:
    """Store only a one-way digest of each high-entropy tracking code."""

    return hashlib.sha256(tracking_code.encode()).hexdigest()


def get_published_product_item(
    db: Session,
    public_id: UUID,
) -> ProductItem | None:
    """Load the complete public-passport graph for one published item."""

    return db.scalar(
        select(ProductItem)
        .options(
            joinedload(ProductItem.organization),
            joinedload(ProductItem.product_model).joinedload(
                ProductModel.category,
            ),
            joinedload(ProductItem.product_model)
            .joinedload(ProductModel.template)
            .selectinload(PassportTemplate.fields),
            selectinload(ProductItem.lifecycle_events),
        )
        .where(
            ProductItem.public_id == public_id,
            ProductItem.status == "published",
        ),
    )


def get_logo_path(organization: Organization) -> str | None:
    """Build a cache-safe public path only when the organization has a logo."""

    if not organization.has_logo:
        return None

    path = f"/api/organizations/{organization.id}/logo"
    if organization.logo_updated_at is not None:
        return f"{path}?v={int(organization.logo_updated_at.timestamp())}"
    return path


def get_product_model_image_path(product_model: ProductModel) -> str | None:
    """Build a cache-safe path when the product model has an image."""

    if not product_model.has_image:
        return None

    path = f"/api/product-models/{product_model.id}/image"
    if product_model.image_updated_at is not None:
        return f"{path}?v={int(product_model.image_updated_at.timestamp())}"
    return path
