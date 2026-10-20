"""Committed notebook outputs must not contain absolute home-directory paths.

The repository is mirrored anonymously for double-blind review, and a path such
as /Users/<name>/... in a saved output identifies the author.
"""

import re
from pathlib import Path

import pytest

NOTEBOOKS = sorted((Path(__file__).resolve().parents[1] / "notebooks").glob("*.ipynb"))
HOME_PATH = re.compile(r"/Users/[^/\s\"]+|/home/[^/\s\"]+|[A-Za-z]:\\\\+Users\\\\+[^\\\s\"]+")


@pytest.mark.parametrize("notebook", NOTEBOOKS, ids=lambda p: p.name)
def test_notebook_has_no_home_paths(notebook):
    matches = sorted(set(HOME_PATH.findall(notebook.read_text(encoding="utf-8"))))
    assert not matches, f"{notebook.name} contains home-directory paths: {matches}"
