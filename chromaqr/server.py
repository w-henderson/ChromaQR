import base64
import binascii
import json
import re
import warnings
from io import BytesIO
from pathlib import Path

from flask import Flask, Response, render_template, request, send_file
from flask_cors import CORS
from PIL import Image, UnidentifiedImageError

from .decode import Decoder
from .encode import Encoder


_PACKAGE_DIRECTORY = Path(__file__).resolve().parent
_MAX_IMAGE_BYTES = 5 * 1024 * 1024
_MAX_IMAGE_PIXELS = 16_000_000
_DATA_URI = re.compile(
    r"^data:image/(?:png|jpeg|webp);base64,([A-Za-z0-9+/]*={0,2})$"
)

app = Flask(
    "ChromaQR",
    template_folder=str(_PACKAGE_DIRECTORY / "templates"),
    static_folder=str(_PACKAGE_DIRECTORY / "static"),
)
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024
CORS(app)


def _json_response(payload, status=200):
    return Response(
        json.dumps(payload),
        status=status,
        mimetype="application/json",
    )


def _decode_error(message, status=400):
    return _json_response({
        "method": "decode",
        "success": False,
        "error": message,
    }, status=status)


def _open_bounded_image(raw):
    if not raw or len(raw) > _MAX_IMAGE_BYTES:
        raise ValueError("image exceeds the 5 MiB decoded-byte limit")
    with warnings.catch_warnings():
        warnings.simplefilter("error", Image.DecompressionBombWarning)
        image = Image.open(BytesIO(raw))
        if image.width * image.height > _MAX_IMAGE_PIXELS:
            raise ValueError("image exceeds the 16 megapixel limit")
        image.load()
    return image.copy()


def _image_from_request():
    if "image" in request.files:
        stream = request.files["image"].stream
        raw = stream.read(_MAX_IMAGE_BYTES + 1)
        return _open_bounded_image(raw)

    value = request.form.get("dataUri", request.form.get("url"))
    if value is None:
        raise ValueError(
            "upload a file named 'image' or provide a bounded image data URI "
            "in 'dataUri'"
        )
    if value.lower().startswith(("http://", "https://")):
        raise ValueError("remote HTTP(S) image URLs are not supported")
    match = _DATA_URI.fullmatch(value)
    if match is None:
        raise ValueError("malformed or unsupported image data URI")
    encoded = match.group(1)
    if len(encoded) > ((_MAX_IMAGE_BYTES + 2) // 3) * 4:
        raise ValueError("image exceeds the 5 MiB decoded-byte limit")
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as error:
        raise ValueError("malformed image data URI") from error
    return _open_bounded_image(raw)


@app.errorhandler(413)
def request_too_large(_error):
    return _decode_error("request exceeds the 8 MiB HTTP limit", status=413)


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/demo")
def demo():
    return render_template("demo.html")


@app.route("/realtime")
def realtime():
    return render_template("realtime.html")


@app.route("/logo.png")
def logo():
    response = send_file(
        _PACKAGE_DIRECTORY / "static" / "logo.png",
        mimetype="image/png",
        max_age=0,
    )
    response.headers["Cache-Control"] = "no-store"
    return response


@app.route("/encode", methods=["POST"])
def encode():
    """Encode UTF-8 form text as original or format-v2 ChromaQR."""

    form = request.form.to_dict()
    if "data" not in form:
        return _json_response({
            "method": "encode",
            "success": False,
            "error": "please specify the data parameter containing the string to encode",
        }, status=400)

    result_mode = form.get("format", "json")
    error_correction = form.get("errorCorrection", "MED")
    if error_correction not in ["LOW", "MED", "HIGH", "MAX"]:
        return _json_response({
            "method": "encode",
            "success": False,
            "error": "invalid error correction value, valid values are LOW, MED, HIGH and MAX",
        }, status=400)
    if result_mode not in ["json", "image"]:
        return _json_response({
            "method": "encode",
            "success": False,
            "error": "unknown format, accepted formats are 'json' and 'image'",
        }, status=400)

    data = form["data"].encode("utf-8")
    compatibility_data = form.get("compatibilityData")
    if compatibility_data is not None:
        compatibility_data = compatibility_data.encode("utf-8")
    try:
        image = Encoder(error_correction=error_correction).encode(
            data,
            compatibility_data=compatibility_data,
        )
    except (TypeError, ValueError) as error:
        return _json_response({
            "method": "encode",
            "success": False,
            "error": str(error),
        }, status=400)

    output_data = BytesIO()
    image.save(output_data, "PNG")
    if result_mode == "image":
        output_data.seek(0)
        response = send_file(
            output_data,
            mimetype="image/png",
            max_age=0,
            download_name="chromaqr.png",
        )
        response.headers["Cache-Control"] = "no-store"
        return response

    data_uri = "data:image/png;base64," + base64.b64encode(
        output_data.getvalue()
    ).decode("ascii")
    return _json_response({
        "method": "encode",
        "success": True,
        "error_correction": error_correction,
        "result": data_uri,
    })


@app.route("/decode", methods=["POST"])
def decode():
    """Decode an uploaded image or bounded local image data URI."""

    try:
        image = _image_from_request()
    except (
        ValueError,
        UnidentifiedImageError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
        OSError,
    ) as error:
        return _decode_error(str(error) or "the supplied image could not be read")

    layer = request.form.get("layer", "chroma")
    if layer not in ["chroma", "compatibility"]:
        return _decode_error(
            "invalid layer, accepted values are 'chroma' and 'compatibility'"
        )

    decoder = Decoder()
    result_bytes = (
        decoder.decode_compatibility(image)
        if layer == "compatibility"
        else decoder.decode(image)
    )
    if not result_bytes:
        return _decode_error(
            "no ChromaQR code was found in the uploaded image",
            status=404,
        )
    try:
        result = result_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return _decode_error(
            "decoded payload is binary; use the Python API or CLI --outFile",
            status=422,
        )
    return _json_response({
        "method": "decode",
        "success": True,
        "result": result,
        "coordinates": decoder.code_quad,
    })


def run(host="127.0.0.1", port=8000):
    """Run Flask's development server on localhost only by default."""

    app.run(host, port)
