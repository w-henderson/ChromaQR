import argparse
from .encode import Encoder

def main():
    parser = argparse.ArgumentParser(description="Get three times the data into a QR code using RGB.")
    parser.add_argument("command", type=str, help="command to perform, must be encode or decode")
    parser.add_argument("--inFile", type=str, help="path to input file")
    parser.add_argument("--text", type=str, help="text to encode")
    parser.add_argument("--outFile", type=str, help="path to output file")
    args = parser.parse_args()

    if args.command == "encode":
        if args.inFile != None:
            with open(args.inFile, "rb") as f:
                inputBytes = f.read()
        else:
            inputBytes = args.text.encode("utf-8")

        encoder = Encoder()
        image = encoder.encode(inputBytes)
        image.save("test.png")