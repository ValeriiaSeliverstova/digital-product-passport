from io import BytesIO

import cloudinary
import cloudinary.uploader

from app.config import settings


def configure_cloudinary() -> None:
    """Configure the SDK only on the backend, where credentials stay private."""

    if not all(
        (
            settings.cloudinary_cloud_name,
            settings.cloudinary_api_key,
            settings.cloudinary_api_secret,
        ),
    ):
        raise RuntimeError("Cloudinary is not configured")

    cloudinary.config(
        cloud_name=settings.cloudinary_cloud_name,
        api_key=settings.cloudinary_api_key,
        api_secret=settings.cloudinary_api_secret.get_secret_value(),
        secure=True,
    )


def upload_image(
    image_data: bytes,
    *,
    folder: str,
    public_id: str,
) -> tuple[str, str]:
    """Upload or replace an image and return its identifier and HTTPS URL."""

    configure_cloudinary()
    result = cloudinary.uploader.upload(
        BytesIO(image_data),
        folder=folder,
        public_id=public_id,
        overwrite=True,
        invalidate=True,
        resource_type="image",
    )
    return str(result["public_id"]), str(result["secure_url"])


def delete_image(public_id: str) -> None:
    """Delete an image and invalidate cached delivery copies."""

    configure_cloudinary()
    cloudinary.uploader.destroy(
        public_id,
        resource_type="image",
        invalidate=True,
    )
