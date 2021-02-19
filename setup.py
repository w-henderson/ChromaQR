from setuptools import setup

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="ChromaQR",
    version="0.0.1",
    description="Get three times the data into a QR code using RGB.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="w-henderson",
    packages=["chromaqr"],
    package_dir={"": "."},
    entry_points={"console_scripts": ["chromaqr = chromaqr.cli:main"]},
    zip_safe=False,
    install_requires=[
        "pyzbar",
        "colorama",
        "qrcode",
        "pillow",
        "flask",
        "flask-cors"
    ],
    extras_require={
        "tests": ["pytest"],
    },
    python_requires=">=3.6",
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
    ],
    include_package_data=True
)