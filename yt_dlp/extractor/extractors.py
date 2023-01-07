import inspect
import os

from ..globals import LAZY_EXTRACTORS, extractors

_CLASS_LOOKUP = None
if not os.environ.get('YTDLP_NO_LAZY_EXTRACTORS'):
    try:
        from .lazy_extractors import _CLASS_LOOKUP
        LAZY_EXTRACTORS.set(True)
    except ImportError:
        LAZY_EXTRACTORS.set(None)

if not _CLASS_LOOKUP:
    from . import _extractors

    _CLASS_LOOKUP = {
        name: value
        for name, value in inspect.getmembers(_extractors)
        if name.endswith('IE') and name != 'GenericIE'
    }
    _CLASS_LOOKUP['GenericIE'] = _extractors.GenericIE

extractors.set(_CLASS_LOOKUP)
globals().update(_CLASS_LOOKUP)
