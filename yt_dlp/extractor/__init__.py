from ..compat.compat_utils import passthrough_module

passthrough_module(__name__, '.extractors')
del passthrough_module


def gen_extractor_classes():
    """ Return a list of supported extractors.
    The order does matter; the first extractor matched is the one handling the URL.
    """
    from .extractors import _ALL_CLASSES

    return _ALL_CLASSES


def gen_extractors():
    """ Return a list of an instance of every supported extractor.
    The order does matter; the first extractor matched is the one handling the URL.
    """
    return [klass() for klass in gen_extractor_classes()]


def list_extractor_classes(age_limit=None):
    """Return a list of extractors that are suitable for the given age, sorted by extractor name"""
    from .generic import GenericIE

    yield from sorted(filter(
        lambda ie: ie.is_suitable(age_limit) and ie != GenericIE,
        gen_extractor_classes()), key=lambda ie: ie.IE_NAME.lower())
    yield GenericIE


def list_extractors(age_limit=None):
    """Return a list of extractor instances that are suitable for the given age, sorted by extractor name"""
    return [ie() for ie in list_extractor_classes(age_limit)]


def get_info_extractor(ie_name):
    """Returns the info extractor class with the given ie_name"""
    from . import extractors

    return getattr(extractors, f'{ie_name}IE')
