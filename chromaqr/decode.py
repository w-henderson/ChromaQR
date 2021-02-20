from PIL import Image, ImageEnhance, ImageOps
from pyzbar import pyzbar

class Decoder:
    """
    Base decoder for QR codes.
    Currently cannot be customised.
    """

    def __init__(self, debug=False):
        self.debug = debug
        self.result = None
        self.code_quad = None

    def decode(self, image: Image) -> bytearray:
        """
        Decode the given PIL Image containing a ChromaQR code into a bytearray.
        If no QR code can be found, an empty bytearray will be returned.
        
        If the `Decoder` object has the property `debug` set to `True`, the program will save the processed image for each of the codes.
        """

        decoded_bytes = b""

        if image.mode == "RGBA":
            converted_image = Image.new("RGB", image.size, (255, 255, 255))
            mask = image.split()[3]
            mask = ImageOps.colorize(mask, "#000000", "#ffffff", blackpoint=254, whitepoint=255)
            mask = mask.convert("1")
            converted_image.paste(image, mask=mask)
        else:
            converted_image = image

        if converted_image.size[0] > 1280 or converted_image.size[1] > 1280:
            converted_image.thumbnail((min(1280, converted_image.size[0]), min(1280, converted_image.size[1])))

        code_quad = None

        for i in range(3):
            rgb_image = ImageOps.autocontrast(converted_image.split()[i])
            rgb_image = ImageOps.colorize(rgb_image, "#000000", "#ffffff", blackpoint=100, whitepoint=180)
            decoded_codes = pyzbar.decode(rgb_image, symbols=[pyzbar.ZBarSymbol.QRCODE])

            if self.debug:
                rgb_image.save("debug_{}.png".format(i))

            if len(decoded_codes) == 0:
                return b""

            decoded_code = decoded_codes[0]
            decoded_bytes += decoded_code.data
            converted_image = converted_image.crop((
                decoded_code.rect.left,
                decoded_code.rect.top,
                decoded_code.rect.left + decoded_code.rect.width,
                decoded_code.rect.top + decoded_code.rect.height,
            ))

            if i == 0:
                code_quad = [
                    [decoded_code.polygon[0].x, decoded_code.polygon[0].y],
                    [decoded_code.polygon[1].x, decoded_code.polygon[1].y],
                    [decoded_code.polygon[2].x, decoded_code.polygon[2].y],
                    [decoded_code.polygon[3].x, decoded_code.polygon[3].y]
                ]

        self.result = decoded_bytes
        self.code_quad = code_quad
        return decoded_bytes