from PIL import Image, ImageEnhance, ImageOps
from pyzbar import pyzbar

"""
Base decoder for QR codes.
Currently cannot be customised.
"""
class Decoder:
    def __init__(self):
        return

    def decode(self, image: Image) -> bytearray:
        decoded_bytes = b""

        if image.size[0] > 800 or image.size[1] > 800:
            image.thumbnail((800, 800))

        for i in range(3):
            rgb_image = ImageOps.colorize(image.split()[i], "#000000", "#ffffff", blackpoint=100, whitepoint=180)
            decoded_codes = pyzbar.decode(rgb_image, symbols=[pyzbar.ZBarSymbol.QRCODE])
            decoded_bytes += decoded_codes[0].data
            image = image.crop((
                decoded_codes[0].rect.left,
                decoded_codes[0].rect.top,
                decoded_codes[0].rect.left + decoded_codes[0].rect.width,
                decoded_codes[0].rect.top + decoded_codes[0].rect.height,
            ))

        return decoded_bytes