from __future__ import unicode_literals, print_function

from inspect import getsource
import io
import os
from os.path import dirname as dirn
import sys

print('WARNING: Lazy loading extractors is an experimental feature that may not always work', file=sys.stderr)

sys.path.insert(0, dirn(dirn((os.path.abspath(__file__)))))

lazy_extractors_filename = sys.argv[1]
if os.path.exists(lazy_extractors_filename):
    os.remove(lazy_extractors_filename)

# Block plugins from loading
os.rename('ytdlp_plugins', 'ytdlp_plugins_blocked')

from yt_dlp.extractor import _ALL_CLASSES
from yt_dlp.extractor.common import InfoExtractor, SearchInfoExtractor

os.rename('ytdlp_plugins_blocked', 'ytdlp_plugins')

with open('devscripts/lazy_load_template.py', 'rt') as f:
    module_template = f.read()

module_contents = [
    module_template + '\n' + getsource(InfoExtractor.suitable) + '\n',
    'class LazyLoadSearchExtractor(LazyLoadExtractor):\n    pass\n']

ie_template = '''
class {name}({bases}):
    _VALID_URL = {valid_url!r}
    _module = '{module}'
'''

make_valid_template = '''
    @classmethod
    def _make_valid_url(cls):
        return {valid_url!r}
'''


def get_base_name(base):
    if base is InfoExtractor:
        return 'LazyLoadExtractor'
    elif base is SearchInfoExtractor:
        return 'LazyLoadSearchExtractor'
    else:
        return base.__name__


def build_lazy_ie(ie, name):
    valid_url = getattr(ie, '_VALID_URL', None)
    s = ie_template.format(
        name=name,
        bases=', '.join(map(get_base_name, ie.__bases__)),
        valid_url=valid_url,
        module=ie.__module__)
    if ie.suitable.__func__ is not InfoExtractor.suitable.__func__:
        s += '\n' + getsource(ie.suitable)
    if hasattr(ie, '_make_valid_url'):
        # search extractors
        s += make_valid_template.format(valid_url=ie._make_valid_url())
    return s


# find the correct sorting and add the required base classes so that subclasses
# can be correctly created
classes = _ALL_CLASSES[:-1]
ordered_cls = []
while classes:
    for c in classes[:]:
        bases = set(c.__bases__) - set((object, InfoExtractor, SearchInfoExtractor))
        stop = False
        for b in bases:
            if b not in classes and b not in ordered_cls:
                if b.__name__ == 'GenericIE':
                    exit()
                classes.insert(0, b)
                stop = True
        if stop:
            break
        if all(b in ordered_cls for b in bases):
            ordered_cls.append(c)
            classes.remove(c)
            break
ordered_cls.append(_ALL_CLASSES[-1])

names = []
for ie in ordered_cls:
    name = ie.__name__
    src = build_lazy_ie(ie, name)
    module_contents.append(src)
    if ie in _ALL_CLASSES:
        names.append(name)

module_contents.append(
    '_ALL_CLASSES = [{0}]'.format(', '.join(names)))

module_src = '\n'.join(module_contents) + '\n'

with io.open(lazy_extractors_filename, 'wt', encoding='utf-8') as f:
    f.write(module_src)
