import re

from .common import InfoExtractor
from ..utils import (
    extract_attributes,
    smuggle_url,
    strip_or_none,
    urljoin,
)


class SkyBaseIE(InfoExtractor):
    BRIGHTCOVE_URL_TEMPLATE = 'http://players.brightcove.net/%s/%s_default/index.html?videoId=%s'
    _SDC_EL_REGEX = r'(?s)(<div[^>]+data-(?:component-name|fn)="sdc-(?:articl|sit)e-video"[^>]*>)'

    def _process_ooyala_element(self, webpage, sdc_el, url):
        sdc = extract_attributes(sdc_el)
        provider = sdc.get('data-provider')
        if provider == 'ooyala':
            video_id = sdc['data-sdc-video-id']
            video_url = 'ooyala:%s' % video_id
            ie_key = 'Ooyala'
            ooyala_el = self._search_regex(
                r'(<div[^>]+class="[^"]*\bsdc-article-video__media-ooyala\b[^"]*"[^>]+data-video-id="%s"[^>]*>)' % video_id,
                webpage, 'video data', fatal=False)
            if ooyala_el:
                ooyala_attrs = extract_attributes(ooyala_el) or {}
                if ooyala_attrs.get('data-token-required') == 'true':
                    token_fetch_url = (self._parse_json(ooyala_attrs.get(
                        'data-token-fetch-options', '{}'),
                        video_id, fatal=False) or {}).get('url')
                    if token_fetch_url:
                        embed_token = self._download_json(urljoin(
                            url, token_fetch_url), video_id, fatal=False)
                        if embed_token:
                            video_url = smuggle_url(
                                video_url, {'embed_token': embed_token})
        elif provider == 'brightcove':
            video_id = sdc['data-video-id']
            account_id = sdc.get('data-account-id') or '6058004172001'
            player_id = sdc.get('data-player-id') or 'RC9PQUaJ6'
            video_url = self.BRIGHTCOVE_URL_TEMPLATE % (account_id, player_id, video_id)
            ie_key = 'BrightcoveNew'

        return {
            '_type': 'url_transparent',
            'id': video_id,
            'url': video_url,
            'ie_key': ie_key,
        }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        info = self._process_ooyala_element(webpage, self._search_regex(
            self._SDC_EL_REGEX, webpage, 'sdc element'), url)
        info.update({
            'title': self._og_search_title(webpage),
            'description': strip_or_none(self._og_search_description(webpage)),
        })
        return info


class SkySportsIE(SkyBaseIE):
    IE_NAME = 'sky:sports'
    _VALID_URL = r'https?://(?:www\.)?skysports\.com/watch/video/([^/]+/)*(?P<id>[0-9]+)'
    _TESTS = [{
        'url': 'http://www.skysports.com/watch/video/10328419/bale-its-our-time-to-shine',
        'md5': '77d59166cddc8d3cb7b13e35eaf0f5ec',
        'info_dict': {
            'id': 'o3eWJnNDE6l7kfNO8BOoBlRxXRQ4ANNQ',
            'ext': 'mp4',
            'title': 'Bale: It\'s our time to shine',
            'description': 'md5:e88bda94ae15f7720c5cb467e777bb6d',
        },
        'add_ie': ['Ooyala'],
    }, {
        'url': 'https://www.skysports.com/watch/video/sports/f1/12160544/abu-dhabi-gp-the-notebook',
        'only_matching': True,
    }, {
        'url': 'https://www.skysports.com/watch/video/tv-shows/12118508/rainford-brent-how-ace-programme-helps',
        'only_matching': True,
    }]


class SkyNewsIE(SkyBaseIE):
    IE_NAME = 'sky:news'
    _VALID_URL = r'https?://news\.sky\.com/video/[0-9a-z-]+-(?P<id>[0-9]+)'
    _TEST = {
        'url': 'https://news.sky.com/video/russian-plane-inspected-after-deadly-fire-11712962',
        'md5': '411e8893fd216c75eaf7e4c65d364115',
        'info_dict': {
            'id': 'ref:1ua21xaDE6lCtZDmbYfl8kwsKLooJbNM',
            'ext': 'mp4',
            'title': 'Russian plane inspected after deadly fire',
            'description': 'The Russian Investigative Committee has released video of the wreckage of a passenger plane which caught fire near Moscow.',
            'uploader_id': '6058004172001',
            'timestamp': 1567112345,
            'upload_date': '20190829',
        },
        'add_ie': ['BrightcoveNew'],
    }


class SkyNewsStoryIE(SkyBaseIE):
    IE_NAME = 'sky:news:story'
    _VALID_URL = r'https?://news\.sky\.com/story/[0-9a-z-]+-(?P<id>[0-9]+)'
    _TEST = {
        'url': 'https://news.sky.com/story/budget-2021-chancellor-rishi-sunak-vows-address-will-deliver-strong-economy-fit-for-a-new-age-of-optimism-12445425',
        'info_dict': {
            'id': 'ref:0714acb9-123d-42c8-91b8-5c1bc6c73f20',
            'title': 'md5:e408dd7aad63f31a1817bbe40c7d276f',
            'description': 'md5:a881e12f49212f92be2befe4a09d288a',
            'ext': 'mp4',
            'upload_date': '20211027',
            'timestamp': 1635317494,
            'uploader_id': '6058004172001',
        }
    }

    def _real_extract(self, url):
        article_id = self._match_id(url)
        webpage = self._download_webpage(url, article_id)

        entries = [self._process_ooyala_element(webpage, sdc_el, url)
                   for sdc_el in re.findall(self._SDC_EL_REGEX, webpage)]

        return self.playlist_result(
            entries, article_id, self._og_search_title(webpage),
            self._html_search_meta(['og:description', 'description'], webpage))


class SkySportsNewsIE(SkyBaseIE):
    IE_NAME = 'sky:sports:news'
    _VALID_URL = r'https?://(?:www\.)?skysports\.com/([^/]+/)*news/\d+/(?P<id>\d+)'
    _TEST = {
        'url': 'http://www.skysports.com/golf/news/12176/10871916/dustin-johnson-ready-to-conquer-players-championship-at-tpc-sawgrass',
        'info_dict': {
            'id': '10871916',
            'title': 'Dustin Johnson ready to conquer Players Championship at TPC Sawgrass',
            'description': 'Dustin Johnson is confident he can continue his dominant form in 2017 by adding the Players Championship to his list of victories.',
        },
        'playlist_count': 2,
    }

    def _real_extract(self, url):
        article_id = self._match_id(url)
        webpage = self._download_webpage(url, article_id)

        entries = []
        for sdc_el in re.findall(self._SDC_EL_REGEX, webpage):
            entries.append(self._process_ooyala_element(webpage, sdc_el, url))

        return self.playlist_result(
            entries, article_id, self._og_search_title(webpage),
            self._html_search_meta(['og:description', 'description'], webpage))
