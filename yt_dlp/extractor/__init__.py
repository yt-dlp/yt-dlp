from __future__ import unicode_literals

from ..utils import load_plugins

try:
    from .lazy_extractors import *
    from .lazy_extractors import _ALL_CLASSES
    _LAZY_LOADER = True
    _PLUGIN_CLASSES = []
except ImportError:
    _LAZY_LOADER = False

if not _LAZY_LOADER:
    from .common import InfoExtractorMeta

    import pkgutil
    import importlib

    for modinfo in pkgutil.iter_modules(__path__):
        _, name, *_ = modinfo
        importlib.import_module('.' + name, package=__package__)

    _PLUGIN_CLASSES = load_plugins()
    _ALL_CLASSES = InfoExtractorMeta.REGISTRY
    _ALL_CLASSES.sort(key=lambda cls: (cls._REGISTRY_TIER, -(cls in _PLUGIN_CLASSES)))

_ALL_CLASSES_MAP = {cls.__name__: cls for cls in _ALL_CLASSES}

def gen_extractor_classes():
    """ Return a list of supported extractors.
    The order does matter; the first extractor matched is the one handling the URL.
    """
    return _ALL_CLASSES


def gen_extractors():
    """ Return a list of an instance of every supported extractor.
    The order does matter; the first extractor matched is the one handling the URL.
    """
    return [klass() for klass in gen_extractor_classes()]


def list_extractors(age_limit):
    """
    Return a list of extractors that are suitable for the given age,
    sorted by extractor ID.
    """

    return sorted(
        filter(lambda ie: ie.is_suitable(age_limit), gen_extractors()),
        key=lambda ie: ie.IE_NAME.lower())


def get_info_extractor(ie_name):
    """Returns the info extractor class with the given ie_name"""
    return _ALL_CLASSES_MAP[ie_name + 'IE']
