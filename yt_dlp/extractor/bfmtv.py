import re

from .common import InfoExtractor
from ..utils import extract_attributes


class BFMTVBaseIE(InfoExtractor):
    _VALID_URL_BASE = r'https?://(?:www\.|rmc\.)?bfmtv\.com/'
    _VALID_URL_TMPL = _VALID_URL_BASE + r'(?:[^/]+/)*[^/?&#]+_%s[A-Z]-(?P<id>\d{12})\.html'
    _VIDEO_BLOCK_REGEX = r'(<div[^>]+class="video_block[^"]*"[^>]*>)'
    BRIGHTCOVE_URL_TEMPLATE = 'http://players.brightcove.net/%s/%s_default/index.html?videoId=%s'

    def _brightcove_url_result(self, video_id, video_block):
        account_id = video_block.get('accountid') or '876450612001'
        player_id = video_block.get('playerid') or 'I2qBTln4u'
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
        video_block = extract_attributes(self._search_regex(
            self._VIDEO_BLOCK_REGEX, webpage, 'video block'))
        return self._brightcove_url_result(video_block['videoid'], video_block)


class BFMTVLiveIE(BFMTVIE):  # XXX: Do not subclass from concrete IE
    IE_NAME = 'bfmtv:live'
    _VALID_URL = BFMTVBaseIE._VALID_URL_BASE + '(?P<id>(?:[^/]+/)?en-direct)'
    _TESTS = [{
        'url': 'https://www.bfmtv.com/en-direct/',
        'info_dict': {
            'id': '5615950982001',
            'ext': 'mp4',
            'title': r're:^le direct BFMTV WEB \d{4}-\d{2}-\d{2} \d{2}:\d{2}$',
            'uploader_id': '876450610001',
            'upload_date': '20220926',
            'timestamp': 1664207191,
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
            'description': None,
            'uploader_id': '876630703001',
            'upload_date': '20230110',
            'timestamp': 1673341692,
            'duration': 109.269,
            'tags': ['rmc', 'show', 'apolline de malherbe', 'info', 'talk', 'matinale', 'radio'],
            'thumbnail': 'https://cf-images.eu-west-1.prod.boltdns.net/v1/static/876630703001/5bef74b8-9d5e-4480-a21f-60c2e2480c46/96c88b74-f9db-45e1-8040-e199c5da216c/1920x1080/match/image.jpg'
        }
    }]

    def _real_extract(self, url):
        bfmtv_id = self._match_id(url)
        webpage = self._download_webpage(url, bfmtv_id)

        entries = []
        for video_block_el in re.findall(self._VIDEO_BLOCK_REGEX, webpage):
            video_block = extract_attributes(video_block_el)
            video_id = video_block.get('videoid')
            if not video_id:
                continue
            entries.append(self._brightcove_url_result(video_id, video_block))

        return self.playlist_result(
            entries, bfmtv_id, self._og_search_title(webpage, fatal=False),
            self._html_search_meta(['og:description', 'description'], webpage))
