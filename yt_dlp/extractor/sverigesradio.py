from .common import InfoExtractor
from ..utils import (
    determine_ext,
    extract_attributes,
    get_element_by_id,
    get_element_html_by_class,
    int_or_none,
    str_or_none,
    traverse_obj,
    url_or_none,
)


class SverigesRadioBaseIE(InfoExtractor):
    _BASE_URL = 'https://sverigesradio.se/sida/playerajax/'
    _QUALITIES = ['low', 'medium', 'high']
    _EXT_TO_CODEC_MAP = {
        'mp3': 'mp3',
        'm4a': 'aac',
    }
    _CODING_FORMAT_TO_ABR_MAP = {
        5: 128,
        11: 192,
        12: 32,
        13: 96,
    }

    def _real_extract(self, url):
        audio_id, display_id = self._match_valid_url(url).group('id', 'slug')
        if not audio_id:
            webpage = self._download_webpage(url, display_id)
            audio_id = (
                traverse_obj(
                    get_element_html_by_class('audio-button', webpage),
                    ({extract_attributes}, ('data-audio-id', 'data-publication-id')), get_all=False)
                or self._parse_json(get_element_by_id('gtm-metadata', webpage), display_id)['pageId'])

        query = {
            'id': audio_id,
            'type': self._AUDIO_TYPE,
        }

        item = self._download_json(
            self._BASE_URL + 'audiometadata', audio_id,
            'Downloading audio JSON metadata', query=query)['items'][0]

        query['format'] = 'iis'
        urls = []
        formats = []
        for quality in self._QUALITIES:
            query['quality'] = quality
            audio_url_data = self._download_json(
                self._BASE_URL + 'getaudiourl', audio_id,
                'Downloading %s format JSON metadata' % quality,
                fatal=False, query=query) or {}
            audio_url = audio_url_data.get('audioUrl')
            if not audio_url or audio_url in urls:
                continue
            urls.append(audio_url)
            ext = determine_ext(audio_url)
            coding_format = audio_url_data.get('codingFormat')
            abr = int_or_none(self._search_regex(
                r'_a(\d+)\.m4a', audio_url, 'audio bitrate',
                default=None)) or self._CODING_FORMAT_TO_ABR_MAP.get(coding_format)
            formats.append({
                'abr': abr,
                'acodec': self._EXT_TO_CODEC_MAP.get(ext),
                'ext': ext,
                'format_id': str_or_none(coding_format),
                'vcodec': 'none',
                'url': audio_url,
            })

        return {
            'id': audio_id,
            'formats': formats,
            **traverse_obj(item, {
                'title': 'subtitle',
                'series': 'title',
                'duration': ('duration', {int_or_none}),
                'thumbnail': ('displayimageurl', {url_or_none}),
                'description': 'description',
            }),
        }


class SverigesRadioPublicationIE(SverigesRadioBaseIE):
    IE_NAME = 'sverigesradio:publication'
    _VALID_URL = r'https?://(?:www\.)?sverigesradio\.se/(?:sida/)?(?:artikel|gruppsida)(?:\.aspx\?.*?\bartikel=(?P<id>[0-9]+)|/(?P<slug>[\w-]+))'
    _TESTS = [{
        'url': 'https://sverigesradio.se/sida/artikel.aspx?programid=83&artikel=7038546',
        'md5': '6a4917e1923fccb080e5a206a5afa542',
        'info_dict': {
            'id': '7038546',
            'ext': 'm4a',
            'duration': 132,
            'series': 'Nyheter (Ekot)',
            'title': 'Esa Teittinen: Sanningen har inte kommit fram',
            'description': 'md5:daf7ce66a8f0a53d5465a5984d3839df',
            'thumbnail': r're:^https?://.*\.jpg',
        },
    }, {
        'url': 'https://sverigesradio.se/artikel/tysk-fotbollsfeber-bayern-munchens-10-ariga-segersvit-kan-brytas',
        'md5': 'f8a914ad50f491bb74eed403ab4bfef6',
        'info_dict': {
            'id': '8360345',
            'ext': 'm4a',
            'title': 'Tysk fotbollsfeber när Bayern Münchens 10-åriga segersvit kan brytas',
            'series': 'Radiosporten',
            'description': 'md5:5254610e20ce527ecb3a6102a06dcc5f',
            'duration': 72,
            'thumbnail': r're:^https?://.*\.jpg',
        },
    }, {
        'url': 'https://sverigesradio.se/sida/gruppsida.aspx?programid=3304&grupp=6247&artikel=7146887',
        'only_matching': True,
    }]
    _AUDIO_TYPE = 'publication'


class SverigesRadioEpisodeIE(SverigesRadioBaseIE):
    IE_NAME = 'sverigesradio:episode'
    _VALID_URL = r'https?://(?:www\.)?sverigesradio\.se/(?:sida/)?avsnitt/(?:(?P<id>\d+)|(?P<slug>[\w-]+))(?:$|[#?])'
    _TESTS = [{
        'url': 'https://sverigesradio.se/avsnitt/1140922?programid=1300',
        'md5': '20dc4d8db24228f846be390b0c59a07c',
        'info_dict': {
            'id': '1140922',
            'ext': 'mp3',
            'duration': 3307,
            'series': 'Konflikt',
            'title': 'Metoo och valen',
            'description': 'md5:fcb5c1f667f00badcc702b196f10a27e',
            'thumbnail': r're:^https?://.*\.jpg',
        },
    }, {
        'url': 'https://sverigesradio.se/avsnitt/p4-live-med-first-aid-kit-scandinavium-mars-2023',
        'md5': 'ce17fb82520a8033dbb846993d5589fe',
        'info_dict': {
            'id': '2160416',
            'ext': 'm4a',
            'title': 'P4 Live med First Aid Kit',
            'description': 'md5:6d5b78eed3d2b65f6de04daa45e9285d',
            'thumbnail': r're:^https?://.*\.jpg',
            'series': 'P4 Live',
            'duration': 5640,
        },
    }]
    _AUDIO_TYPE = 'episode'
