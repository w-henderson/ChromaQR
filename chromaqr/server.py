from flask import Flask, Response, request, send_file
from flask_cors import CORS
from .encode import Encoder
from .decode import Decoder
from io import BytesIO
from PIL import Image
from base64 import b64encode, b64decode
import os
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
        return Response(json.dumps({
            "method": "encode",
            "success": False,
            "error": "please specify the data parameter containing the string to encode"
        }), status=400, mimetype="application/json")

    if "format" not in request.form.to_dict().keys():
        result_mode = "json"
    else:
        result_mode = request.form.to_dict()["format"]

    data = request.form.to_dict()["data"]
    encoder = Encoder()
    image = encoder.encode(data.encode("utf-8"))
    
    output_data = BytesIO()
    image.save(output_data, "png")
    b64 = b64encode(output_data.getvalue())
    data_uri = u"data:image/png;base64,"+b64.decode("utf-8")

    if result_mode == "json":
        return Response(json.dumps({
            "method": "encode",
            "success": True,
            "error_correction": "MED",
            "result": data_uri
        }), mimetype="application/json")
    elif result_mode == "image":
        output_data.seek(0)
        return send_file(output_data, mimetype="image/png", cache_timeout=0)
    else:
        return Response(json.dumps({
            "method": "encode",
            "success": False,
            "error": "unknown format, accepted formats are 'json' and 'image'"
        }), status=400, mimetype="application/json")


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
        return Response(json.dumps({
            "method": "decode",
            "success": False,
            "error": "no image file was recognised in your request, make sure it's called 'image'"
        }), status=400, mimetype="application/json")

    decoder = Decoder()
    result = decoder.decode(image).decode("utf-8")

    if result != "":
        return Response(json.dumps({
            "method": "decode",
            "success": True,
            "result": result
        }), mimetype="application/json")
    else:
        return Response(json.dumps({
            "method": "decode",
            "success": False,
            "error": "no ChromaQR code was found in the uploaded image"
        }), status=404, mimetype="application/json")

def run(host="0.0.0.0", port=8000):
    app.run(host, port)

@app.route("/demo")
def demo():
    return """
        <html>
            <meta name="viewport" content="width=device-width">
            <style>
                body {
                    font-family:Helvetica;
                    text-align:center;
                    display:flex;
                    place-items:center;
                    place-content:center;
                    flex-direction:column;
                    height:100%;
                    margin:0;
                }
            </style>
            <body>
                <h1 style="margin-top:0">ChromaQR API Demo</h1>
                <h2>Demo Encode</h2>
                <form action="/encode" method="POST" enctype="multipart/form-data">
                    <input type="text" name="data" placeholder="Text to encode" style="margin-bottom:5px" />
                    <input type="submit" /><br>
                    <input type="radio" id="json" name="format" value="json">
                    <label for="json">Return JSON (default)</label><br>
                    <input type="radio" id="image" name="format" value="image">
                    <label for="image">Return Image</label>
                </form>
                <h2>Demo Decode</h2>
                <form action="/decode" method="POST" enctype="multipart/form-data">
                    <input type="file" name="image" />
                    <input type="submit" />
                </form><br>
                <a href="https://github.com/w-henderson/ChromaQR">Visit the GitHub</a>
            </body>
        </html>
    """