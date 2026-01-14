# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import sys
from pathlib import Path

sys.path.insert(0, str(Path('..', '..', 'src').resolve()))

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'OM'
copyright = '2026, OM Development Team'
author = 'OM Development Team'
release = '23.8.2'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'myst_parser',
    'sphinx_click',
    'sphinxcontrib.images',
]

templates_path = ['_templates']
exclude_patterns = []

add_module_names = False

autodoc_typehints = 'description'

autodoc_mock_imports = [
    'asapo_consumer',
    'psana',
    'seedee',
]

autodoc_default_options = {
    'members': True,
    'member-order': 'bysource',
    'exclude-members': '__new__',
    'undoc-members': False,
}

autoclass_content = 'init'

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'pydata_sphinx_theme'

html_static_path = ['_static/css']
html_css_files = ['custom.css']

html_show_sourcelink = False

html_sidebars = {
  '**': []
}

html_theme_options = {
    'show_prev_next': False,
    'logo': {
        'text': 'OM: Online Monitor',
    },
}

html_context = {
    'github_url': 'https://github.com',
    'github_user': 'omdevteam',
    'github_repo': 'om',
}

