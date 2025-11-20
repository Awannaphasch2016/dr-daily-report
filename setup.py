"""Setup for DR CLI"""

from setuptools import setup, find_packages
from pathlib import Path

setup(
    name="dr-cli",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "click>=8.0.0",
    ],
    entry_points={
        "console_scripts": [
            "dr=dr_cli.main:main",
        ],
    },
    python_requires=">=3.8",
    author="DR Team",
    description="Unified CLI for Daily Report repository",
    long_description=open("README.md").read() if Path("README.md").exists() else "",
    long_description_content_type="text/markdown",
)
