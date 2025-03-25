#!/usr/bin/env python3

# Allow direct execution
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


import contextlib
import re
import string
import urllib.request

from test.helper import FakeYDL, is_download_test
from yt_dlp.extractor import YoutubeIE
from yt_dlp.jsinterp import JSInterpreter

_SIG_TESTS = [
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
        '123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQ0STUVWXYZ!"#$%&\'()*+,@./:;<=>',
    ),
    (
        'https://s.ytimg.com/yts/jsbin/html5player-en_US-vfl9FYC6l.js',
        83,
        '123456789abcdefghijklmnopqr0tuvwxyzABCDETGHIJKLMNOPQRS>UVWXYZ!"#$%&\'()*+,-./:;<=F',
    ),
    (
        'https://s.ytimg.com/yts/jsbin/html5player-en_US-vflCGk6yw/html5player.js',
        '4646B5181C6C3020DF1D9C7FCFEA.AD80ABF70C39BD369CCCAE780AFBB98FA6B6CB42766249D9488C288',
        '82C8849D94266724DC6B6AF89BBFA087EACCD963.B93C07FBA084ACAEFCF7C9D1FD0203C6C1815B6B',
    ),
    (
        'https://s.ytimg.com/yts/jsbin/html5player-en_US-vflKjOTVq/html5player.js',
        '312AA52209E3623129A412D56A40F11CB0AF14AE.3EE09501CB14E3BCDC3B2AE808BF3F1D14E7FBF12',
        '112AA5220913623229A412D56A40F11CB0AF14AE.3EE0950FCB14EEBCDC3B2AE808BF331D14E7FBF3',
    ),
    (
        'https://www.youtube.com/s/player/6ed0d907/player_ias.vflset/en_US/base.js',
        '2aq0aqSyOoJXtK73m-uME_jv7-pT15gOFC02RFkGMqWpzEICs69VdbwQ0LDp1v7j8xx92efCJlYFYb1sUkkBSPOlPmXgIARw8JQ0qOAOAA',
        'AOq0QJ8wRAIgXmPlOPSBkkUs1bYFYlJCfe29xx8j7v1pDL2QwbdV96sCIEzpWqMGkFR20CFOg51Tp-7vj_EMu-m37KtXJoOySqa0',
    ),
    (
        'https://www.youtube.com/s/player/3bb1f723/player_ias.vflset/en_US/base.js',
        '2aq0aqSyOoJXtK73m-uME_jv7-pT15gOFC02RFkGMqWpzEICs69VdbwQ0LDp1v7j8xx92efCJlYFYb1sUkkBSPOlPmXgIARw8JQ0qOAOAA',
        'MyOSJXtKI3m-uME_jv7-pT12gOFC02RFkGoqWpzE0Cs69VdbwQ0LDp1v7j8xx92efCJlYFYb1sUkkBSPOlPmXgIARw8JQ0qOAOAA',
    ),
    (
        'https://www.youtube.com/s/player/2f1832d2/player_ias.vflset/en_US/base.js',
        '2aq0aqSyOoJXtK73m-uME_jv7-pT15gOFC02RFkGMqWpzEICs69VdbwQ0LDp1v7j8xx92efCJlYFYb1sUkkBSPOlPmXgIARw8JQ0qOAOAA',
        '0QJ8wRAIgXmPlOPSBkkUs1bYFYlJCfe29xxAj7v1pDL0QwbdV96sCIEzpWqMGkFR20CFOg51Tp-7vj_EMu-m37KtXJ2OySqa0q',
    ),
    (
        'https://www.youtube.com/s/player/643afba4/tv-player-ias.vflset/tv-player-ias.js',
        '2aq0aqSyOoJXtK73m-uME_jv7-pT15gOFC02RFkGMqWpzEICs69VdbwQ0LDp1v7j8xx92efCJlYFYb1sUkkBSPOlPmXgIARw8JQ0qOAOAA',
        'AAOAOq0QJ8wRAIgXmPlOPSBkkUs1bYFYlJCfe29xx8j7vgpDL0QwbdV06sCIEzpWqMGkFR20CFOS21Tp-7vj_EMu-m37KtXJoOy1',
    ),
    (
        'https://www.youtube.com/s/player/363db69b/player_ias.vflset/en_US/base.js',
        '2aq0aqSyOoJXtK73m-uME_jv7-pT15gOFC02RFkGMqWpzEICs69VdbwQ0LDp1v7j8xx92efCJlYFYb1sUkkBSPOlPmXgIARw8JQ0qOAOAA',
        '0aqSyOoJXtK73m-uME_jv7-pT15gOFC02RFkGMqWpz2ICs6EVdbwQ0LDp1v7j8xx92efCJlYFYb1sUkkBSPOlPmXgIARw8JQ0qOAOAA',
    ),
    (
        'https://www.youtube.com/s/player/4fcd6e4a/player_ias.vflset/en_US/base.js',
        '2aq0aqSyOoJXtK73m-uME_jv7-pT15gOFC02RFkGMqWpzEICs69VdbwQ0LDp1v7j8xx92efCJlYFYb1sUkkBSPOlPmXgIARw8JQ0qOAOAA',
        'wAOAOq0QJ8ARAIgXmPlOPSBkkUs1bYFYlJCfe29xx8q7v1pDL0QwbdV96sCIEzpWqMGkFR20CFOg51Tp-7vj_EMu-m37KtXJoOySqa0',
    ),
]

_NSIG_TESTS = [
    (
        'https://www.youtube.com/s/player/7862ca1f/player_ias.vflset/en_US/base.js',
        'X_LCxVDjAavgE5t', 'yxJ1dM6iz5ogUg',
    ),
    (
        'https://www.youtube.com/s/player/9216d1f7/player_ias.vflset/en_US/base.js',
        'SLp9F5bwjAdhE9F-', 'gWnb9IK2DJ8Q1w',
    ),
    (
        'https://www.youtube.com/s/player/f8cb7a3b/player_ias.vflset/en_US/base.js',
        'oBo2h5euWy6osrUt', 'ivXHpm7qJjJN',
    ),
    (
        'https://www.youtube.com/s/player/2dfe380c/player_ias.vflset/en_US/base.js',
        'oBo2h5euWy6osrUt', '3DIBbn3qdQ',
    ),
    (
        'https://www.youtube.com/s/player/f1ca6900/player_ias.vflset/en_US/base.js',
        'cu3wyu6LQn2hse', 'jvxetvmlI9AN9Q',
    ),
    (
        'https://www.youtube.com/s/player/8040e515/player_ias.vflset/en_US/base.js',
        'wvOFaY-yjgDuIEg5', 'HkfBFDHmgw4rsw',
    ),
    (
        'https://www.youtube.com/s/player/e06dea74/player_ias.vflset/en_US/base.js',
        'AiuodmaDDYw8d3y4bf', 'ankd8eza2T6Qmw',
    ),
    (
        'https://www.youtube.com/s/player/5dd88d1d/player-plasma-ias-phone-en_US.vflset/base.js',
        'kSxKFLeqzv_ZyHSAt', 'n8gS8oRlHOxPFA',
    ),
    (
        'https://www.youtube.com/s/player/324f67b9/player_ias.vflset/en_US/base.js',
        'xdftNy7dh9QGnhW', '22qLGxrmX8F1rA',
    ),
    (
        'https://www.youtube.com/s/player/4c3f79c5/player_ias.vflset/en_US/base.js',
        'TDCstCG66tEAO5pR9o', 'dbxNtZ14c-yWyw',
    ),
    (
        'https://www.youtube.com/s/player/c81bbb4a/player_ias.vflset/en_US/base.js',
        'gre3EcLurNY2vqp94', 'Z9DfGxWP115WTg',
    ),
    (
        'https://www.youtube.com/s/player/1f7d5369/player_ias.vflset/en_US/base.js',
        'batNX7sYqIJdkJ', 'IhOkL_zxbkOZBw',
    ),
    (
        'https://www.youtube.com/s/player/009f1d77/player_ias.vflset/en_US/base.js',
        '5dwFHw8aFWQUQtffRq', 'audescmLUzI3jw',
    ),
    (
        'https://www.youtube.com/s/player/dc0c6770/player_ias.vflset/en_US/base.js',
        '5EHDMgYLV6HPGk_Mu-kk', 'n9lUJLHbxUI0GQ',
    ),
    (
        'https://www.youtube.com/s/player/113ca41c/player_ias.vflset/en_US/base.js',
        'cgYl-tlYkhjT7A', 'hI7BBr2zUgcmMg',
    ),
    (
        'https://www.youtube.com/s/player/c57c113c/player_ias.vflset/en_US/base.js',
        'M92UUMHa8PdvPd3wyM', '3hPqLJsiNZx7yA',
    ),
    (
        'https://www.youtube.com/s/player/5a3b6271/player_ias.vflset/en_US/base.js',
        'B2j7f_UPT4rfje85Lu_e', 'm5DmNymaGQ5RdQ',
    ),
    (
        'https://www.youtube.com/s/player/7a062b77/player_ias.vflset/en_US/base.js',
        'NRcE3y3mVtm_cV-W', 'VbsCYUATvqlt5w',
    ),
    (
        'https://www.youtube.com/s/player/dac945fd/player_ias.vflset/en_US/base.js',
        'o8BkRxXhuYsBCWi6RplPdP', '3Lx32v_hmzTm6A',
    ),
    (
        'https://www.youtube.com/s/player/6f20102c/player_ias.vflset/en_US/base.js',
        'lE8DhoDmKqnmJJ', 'pJTTX6XyJP2BYw',
    ),
    (
        'https://www.youtube.com/s/player/cfa9e7cb/player_ias.vflset/en_US/base.js',
        'aCi3iElgd2kq0bxVbQ', 'QX1y8jGb2IbZ0w',
    ),
    (
        'https://www.youtube.com/s/player/8c7583ff/player_ias.vflset/en_US/base.js',
        '1wWCVpRR96eAmMI87L', 'KSkWAVv1ZQxC3A',
    ),
    (
        'https://www.youtube.com/s/player/b7910ca8/player_ias.vflset/en_US/base.js',
        '_hXMCwMt9qE310D', 'LoZMgkkofRMCZQ',
    ),
    (
        'https://www.youtube.com/s/player/590f65a6/player_ias.vflset/en_US/base.js',
        '1tm7-g_A9zsI8_Lay_', 'xI4Vem4Put_rOg',
    ),
    (
        'https://www.youtube.com/s/player/b22ef6e7/player_ias.vflset/en_US/base.js',
        'b6HcntHGkvBLk_FRf', 'kNPW6A7FyP2l8A',
    ),
    (
        'https://www.youtube.com/s/player/3400486c/player_ias.vflset/en_US/base.js',
        'lL46g3XifCKUZn1Xfw', 'z767lhet6V2Skl',
    ),
    (
        'https://www.youtube.com/s/player/20dfca59/player_ias.vflset/en_US/base.js',
        '-fLCxedkAk4LUTK2', 'O8kfRq1y1eyHGw',
    ),
    (
        'https://www.youtube.com/s/player/b12cc44b/player_ias.vflset/en_US/base.js',
        'keLa5R2U00sR9SQK', 'N1OGyujjEwMnLw',
    ),
    (
        'https://www.youtube.com/s/player/3bb1f723/player_ias.vflset/en_US/base.js',
        'gK15nzVyaXE9RsMP3z', 'ZFFWFLPWx9DEgQ',
    ),
    (
        'https://www.youtube.com/s/player/2f1832d2/player_ias.vflset/en_US/base.js',
        'YWt1qdbe8SAfkoPHW5d', 'RrRjWQOJmBiP',
    ),
    (
        'https://www.youtube.com/s/player/9c6dfc4a/player_ias.vflset/en_US/base.js',
        'jbu7ylIosQHyJyJV', 'uwI0ESiynAmhNg',
    ),
    (
        'https://www.youtube.com/s/player/e7567ecf/player_ias_tce.vflset/en_US/base.js',
        'Sy4aDGc0VpYRR9ew_', '5UPOT1VhoZxNLQ',
    ),
    (
        'https://www.youtube.com/s/player/d50f54ef/player_ias_tce.vflset/en_US/base.js',
        'Ha7507LzRmH3Utygtj', 'XFTb2HoeOE5MHg',
    ),
    (
        'https://www.youtube.com/s/player/074a8365/player_ias_tce.vflset/en_US/base.js',
        'Ha7507LzRmH3Utygtj', 'ufTsrE0IVYrkl8v',
    ),
    (
        'https://www.youtube.com/s/player/643afba4/player_ias.vflset/en_US/base.js',
        'N5uAlLqm0eg1GyHO', 'dCBQOejdq5s-ww',
    ),
    (
        'https://www.youtube.com/s/player/69f581a5/tv-player-ias.vflset/tv-player-ias.js',
        '-qIP447rVlTTwaZjY', 'KNcGOksBAvwqQg',
    ),
    (
        'https://www.youtube.com/s/player/643afba4/tv-player-ias.vflset/tv-player-ias.js',
        'ir9-V6cdbCiyKxhr', '2PL7ZDYAALMfmA',
    ),
    (
        'https://www.youtube.com/s/player/363db69b/player_ias.vflset/en_US/base.js',
        'eWYu5d5YeY_4LyEDc', 'XJQqf-N7Xra3gg',
    ),
    (
        'https://www.youtube.com/s/player/4fcd6e4a/player_ias.vflset/en_US/base.js',
        'o_L251jm8yhZkWtBW', 'lXoxI3XvToqn6A',
    ),
]


@is_download_test
class TestPlayerInfo(unittest.TestCase):
    def test_youtube_extract_player_info(self):
        PLAYER_URLS = (
            ('https://www.youtube.com/s/player/4c3f79c5/player_ias.vflset/en_US/base.js', '4c3f79c5'),
            ('https://www.youtube.com/s/player/64dddad9/player_ias.vflset/en_US/base.js', '64dddad9'),
            ('https://www.youtube.com/s/player/64dddad9/player_ias.vflset/fr_FR/base.js', '64dddad9'),
            ('https://www.youtube.com/s/player/64dddad9/player-plasma-ias-phone-en_US.vflset/base.js', '64dddad9'),
            ('https://www.youtube.com/s/player/64dddad9/player-plasma-ias-phone-de_DE.vflset/base.js', '64dddad9'),
            ('https://www.youtube.com/s/player/64dddad9/player-plasma-ias-tablet-en_US.vflset/base.js', '64dddad9'),
            ('https://www.youtube.com/s/player/e7567ecf/player_ias_tce.vflset/en_US/base.js', 'e7567ecf'),
            ('https://www.youtube.com/s/player/643afba4/tv-player-ias.vflset/tv-player-ias.js', '643afba4'),
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


@is_download_test
class TestSignature(unittest.TestCase):
    def setUp(self):
        TEST_DIR = os.path.dirname(os.path.abspath(__file__))
        self.TESTDATA_DIR = os.path.join(TEST_DIR, 'testdata/sigs')
        if not os.path.exists(self.TESTDATA_DIR):
            os.mkdir(self.TESTDATA_DIR)

    def tearDown(self):
        with contextlib.suppress(OSError):
            for f in os.listdir(self.TESTDATA_DIR):
                os.remove(f)


def t_factory(name, sig_func, url_pattern):
    def make_tfunc(url, sig_input, expected_sig):
        m = url_pattern.match(url)
        assert m, f'{url!r} should follow URL format'
        test_id = re.sub(r'[/.-]', '_', m.group('id') or m.group('compat_id'))

        def test_func(self):
            basename = f'player-{name}-{test_id}.js'
            fn = os.path.join(self.TESTDATA_DIR, basename)

            if not os.path.exists(fn):
                urllib.request.urlretrieve(url, fn)
            with open(fn, encoding='utf-8') as testf:
                jscode = testf.read()
            self.assertEqual(sig_func(jscode, sig_input), expected_sig)

        test_func.__name__ = f'test_{name}_js_{test_id}'
        setattr(TestSignature, test_func.__name__, test_func)
    return make_tfunc


def signature(jscode, sig_input):
    func = YoutubeIE(FakeYDL())._parse_sig_js(jscode)
    src_sig = (
        str(string.printable[:sig_input])
        if isinstance(sig_input, int) else sig_input)
    return func(src_sig)


def n_sig(jscode, sig_input):
    ie = YoutubeIE(FakeYDL())
    funcname = ie._extract_n_function_name(jscode)
    jsi = JSInterpreter(jscode)
    func = jsi.extract_function_from_code(*ie._fixup_n_function_code(*jsi.extract_function_code(funcname), jscode))
    return func([sig_input])


make_sig_test = t_factory(
    'signature', signature,
    re.compile(r'''(?x)
        .+(?:
            /player/(?P<id>[a-zA-Z0-9_/.-]+)|
            /html5player-(?:en_US-)?(?P<compat_id>[a-zA-Z0-9_-]+)(?:/watch_as3|/html5player)?
        )\.js$'''))
for test_spec in _SIG_TESTS:
    make_sig_test(*test_spec)

make_nsig_test = t_factory(
    'nsig', n_sig, re.compile(r'.+/player/(?P<id>[a-zA-Z0-9_/.-]+)\.js$'))
for test_spec in _NSIG_TESTS:
    make_nsig_test(*test_spec)


if __name__ == '__main__':
    unittest.main()
