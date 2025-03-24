from setuptools import setup, find_packages

setup(
    name="pixelvault",
    version="1.0.0",
    description="A modern GTK4-based image viewer application for Arch Linux",
    author="PixelVault Team",
    author_email="info@pixelvault.example.com",
    url="https://github.com/yourusername/pixelvault",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "pygobject",
        "pillow",
        "requests",
        "aiohttp",
        "aiofiles"
    ],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: X11 Applications :: GTK",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Multimedia :: Graphics :: Viewers",
    ],
    entry_points={
        "console_scripts": [
            "pixelvault=src.main:main",
        ],
    },
) 