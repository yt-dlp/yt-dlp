import inspect
import os

from ..globals import LAZY_EXTRACTORS
from ..globals import extractors as _extractors_context

_CLASS_LOOKUP = None
if os.environ.get('YTDLP_NO_LAZY_EXTRACTORS'):
    LAZY_EXTRACTORS.value = False
else:
    try:
        from .lazy_extractors import _CLASS_LOOKUP
        LAZY_EXTRACTORS.value = True
    except ImportError:
        LAZY_EXTRACTORS.value = None

if not _CLASS_LOOKUP:
    from . import _extractors

    _CLASS_LOOKUP = {
        name: value
        for name, value in inspect.getmembers(_extractors)
        if name.endswith('IE') and name != 'GenericIE'
    }
    _CLASS_LOOKUP['GenericIE'] = _extractors.GenericIE

# We want to append to the main lookup
_current = _extractors_context.value
for name, ie in _CLASS_LOOKUP.items():
    _current.setdefault(name, ie)


def __getattr__(name):
    value = _CLASS_LOOKUP.get(name)
    if not value:
        raise AttributeError(f'module {__name__} has no attribute {name}')
    return value
