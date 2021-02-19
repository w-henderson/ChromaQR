# Documentation

## CLI

### Encoding
To encode with the CLI, you must either pass the `--inFile` parameter containing the path to a file to encode, or the `--text` parameter containing text to encode. You must also pass the `--outFile` parameter containing the path to the output image file. The image will always be a PNG even if you specify a different file type. You may optionally pass the `--errorCorrection` parameter with one of the values `LOW`, `MED`, `HIGH`, or `MAX`, which will change the error correction level on the output ChromaQR code. This defaults to `MED`.

**Examples:**
```sh
$ chromaqr encode --text "Hello from ChromaQR!" --outFile "demo.png"

$ chromaqr encode --inFile "beeMovieScript.txt" --outFile "demo.png"

$ chromaqr encode --text "Hello from ChromaQR!" --errorCorrection "HIGH"
```

### Decoding
To decode with the CLI, you must pass the `--inFile` parameter containing the path to the input image file. You may also optionally use the `--outFile` parameter to write the decoded content into a specified file path, otherwise the result will be printed to the console. Another optional parameter is `--debug`, which is a flag indicating to save the image being processed at each step of the decoding process. This should only be used for debugging.

**Examples:**
```sh
$ chromaqr decode --inFile "demo.png"
Hello from ChromaQR!

$ chromaqr decode --inFile "demo.png" --outFile "beeMovieScript.txt"
```

### Hosting a server
This leads on to the next part of the documentation, but hosting a server is done with the command `chromaqr serve`. Optionally, you can pass the `--port` parameter to specify which port to serve on, and this default to 8000.

**Example:**
```sh
$ chromaqr serve --port 80
```

## API

The HTTP API is another way to interact with ChromaQR codes. You can try it out at the [demo page](https://chromaqr.herokuapp.com/demo).

### Encoding
To encode with the API, send a POST request to the `/encode` endpoint (on my Heroku instance this will be `https://chromaqr.herokuapp.com/encode`) with the form parameter `data` set to the data you wish to encode. You can pass the `errorCorrection` optional parameter with one of the values `LOW`, `MED`, `HIGH`, or `MAX` to specify the error correction to use. You can also pass the `format` optional parameter to indicate how you want your result returned. By default, it is set to `json`, which returns a JSON string. You can change it to `image` which just serves the image instead.

**Examples with `curl`:**
```sh
$ curl --data data="Hello from ChromaQR!" https://chromaqr.herokuapp.com/encode
{
    "method": "encode",
    "success": true,
    "error_correction": "MED",
    "result": "data:image/png;base64,... data URI here"
}

$ curl --data "data='Hello from ChromaQR!'&format=image" https://chromaqr.herokuapp.com/encode --output "demo.png"

$ curl --data "data='Hello from ChromaQR!'&errorCorrection=MAX" https://chromaqr.herokuapp.com/encode
{
    "method": "encode",
    "success": true,
    "error_correction": "MAX",
    "result": "data:image/png;base64,... data URI here"
}
```

### Decoding
To decode with the API, send a POST request to the `/decode` endpoint (on my Heroku instance this will be `https://chromaqr.herokuapp.com/decode`) with the form file `image` set to the image file you wish to decode. If an error occurs, this is sent.

**Example with `curl`:**
```sh
$ curl -F image=@demo.png https://chromaqr.herokuapp.com/decode
{
    "method": "decode",
    "success": true,
    "result": "Hello from ChromaQR!"
}

$ curl -F image=@bad_image.png https://chromaqr.herokuapp.com/encode
{
    "method": "decode",
    "success": false,
    "error": "descriptive error message here"
}
```
## Python Package

### Encoding
```py
from chromaqr import Encoder # Import ChromaQR

encoder = Encoder(error_correction="MED") # Initialise the encoder by optionally specifying the error correction level
image = encoder.encode(b"Hello from ChromaQR!") # Encode the bytes into a PIL image
image.save("demo.png") # Save the PIL image to disk (not part of ChromaQR)
```

### Decoding
```py
from chromaqr import Decoder # Import ChromaQR
from PIL import Image # Import PIL

decoder = Decoder() # Initialise the decoder
image = Image.open("demo.png") # Open the PIL image
result = decoder.decode(image) # Decode the PIL image into bytes
print(result) # Print the bytes
```