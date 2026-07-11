from setuptools import find_namespace_packages, setup


with open("README.md", "r", encoding="utf-8") as readme:
    long_description = readme.read()

setup(
    name="ChromaQR",
    version="0.0.1",
    description="Layer additional data into QR codes using luma-balanced RGB.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="w-henderson",
    license="MIT",
    packages=find_namespace_packages(
        include=("chromaqr", "chromaqr.*")
    ),
    include_package_data=True,
    package_data={
        "chromaqr": ["templates/*.html", "static/*.png"],
    },
    entry_points={"console_scripts": ["chromaqr=chromaqr.cli:main"]},
    zip_safe=False,
    install_requires=[
        "pyzbar",
        "colorama",
        "qrcode",
        "pillow>=9.1",
        "flask>=2.2",
        "flask-cors",
    ],
    extras_require={
        "tests": [
            "pytest",
            "opencv-python-headless",
            "build",
            "twine",
        ],
    },
    python_requires=">=3.9",
    classifiers=[
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
    ],
)
