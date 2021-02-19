from flask import Flask, request
from flask_cors import CORS
from .encode import Encoder
from .decode import Decoder
from io import BytesIO
from PIL import Image
from base64 import b64encode, b64decode
import json

app = Flask("ChromaQR")
CORS(app)

@app.route("/")
def home():
    return "ChromaQR server online"

@app.route("/encode", methods=["POST"])
def encode():
    """
    Encoding endpoint for the API.
    Takes one parameter, `data`, to encode.
    """

    if "data" not in request.form.to_dict().keys():
        return json.dumps({
            "method": "encode",
            "success": False,
            "error": "please specify the data parameter containing the string to encode"
        }), 400

    data = request.form.to_dict()["data"]
    encoder = Encoder()
    image = encoder.encode(data.encode("utf-8"))
    
    output_data = BytesIO()
    image.save(output_data, "PNG")
    b64 = b64encode(output_data.getvalue())
    data_uri = u"data:image/png;base64,"+b64.decode("utf-8")

    return json.dumps({
        "method": "encode",
        "success": True,
        "error_correction": "MED",
        "result": data_uri
    })

@app.route("/decode", methods=["POST"])
def decode():
    """
    Decoding endpoint for the API.
    Takes a file upload called image.
    """

    try:
        file = request.files["image"]
        image = Image.open(file.stream)
    except:
        return json.dumps({
            "method": "decode",
            "success": False,
            "error": "no image file was recognised in your request, make sure it's called 'image'"
        })

    decoder = Decoder()
    result = decoder.decode(image).decode("utf-8")

    if result != "":
        return json.dumps({
            "method": "decode",
            "success": True,
            "result": result
        })
    else:
        return json.dumps({
            "method": "decode",
            "success": False,
            "error": "no ChromaQR code was found in the uploaded image"
        })

def run(host="0.0.0.0", port=8000):
    app.run(host, port)