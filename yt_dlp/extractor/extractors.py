import os

from ..globals import ALL_IES, LAZY_EXTRACTORS, PLUGIN_IES
from ..plugins import load_plugins

# NB: Must be before other imports so that plugins can be correctly injected
PLUGIN_IES.set(load_plugins('extractor', 'IE'))
del load_plugins
ALL_IES.set(PLUGIN_IES.get().copy())

from .common import _PLUGIN_OVERRIDES  # noqa: F401

if os.environ.get('YTDLP_NO_LAZY_EXTRACTORS'):
    LAZY_EXTRACTORS.set(False)
else:
    try:
        from .lazy_extractors import _ALL_CLASSES
    except ImportError:
        LAZY_EXTRACTORS.set(None)
    else:
        LAZY_EXTRACTORS.set(True)
        ALL_IES.get().update({ie.__name__: ie for ie in _ALL_CLASSES})

if not LAZY_EXTRACTORS.get():
    from . import _extractors
    ALL_IES.get().update(
        (name, ie) for name, ie in vars(_extractors).items()
        if name.endswith('IE') and name != 'GenericIE'
    )
    ALL_IES.get()['GenericIE'] = _extractors.GenericIE

globals().update(ALL_IES.get())
