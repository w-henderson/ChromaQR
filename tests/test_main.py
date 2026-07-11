import chromaqr
import pytest
from PIL import Image

def test_generated_decode():
    decoder = chromaqr.Decoder()
    assert decoder.decode(Image.open("tests/images/generated.png")) == b"Hello from ChromaQR!"

def test_photo_decode():
    decoder = chromaqr.Decoder()
    assert decoder.decode(Image.open("tests/images/photo.jpg")) == b"Hello from ChromaQR!"

def test_encode_decode():
    encoder = chromaqr.Encoder()
    decoder = chromaqr.Decoder()

    stringToEncode = b"Hello from ChromaQR!"

    encoded = encoder.encode(stringToEncode)
    decoded = decoder.decode(encoded)

    assert decoded == stringToEncode


def test_original_encoder_rejects_high_bytes_instead_of_corrupting_them():
    with pytest.raises(ValueError, match="7-bit ASCII"):
        chromaqr.Encoder().encode(b"\x80\xff")

    with pytest.raises(ValueError, match="compatibility_data must be 7-bit ASCII"):
        chromaqr.Encoder().encode_compatible(b"binary is fine \xff", "é".encode())
