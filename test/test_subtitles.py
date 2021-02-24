#!/usr/bin/env python
from __future__ import unicode_literals

# Allow direct execution
import os
import sys
import unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from test.helper import FakeYDL, md5


from yt_dlp.extractor import (
    YoutubeIE,
    DailymotionIE,
    TEDIE,
    VimeoIE,
    WallaIE,
    CeskaTelevizeIE,
    LyndaIE,
    NPOIE,
    ComedyCentralIE,
    NRKTVIE,
    RaiPlayIE,
    VikiIE,
    ThePlatformIE,
    ThePlatformFeedIE,
    RTVEALaCartaIE,
    DemocracynowIE,
)


class BaseTestSubtitles(unittest.TestCase):
    url = None
    IE = None

    def setUp(self):
        self.DL = FakeYDL()
        self.ie = self.IE()
        self.DL.add_info_extractor(self.ie)

    def getInfoDict(self):
        info_dict = self.DL.extract_info(self.url, download=False)
        return info_dict

    def getSubtitles(self):
        info_dict = self.getInfoDict()
        subtitles = info_dict['requested_subtitles']
        if not subtitles:
            return subtitles
        for sub_info in subtitles.values():
            if sub_info.get('data') is None:
                uf = self.DL.urlopen(sub_info['url'])
                sub_info['data'] = uf.read().decode('utf-8')
        return dict((l, sub_info['data']) for l, sub_info in subtitles.items())


class TestYoutubeSubtitles(BaseTestSubtitles):
    url = 'QRS8MkLhQmM'
    IE = YoutubeIE

    def test_youtube_allsubtitles(self):
        self.DL.params['writesubtitles'] = True
        self.DL.params['allsubtitles'] = True
        subtitles = self.getSubtitles()
        self.assertEqual(len(subtitles.keys()), 13)
        self.assertEqual(md5(subtitles['en']), '688dd1ce0981683867e7fe6fde2a224b')
        self.assertEqual(md5(subtitles['it']), '31324d30b8430b309f7f5979a504a769')
        for lang in ['fr', 'de']:
            self.assertTrue(subtitles.get(lang) is not None, 'Subtitles for \'%s\' not extracted' % lang)

    def test_youtube_subtitles_ttml_format(self):
        self.DL.params['writesubtitles'] = True
        self.DL.params['subtitlesformat'] = 'ttml'
        subtitles = self.getSubtitles()
        self.assertEqual(md5(subtitles['en']), 'c97ddf1217390906fa9fbd34901f3da2')

    def test_youtube_subtitles_vtt_format(self):
        self.DL.params['writesubtitles'] = True
        self.DL.params['subtitlesformat'] = 'vtt'
        subtitles = self.getSubtitles()
        self.assertEqual(md5(subtitles['en']), 'ae1bd34126571a77aabd4d276b28044d')

    def test_youtube_automatic_captions(self):
        self.url = '8YoUxe5ncPo'
        self.DL.params['writeautomaticsub'] = True
        self.DL.params['subtitleslangs'] = ['it']
        subtitles = self.getSubtitles()
        self.assertTrue(subtitles['it'] is not None)

    def test_youtube_no_automatic_captions(self):
        self.url = 'QRS8MkLhQmM'
        self.DL.params['writeautomaticsub'] = True
        subtitles = self.getSubtitles()
        self.assertTrue(not subtitles)

    def test_youtube_translated_subtitles(self):
        # This video has a subtitles track, which can be translated
        self.url = 'i0ZabxXmH4Y'
        self.DL.params['writeautomaticsub'] = True
        self.DL.params['subtitleslangs'] = ['it']
        subtitles = self.getSubtitles()
        self.assertTrue(subtitles['it'] is not None)

    def test_youtube_nosubtitles(self):
        self.DL.expect_warning('video doesn\'t have subtitles')
        self.url = 'n5BB19UTcdA'
        self.DL.params['writesubtitles'] = True
        self.DL.params['allsubtitles'] = True
        subtitles = self.getSubtitles()
        self.assertFalse(subtitles)


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
            self.assertTrue(subtitles.get(lang) is not None, 'Subtitles for \'%s\' not extracted' % lang)

    def test_nosubtitles(self):
        self.DL.expect_warning('video doesn\'t have subtitles')
        self.url = 'http://www.dailymotion.com/video/x12u166_le-zapping-tele-star-du-08-aout-2013_tv'
        self.DL.params['writesubtitles'] = True
        self.DL.params['allsubtitles'] = True
        subtitles = self.getSubtitles()
        self.assertFalse(subtitles)


class TestTedSubtitles(BaseTestSubtitles):
    url = 'http://www.ted.com/talks/dan_dennett_on_our_consciousness.html'
    IE = TEDIE

    def test_allsubtitles(self):
        self.DL.params['writesubtitles'] = True
        self.DL.params['allsubtitles'] = True
        subtitles = self.getSubtitles()
        self.assertTrue(len(subtitles.keys()) >= 28)
        self.assertEqual(md5(subtitles['en']), '4262c1665ff928a2dada178f62cb8d14')
        self.assertEqual(md5(subtitles['fr']), '66a63f7f42c97a50f8c0e90bc7797bb5')
        for lang in ['es', 'fr', 'de']:
            self.assertTrue(subtitles.get(lang) is not None, 'Subtitles for \'%s\' not extracted' % lang)


class TestVimeoSubtitles(BaseTestSubtitles):
    url = 'http://vimeo.com/76979871'
    IE = VimeoIE

    def test_allsubtitles(self):
        self.DL.params['writesubtitles'] = True
        self.DL.params['allsubtitles'] = True
        subtitles = self.getSubtitles()
        self.assertEqual(set(subtitles.keys()), set(['de', 'en', 'es', 'fr']))
        self.assertEqual(md5(subtitles['en']), '8062383cf4dec168fc40a088aa6d5888')
        self.assertEqual(md5(subtitles['fr']), 'b6191146a6c5d3a452244d853fde6dc8')

    def test_nosubtitles(self):
        self.DL.expect_warning('video doesn\'t have subtitles')
        self.url = 'http://vimeo.com/56015672'
        self.DL.params['writesubtitles'] = True
        self.DL.params['allsubtitles'] = True
        subtitles = self.getSubtitles()
        self.assertFalse(subtitles)


class TestWallaSubtitles(BaseTestSubtitles):
    url = 'http://vod.walla.co.il/movie/2705958/the-yes-men'
    IE = WallaIE

    def test_allsubtitles(self):
        self.DL.expect_warning('Automatic Captions not supported by this server')
        self.DL.params['writesubtitles'] = True
        self.DL.params['allsubtitles'] = True
        subtitles = self.getSubtitles()
        self.assertEqual(set(subtitles.keys()), set(['heb']))
        self.assertEqual(md5(subtitles['heb']), 'e758c5d7cb982f6bef14f377ec7a3920')

    def test_nosubtitles(self):
        self.DL.expect_warning('video doesn\'t have subtitles')
        self.url = 'http://vod.walla.co.il/movie/2642630/one-direction-all-for-one'
        self.DL.params['writesubtitles'] = True
        self.DL.params['allsubtitles'] = True
        subtitles = self.getSubtitles()
        self.assertFalse(subtitles)


class TestCeskaTelevizeSubtitles(BaseTestSubtitles):
    url = 'http://www.ceskatelevize.cz/ivysilani/10600540290-u6-uzasny-svet-techniky'
    IE = CeskaTelevizeIE

    def test_allsubtitles(self):
        self.DL.expect_warning('Automatic Captions not supported by this server')
        self.DL.params['writesubtitles'] = True
        self.DL.params['allsubtitles'] = True
        subtitles = self.getSubtitles()
        self.assertEqual(set(subtitles.keys()), set(['cs']))
        self.assertTrue(len(subtitles['cs']) > 20000)

    def test_nosubtitles(self):
        self.DL.expect_warning('video doesn\'t have subtitles')
        self.url = 'http://www.ceskatelevize.cz/ivysilani/ivysilani/10441294653-hyde-park-civilizace/214411058091220'
        self.DL.params['writesubtitles'] = True
        self.DL.params['allsubtitles'] = True
        subtitles = self.getSubtitles()
        self.assertFalse(subtitles)


class TestLyndaSubtitles(BaseTestSubtitles):
    url = 'http://www.lynda.com/Bootstrap-tutorials/Using-exercise-files/110885/114408-4.html'
    IE = LyndaIE

    def test_allsubtitles(self):
        self.DL.params['writesubtitles'] = True
        self.DL.params['allsubtitles'] = True
        subtitles = self.getSubtitles()
        self.assertEqual(set(subtitles.keys()), set(['en']))
        self.assertEqual(md5(subtitles['en']), '09bbe67222259bed60deaa26997d73a7')


class TestNPOSubtitles(BaseTestSubtitles):
    url = 'http://www.npo.nl/nos-journaal/28-08-2014/POW_00722860'
    IE = NPOIE

    def test_allsubtitles(self):
        self.DL.params['writesubtitles'] = True
        self.DL.params['allsubtitles'] = True
        subtitles = self.getSubtitles()
        self.assertEqual(set(subtitles.keys()), set(['nl']))
        self.assertEqual(md5(subtitles['nl']), 'fc6435027572b63fb4ab143abd5ad3f4')


class TestMTVSubtitles(BaseTestSubtitles):
    url = 'http://www.cc.com/video-clips/p63lk0/adam-devine-s-house-party-chasing-white-swans'
    IE = ComedyCentralIE

    def getInfoDict(self):
        return super(TestMTVSubtitles, self).getInfoDict()['entries'][0]

    def test_allsubtitles(self):
        self.DL.params['writesubtitles'] = True
        self.DL.params['allsubtitles'] = True
        subtitles = self.getSubtitles()
        self.assertEqual(set(subtitles.keys()), set(['en']))
        self.assertEqual(md5(subtitles['en']), '78206b8d8a0cfa9da64dc026eea48961')


class TestNRKSubtitles(BaseTestSubtitles):
    url = 'http://tv.nrk.no/serie/ikke-gjoer-dette-hjemme/DMPV73000411/sesong-2/episode-1'
    IE = NRKTVIE

    def test_allsubtitles(self):
        self.DL.params['writesubtitles'] = True
        self.DL.params['allsubtitles'] = True
        subtitles = self.getSubtitles()
        self.assertEqual(set(subtitles.keys()), set(['no']))
        self.assertEqual(md5(subtitles['no']), '544fa917d3197fcbee64634559221cc2')


class TestRaiPlaySubtitles(BaseTestSubtitles):
    IE = RaiPlayIE

    def test_subtitles_key(self):
        self.url = 'http://www.raiplay.it/video/2014/04/Report-del-07042014-cb27157f-9dd0-4aee-b788-b1f67643a391.html'
        self.DL.params['writesubtitles'] = True
        self.DL.params['allsubtitles'] = True
        subtitles = self.getSubtitles()
        self.assertEqual(set(subtitles.keys()), set(['it']))
        self.assertEqual(md5(subtitles['it']), 'b1d90a98755126b61e667567a1f6680a')

    def test_subtitles_array_key(self):
        self.url = 'https://www.raiplay.it/video/2020/12/Report---04-01-2021-2e90f1de-8eee-4de4-ac0e-78d21db5b600.html'
        self.DL.params['writesubtitles'] = True
        self.DL.params['allsubtitles'] = True
        subtitles = self.getSubtitles()
        self.assertEqual(set(subtitles.keys()), set(['it']))
        self.assertEqual(md5(subtitles['it']), '4b3264186fbb103508abe5311cfcb9cd')


class TestVikiSubtitles(BaseTestSubtitles):
    url = 'http://www.viki.com/videos/1060846v-punch-episode-18'
    IE = VikiIE

    def test_allsubtitles(self):
        self.DL.params['writesubtitles'] = True
        self.DL.params['allsubtitles'] = True
        subtitles = self.getSubtitles()
        self.assertEqual(set(subtitles.keys()), set(['en']))
        self.assertEqual(md5(subtitles['en']), '53cb083a5914b2d84ef1ab67b880d18a')


class TestThePlatformSubtitles(BaseTestSubtitles):
    # from http://www.3playmedia.com/services-features/tools/integrations/theplatform/
    # (see http://theplatform.com/about/partners/type/subtitles-closed-captioning/)
    url = 'theplatform:JFUjUE1_ehvq'
    IE = ThePlatformIE

    def test_allsubtitles(self):
        self.DL.params['writesubtitles'] = True
        self.DL.params['allsubtitles'] = True
        subtitles = self.getSubtitles()
        self.assertEqual(set(subtitles.keys()), set(['en']))
        self.assertEqual(md5(subtitles['en']), '97e7670cbae3c4d26ae8bcc7fdd78d4b')


class TestThePlatformFeedSubtitles(BaseTestSubtitles):
    url = 'http://feed.theplatform.com/f/7wvmTC/msnbc_video-p-test?form=json&pretty=true&range=-40&byGuid=n_hardball_5biden_140207'
    IE = ThePlatformFeedIE

    def test_allsubtitles(self):
        self.DL.params['writesubtitles'] = True
        self.DL.params['allsubtitles'] = True
        subtitles = self.getSubtitles()
        self.assertEqual(set(subtitles.keys()), set(['en']))
        self.assertEqual(md5(subtitles['en']), '48649a22e82b2da21c9a67a395eedade')


class TestRtveSubtitles(BaseTestSubtitles):
    url = 'http://www.rtve.es/alacarta/videos/los-misterios-de-laura/misterios-laura-capitulo-32-misterio-del-numero-17-2-parte/2428621/'
    IE = RTVEALaCartaIE

    def test_allsubtitles(self):
        print('Skipping, only available from Spain')
        return
        self.DL.params['writesubtitles'] = True
        self.DL.params['allsubtitles'] = True
        subtitles = self.getSubtitles()
        self.assertEqual(set(subtitles.keys()), set(['es']))
        self.assertEqual(md5(subtitles['es']), '69e70cae2d40574fb7316f31d6eb7fca')


class TestDemocracynowSubtitles(BaseTestSubtitles):
    url = 'http://www.democracynow.org/shows/2015/7/3'
    IE = DemocracynowIE

    def test_allsubtitles(self):
        self.DL.params['writesubtitles'] = True
        self.DL.params['allsubtitles'] = True
        subtitles = self.getSubtitles()
        self.assertEqual(set(subtitles.keys()), set(['en']))
        self.assertEqual(md5(subtitles['en']), 'acaca989e24a9e45a6719c9b3d60815c')

    def test_subtitles_in_page(self):
        self.url = 'http://www.democracynow.org/2015/7/3/this_flag_comes_down_today_bree'
        self.DL.params['writesubtitles'] = True
        self.DL.params['allsubtitles'] = True
        subtitles = self.getSubtitles()
        self.assertEqual(set(subtitles.keys()), set(['en']))
        self.assertEqual(md5(subtitles['en']), 'acaca989e24a9e45a6719c9b3d60815c')


if __name__ == '__main__':
    unittest.main()
