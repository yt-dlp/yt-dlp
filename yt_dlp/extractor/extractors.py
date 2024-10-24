import contextlib
import os

from ..plugins import load_plugins

# NB: Must be before other imports so that plugins can be correctly injected
_PLUGIN_CLASSES = load_plugins('extractor', 'IE')

_LAZY_LOADER = False
if not os.environ.get('YTDLP_NO_LAZY_EXTRACTORS'):
    with contextlib.suppress(ImportError):
        from .lazy_extractors import *  # noqa: F403
        from .lazy_extractors import _ALL_CLASSES
        _LAZY_LOADER = True

if not _LAZY_LOADER:
    from ._extractors import *  # noqa: F403
    _ALL_CLASSES = [  # noqa: F811
        klass
        for name, klass in globals().items()
        if name.endswith('IE') and name != 'GenericIE'
    ]
    _ALL_CLASSES.append(GenericIE)  # noqa: F405

globals().update(_PLUGIN_CLASSES)
_ALL_CLASSES[:0] = _PLUGIN_CLASSES.values()

from .common import _PLUGIN_OVERRIDES  # noqa: F401
