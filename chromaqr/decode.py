from PIL import Image, ImageEnhance, ImageOps
from pyzbar import pyzbar

"""
Base decoder for QR codes.
Currently cannot be customised.
"""
class Decoder:
    def __init__(self, debug=False):
        self.debug = debug

    def decode(self, image: Image) -> bytearray:
        decoded_bytes = b""

        if image.size[0] > 800 or image.size[1] > 800:
            image.thumbnail((800, 800))

        for i in range(3):
            rgb_image = ImageOps.colorize(image.split()[i], "#000000", "#ffffff", blackpoint=100, whitepoint=180)
            decoded_codes = pyzbar.decode(rgb_image, symbols=[pyzbar.ZBarSymbol.QRCODE])

            if self.debug:
                rgb_image.save("debug_{}.png".format(i))

            if len(decoded_codes) == 0:
                return b""

            decoded_code = decoded_codes[0]
            decoded_bytes += decoded_code.data
            image = image.crop((
                decoded_code.rect.left,
                decoded_code.rect.top,
                decoded_code.rect.left + decoded_code.rect.width,
                decoded_code.rect.top + decoded_code.rect.height,
            ))

        return decoded_bytes