import zlib

from PIL import Image, ImageChops, ImageOps
from pyzbar import pyzbar

from .encode import Encoder, _BASE45_ALPHABET


_BASE45_VALUES = {character: index for index, character in enumerate(_BASE45_ALPHABET)}


def _base45_decode(value):
    try:
        text = value.decode("ascii")
    except UnicodeDecodeError as error:
        raise ValueError("Base45 data is not ASCII") from error

    output = bytearray()
    offset = 0
    while offset < len(text):
        remaining = len(text) - offset
        if remaining == 1:
            raise ValueError("invalid Base45 length")
        try:
            first = _BASE45_VALUES[text[offset]]
            second = _BASE45_VALUES[text[offset + 1]]
            if remaining >= 3:
                third = _BASE45_VALUES[text[offset + 2]]
                decoded = first + second * 45 + third * 45 * 45
                if decoded > 0xFFFF:
                    raise ValueError("invalid Base45 pair")
                output.extend(divmod(decoded, 256))
                offset += 3
            else:
                decoded = first + second * 45
                if decoded > 0xFF:
                    raise ValueError("invalid Base45 byte")
                output.append(decoded)
                offset += 2
        except KeyError as error:
            raise ValueError("invalid Base45 character") from error
    return bytes(output)


class Decoder:
    """Decoder for original and format-v2 backwards-compatible ChromaQR."""

    def __init__(self, debug=False):
        self.debug = debug
        self.result = None
        self.code_quad = None

    def _prepare_image(self, image):
        if image.mode == "RGBA":
            converted_image = Image.new("RGB", image.size, (255, 255, 255))
            converted_image.paste(image, mask=image.getchannel("A"))
        else:
            converted_image = image.convert("RGB")

        if converted_image.size[0] > 1280 or converted_image.size[1] > 1280:
            converted_image.thumbnail((1280, 1280), Image.Resampling.LANCZOS)
        return converted_image

    @staticmethod
    def _otsu_threshold(image, mask=None, fallback=128):
        """Return an Otsu threshold, optionally using only pixels in a mask."""

        histogram = image.histogram(mask=mask)
        total = sum(histogram)
        if total == 0:
            return fallback

        weighted_sum = sum(index * count for index, count in enumerate(histogram))
        background_weight = 0
        background_sum = 0
        best_variance = -1
        threshold = fallback
        for index, count in enumerate(histogram):
            background_weight += count
            if background_weight == 0:
                continue
            foreground_weight = total - background_weight
            if foreground_weight == 0:
                break
            background_sum += index * count
            background_mean = background_sum / background_weight
            foreground_mean = (weighted_sum - background_sum) / foreground_weight
            variance = (
                background_weight * foreground_weight
                * (background_mean - foreground_mean) ** 2
            )
            if variance > best_variance:
                best_variance = variance
                threshold = index
        return threshold

    @staticmethod
    def _decode_one(image):
        decoded_codes = pyzbar.decode(image, symbols=[pyzbar.ZBarSymbol.QRCODE])
        return decoded_codes[0] if decoded_codes else None

    @staticmethod
    def _quad(decoded_code):
        return [
            [point.x, point.y]
            for point in decoded_code.polygon[:4]
        ]

    @staticmethod
    def _palette_image(colours):
        palette = Image.new("P", (1, 1))
        values = [component for colour in colours for component in colour]
        values.extend(list(colours[0]) * (256 - len(colours)))
        palette.putpalette(values)
        return palette

    def _extract_chroma_channels(self, converted_image):
        """
        Recover three hidden QR layers using the two luma-balanced codebooks.

        Otsu classification locks each pixel to the dark or light family, then
        Pillow's fixed-palette quantizer finds the nearest colour within that
        family. This joint RGB decision is much less sensitive to JPEG and
        resize noise than three independent channel thresholds.
        """

        grayscale = ImageOps.grayscale(converted_image)
        base_threshold = self._otsu_threshold(grayscale)
        light_mask = grayscale.point(
            lambda value: 255 if value > base_threshold else 0
        )
        dark_quantized = converted_image.quantize(
            palette=self._palette_image(Encoder.DARK_CODEBOOK),
            dither=Image.Dither.NONE,
        )
        light_quantized = converted_image.quantize(
            palette=self._palette_image(Encoder.LIGHT_CODEBOOK),
            dither=Image.Dither.NONE,
        )

        extracted_channels = []
        for channel_index in range(3):
            shift = 2 - channel_index
            lookup = [
                255 if (((index if index < 8 else 0) >> shift) & 1) else 0
                for index in range(256)
            ]
            dark_bits = dark_quantized.point(lookup, mode="L")
            light_bits = light_quantized.point(lookup, mode="L")
            extracted = Image.composite(light_bits, dark_bits, light_mask)
            extracted_channels.append(extracted)
            if self.debug:
                extracted.save("debug_compatible_{}.png".format(channel_index))
        return extracted_channels

    @staticmethod
    def _parse_frame(data, expected_index):
        try:
            fields = data.split(b":", 5)
            if len(fields) != 6:
                return None
            marker, total_length, total_crc, chunk_length, chunk_crc, body = fields
            if marker != ("CQR2{}".format("ABC"[expected_index])).encode("ascii"):
                return None
            total_length = int(total_length, 16)
            total_crc = int(total_crc, 16)
            chunk_length = int(chunk_length, 16)
            chunk_crc = int(chunk_crc, 16)
            chunk = _base45_decode(body)
        except (ValueError, IndexError):
            return None
        if len(chunk) != chunk_length:
            return None
        if (zlib.crc32(chunk) & 0xFFFFFFFF) != chunk_crc:
            return None
        return total_length, total_crc, chunk

    def _decode_extracted(self, converted_image):
        frames = []
        first_code = None
        for index, extracted in enumerate(
            self._extract_chroma_channels(converted_image)
        ):
            decoded_code = self._decode_one(extracted)
            if decoded_code is None:
                return None
            frame = self._parse_frame(decoded_code.data, index)
            if frame is None:
                return None
            frames.append(frame)
            if first_code is None:
                first_code = decoded_code

        total_lengths = {frame[0] for frame in frames}
        total_crcs = {frame[1] for frame in frames}
        if len(total_lengths) != 1 or len(total_crcs) != 1:
            return None
        result = b"".join(frame[2] for frame in frames)
        if len(result) != frames[0][0]:
            return None
        if (zlib.crc32(result) & 0xFFFFFFFF) != frames[0][1]:
            return None
        return result, self._quad(first_code)

    @staticmethod
    def _is_effectively_grayscale(image):
        red, green, blue = image.split()
        differences = (
            ImageChops.difference(red, green).getextrema()[1],
            ImageChops.difference(red, blue).getextrema()[1],
            ImageChops.difference(green, blue).getextrema()[1],
        )
        return max(differences) <= 8

    def _decode_legacy(self, converted_image):
        """Decode original ChromaQR only when its colour layers are distinct."""

        # This is the critical ambiguity guard: an ordinary/grayscale QR has
        # three identical decodable channels and is not a ChromaQR.
        if self._is_effectively_grayscale(converted_image):
            return None

        decoded_parts = []
        code_quad = None
        working_image = converted_image
        for index in range(3):
            rgb_image = ImageOps.autocontrast(working_image.split()[index])
            rgb_image = ImageOps.colorize(
                rgb_image,
                "#000000",
                "#ffffff",
                blackpoint=100,
                whitepoint=180,
            )
            decoded_code = self._decode_one(rgb_image)
            if self.debug:
                rgb_image.save("debug_{}.png".format(index))
            if decoded_code is None:
                return None
            decoded_parts.append(decoded_code.data)
            if index == 0:
                code_quad = self._quad(decoded_code)
            working_image = working_image.crop((
                decoded_code.rect.left,
                decoded_code.rect.top,
                decoded_code.rect.left + decoded_code.rect.width,
                decoded_code.rect.top + decoded_code.rect.height,
            ))

        # Also reject coloured ordinary QR artwork whose channels carry the
        # same payload. Some genuine old codes with three identical chunks are
        # inherently ambiguous and intentionally require explicit migration.
        if decoded_parts[0] == decoded_parts[1] == decoded_parts[2]:
            return None
        return b"".join(decoded_parts), code_quad

    def decode_compatible(self, image: Image) -> bytearray:
        """Decode only a framed format-v2 colour payload."""

        decoded = self._decode_extracted(self._prepare_image(image))
        if decoded is None:
            self.result = b""
            self.code_quad = None
            return b""
        self.result, self.code_quad = decoded
        return self.result

    def decode_compatibility(self, image: Image) -> bytearray:
        """Decode the ordinary QR payload from a binarized luminance layer."""

        converted_image = self._prepare_image(image)
        grayscale = ImageOps.grayscale(converted_image)
        threshold = self._otsu_threshold(grayscale)
        binary = grayscale.point(lambda value: 255 if value > threshold else 0)
        decoded_code = self._decode_one(binary)
        if decoded_code is None:
            self.result = b""
            self.code_quad = None
            return b""
        self.result = decoded_code.data
        self.code_quad = self._quad(decoded_code)
        return self.result

    def decode(self, image: Image) -> bytearray:
        """Decode format-v2 first, then an unambiguous original ChromaQR."""

        converted_image = self._prepare_image(image)
        decoded = self._decode_extracted(converted_image)
        if decoded is None:
            decoded = self._decode_legacy(converted_image)
        if decoded is None:
            self.result = b""
            self.code_quad = None
            return b""
        self.result, self.code_quad = decoded
        return self.result
