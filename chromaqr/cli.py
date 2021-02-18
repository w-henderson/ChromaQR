import argparse
from PIL import Image
from .encode import Encoder
from .decode import Decoder

def main():
    """
    Main CLI function.
    Called by running `chromaqr` at the command line.
    """

    parser = argparse.ArgumentParser(description="Get three times the data into a QR code using RGB.")
    parser.add_argument("command", type=str, help="command to perform, must be encode or decode")
    parser.add_argument("--inFile", type=str, help="path to input file")
    parser.add_argument("--text", type=str, help="text to encode")
    parser.add_argument("--outFile", type=str, help="path to output file")
    parser.add_argument("--debug", action="store_true", help="whether to encode in debug mode")
    parser.add_argument("--errorCorrection", choices=["LOW", "MED", "HIGH", "MAX"], default="MED", help="level of error correction to use")
    args = parser.parse_args()

    if args.command == "encode":
        if args.inFile != None:
            with open(args.inFile, "rb") as f:
                inputBytes = f.read()
        else:
            inputBytes = args.text.encode("utf-8")

        encoder = Encoder(error_correction=args.errorCorrection)
        image = encoder.encode(inputBytes)

        if args.outFile != None:
            image.save(args.outFile)
        else:
            print("error: you must provide an --outFile to encode to")
    
    elif args.command == "decode":
        if args.inFile != None:
            inputImage = Image.open(args.inFile)
        else:
            print("error: you must provide an --inFile to decode")
            return

        decoder = Decoder()
        decoded_bytes = decoder.decode(inputImage)

        if args.outFile != None:
            with open(args.outFile, "wb") as f:
                f.write(decoded_bytes)
        else:
            print(decoded_bytes)