import http.cookies
import re
import xml.etree.ElementTree

import pytest

from yt_dlp.utils import (
    ExtractorError,
    determine_ext,
    dict_get,
    int_or_none,
    join_nonempty,
    str_or_none,
)
from yt_dlp.utils.traversal import (
    find_element,
    find_elements,
    require,
    subs_list_to_dict,
    traverse_obj,
    trim_str,
    unpack,
)

_TEST_DATA = {
    100: 100,
    1.2: 1.2,
    'str': 'str',
    'None': None,
    '...': ...,
    'urls': [
        {'index': 0, 'url': 'https://www.example.com/0'},
        {'index': 1, 'url': 'https://www.example.com/1'},
    ],
    'data': (
        {'index': 2},
        {'index': 3},
    ),
    'dict': {},
}

_TEST_HTML = '''<html><body>
    <div class="a">1</div>
    <div class="a" id="x" custom="z">2</div>
    <div class="b" data-id="y" custom="z">3</div>
    <p class="a">4</p>
    <p id="d" custom="e">5</p>
</body></html>'''


class TestTraversal:
    def test_traversal_base(self):
        assert traverse_obj(_TEST_DATA, ('str',)) == 'str', \
            'allow tuple path'
        assert traverse_obj(_TEST_DATA, ['str']) == 'str', \
            'allow list path'
        assert traverse_obj(_TEST_DATA, (value for value in ('str',))) == 'str', \
            'allow iterable path'
        assert traverse_obj(_TEST_DATA, 'str') == 'str', \
            'single items should be treated as a path'
        assert traverse_obj(_TEST_DATA, 100) == 100, \
            'allow int path'
        assert traverse_obj(_TEST_DATA, 1.2) == 1.2, \
            'allow float path'
        assert traverse_obj(_TEST_DATA, None) == _TEST_DATA, \
            '`None` should not perform any modification'

    def test_traversal_ellipsis(self):
        assert traverse_obj(_TEST_DATA, ...) == [x for x in _TEST_DATA.values() if x not in (None, {})], \
            '`...` should give all non discarded values'
        assert traverse_obj(_TEST_DATA, ('urls', 0, ...)) == list(_TEST_DATA['urls'][0].values()), \
            '`...` selection for dicts should select all values'
        assert traverse_obj(_TEST_DATA, (..., ..., 'url')) == ['https://www.example.com/0', 'https://www.example.com/1'], \
            'nested `...` queries should work'
        assert traverse_obj(_TEST_DATA, (..., ..., 'index')) == list(range(4)), \
            '`...` query result should be flattened'
        assert traverse_obj(iter(range(4)), ...) == list(range(4)), \
            '`...` should accept iterables'

    def test_traversal_function(self):
        filter_func = lambda x, y: x == 'urls' and isinstance(y, list)
        assert traverse_obj(_TEST_DATA, filter_func) == [_TEST_DATA['urls']], \
            'function as query key should perform a filter based on (key, value)'
        assert traverse_obj(_TEST_DATA, lambda _, x: isinstance(x[0], str)) == ['str'], \
            'exceptions in the query function should be catched'
        assert traverse_obj(iter(range(4)), lambda _, x: x % 2 == 0) == [0, 2], \
            'function key should accept iterables'
        # Wrong function signature should raise (debug mode)
        with pytest.raises(Exception):
            traverse_obj(_TEST_DATA, lambda a: ...)
        with pytest.raises(Exception):
            traverse_obj(_TEST_DATA, lambda a, b, c: ...)

    def test_traversal_set(self):
        # transformation/type, like `expected_type`
        assert traverse_obj(_TEST_DATA, (..., {str.upper})) == ['STR'], \
            'Function in set should be a transformation'
        assert traverse_obj(_TEST_DATA, (..., {str})) == ['str'], \
            'Type in set should be a type filter'
        assert traverse_obj(_TEST_DATA, (..., {str, int})) == [100, 'str'], \
            'Multiple types in set should be a type filter'
        assert traverse_obj(_TEST_DATA, {dict}) == _TEST_DATA, \
            'A single set should be wrapped into a path'
        assert traverse_obj(_TEST_DATA, (..., {str.upper})) == ['STR'], \
            'Transformation function should not raise'
        expected = [x for x in map(str_or_none, _TEST_DATA.values()) if x is not None]
        assert traverse_obj(_TEST_DATA, (..., {str_or_none})) == expected, \
            'Function in set should be a transformation'
        assert traverse_obj(_TEST_DATA, ('fail', {lambda _: 'const'})) == 'const', \
            'Function in set should always be called'
        # Sets with length < 1 or > 1 not including only types should raise
        with pytest.raises(Exception):
            traverse_obj(_TEST_DATA, set())
        with pytest.raises(Exception):
            traverse_obj(_TEST_DATA, {str.upper, str})

    def test_traversal_slice(self):
        _SLICE_DATA = [0, 1, 2, 3, 4]

        assert traverse_obj(_TEST_DATA, ('dict', slice(1))) is None, \
            'slice on a dictionary should not throw'
        assert traverse_obj(_SLICE_DATA, slice(1)) == _SLICE_DATA[:1], \
            'slice key should apply slice to sequence'
        assert traverse_obj(_SLICE_DATA, slice(1, 2)) == _SLICE_DATA[1:2], \
            'slice key should apply slice to sequence'
        assert traverse_obj(_SLICE_DATA, slice(1, 4, 2)) == _SLICE_DATA[1:4:2], \
            'slice key should apply slice to sequence'

    def test_traversal_alternatives(self):
        assert traverse_obj(_TEST_DATA, 'fail', 'str') == 'str', \
            'multiple `paths` should be treated as alternative paths'
        assert traverse_obj(_TEST_DATA, 'str', 100) == 'str', \
            'alternatives should exit early'
        assert traverse_obj(_TEST_DATA, 'fail', 'fail') is None, \
            'alternatives should return `default` if exhausted'
        assert traverse_obj(_TEST_DATA, (..., 'fail'), 100) == 100, \
            'alternatives should track their own branching return'
        assert traverse_obj(_TEST_DATA, ('dict', ...), ('data', ...)) == list(_TEST_DATA['data']), \
            'alternatives on empty objects should search further'

    def test_traversal_branching_nesting(self):
        assert traverse_obj(_TEST_DATA, ('urls', (3, 0), 'url')) == ['https://www.example.com/0'], \
            'tuple as key should be treated as branches'
        assert traverse_obj(_TEST_DATA, ('urls', [3, 0], 'url')) == ['https://www.example.com/0'], \
            'list as key should be treated as branches'
        assert traverse_obj(_TEST_DATA, ('urls', ((1, 'fail'), (0, 'url')))) == ['https://www.example.com/0'], \
            'double nesting in path should be treated as paths'
        assert traverse_obj(['0', [1, 2]], [(0, 1), 0]) == [1], \
            'do not fail early on branching'
        expected = ['https://www.example.com/0', 'https://www.example.com/1']
        assert traverse_obj(_TEST_DATA, ('urls', ((0, ('fail', 'url')), (1, 'url')))) == expected, \
            'tripple nesting in path should be treated as branches'
        assert traverse_obj(_TEST_DATA, ('urls', ('fail', (..., 'url')))) == expected, \
            'ellipsis as branch path start gets flattened'

    def test_traversal_dict(self):
        assert traverse_obj(_TEST_DATA, {0: 100, 1: 1.2}) == {0: 100, 1: 1.2}, \
            'dict key should result in a dict with the same keys'
        expected = {0: 'https://www.example.com/0'}
        assert traverse_obj(_TEST_DATA, {0: ('urls', 0, 'url')}) == expected, \
            'dict key should allow paths'
        expected = {0: ['https://www.example.com/0']}
        assert traverse_obj(_TEST_DATA, {0: ('urls', (3, 0), 'url')}) == expected, \
            'tuple in dict path should be treated as branches'
        assert traverse_obj(_TEST_DATA, {0: ('urls', ((1, 'fail'), (0, 'url')))}) == expected, \
            'double nesting in dict path should be treated as paths'
        expected = {0: ['https://www.example.com/1', 'https://www.example.com/0']}
        assert traverse_obj(_TEST_DATA, {0: ('urls', ((1, ('fail', 'url')), (0, 'url')))}) == expected, \
            'tripple nesting in dict path should be treated as branches'
        assert traverse_obj(_TEST_DATA, {0: 'fail'}) == {}, \
            'remove `None` values when top level dict key fails'
        assert traverse_obj(_TEST_DATA, {0: 'fail'}, default=...) == {0: ...}, \
            'use `default` if key fails and `default`'
        assert traverse_obj(_TEST_DATA, {0: 'dict'}) == {}, \
            'remove empty values when dict key'
        assert traverse_obj(_TEST_DATA, {0: 'dict'}, default=...) == {0: ...}, \
            'use `default` when dict key and `default`'
        assert traverse_obj(_TEST_DATA, {0: {0: 'fail'}}) == {}, \
            'remove empty values when nested dict key fails'
        assert traverse_obj(None, {0: 'fail'}) == {}, \
            'default to dict if pruned'
        assert traverse_obj(None, {0: 'fail'}, default=...) == {0: ...}, \
            'default to dict if pruned and default is given'
        assert traverse_obj(_TEST_DATA, {0: {0: 'fail'}}, default=...) == {0: {0: ...}}, \
            'use nested `default` when nested dict key fails and `default`'
        assert traverse_obj(_TEST_DATA, {0: ('dict', ...)}) == {}, \
            'remove key if branch in dict key not successful'

    def test_traversal_default(self):
        _DEFAULT_DATA = {'None': None, 'int': 0, 'list': []}

        assert traverse_obj(_DEFAULT_DATA, 'fail') is None, \
            'default value should be `None`'
        assert traverse_obj(_DEFAULT_DATA, 'fail', 'fail', default=...) == ..., \
            'chained fails should result in default'
        assert traverse_obj(_DEFAULT_DATA, 'None', 'int') == 0, \
            'should not short cirquit on `None`'
        assert traverse_obj(_DEFAULT_DATA, 'fail', default=1) == 1, \
            'invalid dict key should result in `default`'
        assert traverse_obj(_DEFAULT_DATA, 'None', default=1) == 1, \
            '`None` is a deliberate sentinel and should become `default`'
        assert traverse_obj(_DEFAULT_DATA, ('list', 10)) is None, \
            '`IndexError` should result in `default`'
        assert traverse_obj(_DEFAULT_DATA, (..., 'fail'), default=1) == 1, \
            'if branched but not successful return `default` if defined, not `[]`'
        assert traverse_obj(_DEFAULT_DATA, (..., 'fail'), default=None) is None, \
            'if branched but not successful return `default` even if `default` is `None`'
        assert traverse_obj(_DEFAULT_DATA, (..., 'fail')) == [], \
            'if branched but not successful return `[]`, not `default`'
        assert traverse_obj(_DEFAULT_DATA, ('list', ...)) == [], \
            'if branched but object is empty return `[]`, not `default`'
        assert traverse_obj(None, ...) == [], \
            'if branched but object is `None` return `[]`, not `default`'
        assert traverse_obj({0: None}, (0, ...)) == [], \
            'if branched but state is `None` return `[]`, not `default`'

    @pytest.mark.parametrize('path', [
        ('fail', ...),
        (..., 'fail'),
        100 * ('fail',) + (...,),
        (...,) + 100 * ('fail',),
    ])
    def test_traversal_branching(self, path):
        assert traverse_obj({}, path) == [], \
            'if branched but state is `None`, return `[]` (not `default`)'
        assert traverse_obj({}, 'fail', path) == [], \
            'if branching in last alternative and previous did not match, return `[]` (not `default`)'
        assert traverse_obj({0: 'x'}, 0, path) == 'x', \
            'if branching in last alternative and previous did match, return single value'
        assert traverse_obj({0: 'x'}, path, 0) == 'x', \
            'if branching in first alternative and non-branching path does match, return single value'
        assert traverse_obj({}, path, 'fail') is None, \
            'if branching in first alternative and non-branching path does not match, return `default`'

    def test_traversal_expected_type(self):
        _EXPECTED_TYPE_DATA = {'str': 'str', 'int': 0}

        assert traverse_obj(_EXPECTED_TYPE_DATA, 'str', expected_type=str) == 'str', \
            'accept matching `expected_type` type'
        assert traverse_obj(_EXPECTED_TYPE_DATA, 'str', expected_type=int) is None, \
            'reject non matching `expected_type` type'
        assert traverse_obj(_EXPECTED_TYPE_DATA, 'int', expected_type=lambda x: str(x)) == '0', \
            'transform type using type function'
        assert traverse_obj(_EXPECTED_TYPE_DATA, 'str', expected_type=lambda _: 1 / 0) is None, \
            'wrap expected_type fuction in try_call'
        assert traverse_obj(_EXPECTED_TYPE_DATA, ..., expected_type=str) == ['str'], \
            'eliminate items that expected_type fails on'
        assert traverse_obj(_TEST_DATA, {0: 100, 1: 1.2}, expected_type=int) == {0: 100}, \
            'type as expected_type should filter dict values'
        assert traverse_obj(_TEST_DATA, {0: 100, 1: 1.2, 2: 'None'}, expected_type=str_or_none) == {0: '100', 1: '1.2'}, \
            'function as expected_type should transform dict values'
        assert traverse_obj(_TEST_DATA, ({0: 1.2}, 0, {int_or_none}), expected_type=int) == 1, \
            'expected_type should not filter non final dict values'
        assert traverse_obj(_TEST_DATA, {0: {0: 100, 1: 'str'}}, expected_type=int) == {0: {0: 100}}, \
            'expected_type should transform deep dict values'
        assert traverse_obj(_TEST_DATA, [({0: '...'}, {0: '...'})], expected_type=type(...)) == [{0: ...}, {0: ...}], \
            'expected_type should transform branched dict values'
        assert traverse_obj({1: {3: 4}}, [(1, 2), 3], expected_type=int) == [4], \
            'expected_type regression for type matching in tuple branching'
        assert traverse_obj(_TEST_DATA, ['data', ...], expected_type=int) == [], \
            'expected_type regression for type matching in dict result'

    def test_traversal_get_all(self):
        _GET_ALL_DATA = {'key': [0, 1, 2]}

        assert traverse_obj(_GET_ALL_DATA, ('key', ...), get_all=False) == 0, \
            'if not `get_all`, return only first matching value'
        assert traverse_obj(_GET_ALL_DATA, ..., get_all=False) == [0, 1, 2], \
            'do not overflatten if not `get_all`'

    def test_traversal_casesense(self):
        _CASESENSE_DATA = {
            'KeY': 'value0',
            0: {
                'KeY': 'value1',
                0: {'KeY': 'value2'},
            },
        }

        assert traverse_obj(_CASESENSE_DATA, 'key') is None, \
            'dict keys should be case sensitive unless `casesense`'
        assert traverse_obj(_CASESENSE_DATA, 'keY', casesense=False) == 'value0', \
            'allow non matching key case if `casesense`'
        assert traverse_obj(_CASESENSE_DATA, [0, ('keY',)], casesense=False) == ['value1'], \
            'allow non matching key case in branch if `casesense`'
        assert traverse_obj(_CASESENSE_DATA, [0, ([0, 'keY'],)], casesense=False) == ['value2'], \
            'allow non matching key case in branch path if `casesense`'

    def test_traversal_traverse_string(self):
        _TRAVERSE_STRING_DATA = {'str': 'str', 1.2: 1.2}

        assert traverse_obj(_TRAVERSE_STRING_DATA, ('str', 0)) is None, \
            'do not traverse into string if not `traverse_string`'
        assert traverse_obj(_TRAVERSE_STRING_DATA, ('str', 0), traverse_string=True) == 's', \
            'traverse into string if `traverse_string`'
        assert traverse_obj(_TRAVERSE_STRING_DATA, (1.2, 1), traverse_string=True) == '.', \
            'traverse into converted data if `traverse_string`'
        assert traverse_obj(_TRAVERSE_STRING_DATA, ('str', ...), traverse_string=True) == 'str', \
            '`...` should result in string (same value) if `traverse_string`'
        assert traverse_obj(_TRAVERSE_STRING_DATA, ('str', slice(0, None, 2)), traverse_string=True) == 'sr', \
            '`slice` should result in string if `traverse_string`'
        assert traverse_obj(_TRAVERSE_STRING_DATA, ('str', lambda i, v: i or v == 's'), traverse_string=True) == 'str', \
            'function should result in string if `traverse_string`'
        assert traverse_obj(_TRAVERSE_STRING_DATA, ('str', (0, 2)), traverse_string=True) == ['s', 'r'], \
            'branching should result in list if `traverse_string`'
        assert traverse_obj({}, (0, ...), traverse_string=True) == [], \
            'branching should result in list if `traverse_string`'
        assert traverse_obj({}, (0, lambda x, y: True), traverse_string=True) == [], \
            'branching should result in list if `traverse_string`'
        assert traverse_obj({}, (0, slice(1)), traverse_string=True) == [], \
            'branching should result in list if `traverse_string`'

    def test_traversal_re(self):
        mobj = re.fullmatch(r'0(12)(?P<group>3)(4)?', '0123')
        assert traverse_obj(mobj, ...) == [x for x in mobj.groups() if x is not None], \
            '`...` on a `re.Match` should give its `groups()`'
        assert traverse_obj(mobj, lambda k, _: k in (0, 2)) == ['0123', '3'], \
            'function on a `re.Match` should give groupno, value starting at 0'
        assert traverse_obj(mobj, 'group') == '3', \
            'str key on a `re.Match` should give group with that name'
        assert traverse_obj(mobj, 2) == '3', \
            'int key on a `re.Match` should give group with that name'
        assert traverse_obj(mobj, 'gRoUp', casesense=False) == '3', \
            'str key on a `re.Match` should respect casesense'
        assert traverse_obj(mobj, 'fail') is None, \
            'failing str key on a `re.Match` should return `default`'
        assert traverse_obj(mobj, 'gRoUpS', casesense=False) is None, \
            'failing str key on a `re.Match` should return `default`'
        assert traverse_obj(mobj, 8) is None, \
            'failing int key on a `re.Match` should return `default`'
        assert traverse_obj(mobj, lambda k, _: k in (0, 'group')) == ['0123', '3'], \
            'function on a `re.Match` should give group name as well'

    def test_traversal_xml_etree(self):
        etree = xml.etree.ElementTree.fromstring('''<?xml version="1.0"?>
        <data>
            <country name="Liechtenstein">
                <rank>1</rank>
                <year>2008</year>
                <gdppc>141100</gdppc>
                <neighbor name="Austria" direction="E"/>
                <neighbor name="Switzerland" direction="W"/>
            </country>
            <country name="Singapore">
                <rank>4</rank>
                <year>2011</year>
                <gdppc>59900</gdppc>
                <neighbor name="Malaysia" direction="N"/>
            </country>
            <country name="Panama">
                <rank>68</rank>
                <year>2011</year>
                <gdppc>13600</gdppc>
                <neighbor name="Costa Rica" direction="W"/>
                <neighbor name="Colombia" direction="E"/>
            </country>
        </data>''')
        assert traverse_obj(etree, '') == etree, \
            'empty str key should return the element itself'
        assert traverse_obj(etree, 'country') == list(etree), \
            'str key should lead all children with that tag name'
        assert traverse_obj(etree, ...) == list(etree), \
            '`...` as key should return all children'
        assert traverse_obj(etree, lambda _, x: x[0].text == '4') == [etree[1]], \
            'function as key should get element as value'
        assert traverse_obj(etree, lambda i, _: i == 1) == [etree[1]], \
            'function as key should get index as key'
        assert traverse_obj(etree, 0) == etree[0], \
            'int key should return the nth child'
        expected = ['Austria', 'Switzerland', 'Malaysia', 'Costa Rica', 'Colombia']
        assert traverse_obj(etree, './/neighbor/@name') == expected, \
            '`@<attribute>` at end of path should give that attribute'
        assert traverse_obj(etree, '//neighbor/@fail') == [None, None, None, None, None], \
            '`@<nonexistant>` at end of path should give `None`'
        assert traverse_obj(etree, ('//neighbor/@', 2)) == {'name': 'Malaysia', 'direction': 'N'}, \
            '`@` should give the full attribute dict'
        assert traverse_obj(etree, '//year/text()') == ['2008', '2011', '2011'], \
            '`text()` at end of path should give the inner text'
        assert traverse_obj(etree, '//*[@direction]/@direction') == ['E', 'W', 'N', 'W', 'E'], \
            'full Python xpath features should be supported'
        assert traverse_obj(etree, (0, '@name')) == 'Liechtenstein', \
            'special transformations should act on current element'
        assert traverse_obj(etree, ('country', 0, ..., 'text()', {int_or_none})) == [1, 2008, 141100], \
            'special transformations should act on current element'

    def test_traversal_unbranching(self):
        assert traverse_obj(_TEST_DATA, [(100, 1.2), all]) == [100, 1.2], \
            '`all` should give all results as list'
        assert traverse_obj(_TEST_DATA, [(100, 1.2), any]) == 100, \
            '`any` should give the first result'
        assert traverse_obj(_TEST_DATA, [100, all]) == [100], \
            '`all` should give list if non branching'
        assert traverse_obj(_TEST_DATA, [100, any]) == 100, \
            '`any` should give single item if non branching'
        assert traverse_obj(_TEST_DATA, [('dict', 'None', 100), all]) == [100], \
            '`all` should filter `None` and empty dict'
        assert traverse_obj(_TEST_DATA, [('dict', 'None', 100), any]) == 100, \
            '`any` should filter `None` and empty dict'
        assert traverse_obj(_TEST_DATA, [{
            'all': [('dict', 'None', 100, 1.2), all],
            'any': [('dict', 'None', 100, 1.2), any],
        }]) == {'all': [100, 1.2], 'any': 100}, \
            '`all`/`any` should apply to each dict path separately'
        assert traverse_obj(_TEST_DATA, [{
            'all': [('dict', 'None', 100, 1.2), all],
            'any': [('dict', 'None', 100, 1.2), any],
        }], get_all=False) == {'all': [100, 1.2], 'any': 100}, \
            '`all`/`any` should apply to dict regardless of `get_all`'
        assert traverse_obj(_TEST_DATA, [('dict', 'None', 100, 1.2), all, {float}]) is None, \
            '`all` should reset branching status'
        assert traverse_obj(_TEST_DATA, [('dict', 'None', 100, 1.2), any, {float}]) is None, \
            '`any` should reset branching status'
        assert traverse_obj(_TEST_DATA, [('dict', 'None', 100, 1.2), all, ..., {float}]) == [1.2], \
            '`all` should allow further branching'
        assert traverse_obj(_TEST_DATA, [('dict', 'None', 'urls', 'data'), any, ..., 'index']) == [0, 1], \
            '`any` should allow further branching'

    def test_traversal_morsel(self):
        morsel = http.cookies.Morsel()
        values = dict(zip(morsel, 'abcdefghijklmnop', strict=False))
        morsel.set('item_key', 'item_value', 'coded_value')
        morsel.update(values)
        values['key'] = 'item_key'
        values['value'] = 'item_value'

        for key, value in values.items():
            assert traverse_obj(morsel, key) == value, \
                'Morsel should provide access to all values'
        assert traverse_obj(morsel, ...) == list(values.values()), \
            '`...` should yield all values'
        assert traverse_obj(morsel, lambda k, v: True) == list(values.values()), \
            'function key should yield all values'
        assert traverse_obj(morsel, [(None,), any]) == morsel, \
            'Morsel should not be implicitly changed to dict on usage'

    def test_traversal_filter(self):
        data = [None, False, True, 0, 1, 0.0, 1.1, '', 'str', {}, {0: 0}, [], [1]]

        assert traverse_obj(data, [..., filter]) == [True, 1, 1.1, 'str', {0: 0}, [1]], \
            '`filter` should filter falsy values'


class TestTraversalHelpers:
    def test_traversal_require(self):
        with pytest.raises(ExtractorError):
            traverse_obj(_TEST_DATA, ['None', {require('value')}])
        assert traverse_obj(_TEST_DATA, ['str', {require('value')}]) == 'str', \
            '`require` should pass through non `None` values'

    def test_subs_list_to_dict(self):
        assert traverse_obj([
            {'name': 'de', 'url': 'https://example.com/subs/de.vtt'},
            {'name': 'en', 'url': 'https://example.com/subs/en1.ass'},
            {'name': 'en', 'url': 'https://example.com/subs/en2.ass'},
        ], [..., {
            'id': 'name',
            'url': 'url',
        }, all, {subs_list_to_dict}]) == {
            'de': [{'url': 'https://example.com/subs/de.vtt'}],
            'en': [
                {'url': 'https://example.com/subs/en1.ass'},
                {'url': 'https://example.com/subs/en2.ass'},
            ],
        }, 'function should build subtitle dict from list of subtitles'
        assert traverse_obj([
            {'name': 'de', 'url': 'https://example.com/subs/de.ass'},
            {'name': 'de'},
            {'name': 'en', 'content': 'content'},
            {'url': 'https://example.com/subs/en'},
        ], [..., {
            'id': 'name',
            'data': 'content',
            'url': 'url',
        }, all, {subs_list_to_dict(lang=None)}]) == {
            'de': [{'url': 'https://example.com/subs/de.ass'}],
            'en': [{'data': 'content'}],
        }, 'subs with mandatory items missing should be filtered'
        assert traverse_obj([
            {'url': 'https://example.com/subs/de.ass', 'name': 'de'},
            {'url': 'https://example.com/subs/en', 'name': 'en'},
        ], [..., {
            'id': 'name',
            'ext': ['url', {determine_ext(default_ext=None)}],
            'url': 'url',
        }, all, {subs_list_to_dict(ext='ext')}]) == {
            'de': [{'url': 'https://example.com/subs/de.ass', 'ext': 'ass'}],
            'en': [{'url': 'https://example.com/subs/en', 'ext': 'ext'}],
        }, '`ext` should set default ext but leave existing value untouched'
        assert traverse_obj([
            {'name': 'en', 'url': 'https://example.com/subs/en2', 'prio': True},
            {'name': 'en', 'url': 'https://example.com/subs/en1', 'prio': False},
        ], [..., {
            'id': 'name',
            'quality': ['prio', {int}],
            'url': 'url',
        }, all, {subs_list_to_dict(ext='ext')}]) == {'en': [
            {'url': 'https://example.com/subs/en1', 'ext': 'ext'},
            {'url': 'https://example.com/subs/en2', 'ext': 'ext'},
        ]}, '`quality` key should sort subtitle list accordingly'
        assert traverse_obj([
            {'name': 'de', 'url': 'https://example.com/subs/de.ass'},
            {'name': 'de'},
            {'name': 'en', 'content': 'content'},
            {'url': 'https://example.com/subs/en'},
        ], [..., {
            'id': 'name',
            'url': 'url',
            'data': 'content',
        }, all, {subs_list_to_dict(lang='en')}]) == {
            'de': [{'url': 'https://example.com/subs/de.ass'}],
            'en': [
                {'data': 'content'},
                {'url': 'https://example.com/subs/en'},
            ],
        }, 'optionally provided lang should be used if no id available'
        assert traverse_obj([
            {'name': 1, 'url': 'https://example.com/subs/de1'},
            {'name': {}, 'url': 'https://example.com/subs/de2'},
            {'name': 'de', 'ext': 1, 'url': 'https://example.com/subs/de3'},
            {'name': 'de', 'ext': {}, 'url': 'https://example.com/subs/de4'},
        ], [..., {
            'id': 'name',
            'url': 'url',
            'ext': 'ext',
        }, all, {subs_list_to_dict(lang=None)}]) == {
            'de': [
                {'url': 'https://example.com/subs/de3'},
                {'url': 'https://example.com/subs/de4'},
            ],
        }, 'non str types should be ignored for id and ext'
        assert traverse_obj([
            {'name': 1, 'url': 'https://example.com/subs/de1'},
            {'name': {}, 'url': 'https://example.com/subs/de2'},
            {'name': 'de', 'ext': 1, 'url': 'https://example.com/subs/de3'},
            {'name': 'de', 'ext': {}, 'url': 'https://example.com/subs/de4'},
        ], [..., {
            'id': 'name',
            'url': 'url',
            'ext': 'ext',
        }, all, {subs_list_to_dict(lang='de')}]) == {
            'de': [
                {'url': 'https://example.com/subs/de1'},
                {'url': 'https://example.com/subs/de2'},
                {'url': 'https://example.com/subs/de3'},
                {'url': 'https://example.com/subs/de4'},
            ],
        }, 'non str types should be replaced by default id'

    def test_trim_str(self):
        with pytest.raises(TypeError):
            trim_str('positional')

        assert callable(trim_str(start='a'))
        assert trim_str(start='ab')('abc') == 'c'
        assert trim_str(end='bc')('abc') == 'a'
        assert trim_str(start='a', end='c')('abc') == 'b'
        assert trim_str(start='ab', end='c')('abc') == ''
        assert trim_str(start='a', end='bc')('abc') == ''
        assert trim_str(start='ab', end='bc')('abc') == ''
        assert trim_str(start='abc', end='abc')('abc') == ''
        assert trim_str(start='', end='')('abc') == 'abc'

    def test_unpack(self):
        assert unpack(lambda *x: ''.join(map(str, x)))([1, 2, 3]) == '123'
        assert unpack(join_nonempty)([1, 2, 3]) == '1-2-3'
        assert unpack(join_nonempty, delim=' ')([1, 2, 3]) == '1 2 3'
        with pytest.raises(TypeError):
            unpack(join_nonempty)()
        with pytest.raises(TypeError):
            unpack()

    def test_find_element(self):
        for improper_kwargs in [
            dict(attr='data-id'),
            dict(value='y'),
            dict(attr='data-id', value='y', cls='a'),
            dict(attr='data-id', value='y', id='x'),
            dict(cls='a', id='x'),
            dict(cls='a', tag='p'),
            dict(cls='[ab]', regex=True),
        ]:
            with pytest.raises(AssertionError):
                find_element(**improper_kwargs)(_TEST_HTML)

        assert find_element(cls='a')(_TEST_HTML) == '1'
        assert find_element(cls='a', html=True)(_TEST_HTML) == '<div class="a">1</div>'
        assert find_element(id='x')(_TEST_HTML) == '2'
        assert find_element(id='[ex]')(_TEST_HTML) is None
        assert find_element(id='[ex]', regex=True)(_TEST_HTML) == '2'
        assert find_element(id='x', html=True)(_TEST_HTML) == '<div class="a" id="x" custom="z">2</div>'
        assert find_element(attr='data-id', value='y')(_TEST_HTML) == '3'
        assert find_element(attr='data-id', value='y(?:es)?')(_TEST_HTML) is None
        assert find_element(attr='data-id', value='y(?:es)?', regex=True)(_TEST_HTML) == '3'
        assert find_element(
            attr='data-id', value='y', html=True)(_TEST_HTML) == '<div class="b" data-id="y" custom="z">3</div>'

    def test_find_elements(self):
        for improper_kwargs in [
            dict(tag='p'),
            dict(attr='data-id'),
            dict(value='y'),
            dict(attr='data-id', value='y', cls='a'),
            dict(cls='a', tag='div'),
            dict(cls='[ab]', regex=True),
        ]:
            with pytest.raises(AssertionError):
                find_elements(**improper_kwargs)(_TEST_HTML)

        assert find_elements(cls='a')(_TEST_HTML) == ['1', '2', '4']
        assert find_elements(cls='a', html=True)(_TEST_HTML) == [
            '<div class="a">1</div>', '<div class="a" id="x" custom="z">2</div>', '<p class="a">4</p>']
        assert find_elements(attr='custom', value='z')(_TEST_HTML) == ['2', '3']
        assert find_elements(attr='custom', value='[ez]')(_TEST_HTML) == []
        assert find_elements(attr='custom', value='[ez]', regex=True)(_TEST_HTML) == ['2', '3', '5']


class TestDictGet:
    def test_dict_get(self):
        FALSE_VALUES = {
            'none': None,
            'false': False,
            'zero': 0,
            'empty_string': '',
            'empty_list': [],
        }
        d = {**FALSE_VALUES, 'a': 42}
        assert dict_get(d, 'a') == 42
        assert dict_get(d, 'b') is None
        assert dict_get(d, 'b', 42) == 42
        assert dict_get(d, ('a',)) == 42
        assert dict_get(d, ('b', 'a')) == 42
        assert dict_get(d, ('b', 'c', 'a', 'd')) == 42
        assert dict_get(d, ('b', 'c')) is None
        assert dict_get(d, ('b', 'c'), 42) == 42
        for key, false_value in FALSE_VALUES.items():
            assert dict_get(d, ('b', 'c', key)) is None
            assert dict_get(d, ('b', 'c', key), skip_false_values=False) == false_value
