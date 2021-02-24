# coding: utf-8
#
# yt-dlp documentation build configuration file

import sys
import os

# Allows to import yt-dlp
sys.path.insert(0, os.path.abspath('..'))
from recommonmark.transform import AutoStructify

# -- General configuration ------------------------------------------------

# The suffix of source filenames.
source_suffix = ['.rst', '.md']

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.autodoc',
    'recommonmark',
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'yt-dlp'
author = u'yt-dlp'
copyright = u'UNLICENSE'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
from yt_dlp.version import __version__
version = __version__
# The full version, including alpha/beta/rc tags.
release = version

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build']

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# -- Options for HTML output ----------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'default'

# Disable highlights
highlight_language = 'none'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
# html_static_path = ['_static']


def setup(app):
    app.add_config_value('recommonmark_config', {
        'enable_math': False,
        'enable_inline_math': False,
        'enable_eval_rst': True,
        'enable_auto_toc_tree': True,
    }, True)
    app.add_transform(AutoStructify)
