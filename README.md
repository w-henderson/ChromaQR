<p align="center">
    <img src="tests/images/generated.png"><br>
    <img src="https://img.shields.io/github/workflow/status/w-henderson/ChromaQR/ChromaQR-Tests?style=for-the-badge" style="margin-right: 5px">
    <img src="https://img.shields.io/badge/python-3-blue?style=for-the-badge&logo=python" style="margin-right: 5px">
    <img src="https://img.shields.io/badge/license-MIT-green?style=for-the-badge" style="margin-right: 5px">
    <img src="https://img.shields.io/badge/colour-chroma-red?style=for-the-badge">
</p>

# ChromaQR
A traditional QR code allows for a maximum of just [2953 bytes](https://www.qrcode.com/en/about/version.html) to be encoded, as it only uses black and white colours. I saw an easy upgrade here: why not use the three RGB colour channels separately to triple the storage to 8859 bytes? So that's what ChromaQR does, in the form of a CLI, HTTP API, and Python package.

## Quick Start with the CLI
- Install the Python package with `pip install git+git://github.com/w-henderson/ChromaQR.git#egg=ChromaQR`.
- You can now encode ChromaQR codes with `chromaqr encode --text "Some text here" --outFile encoded.png` or `chromaqr encode --inFile bigText.txt --outFile encoded.png`.
- You can decode ChromaQR codes with `chromaqr decode --inFile encoded.png` to print the decoded text to the console or `chromaqr decode --inFile encoded.png --outFile decoded.txt`.

## Quick Start with the API
To try out the API easily from your browser, visit the [demo page](https://chromaqr.herokuapp.com/demo). If you want to try scanning with your device's camera, you can try the [realtime demo](https://chromaqr.herokuapp.com/realtime).

To encode some text with the API, make a POST request to `https://chromaqr.herokuapp.com/encode` (or wherever you host your own instance) with the form parameter `data` set to the text you want to encode. You'll receive a JSON response that looks like this:
```json
{
    "method": "encode",
    "success": true,
    "error_correction": "MED",
    "result": "data:image/png;base64,... data URI here"
}
```
To decode an image, make a POST request to, you guessed it, `https://chromaqr.herokuapp.com/decode` (or wherever you host your own instance) with the form file `image` set to the image file you want to decode. If successful, you'll receive a JSON response that looks like this:
```json
{
    "method": "decode",
    "success": true,
    "result": "decoded text from the ChromaQR code here"
}
```

**Visit [DOCUMENTATION.md](DOCUMENTATION.md) for more information on everything.**

## How does ChromaQR work?
ChromaQR simply splits the data you're trying to encode into three chunks, then converts each of the three chunks into a regular QR code. These three QR codes are then treated as the red, green and blue channels of an image, which are then combined into the final ChromaQR code. To decode, this process is performed in reverse, but due to the nature of cameras, red, green and blue are not necessarily equal so additional processing is performed to ensure each of the three regular QR codes can be decoded properly.

## Benefits of ChromaQR
Imagine, if you will, that you were trying to fit as much of the Bee Movie script into a QR code as possible. With a traditional QR code, you can only fit the first 5 minutes and 44 seconds even after turning error correction all the way down. On the other hand, with a ChromaQR code, you can cram in a whopping 21 minutes and 3 seconds into the same space, without applying any additional compression. Alongside this, ChromaQR codes are just as easy to scan as traditional QR codes.

| 5:44 of the Bee Movie script | 21:03 of the Bee Movie script |
| --- | --- |
| <img src="assets/biggest_possible_qrcode.png" width=300> | <img src="assets/biggest_possible_chromaqrcode.png" width=300>