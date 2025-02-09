import re

from .common import InfoExtractor
from ..utils import ExtractorError, extract_attributes


class BFMTVBaseIE(InfoExtractor):
    _VALID_URL_BASE = r'https?://(?:www\.|rmc\.)?bfmtv\.com/'
    _VALID_URL_TMPL = _VALID_URL_BASE + r'(?:[^/]+/)*[^/?&#]+_%s[A-Z]-(?P<id>\d{12})\.html'
    _VIDEO_BLOCK_REGEX = r'(<div[^>]+class="video_block[^"]*"[^>]*>.*?</div>)'
    _VIDEO_ELEMENT_REGEX = r'(<video-js[^>]+>)'
    BRIGHTCOVE_URL_TEMPLATE = 'http://players.brightcove.net/%s/%s_default/index.html?videoId=%s'

    def _extract_video(self, video_block):
        video_element = self._search_regex(
            self._VIDEO_ELEMENT_REGEX, video_block, 'video element', default=None)
        if video_element:
            video_element_attrs = extract_attributes(video_element)
            video_id = video_element_attrs.get('data-video-id')
            if not video_id:
                return
            account_id = video_element_attrs.get('data-account') or '876450610001'
            player_id = video_element_attrs.get('adjustplayer') or '19dszYXgm'
        else:
            video_block_attrs = extract_attributes(video_block)
            video_id = video_block_attrs.get('videoid')
            if not video_id:
                return
            account_id = video_block_attrs.get('accountid') or '876630703001'
            player_id = video_block_attrs.get('playerid') or 'KbPwEbuHx'
        return self.url_result(
            self.BRIGHTCOVE_URL_TEMPLATE % (account_id, player_id, video_id),
            'BrightcoveNew', video_id)


class BFMTVIE(BFMTVBaseIE):
    IE_NAME = 'bfmtv'
    _VALID_URL = BFMTVBaseIE._VALID_URL_TMPL % 'V'
    _TESTS = [{
        'url': 'https://www.bfmtv.com/politique/emmanuel-macron-l-islam-est-une-religion-qui-vit-une-crise-aujourd-hui-partout-dans-le-monde_VN-202010020146.html',
        'info_dict': {
            'id': '6196747868001',
            'ext': 'mp4',
            'title': 'Emmanuel Macron: "L\'Islam est une religion qui vit une crise aujourd’hui, partout dans le monde"',
            'description': 'Le Président s\'exprime sur la question du séparatisme depuis les Mureaux, dans les Yvelines.',
            'uploader_id': '876450610001',
            'upload_date': '20201002',
            'timestamp': 1601629620,
            'duration': 44.757,
            'tags': ['bfmactu', 'politique'],
            'thumbnail': 'https://cf-images.eu-west-1.prod.boltdns.net/v1/static/876450610001/5041f4c1-bc48-4af8-a256-1b8300ad8ef0/cf2f9114-e8e2-4494-82b4-ab794ea4bc7d/1920x1080/match/image.jpg',
        },
    }]

    def _real_extract(self, url):
        bfmtv_id = self._match_id(url)
        webpage = self._download_webpage(url, bfmtv_id)
        video = self._extract_video(self._search_regex(
            self._VIDEO_BLOCK_REGEX, webpage, 'video block'))
        if not video:
            raise ExtractorError('Failed to extract video')
        return video


class BFMTVLiveIE(BFMTVBaseIE):
    IE_NAME = 'bfmtv:live'
    _VALID_URL = BFMTVBaseIE._VALID_URL_BASE + '(?P<id>(?:[^/]+/)?en-direct)'
    _TESTS = [{
        'url': 'https://www.bfmtv.com/en-direct/',
        'info_dict': {
            'id': '6346069778112',
            'ext': 'mp4',
            'title': r're:^Le Live BFM TV \d{4}-\d{2}-\d{2} \d{2}:\d{2}$',
            'uploader_id': '876450610001',
            'upload_date': '20240202',
            'timestamp': 1706887572,
            'live_status': 'is_live',
            'thumbnail': r're:https://.+/image\.jpg',
            'tags': [],
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'https://www.bfmtv.com/economie/en-direct/',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        bfmtv_id = self._match_id(url)
        webpage = self._download_webpage(url, bfmtv_id)
        video = self._extract_video(self._search_regex(
            self._VIDEO_BLOCK_REGEX, webpage, 'video block'))
        if not video:
            raise ExtractorError('Failed to extract video')
        return video


class BFMTVArticleIE(BFMTVBaseIE):
    IE_NAME = 'bfmtv:article'
    _VALID_URL = BFMTVBaseIE._VALID_URL_TMPL % 'A'
    _TESTS = [{
        'url': 'https://www.bfmtv.com/sante/covid-19-un-responsable-de-l-institut-pasteur-se-demande-quand-la-france-va-se-reconfiner_AV-202101060198.html',
        'info_dict': {
            'id': '202101060198',
            'title': 'Covid-19: un responsable de l\'Institut Pasteur se demande "quand la France va se reconfiner"',
            'description': 'md5:947974089c303d3ac6196670ae262843',
        },
        'playlist_count': 2,
    }, {
        'url': 'https://www.bfmtv.com/international/pour-bolsonaro-le-bresil-est-en-faillite-mais-il-ne-peut-rien-faire_AD-202101060232.html',
        'only_matching': True,
    }, {
        'url': 'https://www.bfmtv.com/sante/covid-19-oui-le-vaccin-de-pfizer-distribue-en-france-a-bien-ete-teste-sur-des-personnes-agees_AN-202101060275.html',
        'only_matching': True,
    }, {
        'url': 'https://rmc.bfmtv.com/actualites/societe/transports/ce-n-est-plus-tout-rentable-le-bioethanol-e85-depasse-1eu-le-litre-des-automobilistes-regrettent_AV-202301100268.html',
        'info_dict': {
            'id': '6318445464112',
            'ext': 'mp4',
            'title': 'Le plein de bioéthanol fait de plus en plus mal à la pompe',
            'uploader_id': '876630703001',
            'upload_date': '20230110',
            'timestamp': 1673341692,
            'duration': 109.269,
            'tags': ['rmc', 'show', 'apolline de malherbe', 'info', 'talk', 'matinale', 'radio'],
            'thumbnail': 'https://cf-images.eu-west-1.prod.boltdns.net/v1/static/876630703001/5bef74b8-9d5e-4480-a21f-60c2e2480c46/96c88b74-f9db-45e1-8040-e199c5da216c/1920x1080/match/image.jpg',
        },
    }]

    def _entries(self, webpage):
        for video_block_el in re.findall(self._VIDEO_BLOCK_REGEX, webpage):
            video = self._extract_video(video_block_el)
            if video:
                yield video

    def _real_extract(self, url):
        bfmtv_id = self._match_id(url)
        webpage = self._download_webpage(url, bfmtv_id)

        return self.playlist_result(
            self._entries(webpage), bfmtv_id, self._og_search_title(webpage, fatal=False),
            self._html_search_meta(['og:description', 'description'], webpage))
