#!/usr/bin/env python3

# Allow direct execution
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


import datetime as dt
import json
import math
import re
import unittest

from yt_dlp.utils.jslib import devalue


TEST_CASES_EQUALS = [{
    'name': 'int',
    'unparsed': [-42],
    'parsed': -42,
}, {
    'name': 'str',
    'unparsed': ['woo!!!'],
    'parsed': 'woo!!!',
}, {
    'name': 'Number',
    'unparsed': [['Object', 42]],
    'parsed': 42,
}, {
    'name': 'String',
    'unparsed': [['Object', 'yar']],
    'parsed': 'yar',
}, {
    'name': 'Infinity',
    'unparsed': -4,
    'parsed': math.inf,
}, {
    'name': 'negative Infinity',
    'unparsed': -5,
    'parsed': -math.inf,
}, {
    'name': 'negative zero',
    'unparsed': -6,
    'parsed': -0.0,
}, {
    'name': 'RegExp',
    'unparsed': [['RegExp', 'regexp', 'gim']],  # XXX: flags are ignored
    'parsed': re.compile('regexp'),
}, {
    'name': 'Date',
    'unparsed': [['Date', '2001-09-09T01:46:40.000Z']],
    'parsed': dt.datetime.fromtimestamp(1e9, tz=dt.timezone.utc),
}, {
    'name': 'Array',
    'unparsed': [[1, 2, 3], 'a', 'b', 'c'],
    'parsed': ['a', 'b', 'c'],
}, {
    'name': 'Array (empty)',
    'unparsed': [[]],
    'parsed': [],
}, {
    'name': 'Array (sparse)',
    'unparsed': [[-2, 1, -2], 'b'],
    'parsed': [None, 'b', None],
}, {
    'name': 'Object',
    'unparsed': [{'foo': 1, 'x-y': 2}, 'bar', 'z'],
    'parsed': {'foo': 'bar', 'x-y': 'z'},
}, {
    'name': 'Set',
    'unparsed': [['Set', 1, 2, 3], 1, 2, 3],
    'parsed': [1, 2, 3],
}, {
    'name': 'Map',
    'unparsed': [['Map', 1, 2], 'a', 'b'],
    'parsed': [['a', 'b']],
}, {
    'name': 'BigInt',
    'unparsed': [['BigInt', '1']],
    'parsed': 1,
}, {
    'name': 'Uint8Array',
    'unparsed': [['Uint8Array', 'AQID']],
    'parsed': [1, 2, 3],
}, {
    'name': 'ArrayBuffer',
    'unparsed': [['ArrayBuffer', 'AQID']],
    'parsed': [1, 2, 3],
}, {
    'name': 'str (repetition)',
    'unparsed': [[1, 1], 'a string'],
    'parsed': ['a string', 'a string'],
}, {
    'name': 'None (repetition)',
    'unparsed': [[1, 1], None],
    'parsed': [None, None],
}, {
    'name': 'dict (repetition)',
    'unparsed': [[1, 1], {}],
    'parsed': [{}, {}],
}, {
    'name': 'Object without prototype',
    'unparsed': [['null']],
    'parsed': {},
}, {
    'name': 'cross-realm POJO',
    'unparsed': [{}],
    'parsed': {},
}]

TEST_CASES_IS = [{
    'name': 'bool',
    'unparsed': [True],
    'parsed': True,
}, {
    'name': 'Boolean',
    'unparsed': [['Object', False]],
    'parsed': False,
}, {
    'name': 'undefined',
    'unparsed': -1,
    'parsed': None,
}, {
    'name': 'null',
    'unparsed': [None],
    'parsed': None,
}, {
    'name': 'NaN',
    'unparsed': -3,
    'parsed': math.nan,
}]

TEST_CASES_INVALID = [{
    'name': 'empty string',
    'unparsed': '',
    'error': ValueError,
    'pattern': r'expected int or list as input',
}, {
    'name': 'hole',
    'unparsed': -2,
    'error': ValueError,
    'pattern': r'invalid integer input',
}, {
    'name': 'string',
    'unparsed': 'hello',
    'error': ValueError,
    'pattern': r'expected int or list as input',
}, {
    'name': 'number',
    'unparsed': 42,
    'error': ValueError,
    'pattern': r'invalid integer input',
}, {
    'name': 'boolean',
    'unparsed': True,
    'error': ValueError,
    'pattern': r'expected int or list as input',
}, {
    'name': 'null',
    'unparsed': None,
    'error': ValueError,
    'pattern': r'expected int or list as input',
}, {
    'name': 'object',
    'unparsed': {},
    'error': ValueError,
    'pattern': r'expected int or list as input',
}, {
    'name': 'empty array',
    'unparsed': [],
    'error': ValueError,
    'pattern': r'expected a non-empty list as input',
}, {
    'name': 'Python negative indexing',
    'unparsed': [[1, 2, 3, 4, 5, 6, 7, -7], 1, 2, 3, 4, 5, 6, 7],
    'error': IndexError,
    'pattern': r'invalid index: -7',
}]


class TestDevalue(unittest.TestCase):
    def test_devalue_parse_equals(self):
        for tc in TEST_CASES_EQUALS:
            self.assertEqual(devalue.parse(tc['unparsed']), tc['parsed'], tc['name'])

    def test_devalue_parse_is(self):
        for tc in TEST_CASES_IS:
            self.assertIs(devalue.parse(tc['unparsed']), tc['parsed'], tc['name'])

    def test_devalue_parse_invalid(self):
        for tc in TEST_CASES_INVALID:
            with self.assertRaisesRegex(tc['error'], tc['pattern'], msg=tc['name']):
                devalue.parse(tc['unparsed'])

    def test_devalue_parse_cyclical(self):
        name = 'Map (cyclical)'
        result = devalue.parse([['Map', 1, 0], 'self'])
        self.assertEqual(result[0][0], 'self', name)
        self.assertIs(result, result[0][1], name)

        name = 'Set (cyclical)'
        result = devalue.parse([['Set', 0, 1], 42])
        self.assertEqual(result[1], 42, name)
        self.assertIs(result, result[0], name)

        result = devalue.parse([[0]])
        self.assertIs(result, result[0], 'Array (cyclical)')

        name = 'Object (cyclical)'
        result = devalue.parse([{'self': 0}])
        self.assertIs(result, result['self'], name)

        name = 'Object with null prototype (cyclical)'
        result = devalue.parse([['null', 'self', 0]])
        self.assertIs(result, result['self'], name)

        name = 'Objects (cyclical)'
        result = devalue.parse([[1, 2], {'second': 2}, {'first': 1}])
        self.assertIs(result[0], result[1]['first'], name)
        self.assertIs(result[1], result[0]['second'], name)

    def test_devalue_parse_revivers(self):
        self.assertEqual(
            devalue.parse([['indirect', 1], {'a': 2}, 'b'], revivers={'indirect': lambda x: x}),
            {'a': 'b'}, 'revivers (indirect)')

        self.assertEqual(
            devalue.parse([['parse', 1], '{"a":0}'], revivers={'parse': lambda x: json.loads(x)}),
            {'a': 0}, 'revivers (parse)')


if __name__ == '__main__':
    unittest.main()
