import hashlib
import hmac
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.azure_devops import AzureDevOpsRequestError, get_support_work_item
from app.database import get_db
from app.models import SupportTicket
from app.schemas.support_ticket import (
    SupportTicketStatusResponse,
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

    support_ticket = db.scalar(
        select(SupportTicket).where(SupportTicket.azure_ticket_id == ticket_id),
    )
    supplied_hash = hashlib.sha256(data.tracking_code.encode()).hexdigest()
    if support_ticket is None or not hmac.compare_digest(
        supplied_hash,
        support_ticket.tracking_code_hash if support_ticket else "0" * 64,
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Support ticket or tracking code was not found",
        )

    try:
        azure_fields = get_support_work_item(ticket_id)
        ticket_status = azure_fields["System.State"]
        submitted_at = azure_fields["System.CreatedDate"]
        updated_at = azure_fields.get("System.ChangedDate")
        if not isinstance(ticket_status, str) or not isinstance(submitted_at, str):
            raise KeyError
    except (AzureDevOpsRequestError, KeyError) as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Support ticket status could not be loaded",
        ) from error

    response.headers["Cache-Control"] = "no-store"
    return SupportTicketStatusResponse(
        ticket_id=ticket_id,
        subject=support_ticket.subject,
        status=ticket_status,
        submitted_at=submitted_at,
        updated_at=updated_at if isinstance(updated_at, str) else None,
    )
