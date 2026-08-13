from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.ai_extraction import (
    MAX_SOURCE_BYTES,
    AiExtractionProviderError,
    AiExtractionUnavailableError,
    extract_document,
)
from app.database import get_db
from app.dependencies.auth import require_product_item_member
from app.models import PassportTemplate, ProductModel, User
from app.schemas.ai_extraction import AiExtractionResponse


router = APIRouter(prefix="/api/product-models", tags=["AI extraction"])

DatabaseSession = Annotated[Session, Depends(get_db)]
ProductItemMember = Annotated[User, Depends(require_product_item_member)]


@router.post("/{model_id}/ai-extraction", response_model=AiExtractionResponse)
def extract_product_data(
    model_id: UUID,
    db: DatabaseSession,
    current_user: ProductItemMember,
    document: Annotated[UploadFile, File()],
) -> AiExtractionResponse:
    """Extract reviewable suggestions for an owned product model."""

    product_model = db.scalar(
        select(ProductModel)
        .options(
            joinedload(ProductModel.template).selectinload(
                PassportTemplate.fields,
            ),
        )
        .where(
            ProductModel.id == model_id,
            ProductModel.organization_id == current_user.organization_id,
        ),
    )
    if product_model is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product model not found",
        )
    if (
        product_model.status != "active"
        or product_model.template.status != "active"
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="AI extraction requires an active model and template",
        )

    source_data = document.file.read(MAX_SOURCE_BYTES + 1)
    if len(source_data) > MAX_SOURCE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="Source document must not exceed 10 MB",
        )
    mime_type = detect_source_content_type(source_data, document.content_type)
    if mime_type is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                "Source document must be a PDF, JPEG, PNG, WebP, HEIC, "
                "or HEIF file"
            ),
        )

    try:
        return extract_document(source_data, mime_type, product_model)
    except AiExtractionUnavailableError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI extraction is not configured",
        ) from error
    except AiExtractionProviderError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI extraction is temporarily unavailable",
        ) from error


def detect_source_content_type(
    data: bytes,
    declared_content_type: str | None,
) -> str | None:
    """Recognize supported source formats from bytes, not only filenames."""

    if data.startswith(b"%PDF-"):
        return "application/pdf"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    if len(data) >= 12 and data[4:8] == b"ftyp":
        brand = data[8:12]
        if brand in {b"heic", b"heix", b"hevc", b"hevx"}:
            return "image/heic"
        if brand in {b"mif1", b"msf1"}:
            return (
                declared_content_type
                if declared_content_type in {"image/heic", "image/heif"}
                else "image/heif"
            )
    return None
