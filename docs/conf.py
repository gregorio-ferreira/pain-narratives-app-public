# Sphinx configuration for documentation generation

project = "AINarratives"
copyright = "2025, AINarratives Team"
author = "AINarratives Team"
release = "1.0.0"
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
]
autodoc_typehints = "description"
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]
html_theme = "alabaster"
