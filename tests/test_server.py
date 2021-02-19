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
    assert response_json["error"] == "no image file was recognised in your request, make sure it's called 'image'"

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