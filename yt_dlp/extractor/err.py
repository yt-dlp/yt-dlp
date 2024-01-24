from .common import InfoExtractor
from ..utils import clean_html, int_or_none, str_or_none, url_or_none
from ..utils.traversal import traverse_obj


class ERRJupiterIE(InfoExtractor):
    _VALID_URL = r'https?://jupiter(?:pluss)?\.err\.ee/(?P<id>\d+)'
    _TESTS = [{
        'note': 'S01E06: Impulss',
        'url': 'https://jupiter.err.ee/1609145945/impulss',
        'md5': 'a378486df07ed1ba74e46cc861886243',
        'info_dict': {
            'id': '1609145945',
            'ext': 'mp4',
            'title': 'Impulss',
            'alt_title': 'Loteriipilet hooldekodusse',
            'description': 'md5:fa8a2ed0cdccb130211513443ee4d571',
            'release_date': '20231107',
            'upload_date': '20231026',
            'modified_date': '20231118',
            'release_timestamp': 1699380000,
            'timestamp': 1698327601,
            'modified_timestamp': 1700311802,
            'series': 'Impulss',
            'season': 'Season 1',
            'season_number': 1,
            'episode': 'Loteriipilet hooldekodusse',
            'episode_number': 6,
            'series_id': '1609108187',
            'release_year': 2023,
            'episode_id': '1609145945',
        },
    }, {
        'note': 'Jupiter+: Clip: bolee-zelenyj-tallinn',
        'url': 'https://jupiterpluss.err.ee/1609180445/bolee-zelenyj-tallinn',
        'md5': '1b812270c4daf6ce51c06bfeaf33ed95',
        'info_dict': {
            'id': '1609180445',
            'ext': 'mp4',
            'title': 'Более зеленый Таллинн',
            'alt_title': '',
            'description': 'md5:fd34d9bf939c28c4a725b19a7f0d6320',
            'release_date': '20231224',
            'upload_date': '20231130',
            'modified_date': '20231207',
            'release_timestamp': 1703423400,
            'timestamp': 1701338400,
            'modified_timestamp': 1701967200,
            'release_year': 2023,
        },
    }, {
        'note': 'Jupiter+: Podcast: ',
        'url': 'https://jupiterpluss.err.ee/1608990335/lesnye-istorii-aisty',
        'md5': '8b46d7e4510b254a14b7a52211b5bf96',
        'info_dict': {
            'id': '1608990335',
            'ext': 'm4a',
            'title': 'Лесные истории | Аисты',
            'alt_title': '',
            'description': 'md5:065e721623e271e7a63e6540d409ca6b',
            'release_date': '20230609',
            'upload_date': '20230527',
            'modified_date': '20230608',
            'release_timestamp': 1686308700,
            'timestamp': 1685145600,
            'modified_timestamp': 1686252600,
            'release_year': 2023,
            'episode': 'Episode 0',
            'episode_id': '1608990335',
            'episode_number': 0,
            'season': 'Season 0',
            'season_number': 0,
            'series': 'Лесные истории | Аисты',
            'series_id': '1037497',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        data = self._download_json(
            'https://services.err.ee/api/v2/vodContent/getContentPageData', video_id,
            query={'contentId': video_id})['data']['mainContent']

        media_data = traverse_obj(data, ('medias', ..., {dict}), get_all=False)
        if traverse_obj(media_data, ('restrictions', 'drm', {bool})):
            self.raise_no_formats('This video is DRM protected', expected=True)

        formats, subtitles = [], {}
        for url in set(traverse_obj(media_data, ('src', ('hls', 'hls2', 'hlsNew'), {url_or_none}))):
            fmts, subs = self._extract_m3u8_formats_and_subtitles(
                url, video_id, 'mp4', m3u8_id='hls', fatal=False)
            formats.extend(fmts)
            self._merge_subtitles(subs, target=subtitles)
        for url in set(traverse_obj(media_data, ('src', ('dash', 'dashNew'), {url_or_none}))):
            fmts, subs = self._extract_mpd_formats_and_subtitles(
                url, video_id, mpd_id='dash', fatal=False)
            formats.extend(fmts)
            self._merge_subtitles(subs, target=subtitles)
        if url := traverse_obj(media_data, ('src', 'file', {url_or_none})):
            formats.append({
                'url': url,
                'format_id': 'http',
            })

        return {
            'id': video_id,
            'formats': formats,
            'subtitles': subtitles,
            **traverse_obj(data, {
                'title': ('heading', {str}),
                'alt_title': ('subHeading', {str}),
                'description': (('lead', 'body'), {clean_html}, {lambda x: x or None}),
                'timestamp': ('created', {int_or_none}),
                'modified_timestamp': ('updated', {int_or_none}),
                'release_timestamp': (('scheduleStart', 'publicStart'), {int_or_none}),
                'release_year': ('year', {int_or_none}),
            }, get_all=False),
            **(traverse_obj(data, {
                'series': ('heading', {str}),
                'series_id': ('rootContentId', {str_or_none}),
                'episode': ('subHeading', {str}),
                'season_number': ('season', {int_or_none}),
                'episode_number': ('episode', {int_or_none}),
                'episode_id': ('id', {str_or_none}),
            }) if data.get('type') == 'episode' else {}),
        }
