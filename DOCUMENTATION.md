# ChromaQR documentation

## Formats and decoding rules

ChromaQR supports two formats:

1. **Format-v2 compatible (recommended):** dark/light module families are an ordinary standards-compliant QR payload. Eight nearly equal-luminance colours inside each family encode three additional QR bits per module. Each colour channel contains a `CQR2A`, `CQR2B`, or `CQR2C` frame with the format version, channel identity, total/chunk lengths, and total/chunk CRC-32. Payload bytes are Base45 encoded into QR alphanumeric mode, avoiding zbar's platform-dependent byte transcoding.
2. **Original legacy:** three monochrome QR images are merged as RGB channels. It has more theoretical LOW capacity but no ordinary-scanner layer.

`Decoder.decode()` accepts a format-v2 payload only after all three markers, lengths, identities, and CRCs validate. It then tries the original decoder only when the source is genuinely chromatic and the three decoded parts differ. Therefore ordinary QR and grayscale compatible images return `b""` rather than a fabricated triple-repeated payload. The intentional trade-off is that old codes with identical data in all three chunks are ambiguous and are rejected.

`Decoder.decode_compatible()` accepts format-v2 only. `Decoder.decode_compatibility()` Otsu-binarizes luminance and returns any ordinary QR payload, including the compatibility layer.

## Native prerequisite and installation

Python 3.9 or newer is supported. Install zbar before the Python package:

```sh
# Debian/Ubuntu
sudo apt-get update && sudo apt-get install libzbar0

# macOS
brew install zbar

pip install "git+https://github.com/w-henderson/ChromaQR.git#egg=ChromaQR"
```

Windows `pyzbar` wheels generally include zbar DLLs. Consult the [pyzbar package page](https://pypi.org/project/pyzbar/) for platform troubleshooting.

## CLI

General form:

```text
chromaqr {encode,decode,serve} [options]
```

### Encode

Required:

- one of `--text TEXT` or `--inFile PATH`; format-v2 hidden input is binary-safe, while original mode requires 7-bit ASCII
- `--outFile PATH`

Optional:

- `--compatibilityText TEXT` or `--compatibilityInFile PATH`: selecting either creates format-v2 and supplies its 7-bit ASCII ordinary layer
- `--errorCorrection LOW|MED|HIGH|MAX` (default `MED`)

Examples:

```sh
chromaqr encode --text "Hello from ChromaQR!" --outFile original.png
chromaqr encode --inFile payload.bin \
  --compatibilityText "https://your-domain.example/chromaqr" \
  --errorCorrection HIGH --outFile compatible.png
```

`--inFile` and `--compatibilityInFile` are byte-preserving. The output is determined by Pillow from the output filename; use `.png` because lossless storage is most reliable.

### Decode

Required:

- `--inFile IMAGE`

Optional:

- `--layer chroma|compatibility` (default `chroma`)
- `--outFile PATH`: writes exact decoded bytes
- `--debug`: writes intermediate channel extraction images

Examples:

```sh
chromaqr decode --inFile compatible.png
chromaqr decode --inFile compatible.png --layer compatibility
chromaqr decode --inFile compatible.png --outFile payload.bin
```

Console output is decoded as text. Use `--outFile` for arbitrary binary payloads.

### Development server

```sh
chromaqr serve --port 8000
```

This binds Flask's development server to `127.0.0.1`. It is **localhost development only**, not a public production deployment. Use a production WSGI server and TLS reverse proxy for public hosting. Add authentication, authorization, rate limiting, request logging, and tighter platform limits according to your threat model.

## Python API

### `Encoder(error_correction="MED")`

`error_correction` must be `LOW`, `MED`, `HIGH`, or `MAX`.

```python
from chromaqr import Encoder

encoder = Encoder("MED")
legacy_image = encoder.encode(b"legacy ASCII bytes")
compatible_image = encoder.encode(
    b"hidden bytes\x00\xff",
    compatibility_data=b"ordinary QR text",
)
# Equivalent explicit spelling:
compatible_image = encoder.encode_compatible(
    b"hidden bytes\x00\xff",
    b"ordinary QR text",
)
compatible_image.save("compatible.png")
```

`data` and `compatibility_data` must be bytes-like (`bytes`, `bytearray`, or `memoryview`). Format-v2 framing makes arbitrary hidden `data` bytes round-trip. New original-format encoding is explicitly restricted to 7-bit ASCII because zbar's historical QR byte-mode conversion can silently alter bytes above `0x7f`; such input raises `ValueError` with guidance to use compatible mode. The ordinary `compatibility_data` is also restricted to 7-bit ASCII for consistent conventional-reader output. `encoder.compatible_max_payload_bytes` reports the exact colour-layer maximum for the selected error-correction level. Inputs above capacity raise `ValueError`; wrong types raise `TypeError`.

### `Decoder(debug=False)`

```python
from PIL import Image
from chromaqr import Decoder

image = Image.open("compatible.png")
decoder = Decoder()
colour_bytes = decoder.decode(image)
format_v2_only = decoder.decode_compatible(image)
ordinary_bytes = decoder.decode_compatibility(image)
coordinates = decoder.code_quad
```

All methods return `bytes`; failure returns `b""`. `code_quad` is the four detected QR corners after success and `None` after failure. `decode()` tries validated format-v2 followed by only an unambiguous original-format fallback.

Input images are converted to RGB and reduced to at most 1280 pixels on either axis for decoding. Compatible extraction uses Otsu luminance-family separation and nearest RGB codebook colour; compatibility extraction uses Otsu-binarized grayscale.

## Capacity

### Format-v2 colour layer

These exact maxima include Base45 expansion and the 42-character marker/length/CRC frame in each of the three channels:

| Error correction | QR level | Maximum colour bytes |
| --- | --- | ---: |
| LOW | L | 8,508 |
| MED | M | 6,696 |
| HIGH | Q | 4,755 |
| MAX | H | 3,618 |

The independent ordinary payload must also fit one QR code at the selected level and at the version selected by the largest layer. Version-40 byte-mode capacities are 2,953 (L), 2,331 (M), 1,663 (Q), and 1,273 (H) bytes. QR alphanumeric payloads can be larger. Either side can be the capacity-limiting layer; a clear `ValueError` identifies overflow.

### Original legacy format

Original mode splits 7-bit ASCII data into three unframed chunks and has a nominal LOW maximum of 8,859 bytes. New encoding rejects bytes above `0x7f`; use format-v2 for binary or non-ASCII UTF-8. Original mode is not ordinary-scanner compatible and does not provide format-v2 integrity/identity guarantees. The capacity-comparison images in the README are explicitly original-format examples.

## Colour design and practical reliability

The dark codebook has Rec.601 luminance 54.7–55.3; its exact RGB inverse forms a light codebook at 199.7–200.3. Each family therefore appears almost constant in grayscale, the dark/light gap exceeds 144, and the nearest adjacent codebook colours are about 42.6 RGB units apart. The ordinary layer behaves like a two-level QR rather than the previous 16-level construction.

Automated coverage includes:

- a 6,000-byte MED colour payload at approximately version 38
- LOW, MED, HIGH, and MAX
- independent OpenCV scans of the colour image and grayscale conversion
- a black/white ordinary QR control
- 75% bicubic resizing
- JPEG quality 90 with 4:4:4 (`subsampling=0`)
- ordinary and grayscale rejection regressions
- all 256 byte values in format-v2

PNG is recommended. The ordinary layer is intentionally more robust than the colour layer. Heavy chroma subsampling, severe white-balance/exposure shifts, blur, insufficient module resolution, gamut-limited printing, camera processing, or grayscale conversion may preserve the ordinary QR while destroying colour data. CRC checks turn damaged or mixed channels into a clean failure rather than silent output. No claim is made that all phone/scanner pipelines preserve colour.

## HTTP API

ChromaQR has no public hosted service. Replace `https://your-domain.example` with your own production deployment.

## Project lineage and thanks

ChromaQR was originally created by [William Henderson (@w-henderson)](https://github.com/w-henderson). The backwards-compatible format documented here extends his [original ChromaQR repository](https://github.com/w-henderson/ChromaQR). Thank you to William for creating and open-sourcing the original project.

### `POST /encode`

Form fields:

- `data` (required): UTF-8 hidden text in compatible mode; 7-bit ASCII in original mode
- `compatibilityData` (optional): 7-bit ASCII ordinary payload; presence selects format-v2
- `errorCorrection` (optional): `LOW`, `MED`, `HIGH`, or `MAX`; default `MED`
- `format` (optional): `json` or `image`; default `json`

JSON example:

```sh
curl --data-urlencode "data=hidden colour text" \
  --data-urlencode "compatibilityData=https://your-domain.example/chromaqr" \
  --data "errorCorrection=MED" \
  https://your-domain.example/encode
```

```json
{
  "method": "encode",
  "success": true,
  "error_correction": "MED",
  "result": "data:image/png;base64,..."
}
```

Direct PNG for either original or compatible mode:

```sh
curl --data-urlencode "data=hidden colour text" \
  --data-urlencode "compatibilityData=ordinary text" \
  --data "format=image" \
  https://your-domain.example/encode --output compatible.png
```

Invalid options or capacity overflow return HTTP 400 JSON. Image responses use `Cache-Control: no-store`.

### `POST /decode`

Accepted input (choose one):

- multipart file field `image`
- `dataUri=data:image/png;base64,...` (also JPEG and WebP), intended for the packaged realtime UI

Optional `layer=chroma|compatibility` defaults to `chroma`.

```sh
curl -F image=@compatible.png https://your-domain.example/decode
curl -F image=@compatible.png -F layer=compatibility \
  https://your-domain.example/decode
```

Success:

```json
{
  "method": "decode",
  "success": true,
  "result": "decoded UTF-8 text",
  "coordinates": [[40, 40], [40, 410], [410, 410], [410, 40]]
}
```

No code returns 404. Malformed/unsupported images and data URIs return 400. Binary output that is not UTF-8 returns 422 with guidance to use Python or CLI `--outFile`.

### Upload security

`/decode` never fetches arbitrary `http://` or `https://` URLs; all such values, including loopback and private-network addresses, are rejected. Limits are:

- 8 MiB total HTTP request (`MAX_CONTENT_LENGTH`)
- 5 MiB decoded image bytes
- 16 million image pixels
- image types accepted for data URIs: PNG, JPEG, WebP

Images are fully loaded within guarded Pillow decompression-bomb handling before decoding. Exceptions produce bounded JSON errors rather than debug traces. These controls reduce SSRF, memory, and decompression risks, but a public service still needs production process isolation, concurrency/time limits, patching, monitoring, and rate limiting.

## Packaged web UI

The wheel and sdist include:

- `chromaqr/templates/base.html`
- `chromaqr/templates/home.html`
- `chromaqr/templates/demo.html`
- `chromaqr/templates/realtime.html`
- `chromaqr/static/logo.png`

Routes `/`, `/demo`, `/realtime`, and `/logo.png` use package-relative resources and never reference the repository's `tests/` directory.
