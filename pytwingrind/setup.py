#!/usr/bin/env python

from setuptools import setup, find_packages
from os import environ

setup(
    name="pytwingrind",
    version=f"0.2.0",
    author="Stefan Besler",
    author_email="stefan@besler.me",
    description="Call-graph profiling for TwinCAT 3.",
    long_description="Call-graph profiling for TwinCAT 3.",
    long_description_content_type="text/markdown",
    url="https://github.com/stefanbesler/twingrind",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
    ],
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "twingrind = pytwingrind.__main__:main"
        ],
    },
    install_requires=list(open('requirements.txt')),
)
