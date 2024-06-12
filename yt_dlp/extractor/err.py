from .common import InfoExtractor
from ..utils import (
    clean_html,
    int_or_none,
    str_or_none,
    url_or_none,
)
from ..utils.traversal import traverse_obj


class ERRJupiterIE(InfoExtractor):
    _VALID_URL = r'https?://(?:jupiter(?:pluss)?|lasteekraan)\.err\.ee/(?P<id>\d+)'
    _TESTS = [{
        'note': 'Jupiter: Movie: siin-me-oleme',
        'url': 'https://jupiter.err.ee/1211107/siin-me-oleme',
        'md5': '9b45d1682a98853acaa1e1b0c791f425',
        'info_dict': {
            'id': '1211107',
            'ext': 'mp4',
            'title': 'Siin me oleme!',
            'alt_title': '',
            'description': 'md5:1825b795f5f7584241aeb59e5bbb4f70',
            'release_date': '20231226',
            'upload_date': '20201217',
            'modified_date': '20201217',
            'release_timestamp': 1703577600,
            'timestamp': 1608210000,
            'modified_timestamp': 1608220800,
            'release_year': 1978,
        },
    }, {
        'note': 'Jupiter: Series: Impulss',
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
        'note': 'Jupiter: Radio Show: mnemoturniir episode',
        'url': 'https://jupiter.err.ee/1037919/mnemoturniir',
        'md5': 'f1eb95fe66f9620ff84e81bbac37076a',
        'info_dict': {
            'id': '1037919',
            'ext': 'm4a',
            'title': 'Mnemoturniir',
            'alt_title': '',
            'description': 'md5:626db52394e7583c26ab74d6a34d9982',
            'release_date': '20240121',
            'upload_date': '20240108',
            'modified_date': '20240121',
            'release_timestamp': 1705827900,
            'timestamp': 1704675602,
            'modified_timestamp': 1705827601,
            'series': 'Mnemoturniir',
            'season': 'Season 0',
            'season_number': 0,
            'episode': 'Episode 0',
            'episode_number': 0,
            'series_id': '1037919',
            'release_year': 2024,
            'episode_id': '1609215101',
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
        'note': 'Jupiter+: Series: The Sniffer',
        'url': 'https://jupiterpluss.err.ee/1608311387/njuhach',
        'md5': '2abdeb7131ce551bce49e8d0cea08536',
        'info_dict': {
            'id': '1608311387',
            'ext': 'mp4',
            'title': 'Нюхач',
            'alt_title': '',
            'description': 'md5:8c5c7d8f32ec6e54cd498c9e59ca83bc',
            'release_date': '20230601',
            'upload_date': '20210818',
            'modified_date': '20210903',
            'release_timestamp': 1685633400,
            'timestamp': 1629318000,
            'modified_timestamp': 1630686000,
            'release_year': 2013,
            'episode': 'Episode 1',
            'episode_id': '1608311390',
            'episode_number': 1,
            'season': 'Season 1',
            'season_number': 1,
            'series': 'Нюхач',
            'series_id': '1608311387',
        },
    }, {
        'note': 'Jupiter+: Podcast: lesnye-istorii-aisty',
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
    }, {
        'note': 'Lasteekraan: Pätu',
        'url': 'https://lasteekraan.err.ee/1092243/patu',
        'md5': 'a67eb9b9bcb3d201718c15d1638edf77',
        'info_dict': {
            'id': '1092243',
            'ext': 'mp4',
            'title': 'Pätu',
            'alt_title': '',
            'description': 'md5:64a7b5a80afd7042d3f8ec48c77befd9',
            'release_date': '20230614',
            'upload_date': '20200520',
            'modified_date': '20200520',
            'release_timestamp': 1686745800,
            'timestamp': 1589975640,
            'modified_timestamp': 1589975640,
            'release_year': 1990,
            'episode': 'Episode 1',
            'episode_id': '1092243',
            'episode_number': 1,
            'season': 'Season 1',
            'season_number': 1,
            'series': 'Pätu',
            'series_id': '1092236',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        data = self._download_json(
            'https://services.err.ee/api/v2/vodContent/getContentPageData', video_id,
            query={'contentId': video_id})['data']['mainContent']

        media_data = traverse_obj(data, ('medias', ..., {dict}), get_all=False)
        if traverse_obj(media_data, ('restrictions', 'drm', {bool})):
            self.report_drm(video_id)

        formats, subtitles = [], {}
        for format_url in set(traverse_obj(media_data, ('src', ('hls', 'hls2', 'hlsNew'), {url_or_none}))):
            fmts, subs = self._extract_m3u8_formats_and_subtitles(
                format_url, video_id, 'mp4', m3u8_id='hls', fatal=False)
            formats.extend(fmts)
            self._merge_subtitles(subs, target=subtitles)
        for format_url in set(traverse_obj(media_data, ('src', ('dash', 'dashNew'), {url_or_none}))):
            fmts, subs = self._extract_mpd_formats_and_subtitles(
                format_url, video_id, mpd_id='dash', fatal=False)
            formats.extend(fmts)
            self._merge_subtitles(subs, target=subtitles)
        if format_url := traverse_obj(media_data, ('src', 'file', {url_or_none})):
            formats.append({
                'url': format_url,
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
