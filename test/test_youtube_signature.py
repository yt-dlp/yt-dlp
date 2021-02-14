#!/usr/bin/env python

from __future__ import unicode_literals

# Allow direct execution
import os
import sys
import unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import io
import re
import string

from test.helper import FakeYDL
from yt_dlp.extractor import YoutubeIE
from yt_dlp.compat import compat_str, compat_urlretrieve

_TESTS = [
    (
        'https://s.ytimg.com/yts/jsbin/html5player-vflHOr_nV.js',
        86,
        '>=<;:/.-[+*)(\'&%$#"!ZYX0VUTSRQPONMLKJIHGFEDCBA\\yxwvutsrqponmlkjihgfedcba987654321',
    ),
    (
        'https://s.ytimg.com/yts/jsbin/html5player-vfldJ8xgI.js',
        85,
        '3456789a0cdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRS[UVWXYZ!"#$%&\'()*+,-./:;<=>?@',
    ),
    (
        'https://s.ytimg.com/yts/jsbin/html5player-vfle-mVwz.js',
        90,
        ']\\[@?>=<;:/.-,+*)(\'&%$#"hZYXWVUTSRQPONMLKJIHGFEDCBAzyxwvutsrqponmlkjiagfedcb39876',
    ),
    (
        'https://s.ytimg.com/yts/jsbin/html5player-en_US-vfl0Cbn9e.js',
        84,
        'O1I3456789abcde0ghijklmnopqrstuvwxyzABCDEFGHfJKLMN2PQRSTUVW@YZ!"#$%&\'()*+,-./:;<=',
    ),
    (
        'https://s.ytimg.com/yts/jsbin/html5player-en_US-vflXGBaUN.js',
        '2ACFC7A61CA478CD21425E5A57EBD73DDC78E22A.2094302436B2D377D14A3BBA23022D023B8BC25AA',
        'A52CB8B320D22032ABB3A41D773D2B6342034902.A22E87CDD37DBE75A5E52412DC874AC16A7CFCA2',
    ),
    (
        'https://s.ytimg.com/yts/jsbin/html5player-en_US-vflBb0OQx.js',
        84,
        '123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQ0STUVWXYZ!"#$%&\'()*+,@./:;<=>'
    ),
    (
        'https://s.ytimg.com/yts/jsbin/html5player-en_US-vfl9FYC6l.js',
        83,
        '123456789abcdefghijklmnopqr0tuvwxyzABCDETGHIJKLMNOPQRS>UVWXYZ!"#$%&\'()*+,-./:;<=F'
    ),
    (
        'https://s.ytimg.com/yts/jsbin/html5player-en_US-vflCGk6yw/html5player.js',
        '4646B5181C6C3020DF1D9C7FCFEA.AD80ABF70C39BD369CCCAE780AFBB98FA6B6CB42766249D9488C288',
        '82C8849D94266724DC6B6AF89BBFA087EACCD963.B93C07FBA084ACAEFCF7C9D1FD0203C6C1815B6B'
    ),
    (
        'https://s.ytimg.com/yts/jsbin/html5player-en_US-vflKjOTVq/html5player.js',
        '312AA52209E3623129A412D56A40F11CB0AF14AE.3EE09501CB14E3BCDC3B2AE808BF3F1D14E7FBF12',
        '112AA5220913623229A412D56A40F11CB0AF14AE.3EE0950FCB14EEBCDC3B2AE808BF331D14E7FBF3',
    )
]


class TestPlayerInfo(unittest.TestCase):
    def test_youtube_extract_player_info(self):
        PLAYER_URLS = (
            ('https://www.youtube.com/s/player/64dddad9/player_ias.vflset/en_US/base.js', '64dddad9'),
            ('https://www.youtube.com/s/player/64dddad9/player_ias.vflset/fr_FR/base.js', '64dddad9'),
            ('https://www.youtube.com/s/player/64dddad9/player-plasma-ias-phone-en_US.vflset/base.js', '64dddad9'),
            ('https://www.youtube.com/s/player/64dddad9/player-plasma-ias-phone-de_DE.vflset/base.js', '64dddad9'),
            ('https://www.youtube.com/s/player/64dddad9/player-plasma-ias-tablet-en_US.vflset/base.js', '64dddad9'),
            # obsolete
            ('https://www.youtube.com/yts/jsbin/player_ias-vfle4-e03/en_US/base.js', 'vfle4-e03'),
            ('https://www.youtube.com/yts/jsbin/player_ias-vfl49f_g4/en_US/base.js', 'vfl49f_g4'),
            ('https://www.youtube.com/yts/jsbin/player_ias-vflCPQUIL/en_US/base.js', 'vflCPQUIL'),
            ('https://www.youtube.com/yts/jsbin/player-vflzQZbt7/en_US/base.js', 'vflzQZbt7'),
            ('https://www.youtube.com/yts/jsbin/player-en_US-vflaxXRn1/base.js', 'vflaxXRn1'),
            ('https://s.ytimg.com/yts/jsbin/html5player-en_US-vflXGBaUN.js', 'vflXGBaUN'),
            ('https://s.ytimg.com/yts/jsbin/html5player-en_US-vflKjOTVq/html5player.js', 'vflKjOTVq'),
        )
        for player_url, expected_player_id in PLAYER_URLS:
            player_id = YoutubeIE._extract_player_info(player_url)
            self.assertEqual(player_id, expected_player_id)


class TestSignature(unittest.TestCase):
    def setUp(self):
        TEST_DIR = os.path.dirname(os.path.abspath(__file__))
        self.TESTDATA_DIR = os.path.join(TEST_DIR, 'testdata')
        if not os.path.exists(self.TESTDATA_DIR):
            os.mkdir(self.TESTDATA_DIR)


def make_tfunc(url, sig_input, expected_sig):
    m = re.match(r'.*-([a-zA-Z0-9_-]+)(?:/watch_as3|/html5player)?\.[a-z]+$', url)
    assert m, '%r should follow URL format' % url
    test_id = m.group(1)

    def test_func(self):
        basename = 'player-%s.js' % test_id
        fn = os.path.join(self.TESTDATA_DIR, basename)

        if not os.path.exists(fn):
            compat_urlretrieve(url, fn)

        ydl = FakeYDL()
        ie = YoutubeIE(ydl)
        with io.open(fn, encoding='utf-8') as testf:
            jscode = testf.read()
        func = ie._parse_sig_js(jscode)
        src_sig = (
            compat_str(string.printable[:sig_input])
            if isinstance(sig_input, int) else sig_input)
        got_sig = func(src_sig)
        self.assertEqual(got_sig, expected_sig)

    test_func.__name__ = str('test_signature_js_' + test_id)
    setattr(TestSignature, test_func.__name__, test_func)


for test_spec in _TESTS:
    make_tfunc(*test_spec)


if __name__ == '__main__':
    unittest.main()
