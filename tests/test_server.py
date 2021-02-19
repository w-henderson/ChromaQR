import chromaqr.server
import pytest
import json
from io import BytesIO

@pytest.fixture
def client():
    chromaqr.server.app.config["TESTING"] = True
    with chromaqr.server.app.test_client() as client:
        yield client

def test_server_encode_success(client):
    """Test case for a successful encode."""

    request = {"data": "Hello from ChromaQR!"}
    
    response = client.post("/encode", data=request, follow_redirects=True)
    response_json = json.loads(response.data)

    assert response.status_code == 200
    assert list(response_json.keys()) == ["method", "success", "error_correction", "result"]
    assert response_json["method"] == "encode"
    assert response_json["success"] == True
    assert response_json["error_correction"] == "MED"
    assert type(response_json["result"]) == str

def test_server_encode_error_correction(client):
    """Test case for a successful encode with a custom error correction."""

    request = {"data": "Hello from ChromaQR!", "errorCorrection": "MAX"}
    
    response = client.post("/encode", data=request, follow_redirects=True)
    response_json = json.loads(response.data)

    assert response.status_code == 200
    assert list(response_json.keys()) == ["method", "success", "error_correction", "result"]
    assert response_json["method"] == "encode"
    assert response_json["success"] == True
    assert response_json["error_correction"] == "MAX"
    assert type(response_json["result"]) == str

def test_server_encode_error(client):
    """Test case for an erroneous encode with the wrong parameters."""

    request = {"wrong_name": "this is not right"}

    response = client.post("/encode", data=request, follow_redirects=True)
    response_json = json.loads(response.data)

    assert response.status_code == 400
    assert list(response_json.keys()) == ["method", "success", "error"]
    assert response_json["method"] == "encode"
    assert response_json["success"] == False
    assert response_json["error"] == "please specify the data parameter containing the string to encode"

def test_server_encode_invalid_format(client):
    """Test case for an erroneous encode with an invalid format."""

    request = {"data": "Hello from ChromaQR!", "format": "invalid"}

    response = client.post("/encode", data=request, follow_redirects=True)
    response_json = json.loads(response.data)

    assert response.status_code == 400
    assert list(response_json.keys()) == ["method", "success", "error"]
    assert response_json["method"] == "encode"
    assert response_json["success"] == False
    assert response_json["error"] == "unknown format, accepted formats are 'json' and 'image'"

def test_server_encode_invalid_error_correction(client):
    """Test case for an erroneous encode with an invalid error correction."""

    request = {"data": "Hello from ChromaQR!", "errorCorrection": "invalid"}

    response = client.post("/encode", data=request, follow_redirects=True)
    response_json = json.loads(response.data)

    assert response.status_code == 400
    assert list(response_json.keys()) == ["method", "success", "error"]
    assert response_json["method"] == "encode"
    assert response_json["success"] == False
    assert response_json["error"] == "invalid error correction value, valid values are LOW, MED, HIGH and MAX"

def test_server_decode_success(client):
    """Test case for a successful decode."""

    with open("tests/images/generated.png", "rb") as imageFile:
        request = {"image": (BytesIO(imageFile.read()), "generated.png")}
    
    response = client.post(
        "/decode",
        data=request,
        follow_redirects=True,
        content_type="multipart/form-data"
    )
    response_json = json.loads(response.data)

    assert response.status_code == 200
    assert list(response_json.keys()) == ["method", "success", "result"]
    assert response_json["method"] == "decode"
    assert response_json["success"] == True
    assert response_json["result"] == "Hello from ChromaQR!"

def test_server_decode_url(client):
    """Test case for a successful decode from a URL."""

    request = {"url": "https://github.com/w-henderson/ChromaQR/raw/master/tests/images/generated.png"}
    
    response = client.post(
        "/decode",
        data=request,
        follow_redirects=True,
        content_type="multipart/form-data"
    )
    response_json = json.loads(response.data)

    assert response.status_code == 200
    assert list(response_json.keys()) == ["method", "success", "result"]
    assert response_json["method"] == "decode"
    assert response_json["success"] == True
    assert response_json["result"] == "Hello from ChromaQR!"

def test_server_decode_uri(client):
    """Test case for a successful decode from a URI."""

    request = {"url": "data:image/png;base64,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"}

    response = client.post(
        "/decode",
        data=request,
        follow_redirects=True,
        content_type="multipart/form-data"
    )
    response_json = json.loads(response.data)

    assert response.status_code == 200
    assert list(response_json.keys()) == ["method", "success", "result"]
    assert response_json["method"] == "decode"
    assert response_json["success"] == True
    assert response_json["result"] == "Hello from ChromaQR!"

def test_server_decode_no_image(client):
    """Test case for an erroneous decode where no image was supplied."""

    request = {}
    
    response = client.post(
        "/decode",
        data=request,
        follow_redirects=True,
        content_type="multipart/form-data"
    )
    response_json = json.loads(response.data)

    assert response.status_code == 400
    assert list(response_json.keys()) == ["method", "success", "error"]
    assert response_json["method"] == "decode"
    assert response_json["success"] == False
    assert response_json["error"] == "no image file was recognised in your request, either upload a file with the identifier 'image' or submit a URL called 'url'"

def test_server_decode_no_code(client):
    """Test case for an erroneous decode where no ChromaQR code was found."""

    with open("tests/images/empty_image.png", "rb") as imageFile:
        request = {"image": (BytesIO(imageFile.read()), "empty_image.png")}
    
    response = client.post(
        "/decode",
        data=request,
        follow_redirects=True,
        content_type="multipart/form-data"
    )
    response_json = json.loads(response.data)

    assert response.status_code == 404
    assert list(response_json.keys()) == ["method", "success", "error"]
    assert response_json["method"] == "decode"
    assert response_json["success"] == False
    assert response_json["error"] == "no ChromaQR code was found in the uploaded image"