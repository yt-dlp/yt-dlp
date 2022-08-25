#!/usr/bin/env python3

# Allow direct execution
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


from inspect import getsource
from itertools import chain

from devscripts.utils import get_filename_args, read_file, write_file
from yt_dlp.utils import try_call

NO_ATTR = object()
STATIC_CLASS_PROPERTIES = [
    'IE_NAME', 'IE_DESC', 'SEARCH_KEY', '_VALID_URL', '_WORKING', '_ENABLED', '_NETRC_MACHINE', 'age_limit'
]
SH_STATIC_CLASS_PROPS = ('_IMPOSSIBLE_HOSTNAMES', '_PREFIX_GROUPS', '_HOSTNAME_GROUPS', '_INSTANCE_LIST', '_DYNAMIC_INSTANCE_LIST', '_NODEINFO_SOFTWARE', '_SOFTWARE_NAME')
CLASS_METHODS = [
    'ie_key', 'working', 'description', 'suitable', '_match_valid_url', '_match_id', 'get_temp_id', 'is_suitable'
]
SH_CLASS_METHODS = ('_test_selfhosted_instance', '_probe_webpage')
IE_TEMPLATE = '''
class {name}({bases}):
    _module = {module!r}
'''
MODULE_TEMPLATE = read_file('devscripts/lazy_load_template.py')


def main():
    lazy_extractors_filename = get_filename_args(default_outfile='yt_dlp/extractor/lazy_extractors.py')
    if os.path.exists(lazy_extractors_filename):
        os.remove(lazy_extractors_filename)

    _ALL_CLASSES = get_all_ies()  # Must be before import

    from yt_dlp.extractor.common import InfoExtractor, SearchInfoExtractor, SelfHostedInfoExtractor

    DummyInfoExtractor = type('InfoExtractor', (InfoExtractor,), {'IE_NAME': NO_ATTR})
    DummySHInfoExtractor = type('SelfHostedInfoExtractor', (SelfHostedInfoExtractor,), {'IE_NAME': NO_ATTR})
    module_src = '\n'.join((
        MODULE_TEMPLATE,
        '    _module = None',
        *extra_ie_code(DummyInfoExtractor),
        '\nclass LazyLoadSearchExtractor(LazyLoadExtractor):\n    pass\n',
        '\nclass LazyLoadSelfHostedExtractor(LazyLoadExtractor):',
        *extra_ie_code(DummySHInfoExtractor, DummyInfoExtractor, SH_STATIC_CLASS_PROPS, SH_CLASS_METHODS),
        *build_ies(_ALL_CLASSES, (InfoExtractor, SearchInfoExtractor, SelfHostedInfoExtractor), DummyInfoExtractor, DummySHInfoExtractor),
    ))

    write_file(lazy_extractors_filename, f'{module_src}\n')


def get_all_ies():
    PLUGINS_DIRNAME = 'ytdlp_plugins'
    BLOCKED_DIRNAME = f'{PLUGINS_DIRNAME}_blocked'
    if os.path.exists(PLUGINS_DIRNAME):
        os.rename(PLUGINS_DIRNAME, BLOCKED_DIRNAME)
    try:
        from yt_dlp.extractor.extractors import _ALL_CLASSES
    finally:
        if os.path.exists(BLOCKED_DIRNAME):
            os.rename(BLOCKED_DIRNAME, PLUGINS_DIRNAME)
    return _ALL_CLASSES


def extra_ie_code(ie, base=None, static_class_properties=(), class_methods=()):
    for var in chain(STATIC_CLASS_PROPERTIES, static_class_properties):
        val = getattr(ie, var)
        if val != (getattr(base, var, NO_ATTR) if base else NO_ATTR):
            yield f'    {var} = {val!r}'
    yield ''

    for name in chain(CLASS_METHODS, class_methods):
        f = getattr(ie, name)
        if not base or f.__func__ != try_call(lambda: getattr(base, name).__func__):
            yield getsource(f)


def build_ies(ies, bases, attr_base, selfhosted_base):
    names = []
    for ie in sort_ies(ies, bases):
        yield build_lazy_ie(ie, ie.__name__, selfhosted_base if ie._SELF_HOSTED else attr_base)
        if ie in ies:
            names.append(ie.__name__)

    yield f'\n_ALL_CLASSES = [{", ".join(names)}]'


def sort_ies(ies, ignored_bases):
    """find the correct sorting and add the required base classes so that subclasses can be correctly created"""
    classes, returned_classes = ies[:-1], set()
    assert ies[-1].__name__ == 'GenericIE', 'Last IE must be GenericIE'
    while classes:
        for c in classes[:]:
            bases = set(c.__bases__) - {object, *ignored_bases}
            restart = False
            for b in sorted(bases, key=lambda x: x.__name__):
                if b not in classes and b not in returned_classes:
                    assert b.__name__ != 'GenericIE', 'Cannot inherit from GenericIE'
                    classes.insert(0, b)
                    restart = True
            if restart:
                break
            if bases <= returned_classes:
                yield c
                returned_classes.add(c)
                classes.remove(c)
                break
    yield ies[-1]


def build_lazy_ie(ie, name, attr_base):
    bases = ', '.join({
        'InfoExtractor': 'LazyLoadExtractor',
        'SearchInfoExtractor': 'LazyLoadSearchExtractor',
        'SelfHostedInfoExtractor': 'LazyLoadSelfHostedExtractor',
    }.get(base.__name__, base.__name__) for base in ie.__bases__)

    s = IE_TEMPLATE.format(name=name, module=ie.__module__, bases=bases)
    return s + '\n'.join(extra_ie_code(ie, attr_base, *((SH_STATIC_CLASS_PROPS, SH_CLASS_METHODS) if 'LazyLoadSelfHostedExtractor' in bases else ())))


if __name__ == '__main__':
    main()
