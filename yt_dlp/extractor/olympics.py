from .common import InfoExtractor
from ..utils import int_or_none, try_get


class OlympicsReplayIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?olympics\.com(?:/tokyo-2020)?/[a-z]{2}/(?:replay|video)/(?P<id>[^/#&?]+)'
    _TESTS = [{
        'url': 'https://olympics.com/fr/video/men-s-109kg-group-a-weightlifting-tokyo-2020-replays',
        'info_dict': {
            'id': 'f6a0753c-8e6f-4b7d-a435-027054a4f8e9',
            'ext': 'mp4',
            'title': '+109kg (H) Groupe A - Haltérophilie | Replay de Tokyo 2020',
            'upload_date': '20210801',
            'timestamp': 1627783200,
            'description': 'md5:c66af4a5bc7429dbcc43d15845ff03b3',
            'uploader': 'International Olympic Committee',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'https://olympics.com/tokyo-2020/en/replay/bd242924-4b22-49a5-a846-f1d4c809250d/mens-bronze-medal-match-hun-esp',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        id = self._match_id(url)

        webpage = self._download_webpage(url, id)
        title = self._html_search_meta(('title', 'og:title', 'twitter:title'), webpage)
        uuid = self._html_search_meta('episode_uid', webpage)
        m3u8_url = self._html_search_meta('video_url', webpage)
        json_ld = self._search_json_ld(webpage, uuid)
        thumbnails_list = json_ld.get('image')
        if not thumbnails_list:
            thumbnails_list = self._html_search_regex(
                r'["\']image["\']:\s*["\']([^"\']+)["\']', webpage, 'images', default='')
            thumbnails_list = thumbnails_list.replace('[', '').replace(']', '').split(',')
            thumbnails_list = [thumbnail.strip() for thumbnail in thumbnails_list]
        thumbnails = []
        for thumbnail in thumbnails_list:
            width_a, height_a, width = self._search_regex(
                r'/images/image/private/t_(?P<width_a>\d+)-(?P<height_a>\d+)_(?P<width>\d+)/primary/[\W\w\d]+',
                thumbnail, 'thumb', group=(1, 2, 3), default=(None, None, None))
            width_a, height_a, width = int_or_none(width_a), int_or_none(height_a), int_or_none(width)
            thumbnails.append({
                'url': thumbnail,
                'width': width,
                'height': int_or_none(try_get(width, lambda x: x * height_a / width_a))
            })
        m3u8_url = self._download_json(
            f'https://olympics.com/tokenGenerator?url={m3u8_url}', uuid, note='Downloading m3u8 url')
        formats, subtitles = self._extract_m3u8_formats_and_subtitles(m3u8_url, uuid, 'mp4', m3u8_id='hls')

        return {
            'id': uuid,
            'title': title,
            'thumbnails': thumbnails,
            'formats': formats,
            'subtitles': subtitles,
            **json_ld
        }
