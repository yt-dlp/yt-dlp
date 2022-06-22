import contextlib
import os

from ..utils import load_plugins

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

_PLUGIN_CLASSES = load_plugins('extractor', 'IE', globals())
_ALL_CLASSES = list(_PLUGIN_CLASSES.values()) + _ALL_CLASSES
