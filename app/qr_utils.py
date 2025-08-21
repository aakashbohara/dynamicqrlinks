import base64
from io import BytesIO

import qrcode
from qrcode.constants import ERROR_CORRECT_H


def generate_qr_base64(data: str) -> str:
    qr = qrcode.QRCode(
        version=1, box_size=10, border=4,
        error_correction=ERROR_CORRECT_H
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buf = BytesIO()
    img.save(buf)
    return base64.b64encode(buf.getvalue()).decode()
