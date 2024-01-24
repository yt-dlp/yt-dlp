from .common import InfoExtractor
from ..utils import clean_html, int_or_none, str_or_none, url_or_none
from ..utils.traversal import traverse_obj


class ERRJupiterIE(InfoExtractor):
    _VALID_URL = r'https?://jupiter(?:pluss)?\.err\.ee/(?P<id>\d+)'
    _TESTS = [{
        'note': 'S01E06: Impulss',
        'url': 'https://jupiter.err.ee/1609145945/impulss',
        'md5': '1ff59d535310ac9c5cf5f287d8f91b2d',
        'info_dict': {
            'id': '1609145945',
            'ext': 'mp4',
            'title': 'Loteriipilet hooldekodusse',
            'description': 'md5:fa8a2ed0cdccb130211513443ee4d571',
            'upload_date': '20231107',
            'timestamp': 1699380000,
            'series': 'Impulss',
            'season': 'Season 1',
            'season_number': 1,
            'episode': 'Loteriipilet hooldekodusse',
            'episode_number': 6,
            'series_id': '1609108187',
            'release_year': 2023,
            'episode_id': '1609145945',
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
