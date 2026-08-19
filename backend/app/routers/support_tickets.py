import hashlib
import hmac
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.azure_devops import (
    AzureDevOpsNotConfiguredError,
    AzureDevOpsRequestError,
    add_support_work_item_comment,
    customer_safe_comment,
    get_support_work_item,
    get_support_work_item_comments,
    is_closed_support_work_item,
)
from app.database import get_db
from app.models import ProductItem, SupportTicket
from app.schemas.support_ticket import (
    SupportTicketStatusResponse,
    SupportTicketReplyRequest,
    SupportTicketTrackRequest,
)


router = APIRouter(prefix="/api/support-tickets", tags=["support tickets"])
DatabaseSession = Annotated[Session, Depends(get_db)]


@router.post("/{ticket_id}/track", response_model=SupportTicketStatusResponse)
def track_support_ticket(
    ticket_id: int,
    data: SupportTicketTrackRequest,
    db: DatabaseSession,
    response: Response,
) -> SupportTicketStatusResponse:
    """Return safe ticket status after verifying the emailed tracking code."""

    support_ticket, product_public_id = _verified_support_ticket(
        ticket_id,
        data.tracking_code,
        data.product_public_id,
        db,
    )

    try:
        azure_fields = get_support_work_item(ticket_id)
        ticket_status = azure_fields["System.State"]
        submitted_at = azure_fields["System.CreatedDate"]
        updated_at = azure_fields.get("System.ChangedDate")
        azure_comments = get_support_work_item_comments(ticket_id)
        if not isinstance(ticket_status, str) or not isinstance(submitted_at, str):
            raise KeyError
    except (
        AzureDevOpsNotConfiguredError,
        AzureDevOpsRequestError,
        KeyError,
    ) as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Support ticket status could not be loaded",
        ) from error

    response.headers["Cache-Control"] = "no-store"
    ticket_is_closed = is_closed_support_work_item(ticket_status)
    safe_updated_at = updated_at if isinstance(updated_at, str) else None
    return SupportTicketStatusResponse(
        ticket_id=ticket_id,
        subject=support_ticket.subject,
        status=ticket_status,
        is_closed=ticket_is_closed,
        submitted_at=submitted_at,
        updated_at=safe_updated_at,
        closed_at=safe_updated_at if ticket_is_closed else None,
        product_public_id=product_public_id,
        comments=[
            safe_comment
            for comment in azure_comments
            if isinstance(comment, dict)
            and (safe_comment := customer_safe_comment(comment)) is not None
        ],
    )


@router.post("/{ticket_id}/comments", status_code=status.HTTP_204_NO_CONTENT)
def reply_to_support_ticket(
    ticket_id: int,
    data: SupportTicketReplyRequest,
    db: DatabaseSession,
) -> Response:
    """Verify the private code and add a customer reply in Azure DevOps."""

    _verified_support_ticket(
        ticket_id,
        data.tracking_code,
        data.product_public_id,
        db,
    )
    try:
        azure_fields = get_support_work_item(ticket_id)
        ticket_status = azure_fields["System.State"]
        if not isinstance(ticket_status, str):
            raise KeyError
        if is_closed_support_work_item(ticket_status):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Closed support tickets cannot receive new messages",
            )
        add_support_work_item_comment(ticket_id=ticket_id, message=data.message)
    except HTTPException:
        raise
    except (AzureDevOpsRequestError, KeyError) as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Support ticket status could not be verified",
        ) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _verified_support_ticket(
    ticket_id: int,
    tracking_code: str,
    product_public_id: UUID | None,
    db: Session,
) -> tuple[SupportTicket, UUID]:
    """Return a local ticket only when its private tracking code matches."""

    row = db.execute(
        select(SupportTicket, ProductItem.public_id)
        .join(ProductItem, SupportTicket.product_item_id == ProductItem.id)
        .where(SupportTicket.azure_ticket_id == ticket_id),
    ).one_or_none()
    support_ticket = row[0] if row is not None else None
    actual_product_public_id = row[1] if row is not None else None
    supplied_hash = hashlib.sha256(tracking_code.encode()).hexdigest()
    if support_ticket is None or not hmac.compare_digest(
        supplied_hash,
        support_ticket.tracking_code_hash if support_ticket else "0" * 64,
    ) or (
        product_public_id is not None
        and product_public_id != actual_product_public_id
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket number or tracking code is invalid",
        )
    return support_ticket, actual_product_public_id
