import base64
import json
import sys
from io import BytesIO

import cv2
import numpy
import pytest
from PIL import Image, ImageEnhance, ImageFilter
from qrcode import QRCode

import chromaqr
import chromaqr.cli
import chromaqr.server


CHROMA_PAYLOAD = (
    b"Duarte: the colour layer works even though an ordinary scanner sees "
    b"only the project URL."
)
COMPATIBILITY_PAYLOAD = b"https://your-domain.example/chromaqr"
EXAMPLE_CHROMA_PAYLOAD = (
    b"Hi Duarte! You found the hidden ChromaQR layer. A normal scanner only "
    b"sees the self-hosted app link; colour reveals this message."
)


def make_compatible_code():
    return chromaqr.Encoder().encode_compatible(
        CHROMA_PAYLOAD,
        COMPATIBILITY_PAYLOAD
    )


def apply_channel_cast(image, factors):
    return Image.merge(
        "RGB",
        tuple(
            channel.point(
                lambda value, factor=factor: min(255, round(value * factor))
            )
            for channel, factor in zip(image.convert("RGB").split(), factors)
        ),
    )


def jpeg_round_trip(image, quality, subsampling):
    output = BytesIO()
    image.save(
        output,
        "JPEG",
        quality=quality,
        subsampling=subsampling,
    )
    output.seek(0)
    return Image.open(output).copy()


def decode_with_opencv(image):
    """Decode with OpenCV, independently of ChromaQR's pyzbar decoder."""

    rgb = numpy.asarray(image.convert("RGB"))
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    result, points, _ = cv2.QRCodeDetector().detectAndDecode(bgr)
    assert points is not None
    return result


def test_ordinary_qr_decoder_reads_compatibility_payload():
    image = make_compatible_code()

    assert decode_with_opencv(image) == COMPATIBILITY_PAYLOAD.decode("ascii")


def test_chromaqr_decoder_reads_colour_payload():
    image = make_compatible_code()
    decoder = chromaqr.Decoder()

    assert decoder.decode_compatible(image) == CHROMA_PAYLOAD
    assert decoder.decode(image) == CHROMA_PAYLOAD
    assert decoder.decode_compatibility(image) == COMPATIBILITY_PAYLOAD


def test_representative_code_uses_every_codebook_colour():
    colours = set(make_compatible_code().getdata())

    assert colours == set(
        chromaqr.Encoder.DARK_CODEBOOK + chromaqr.Encoder.LIGHT_CODEBOOK
    )


def test_ordinary_qr_is_never_fabricated_as_three_chroma_copies():
    qr = QRCode()
    qr.add_data(b"ordinary QR, not ChromaQR", optimize=0)
    qr.make(fit=True)
    image = qr.make_image(fill_color="black", back_color="white").convert("RGB")

    decoder = chromaqr.Decoder()
    assert decoder.decode(image) == b""
    assert decoder.decode_compatible(image) == b""
    assert decoder.decode_compatibility(image) == b"ordinary QR, not ChromaQR"


def test_grayscale_compatible_image_only_exposes_ordinary_layer():
    image = make_compatible_code().convert("L")

    decoder = chromaqr.Decoder()
    assert decoder.decode(image) == b""
    assert decoder.decode_compatible(image) == b""
    assert decoder.decode_compatibility(image) == COMPATIBILITY_PAYLOAD


def test_coloured_ordinary_qr_artwork_never_fabricates_chroma():
    qr = QRCode()
    qr.add_data(b"coloured ordinary QR artwork", optimize=0)
    qr.make(fit=True)
    image = qr.make_image(
        fill_color=(12, 48, 96),
        back_color=(248, 224, 168),
    ).convert("RGB")

    decoder = chromaqr.Decoder()
    assert decoder.decode(image) == b""
    assert decoder.decode_compatible(image) == b""
    assert decoder.decode_compatibility(image) == b"coloured ordinary QR artwork"


def test_readme_example_is_scannable():
    image = Image.open("assets/backward_compatible_demo.png")

    assert chromaqr.Decoder().decode(image) == EXAMPLE_CHROMA_PAYLOAD
    assert decode_with_opencv(image) == COMPATIBILITY_PAYLOAD.decode("ascii")


def test_optional_encode_argument_is_backwards_compatible_api():
    encoder = chromaqr.Encoder(error_correction="HIGH")
    image = encoder.encode(
        CHROMA_PAYLOAD,
        compatibility_data=COMPATIBILITY_PAYLOAD
    )

    assert chromaqr.Decoder().decode(image) == CHROMA_PAYLOAD
    assert decode_with_opencv(image) == COMPATIBILITY_PAYLOAD.decode("ascii")


@pytest.mark.parametrize("degradation", [
    "resize-60",
    "resize-75",
    "jpeg-85-420",
    "jpeg-90-420",
    "jpeg-95-420",
    "blur-0.8",
    "saturation-0.8",
    "saturation-1.2",
])
def test_common_degradation_sweep(degradation):
    image = make_compatible_code()
    if degradation.startswith("resize"):
        scale = int(degradation.split("-")[1]) / 100
        image = image.resize(
            (round(image.width * scale), round(image.height * scale)),
            Image.Resampling.BICUBIC,
        )
    elif degradation.startswith("jpeg"):
        quality = int(degradation.split("-")[1])
        image = jpeg_round_trip(image, quality=quality, subsampling=2)
    elif degradation.startswith("blur"):
        image = image.filter(ImageFilter.GaussianBlur(radius=0.8))
    elif degradation.startswith("saturation"):
        factor = float(degradation.split("-")[1])
        image = ImageEnhance.Color(image).enhance(factor)

    decoder = chromaqr.Decoder()
    assert decoder.decode(image) == CHROMA_PAYLOAD
    assert decoder.decode_compatibility(image) == COMPATIBILITY_PAYLOAD
    assert decode_with_opencv(image) == COMPATIBILITY_PAYLOAD.decode("ascii")


@pytest.mark.parametrize("factors", [
    (1.08, 1.0, 0.92),
    (0.92, 1.0, 1.08),
    (1.12, 1.0, 0.88),
    (0.88, 1.0, 1.12),
])
def test_white_balance_retry_recovers_warm_and_cool_casts(factors):
    image = apply_channel_cast(make_compatible_code(), factors)
    decoder = chromaqr.Decoder()

    # These casts deterministically defeat the raw fixed-codebook decision,
    # proving that the successful public decode comes from the guarded retry.
    assert decoder._decode_extracted(decoder._prepare_image(image)) is None
    assert decoder.decode_compatible(image) == CHROMA_PAYLOAD
    assert decoder.decode(image) == CHROMA_PAYLOAD
    assert decoder.decode_compatibility(image) == COMPATIBILITY_PAYLOAD
    assert decode_with_opencv(image) == COMPATIBILITY_PAYLOAD.decode("ascii")


def test_arbitrary_binary_round_trip_in_compatible_format():
    payload = bytes(range(256)) * 4 + b"\x00\xff\x80"
    image = chromaqr.Encoder().encode_compatible(payload, b"binary payload")

    assert chromaqr.Decoder().decode(image) == payload


def test_palette_luminance_is_balanced_with_strong_family_gap():
    luminance = lambda colour: sum(
        coefficient * component
        for coefficient, component in zip((0.299, 0.587, 0.114), colour)
    )
    dark = [luminance(colour) for colour in chromaqr.Encoder.DARK_CODEBOOK]
    light = [luminance(colour) for colour in chromaqr.Encoder.LIGHT_CODEBOOK]

    assert max(dark) - min(dark) < 1
    assert max(light) - min(light) < 1
    assert min(light) - max(dark) > 140


@pytest.mark.parametrize(
    "error_correction,payload_size",
    [("LOW", 1200), ("MED", 6000), ("HIGH", 1200), ("MAX", 1200)],
)
def test_high_version_and_ec_levels_keep_independent_ordinary_layer(
    error_correction, payload_size
):
    payload = (b"0123456789abcdef" * ((payload_size + 15) // 16))[:payload_size]
    image = chromaqr.Encoder(error_correction).encode_compatible(
        payload, COMPATIBILITY_PAYLOAD
    )

    assert chromaqr.Decoder().decode(image) == payload
    assert decode_with_opencv(image) == COMPATIBILITY_PAYLOAD.decode("ascii")
    assert decode_with_opencv(image.convert("L")) == \
        COMPATIBILITY_PAYLOAD.decode("ascii")


def test_black_and_white_qr_control_is_independently_scannable():
    qr = QRCode()
    qr.add_data(COMPATIBILITY_PAYLOAD, optimize=0)
    qr.make(fit=True)
    image = qr.make_image(fill_color="black", back_color="white").convert("RGB")

    assert decode_with_opencv(image) == COMPATIBILITY_PAYLOAD.decode("ascii")
    assert chromaqr.Decoder().decode(image) == b""


def test_compatible_capacity_error_is_clear():
    encoder = chromaqr.Encoder("MAX")
    with pytest.raises(ValueError, match="maximum at MAX error correction"):
        encoder.encode_compatible(
            b"x" * (encoder.compatible_max_payload_bytes + 1),
            b"ordinary",
        )


def test_cli_encodes_and_selects_compatibility_layer(tmp_path, monkeypatch, capsys):
    output_path = tmp_path / "compatible.png"
    monkeypatch.setattr(sys, "argv", [
        "chromaqr",
        "encode",
        "--text", CHROMA_PAYLOAD.decode("ascii"),
        "--compatibilityText", COMPATIBILITY_PAYLOAD.decode("ascii"),
        "--outFile", str(output_path)
    ])
    chromaqr.cli.main()

    assert chromaqr.Decoder().decode(Image.open(output_path)) == CHROMA_PAYLOAD
    assert decode_with_opencv(Image.open(output_path)) == \
        COMPATIBILITY_PAYLOAD.decode("ascii")

    monkeypatch.setattr(sys, "argv", [
        "chromaqr",
        "decode",
        "--inFile", str(output_path),
        "--layer", "compatibility"
    ])
    chromaqr.cli.main()
    assert capsys.readouterr().out.strip() == COMPATIBILITY_PAYLOAD.decode("ascii")


@pytest.fixture
def client():
    chromaqr.server.app.config["TESTING"] = True
    with chromaqr.server.app.test_client() as test_client:
        yield test_client


def test_http_api_encodes_and_decodes_both_layers(client):
    response = client.post("/encode", data={
        "data": CHROMA_PAYLOAD.decode("ascii"),
        "compatibilityData": COMPATIBILITY_PAYLOAD.decode("ascii")
    })
    assert response.status_code == 200
    encoded = json.loads(response.data)["result"].split(",", 1)[1]
    image_bytes = base64.b64decode(encoded)

    chroma_response = client.post(
        "/decode",
        data={"image": (BytesIO(image_bytes), "compatible.png")},
        content_type="multipart/form-data"
    )
    assert chroma_response.status_code == 200
    assert json.loads(chroma_response.data)["result"] == CHROMA_PAYLOAD.decode("ascii")

    compatibility_response = client.post(
        "/decode",
        data={
            "image": (BytesIO(image_bytes), "compatible.png"),
            "layer": "compatibility"
        },
        content_type="multipart/form-data"
    )
    assert compatibility_response.status_code == 200
    assert json.loads(compatibility_response.data)["result"] == \
        COMPATIBILITY_PAYLOAD.decode("ascii")
