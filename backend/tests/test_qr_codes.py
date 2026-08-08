from app.qr_codes import create_qr_code_svg


def test_qr_code_svg_is_repeatable_and_contains_no_raster_image() -> None:
    public_url = "http://localhost:5173/passport/example-public-id"

    first_svg = create_qr_code_svg(public_url)
    second_svg = create_qr_code_svg(public_url)
    different_svg = create_qr_code_svg(f"{public_url}-different")

    assert first_svg == second_svg
    assert first_svg != different_svg
    assert b"<svg" in first_svg
    assert b"<path" in first_svg
    assert b"<image" not in first_svg
