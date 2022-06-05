#!/usr/bin/env python3
import optparse
import os
import sys
from inspect import getsource

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


NO_ATTR = object()
STATIC_CLASS_PROPERTIES = ['IE_NAME', 'IE_DESC', 'SEARCH_KEY', '_WORKING', '_NETRC_MACHINE', 'age_limit']
CLASS_METHODS = [
    'ie_key', 'working', 'description', 'suitable', '_match_valid_url', '_match_id', 'get_temp_id', 'is_suitable'
]
IE_TEMPLATE = '''
class {name}({bases}):
    _module = {module!r}
'''
with open('devscripts/lazy_load_template.py', encoding='utf-8') as f:
    MODULE_TEMPLATE = f.read()


def main():
    parser = optparse.OptionParser(usage='%prog [OUTFILE.py]')
    args = parser.parse_args()[1] or ['yt_dlp/extractor/lazy_extractors.py']
    if len(args) != 1:
        parser.error('Expected only an output filename')

    lazy_extractors_filename = args[0]
    if os.path.exists(lazy_extractors_filename):
        os.remove(lazy_extractors_filename)

    _ALL_CLASSES = get_all_ies()  # Must be before import

    from yt_dlp.extractor.common import InfoExtractor, SearchInfoExtractor

    DummyInfoExtractor = type('InfoExtractor', (InfoExtractor,), {'IE_NAME': NO_ATTR})
    module_src = '\n'.join((
        MODULE_TEMPLATE,
        '    _module = None',
        *extra_ie_code(DummyInfoExtractor),
        '\nclass LazyLoadSearchExtractor(LazyLoadExtractor):\n    pass\n',
        *build_ies(_ALL_CLASSES, (InfoExtractor, SearchInfoExtractor), DummyInfoExtractor),
    ))

    with open(lazy_extractors_filename, 'wt', encoding='utf-8') as f:
        f.write(f'{module_src}\n')


def get_all_ies():
    PLUGINS_DIRNAME = 'ytdlp_plugins'
    BLOCKED_DIRNAME = f'{PLUGINS_DIRNAME}_blocked'
    if os.path.exists(PLUGINS_DIRNAME):
        os.rename(PLUGINS_DIRNAME, BLOCKED_DIRNAME)
    try:
        from yt_dlp.extractor import _ALL_CLASSES
    finally:
        if os.path.exists(BLOCKED_DIRNAME):
            os.rename(BLOCKED_DIRNAME, PLUGINS_DIRNAME)
    return _ALL_CLASSES


def extra_ie_code(ie, base=None):
    for var in STATIC_CLASS_PROPERTIES:
        val = getattr(ie, var)
        if val != (getattr(base, var) if base else NO_ATTR):
            yield f'    {var} = {val!r}'
    yield ''

    for name in CLASS_METHODS:
        f = getattr(ie, name)
        if not base or f.__func__ != getattr(base, name).__func__:
            yield getsource(f)


def build_ies(ies, bases, attr_base):
    names = []
    for ie in sort_ies(ies, bases):
        yield build_lazy_ie(ie, ie.__name__, attr_base)
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
            for b in bases:
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
    }.get(base.__name__, base.__name__) for base in ie.__bases__)

    s = IE_TEMPLATE.format(name=name, module=ie.__module__, bases=bases)
    valid_url = getattr(ie, '_VALID_URL', None)
    if not valid_url and hasattr(ie, '_make_valid_url'):
        valid_url = ie._make_valid_url()
    if valid_url:
        s += f'    _VALID_URL = {valid_url!r}\n'
    return s + '\n'.join(extra_ie_code(ie, attr_base))


if __name__ == '__main__':
    main()
