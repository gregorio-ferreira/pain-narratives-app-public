#!/usr/bin/env python3
"""
Script to build Sphinx documentation for the AINarratives project.
"""
import os

if __name__ == "__main__":
    os.system("sphinx-apidoc -o docs/ src/pain_narratives/")
    os.system("sphinx-build -b html docs/ docs/_build/html")
    print("Documentation built at docs/_build/html/index.html")
