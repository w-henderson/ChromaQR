import argparse
from PIL import Image
from .encode import Encoder
from .decode import Decoder


def _read_bytes(file_path, text):
    if file_path is not None:
        with open(file_path, "rb") as input_file:
            return input_file.read()
    if text is not None:
        return text.encode("utf-8")
    return None


def main():
    """
    Main CLI function.
    Called by running `chromaqr` at the command line.
    """

    parser = argparse.ArgumentParser(
        description="Get three times the data into a QR code using RGB."
    )
    parser.add_argument(
        "command",
        choices=["encode", "decode", "serve"],
        help="command to perform, must be encode, decode, or serve"
    )
    parser.add_argument("--inFile", type=str, help="path to input file")
    parser.add_argument("--text", type=str, help="text to encode")
    parser.add_argument("--outFile", type=str, help="path to output file")
    parser.add_argument(
        "--compatibilityText",
        type=str,
        help="ordinary QR payload for a backwards-compatible code"
    )
    parser.add_argument(
        "--compatibilityInFile",
        type=str,
        help="file containing the ordinary QR payload"
    )
    parser.add_argument(
        "--layer",
        choices=["chroma", "compatibility"],
        default="chroma",
        help="layer to decode from a backwards-compatible code"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="whether to decode in debug mode"
    )
    parser.add_argument(
        "--errorCorrection",
        choices=["LOW", "MED", "HIGH", "MAX"],
        default="MED",
        help="level of error correction to use"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="port to host the server on"
    )
    args = parser.parse_args()

    if args.command == "encode":
        input_bytes = _read_bytes(args.inFile, args.text)
        if input_bytes is None:
            parser.error("encode requires --inFile or --text")
        if args.outFile is None:
            parser.error("encode requires --outFile")

        compatibility_bytes = _read_bytes(
            args.compatibilityInFile,
            args.compatibilityText
        )
        encoder = Encoder(error_correction=args.errorCorrection)
        try:
            image = encoder.encode(
                input_bytes,
                compatibility_data=compatibility_bytes
            )
        except (TypeError, ValueError) as error:
            parser.error(str(error))
        image.save(args.outFile)

    elif args.command == "decode":
        if args.inFile is None:
            parser.error("decode requires --inFile")

        input_image = Image.open(args.inFile)
        decoder = Decoder(debug=args.debug)
        if args.layer == "compatibility":
            decoded_bytes = decoder.decode_compatibility(input_image)
        else:
            decoded_bytes = decoder.decode(input_image)

        if args.outFile is not None:
            with open(args.outFile, "wb") as output_file:
                output_file.write(decoded_bytes)
        else:
            try:
                print(decoded_bytes.decode("utf-8"))
            except UnicodeDecodeError:
                parser.error(
                    "decoded payload is binary; specify --outFile to preserve bytes"
                )

    elif args.command == "serve":
        from .server import run
        run(port=args.port)
