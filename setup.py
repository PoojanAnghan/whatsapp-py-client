from setuptools import setup, find_packages

setup(
    name="whatsapp-py-client",
    version="1.0.0",
    packages=find_packages(),
    include_package_data=True,
    package_data={
        "whatsapp": ["injected/*.js"],
    },
    entry_points={
        "console_scripts": [
            "whatsapp-py=whatsapp.cli:main",
        ],
    },
    install_requires=[
        "playwright>=1.44.0",
        "pyee>=11.0.0",
        "pydantic>=2.0.0",
        "httpx>=0.27.0",
        "python-magic>=0.4.27",
        "Pillow>=10.0.0",
        "ffmpeg-python>=0.2.0",
        "aiofiles>=23.0.0",
        "qrcode>=7.4.2",
    ],
)
