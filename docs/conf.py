# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys

sys.path.insert(0, os.path.abspath(".."))


# -- Project information -----------------------------------------------------

project = "uniswap-python"
author = "Shane Fontaine, Erik Bjäreholt, and contributors"
copyright = "2021, " + author


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.extlinks",
    "sphinx.ext.autosectionlabel",
    "sphinx_click",
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

extlinks = {
    "issue": ("https://github.com/shanefontaine/uniswap-python/issues/%s", "issue #"),
}


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "sphinx_book_theme"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]

html_title = "uniswap-python"
html_logo = "_static/logo.png"
html_favicon = "_static/favicon.png"

html_theme_options = {
    "repository_url": "https://github.com/shanefontaine/uniswap-python",
    "path_to_docs": "docs",
    "use_repository_button": True,
    "use_edit_page_button": True,
    "extra_navbar": """
    <p>
        Back to <a href="https://github.com/shanefontaine/uniswap-python">GitHub</a>
    </p>""",
}

show_navbar_depth = 2


# Autodoc config

autoclass_content = "both"
autodoc_member_order = "bysource"
