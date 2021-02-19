import chromaqr
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