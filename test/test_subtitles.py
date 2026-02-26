#!/usr/bin/env python3

# Allow direct execution
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


from test.helper import FakeYDL, is_download_test, md5
from yt_dlp.extractor import (
    NPOIE,
    NRKTVIE,
    PBSIE,
    CeskaTelevizeIE,
    DailymotionIE,
    DemocracynowIE,
    LyndaIE,
    RaiPlayIE,
    RTVEALaCartaIE,
    TedTalkIE,
    ThePlatformFeedIE,
    ThePlatformIE,
    VimeoIE,
    WallaIE,
    YoutubeIE,
)


@is_download_test
class BaseTestSubtitles(unittest.TestCase):
    url = None
    IE = None

    def setUp(self):
        self.DL = FakeYDL()
        self.ie = self.IE()
        self.DL.add_info_extractor(self.ie)
        if not self.IE.working():
            print(f'Skipping: {self.IE.ie_key()} marked as not _WORKING')
            self.skipTest('IE marked as not _WORKING')

    def getInfoDict(self):
        return self.DL.extract_info(self.url, download=False)

    def getSubtitles(self):
        info_dict = self.getInfoDict()
        subtitles = info_dict['requested_subtitles']
        if not subtitles:
            return subtitles
        for sub_info in subtitles.values():
            if sub_info.get('data') is None:
                uf = self.DL.urlopen(sub_info['url'])
                sub_info['data'] = uf.read().decode()
        return {l: sub_info['data'] for l, sub_info in subtitles.items()}


@is_download_test
class TestYoutubeSubtitles(BaseTestSubtitles):
    # Available subtitles for QRS8MkLhQmM:
    # Language formats
    # ru       vtt, ttml, srv3, srv2, srv1, json3
    # fr       vtt, ttml, srv3, srv2, srv1, json3
    # en       vtt, ttml, srv3, srv2, srv1, json3
    # nl       vtt, ttml, srv3, srv2, srv1, json3
    # de       vtt, ttml, srv3, srv2, srv1, json3
    # ko       vtt, ttml, srv3, srv2, srv1, json3
    # it       vtt, ttml, srv3, srv2, srv1, json3
    # zh-Hant  vtt, ttml, srv3, srv2, srv1, json3
    # hi       vtt, ttml, srv3, srv2, srv1, json3
    # pt-BR    vtt, ttml, srv3, srv2, srv1, json3
    # es-MX    vtt, ttml, srv3, srv2, srv1, json3
    # ja       vtt, ttml, srv3, srv2, srv1, json3
    # pl       vtt, ttml, srv3, srv2, srv1, json3
    url = 'QRS8MkLhQmM'
    IE = YoutubeIE

    def test_youtube_allsubtitles(self):
        self.DL.params['writesubtitles'] = True
        self.DL.params['allsubtitles'] = True
        subtitles = self.getSubtitles()
        self.assertEqual(len(subtitles.keys()), 13)
        self.assertEqual(md5(subtitles['en']), 'ae1bd34126571a77aabd4d276b28044d')
        self.assertEqual(md5(subtitles['it']), '0e0b667ba68411d88fd1c5f4f4eab2f9')
        for lang in ['fr', 'de']:
            self.assertTrue(subtitles.get(lang) is not None, f'Subtitles for \'{lang}\' not extracted')

    def _test_subtitles_format(self, fmt, md5_hash, lang='en'):
        self.DL.params['writesubtitles'] = True
        self.DL.params['subtitlesformat'] = fmt
        subtitles = self.getSubtitles()
        self.assertEqual(md5(subtitles[lang]), md5_hash)

    def test_youtube_subtitles_ttml_format(self):
        self._test_subtitles_format('ttml', 'c97ddf1217390906fa9fbd34901f3da2')

    def test_youtube_subtitles_vtt_format(self):
        self._test_subtitles_format('vtt', 'ae1bd34126571a77aabd4d276b28044d')

    def test_youtube_subtitles_json3_format(self):
        self._test_subtitles_format('json3', '688dd1ce0981683867e7fe6fde2a224b')

    def _test_automatic_captions(self, url, lang):
        self.url = url
        self.DL.params['writeautomaticsub'] = True
        self.DL.params['subtitleslangs'] = [lang]
        subtitles = self.getSubtitles()
        self.assertTrue(subtitles[lang] is not None)

    def test_youtube_automatic_captions(self):
        # Available automatic captions for 8YoUxe5ncPo:
        # Language formats (all in vtt, ttml, srv3, srv2, srv1, json3)
        # gu, zh-Hans, zh-Hant, gd, ga, gl, lb, la, lo, tt, tr,
        # lv, lt, tk, th, tg, te, fil, haw, yi, ceb, yo, de, da,
        # el, eo, en, eu, et, es, ru, rw, ro, bn, be, bg, uk, jv,
        # bs, ja, or, xh, co, ca, cy, cs, ps, pt, pa, vi, pl, hy,
        # hr, ht, hu, hmn, hi, ha, mg, uz, ml, mn, mi, mk, ur,
        # mt, ms, mr, ug, ta, my, af, sw, is, am,
        #                                         *it*, iw, sv, ar,
        # su, zu, az, id, ig, nl, no, ne, ny, fr, ku, fy, fa, fi,
        # ka, kk, sr, sq, ko, kn, km, st, sk, si, so, sn, sm, sl,
        # ky, sd
        # ...
        self._test_automatic_captions('8YoUxe5ncPo', 'it')

    @unittest.skip('Video unavailable')
    def test_youtube_translated_subtitles(self):
        # This video has a subtitles track, which can be translated (#4555)
        self._test_automatic_captions('Ky9eprVWzlI', 'it')

    def test_youtube_nosubtitles(self):
        self.DL.expect_warning('video doesn\'t have subtitles')
        # Available automatic captions for 8YoUxe5ncPo:
        # ...
        # 8YoUxe5ncPo has no subtitles
        self.url = '8YoUxe5ncPo'
        self.DL.params['writesubtitles'] = True
        self.DL.params['allsubtitles'] = True
        subtitles = self.getSubtitles()
        self.assertFalse(subtitles)


@is_download_test
class TestDailymotionSubtitles(BaseTestSubtitles):
    url = 'http://www.dailymotion.com/video/xczg00'
    IE = DailymotionIE

    def test_allsubtitles(self):
        self.DL.params['writesubtitles'] = True
        self.DL.params['allsubtitles'] = True
        subtitles = self.getSubtitles()
        self.assertTrue(len(subtitles.keys()) >= 6)
        self.assertEqual(md5(subtitles['en']), '976553874490cba125086bbfea3ff76f')
        self.assertEqual(md5(subtitles['fr']), '594564ec7d588942e384e920e5341792')
        for lang in ['es', 'fr', 'de']:
            self.assertTrue(subtitles.get(lang) is not None, f'Subtitles for \'{lang}\' not extracted')

    def test_nosubtitles(self):
        self.DL.expect_warning('video doesn\'t have subtitles')
        self.url = 'http://www.dailymotion.com/video/x12u166_le-zapping-tele-star-du-08-aout-2013_tv'
        self.DL.params['writesubtitles'] = True
        self.DL.params['allsubtitles'] = True
        subtitles = self.getSubtitles()
        self.assertFalse(subtitles)


@is_download_test
@unittest.skip('IE broken')
class TestTedSubtitles(BaseTestSubtitles):
    url = 'http://www.ted.com/talks/dan_dennett_on_our_consciousness.html'
    IE = TedTalkIE

    def test_allsubtitles(self):
        self.DL.params['writesubtitles'] = True
        self.DL.params['allsubtitles'] = True
        subtitles = self.getSubtitles()
        self.assertTrue(len(subtitles.keys()) >= 28)
        self.assertEqual(md5(subtitles['en']), '4262c1665ff928a2dada178f62cb8d14')
        self.assertEqual(md5(subtitles['fr']), '66a63f7f42c97a50f8c0e90bc7797bb5')
        for lang in ['es', 'fr', 'de']:
            self.assertTrue(subtitles.get(lang) is not None, f'Subtitles for \'{lang}\' not extracted')


@is_download_test
class TestVimeoSubtitles(BaseTestSubtitles):
    url = 'http://vimeo.com/76979871'
    IE = VimeoIE

    def test_allsubtitles(self):
        self.DL.params['writesubtitles'] = True
        self.DL.params['allsubtitles'] = True
        subtitles = self.getSubtitles()
        self.assertEqual(set(subtitles.keys()), {'de', 'en', 'es', 'fr'})
        self.assertEqual(md5(subtitles['en']), '386cbc9320b94e25cb364b97935e5dd1')
        self.assertEqual(md5(subtitles['fr']), 'c9b69eef35bc6641c0d4da8a04f9dfac')

    def test_nosubtitles(self):
        self.DL.expect_warning('video doesn\'t have subtitles')
        self.url = 'http://vimeo.com/68093876'
        self.DL.params['writesubtitles'] = True
        self.DL.params['allsubtitles'] = True
        subtitles = self.getSubtitles()
        self.assertFalse(subtitles)


@is_download_test
@unittest.skip('IE broken')
class TestWallaSubtitles(BaseTestSubtitles):
    url = 'http://vod.walla.co.il/movie/2705958/the-yes-men'
    IE = WallaIE

    def test_allsubtitles(self):
        self.DL.expect_warning('Automatic Captions not supported by this server')
        self.DL.params['writesubtitles'] = True
        self.DL.params['allsubtitles'] = True
        subtitles = self.getSubtitles()
        self.assertEqual(set(subtitles.keys()), {'heb'})
        self.assertEqual(md5(subtitles['heb']), 'e758c5d7cb982f6bef14f377ec7a3920')

    def test_nosubtitles(self):
        self.DL.expect_warning('video doesn\'t have subtitles')
        self.url = 'http://vod.walla.co.il/movie/2642630/one-direction-all-for-one'
        self.DL.params['writesubtitles'] = True
        self.DL.params['allsubtitles'] = True
        subtitles = self.getSubtitles()
        self.assertFalse(subtitles)


@is_download_test
@unittest.skip('IE broken')
class TestCeskaTelevizeSubtitles(BaseTestSubtitles):
    url = 'http://www.ceskatelevize.cz/ivysilani/10600540290-u6-uzasny-svet-techniky'
    IE = CeskaTelevizeIE

    def test_allsubtitles(self):
        self.DL.expect_warning('Automatic Captions not supported by this server')
        self.DL.params['writesubtitles'] = True
        self.DL.params['allsubtitles'] = True
        subtitles = self.getSubtitles()
        self.assertEqual(set(subtitles.keys()), {'cs'})
        self.assertTrue(len(subtitles['cs']) > 20000)

    def test_nosubtitles(self):
        self.DL.expect_warning('video doesn\'t have subtitles')
        self.url = 'http://www.ceskatelevize.cz/ivysilani/ivysilani/10441294653-hyde-park-civilizace/214411058091220'
        self.DL.params['writesubtitles'] = True
        self.DL.params['allsubtitles'] = True
        subtitles = self.getSubtitles()
        self.assertFalse(subtitles)


@is_download_test
@unittest.skip('IE broken')
class TestLyndaSubtitles(BaseTestSubtitles):
    url = 'http://www.lynda.com/Bootstrap-tutorials/Using-exercise-files/110885/114408-4.html'
    IE = LyndaIE

    def test_allsubtitles(self):
        self.DL.params['writesubtitles'] = True
        self.DL.params['allsubtitles'] = True
        subtitles = self.getSubtitles()
        self.assertEqual(set(subtitles.keys()), {'en'})
        self.assertEqual(md5(subtitles['en']), '09bbe67222259bed60deaa26997d73a7')


@is_download_test
@unittest.skip('IE broken')
class TestNPOSubtitles(BaseTestSubtitles):
    url = 'http://www.npo.nl/nos-journaal/28-08-2014/POW_00722860'
    IE = NPOIE

    def test_allsubtitles(self):
        self.DL.params['writesubtitles'] = True
        self.DL.params['allsubtitles'] = True
        subtitles = self.getSubtitles()
        self.assertEqual(set(subtitles.keys()), {'nl'})
        self.assertEqual(md5(subtitles['nl']), 'fc6435027572b63fb4ab143abd5ad3f4')


@is_download_test
class TestNRKSubtitles(BaseTestSubtitles):
    url = 'http://tv.nrk.no/serie/ikke-gjoer-dette-hjemme/DMPV73000411/sesong-2/episode-1'
    IE = NRKTVIE

    def test_allsubtitles(self):
        self.DL.params['writesubtitles'] = True
        self.DL.params['allsubtitles'] = True
        subtitles = self.getSubtitles()
        self.assertEqual(set(subtitles.keys()), {'nb-ttv'})
        self.assertEqual(md5(subtitles['nb-ttv']), '67e06ff02d0deaf975e68f6cb8f6a149')


@is_download_test
class TestRaiPlaySubtitles(BaseTestSubtitles):
    IE = RaiPlayIE

    def test_subtitles_key(self):
        self.url = 'http://www.raiplay.it/video/2014/04/Report-del-07042014-cb27157f-9dd0-4aee-b788-b1f67643a391.html'
        self.DL.params['writesubtitles'] = True
        self.DL.params['allsubtitles'] = True
        subtitles = self.getSubtitles()
        self.assertEqual(set(subtitles.keys()), {'it'})
        self.assertEqual(md5(subtitles['it']), 'b1d90a98755126b61e667567a1f6680a')

    def test_subtitles_array_key(self):
        self.url = 'https://www.raiplay.it/video/2020/12/Report---04-01-2021-2e90f1de-8eee-4de4-ac0e-78d21db5b600.html'
        self.DL.params['writesubtitles'] = True
        self.DL.params['allsubtitles'] = True
        subtitles = self.getSubtitles()
        self.assertEqual(set(subtitles.keys()), {'it'})
        self.assertEqual(md5(subtitles['it']), '4b3264186fbb103508abe5311cfcb9cd')


@is_download_test
class TestThePlatformSubtitles(BaseTestSubtitles):
    # from http://www.3playmedia.com/services-features/tools/integrations/theplatform/
    # (see http://theplatform.com/about/partners/type/subtitles-closed-captioning/)
    url = 'theplatform:JFUjUE1_ehvq'
    IE = ThePlatformIE

    def test_allsubtitles(self):
        self.DL.params['writesubtitles'] = True
        self.DL.params['allsubtitles'] = True
        subtitles = self.getSubtitles()
        self.assertEqual(set(subtitles.keys()), {'en'})
        self.assertEqual(md5(subtitles['en']), '97e7670cbae3c4d26ae8bcc7fdd78d4b')


@is_download_test
@unittest.skip('IE broken')
class TestThePlatformFeedSubtitles(BaseTestSubtitles):
    url = 'http://feed.theplatform.com/f/7wvmTC/msnbc_video-p-test?form=json&pretty=true&range=-40&byGuid=n_hardball_5biden_140207'
    IE = ThePlatformFeedIE

    def test_allsubtitles(self):
        self.DL.params['writesubtitles'] = True
        self.DL.params['allsubtitles'] = True
        subtitles = self.getSubtitles()
        self.assertEqual(set(subtitles.keys()), {'en'})
        self.assertEqual(md5(subtitles['en']), '48649a22e82b2da21c9a67a395eedade')


@is_download_test
class TestRtveSubtitles(BaseTestSubtitles):
    url = 'http://www.rtve.es/alacarta/videos/los-misterios-de-laura/misterios-laura-capitulo-32-misterio-del-numero-17-2-parte/2428621/'
    IE = RTVEALaCartaIE

    def test_allsubtitles(self):
        print('Skipping, only available from Spain')
        return
        self.DL.params['writesubtitles'] = True
        self.DL.params['allsubtitles'] = True
        subtitles = self.getSubtitles()
        self.assertEqual(set(subtitles.keys()), {'es'})
        self.assertEqual(md5(subtitles['es']), '69e70cae2d40574fb7316f31d6eb7fca')


@is_download_test
class TestDemocracynowSubtitles(BaseTestSubtitles):
    url = 'http://www.democracynow.org/shows/2015/7/3'
    IE = DemocracynowIE

    def test_allsubtitles(self):
        self.DL.params['writesubtitles'] = True
        self.DL.params['allsubtitles'] = True
        subtitles = self.getSubtitles()
        self.assertEqual(set(subtitles.keys()), {'en'})
        self.assertEqual(md5(subtitles['en']), 'a3cc4c0b5eadd74d9974f1c1f5101045')

    def test_subtitles_in_page(self):
        self.url = 'http://www.democracynow.org/2015/7/3/this_flag_comes_down_today_bree'
        self.DL.params['writesubtitles'] = True
        self.DL.params['allsubtitles'] = True
        subtitles = self.getSubtitles()
        self.assertEqual(set(subtitles.keys()), {'en'})
        self.assertEqual(md5(subtitles['en']), 'a3cc4c0b5eadd74d9974f1c1f5101045')


@is_download_test
class TestPBSSubtitles(BaseTestSubtitles):
    url = 'https://www.pbs.org/video/how-fantasy-reflects-our-world-picecq/'
    IE = PBSIE

    def test_allsubtitles(self):
        self.DL.params['writesubtitles'] = True
        self.DL.params['allsubtitles'] = True
        subtitles = self.getSubtitles()
        self.assertEqual(set(subtitles.keys()), {'en'})

    def test_subtitles_dfxp_format(self):
        self.DL.params['writesubtitles'] = True
        self.DL.params['subtitlesformat'] = 'dfxp'
        subtitles = self.getSubtitles()
        self.assertIn(md5(subtitles['en']), ['643b034254cdc3768ff1e750b6b5873b'])

    def test_subtitles_vtt_format(self):
        self.DL.params['writesubtitles'] = True
        self.DL.params['subtitlesformat'] = 'vtt'
        subtitles = self.getSubtitles()
        self.assertIn(
            md5(subtitles['en']), ['937a05711555b165d4c55a9667017045', 'f49ea998d6824d94959c8152a368ff73'])

    def test_subtitles_srt_format(self):
        self.DL.params['writesubtitles'] = True
        self.DL.params['subtitlesformat'] = 'srt'
        subtitles = self.getSubtitles()
        self.assertIn(md5(subtitles['en']), ['2082c21b43759d9bf172931b2f2ca371'])

    def test_subtitles_sami_format(self):
        self.DL.params['writesubtitles'] = True
        self.DL.params['subtitlesformat'] = 'sami'
        subtitles = self.getSubtitles()
        self.assertIn(md5(subtitles['en']), ['4256b16ac7da6a6780fafd04294e85cd'])


if __name__ == '__main__':
    unittest.main()
