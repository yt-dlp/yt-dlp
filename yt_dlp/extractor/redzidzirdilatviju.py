from .common import InfoExtractor
from ..utils import ExtractorError


class RedzidzirdilatvijuIE(InfoExtractor):
    _VALID_URL = r'https?://redzidzirdilatviju\.lv/(?:en|lv)/search/movie/(?P<id>\d+)'
    IE_DESC = 'Redzidzirdilatviju'
    _TESTS = [{
        'url': 'https://redzidzirdilatviju.lv/en/search/movie/175277',
        'info_dict': {
            'id': '175277',
            'ext': 'mp4',
            'title': 'Krievijas imperatora Nikolaja II vizīte Rīgā',
        },
        'skip': 'Test video may not be available',
    }, {
        'url': 'https://redzidzirdilatviju.lv/lv/search/movie/175277',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        # Try to get metadata from site API first
        video_filename = None
        title = None

        api_data = self._download_json(
            'https://www.redzidzirdilatviju.lv/index',
            video_id,
            query={
                'wt': 'json',
                'q': f'ss_item_type:(movie OR photo OR sound) AND ss_item_entity_id:{video_id}',
                'rows': '1'
            },
            fatal=False
        )

        if api_data:
            docs = api_data.get('response', {}).get('docs', [])
            if docs:
                doc = docs[0]
                video_filename = doc.get('ss_movie$field_video$file$name')
                if video_filename and not video_filename.endswith('.mp4'):
                    video_filename += '.mp4'
                title = doc.get('ts_movie$field_title') or doc.get('tm_movie$field_title')

        # Fallback to old formula if API didn't provide filename
        if not video_filename:
            movie_id_num = int(video_id)
            record_no = movie_id_num - 170304
            if record_no > 0:
                video_filename = f'P{record_no}.mp4'

        if not video_filename:
            raise ExtractorError('No video filename available', expected=True)

        # Fallback title from webpage if needed
        if not title:
            webpage = self._download_webpage(url, video_id)
            title = self._html_search_regex(
                r'<h[2-3][^>]*>([^<]+)</h[2-3]>', webpage, 'title',
                default=f'Movie {video_id}')

        # Build m3u8 URL
        m3u8_url = f'https://filmas.arhivi.lv:30443/s/{video_filename}/playlist.m3u8'

        formats = self._extract_m3u8_formats(m3u8_url, video_id, 'mp4', fatal=False)

        if not formats:
            raise ExtractorError('No video formats found', expected=True)

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
        }
