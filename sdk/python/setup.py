"""Setup script for RegEngine Python SDK"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="regengine",
    version="2.0.0",
    author="RegEngine Team",
    author_email="support@regengine.io",
    description="Official Python SDK for RegEngine v2 Regulatory Intelligence Platform",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/PetrefiedThunder/RegEngine",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.11",
    install_requires=[
        "requests>=2.32.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "black>=24.0.0",
            "mypy>=1.0.0",
        ],
    },
)
