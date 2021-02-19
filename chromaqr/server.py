from flask import Flask, Response, request, send_file, render_template
from flask_cors import CORS
from .encode import Encoder
from .decode import Decoder
from io import BytesIO
from PIL import Image
from base64 import b64encode, b64decode
import os
import json
import urllib.request

absolute_directory = __file__.replace("\\server.py", "")
app = Flask("ChromaQR", template_folder=f"{absolute_directory}\\templates")
CORS(app)

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/demo")
def demo():
    return render_template("demo.html")

@app.route("/logo.png")
def logo():
    return send_file(f"{absolute_directory}\\..\\tests\\images\\generated.png")

@app.route("/encode", methods=["POST"])
def encode():
    """
    Encoding endpoint for the API.
    Takes one parameter, `data`, to encode.
    """

    form = request.form.to_dict()

    if "data" not in form.keys():
        return Response(json.dumps({
            "method": "encode",
            "success": False,
            "error": "please specify the data parameter containing the string to encode"
        }), status=400, mimetype="application/json")

    if "format" not in form.keys():
        result_mode = "json"
    else:
        result_mode = form["format"]

    if "errorCorrection" not in form.keys():
        error_correction = "MED"
    elif form["errorCorrection"] in ["LOW", "MED", "HIGH", "MAX"]:
        error_correction = form["errorCorrection"]
    else:
        return Response(json.dumps({
            "method": "encode",
            "success": False,
            "error": "invalid error correction value, valid values are LOW, MED, HIGH and MAX"
        }), status=400, mimetype="application/json")        

    data = form["data"]
    encoder = Encoder(error_correction=error_correction)
    image = encoder.encode(data.encode("utf-8"))
    
    output_data = BytesIO()
    image.save(output_data, "png")
    b64 = b64encode(output_data.getvalue())
    data_uri = u"data:image/png;base64,"+b64.decode("utf-8")

    if result_mode == "json":
        return Response(json.dumps({
            "method": "encode",
            "success": True,
            "error_correction": error_correction,
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
    Takes a file upload called `image` or a URL pointing to an image called `url`.
    """

    try:
        if "url" in request.form.to_dict().keys():
            response = urllib.request.urlopen(request.form.to_dict()["url"])
            image = Image.open(BytesIO(response.read()))
        else:    
            file = request.files["image"]
            image = Image.open(file.stream)
    except:
        return Response(json.dumps({
            "method": "decode",
            "success": False,
            "error": "no image file was recognised in your request, either upload a file with the identifier 'image' or submit a URL called 'url'"
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