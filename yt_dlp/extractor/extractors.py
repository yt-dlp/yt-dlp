import itertools
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

    members = tuple(
        (name, getattr(_extractors, name))
        for name in dir(_extractors)
        if name.endswith('IE')
    )
    _CLASS_LOOKUP = dict(itertools.chain(
        # Add Youtube first to improve matching performance
        ((name, value) for name, value in members if '.youtube' in value.__module__),
        # Add Generic last so that it is the fallback
        ((name, value) for name, value in members if name != 'GenericIE'),
        (('GenericIE', _extractors.GenericIE),),
    ))

# We want to append to the main lookup
_current = _extractors_context.value
for name, ie in _CLASS_LOOKUP.items():
    _current.setdefault(name, ie)


def __getattr__(name):
    value = _CLASS_LOOKUP.get(name)
    if not value:
        raise AttributeError(f'module {__name__} has no attribute {name}')
    return value
