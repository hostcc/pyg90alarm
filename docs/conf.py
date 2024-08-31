"""
Configuration file for the Sphinx documentation builder.

This file only contains a selection of the most common options. For a full
list see the documentation:
https://www.sphinx-doc.org/en/master/usage/configuration.html
"""

# -- Path setup --------------------------------------------------------------
import sys
from sphinx.util.inspect import getdoc
from sphinx.util.docstrings import separate_metadata
sys.path.extend(['../src'])

# -- Project information -----------------------------------------------------

project = 'pyg90alarm'
copyright = '2021, Ilia Sotnikov'
author = 'Ilia Sotnikov'


extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    'sphinx.ext.intersphinx',
    'enum_tools.autoenum',
    'sphinx.ext.autosectionlabel',
    'sphinx_autodoc_typehints',
]

exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'sphinx_rtd_theme'

autodoc_default_options = {
    'members': True,
    'inherited-members': True,
    'show-inheritance': True,
    'member-order': 'bysource',
    'class-doc-from': 'both',
}

source_suffix = {
    '.rst': 'restructuredtext',
    '.md': 'markdown',
}

intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
}


def autodoc_skip_class(_app, what, name, obj, _skip, _options):
    """
    Allows to declare a class as private by specifying `:meta private:` in its
    docstring.
    """
    if what == 'class':
        try:
            doc = getdoc(obj, cls=name, name=name)
            doc, metadata = separate_metadata(doc)

            if 'private' in metadata:
                return True
        except Exception:
            # Treat any exceptions in the code above non-fatal
            pass
    # Defer to other handlers to decide
    return None


def setup(app):
    """
    Registers custom handler for `autodoc-skip-member` event.
    """
    app.connect('autodoc-skip-member', autodoc_skip_class)
