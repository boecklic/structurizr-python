#!/usr/bin/env python3

import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="structurizr", # Replace with your own username
    version="0.1.0",
    author="Christoph Böcklin",
    author_email="christoph.boecklin@gmail.com",
    description="Library to facilitate model creation interaction with structurizr.com REST API",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/pypa/sampleproject",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)
