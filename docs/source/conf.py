# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path("..", "..", "src").resolve()))

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project: str = "OM"
copyright: str = "2026, OM Development Team"
author: str = "OM Development Team"
release: str = "23.8.2"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions: list[str] = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "myst_parser",
    "sphinx_click",
    "sphinxcontrib.images",
]

templates_path: list[str] = ["_templates"]
exclude_patterns: list[str] = []

add_module_names: bool = False

autodoc_typehints: str = "description"

autodoc_mock_imports: list[str] = [
    "asapo_consumer",
    "psana",
    "seedee",
]

autodoc_default_options: dict[str, Any] = {
    "members": True,
    "member-order": "bysource",
    "exclude-members": "__new__",
    "undoc-members": False,
}

autoclass_content: str = "init"

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme: str = "pydata_sphinx_theme"

html_static_path: list[str] = ["_static/css"]
html_css_files: list[str] = ["custom.css"]

html_show_sourcelink = False

html_sidebars: dict[str, list[str]] = {"**": []}

html_theme_options: dict[str, Any] = {
    "show_prev_next": False,
    "logo": {
        "text": "OM: Online Monitor",
    },
}

html_context: dict[str, str] = {
    "github_url": "https://github.com",
    "github_user": "omdevteam",
    "github_repo": "om",
}
