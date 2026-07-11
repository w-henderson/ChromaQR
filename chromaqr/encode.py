import math
import zlib
from enum import Enum

from PIL import Image
from qrcode import QRCode, constants
from qrcode.exceptions import DataOverflowError


# Error correction: LOW, MEDIUM, HIGH or MAX.
ErrorCorrection = Enum("ErrorCorrection", "LOW MED HIGH MAX")

# RFC 9285 Base45 uses only QR alphanumeric characters.  Encoding framed
# payloads this way avoids zbar's implementation-dependent transcoding of
# arbitrary QR byte-mode data while retaining almost all byte-mode capacity.
_BASE45_ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ $%*+-./:"


def _base45_encode(data):
    output = []
    for offset in range(0, len(data), 2):
        if offset + 1 < len(data):
            value = data[offset] * 256 + data[offset + 1]
            output.extend((
                _BASE45_ALPHABET[value % 45],
                _BASE45_ALPHABET[(value // 45) % 45],
                _BASE45_ALPHABET[value // (45 * 45)],
            ))
        else:
            value = data[offset]
            output.extend((
                _BASE45_ALPHABET[value % 45],
                _BASE45_ALPHABET[value // 45],
            ))
    return "".join(output).encode("ascii")


class Encoder:
    """Encoder for original and backwards-compatible ChromaQR codes."""

    FORMAT_VERSION = 2
    FRAME_PREFIX = "CQR2"
    FRAME_HEADER_CHARS = 42

    # Version 40 QR alphanumeric capacities. The compatible colour payload is
    # framed as Base45 and therefore uses QR alphanumeric mode.
    ALPHANUMERIC_CAPACITY = {
        ErrorCorrection.LOW: 4296,
        ErrorCorrection.MED: 3391,
        ErrorCorrection.HIGH: 2420,
        ErrorCorrection.MAX: 1852,
    }

    # Eight points on an almost constant Rec.601-luminance plane. Light colours
    # are exact RGB inverses. Dark luma: 54.7..55.3; light: 199.7..200.3.
    # Adjacent colours are at least 42.6 RGB units apart and the luma-family gap
    # is over 144, leaving a clean ordinary QR layer after grayscale conversion.
    DARK_CODEBOOK = (
        (105, 30, 50),
        (90, 45, 13),
        (55, 66, 0),
        (20, 80, 20),
        (5, 80, 60),
        (20, 65, 97),
        (55, 44, 110),
        (90, 30, 90),
    )
    LIGHT_CODEBOOK = tuple(
        tuple(255 - component for component in colour)
        for colour in DARK_CODEBOOK
    )

    def __init__(self, error_correction="MED"):
        try:
            self.error_correction = ErrorCorrection[error_correction]
        except KeyError as error:
            raise ValueError(
                "error_correction must be LOW, MED, HIGH, or MAX"
            ) from error

    @property
    def _qr_error_correction(self):
        return {
            ErrorCorrection.LOW: constants.ERROR_CORRECT_L,
            ErrorCorrection.MED: constants.ERROR_CORRECT_M,
            ErrorCorrection.HIGH: constants.ERROR_CORRECT_Q,
            ErrorCorrection.MAX: constants.ERROR_CORRECT_H,
        }[self.error_correction]

    @staticmethod
    def _require_bytes(data, name):
        if not isinstance(data, (bytes, bytearray, memoryview)):
            raise TypeError("{} must be bytes-like".format(name))
        return bytes(data)

    def _split_data(self, data):
        section_length = math.ceil(len(data) / 3)
        return [
            data[0:section_length],
            data[section_length:section_length * 2],
            data[section_length * 2:],
        ]

    def _make_code(self, data, version=None):
        qr_code = QRCode(
            version=version,
            error_correction=self._qr_error_correction,
        )
        qr_code.add_data(data, optimize=0)
        qr_code.make(fit=True)
        return qr_code

    def _make_codes_at_same_version(self, payloads, error_message=None):
        try:
            target_version = max(
                self._make_code(payload).version for payload in payloads
            )
            return [
                self._make_code(payload, version=target_version)
                for payload in payloads
            ]
        except DataOverflowError as error:
            raise ValueError(error_message or (
                "payload exceeds QR version 40 capacity at {} error correction"
                .format(self.error_correction.name)
            )) from error

    @classmethod
    def _base45_length(cls, byte_length):
        return 3 * (byte_length // 2) + 2 * (byte_length % 2)

    @property
    def compatible_max_payload_bytes(self):
        """Maximum colour payload bytes for this EC level (three channels)."""

        available = (
            self.ALPHANUMERIC_CAPACITY[self.error_correction]
            - self.FRAME_HEADER_CHARS
        )
        # Invert Base45's exact 2-byte -> 3-character expansion.
        pairs, remainder = divmod(available, 3)
        per_channel = pairs * 2 + (1 if remainder >= 2 else 0)
        return per_channel * 3

    def _frame_payload(self, data):
        maximum = self.compatible_max_payload_bytes
        if len(data) > maximum:
            raise ValueError(
                "compatible colour payload is {} bytes; maximum at {} error "
                "correction is {} bytes including framing overhead"
                .format(len(data), self.error_correction.name, maximum)
            )

        total_crc = zlib.crc32(data) & 0xFFFFFFFF
        framed = []
        for index, chunk in enumerate(self._split_data(data)):
            header = (
                "{}{}:{:08X}:{:08X}:{:08X}:{:08X}:".format(
                    self.FRAME_PREFIX,
                    "ABC"[index],
                    len(data),
                    total_crc,
                    len(chunk),
                    zlib.crc32(chunk) & 0xFFFFFFFF,
                )
            ).encode("ascii")
            assert len(header) == self.FRAME_HEADER_CHARS
            framed.append(header + _base45_encode(chunk))
        return framed

    def encode(self, data: bytearray, compatibility_data=None) -> Image:
        """
        Encode bytes into a ChromaQR code and return a PIL Image.

        With no ``compatibility_data`` this retains the original three-channel
        format. Supplying ``compatibility_data`` creates format-v2: an ordinary
        QR luminance layer plus a framed, integrity-checked colour payload.
        """

        data = self._require_bytes(data, "data")
        if compatibility_data is not None:
            return self.encode_compatible(data, compatibility_data)

        if any(value > 0x7F for value in data):
            raise ValueError(
                "original format accepts 7-bit ASCII bytes only because legacy "
                "zbar decoders transcode high bytes; use compatible format for "
                "arbitrary bytes"
            )

        codes = self._make_codes_at_same_version(self._split_data(data))
        code_images = [
            code.make_image(fill_color="black", back_color="white").convert("L")
            for code in codes
        ]
        return Image.merge("RGB", code_images)

    def encode_compatible(self, data: bytearray, compatibility_data: bytearray) -> Image:
        """Encode a format-v2 backwards-compatible, two-layer ChromaQR code."""

        data = self._require_bytes(data, "data")
        compatibility_data = self._require_bytes(
            compatibility_data, "compatibility_data"
        )
        if any(value > 0x7F for value in compatibility_data):
            raise ValueError(
                "compatibility_data must be 7-bit ASCII for consistent ordinary "
                "QR decoder behaviour"
            )
        framed_channels = self._frame_payload(data)
        error_message = (
            "payload exceeds QR version 40 capacity at {} error correction; "
            "compatible colour maximum is {} bytes and the ordinary payload "
            "must also fit one QR code"
        ).format(
            self.error_correction.name,
            self.compatible_max_payload_bytes,
        )
        codes = self._make_codes_at_same_version(
            [compatibility_data] + framed_channels,
            error_message=error_message,
        )
        compatibility_code = codes[0]
        chroma_codes = codes[1:]

        compatibility_image = compatibility_code.make_image(
            fill_color="black", back_color="white"
        ).convert("L")
        chroma_images = [
            code.make_image(fill_color="black", back_color="white").convert("L")
            for code in chroma_codes
        ]

        # Hidden-channel white/black values form a three-bit palette index.
        channel_pixels = [image.load() for image in chroma_images]
        base_pixels = compatibility_image.load()
        output = Image.new("RGB", compatibility_image.size)
        output_pixels = output.load()
        for y in range(output.height):
            for x in range(output.width):
                palette_index = (
                    (1 if channel_pixels[0][x, y] > 127 else 0) << 2
                    | (1 if channel_pixels[1][x, y] > 127 else 0) << 1
                    | (1 if channel_pixels[2][x, y] > 127 else 0)
                )
                codebook = (
                    self.DARK_CODEBOOK
                    if base_pixels[x, y] < 128
                    else self.LIGHT_CODEBOOK
                )
                output_pixels[x, y] = codebook[palette_index]

        return output
