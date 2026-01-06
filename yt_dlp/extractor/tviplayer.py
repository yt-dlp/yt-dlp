from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    filter_dict,
    int_or_none,
    js_to_json,
    url_or_none,
)
from ..utils.traversal import traverse_obj


class TVIPlayerIE(InfoExtractor):
    _VALID_URL = r'https?://tviplayer\.iol\.pt(?:/programa/[\w-]+/[a-f0-9]+)?/\w+/(?P<id>\w+)'
    _TESTS = [{
        'url': 'https://tviplayer.iol.pt/programa/a-protegida/67a63479d34ef72ee441fa79/episodio/t1e120',
        'info_dict': {
            'id': '689683000cf20ac1d5f35341',
            'ext': 'mp4',
            'duration': 1593,
            'title': 'A Protegida - Clarice descobre o que une Óscar a Gonçalo e Mónica',
            'thumbnail': 'https://img.iol.pt/image/id/68971037d34ef72ee44941a6/',
            'season_number': 1,
        },
    }]

    def _real_initialize(self):
        self.wms_auth_sign_token = self._download_webpage(
            'https://services.iol.pt/matrix?userId=', 'wmsAuthSign',
            note='Trying to get wmsAuthSign token')

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        json_data = self._search_json(
            r'(?<!-)\bvideo\s*:\s*\[',
            webpage, 'json_data', video_id, transform_source=js_to_json)

        video_url = traverse_obj(json_data, ('videoUrl',), expected_type=url_or_none)
        if not video_url:
            raise ExtractorError('Unable to locate video URL in webpage')

        formats, subtitles = self._extract_m3u8_formats_and_subtitles(
            video_url, video_id, ext='mp4', query=filter_dict({
                'wmsAuthSign': self.wms_auth_sign_token,
            }))

        return {
            'id': traverse_obj(json_data, ('id',)) or video_id,
            'display_id': video_id,
            'title': traverse_obj(json_data, ('title',)) or self._og_search_title(webpage),
            'thumbnail': traverse_obj(
                json_data, ('cover',), ('thumbnail',), expected_type=url_or_none) or self._og_search_thumbnail(webpage),
            'duration': int_or_none(traverse_obj(json_data, ('duration',))),
            'formats': formats,
            'subtitles': subtitles,
            'season_number': traverse_obj(json_data, ('program', 'seasonNum')),
        }
