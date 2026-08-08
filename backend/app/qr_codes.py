from io import BytesIO

import qrcode
from qrcode.image.svg import SvgPathImage


def create_qr_code_svg(public_url: str) -> bytes:
    """Create a scalable QR code containing only the public passport URL."""

    qr_code = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr_code.add_data(public_url)
    qr_code.make(fit=True)

    image = qr_code.make_image(image_factory=SvgPathImage)
    output = BytesIO()
    image.save(output)
    return output.getvalue()
