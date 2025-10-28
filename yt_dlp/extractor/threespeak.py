import re

from .common import InfoExtractor
from ..utils import (
    try_get,
    unified_strdate,
)


class ThreeSpeakIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?3speak\.tv/watch\?v\=[^/]+/(?P<id>[^/$&#?]+)'

    _TESTS = [{
        'url': 'https://3speak.tv/watch?v=dannyshine/wjgoxyfy',
        'info_dict': {
            'id': 'wjgoxyfy',
            'ext': 'mp4',
            'title': 'Can People who took the Vax think Critically',
            'uploader': 'dannyshine',
            'description': 'md5:181aa7ccb304afafa089b5af3bca7a10',
            'tags': ['sex', 'covid', 'antinatalism', 'comedy', 'vaccines'],
            'thumbnail': 'https://media.3speak.tv/wjgoxyfy/thumbnails/default.png',
            'upload_date': '20211021',
            'duration': 2703.867833,
            'filesize': 1620054781,
        },
        'params': {'skip_download': True},
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        json_str = self._html_search_regex(r'JSON\.parse\(\'([^\']+)\'\)', webpage, 'json')
        # The json string itself is escaped. Hence the double parsing
        data_json = self._parse_json(self._parse_json(f'"{json_str}"', video_id), video_id)
        video_json = self._parse_json(data_json['json_metadata'], video_id)
        formats, subtitles = [], {}
        og_m3u8 = self._html_search_regex(r'<meta\s?property=\"ogvideo\"\s?content=\"([^\"]+)\">', webpage, 'og m3u8', fatal=False)
        if og_m3u8:
            https_frmts, https_subs = self._extract_m3u8_formats_and_subtitles(og_m3u8, video_id, fatal=False, m3u8_id='https')
            formats.extend(https_frmts)
            subtitles = self._merge_subtitles(subtitles, https_subs)
        ipfs_m3u8 = try_get(video_json, lambda x: x['video']['info']['ipfs'])
        if ipfs_m3u8:
            ipfs_frmts, ipfs_subs = self._extract_m3u8_formats_and_subtitles(
                f'https://ipfs.3speak.tv/ipfs/{ipfs_m3u8}', video_id, fatal=False, m3u8_id='ipfs')
            formats.extend(ipfs_frmts)
            subtitles = self._merge_subtitles(subtitles, ipfs_subs)
        return {
            'id': video_id,
            'title': data_json.get('title') or data_json.get('root_title'),
            'uploader': data_json.get('author'),
            'description': try_get(video_json, lambda x: x['video']['content']['description']),
            'tags': try_get(video_json, lambda x: x['video']['content']['tags']),
            'thumbnail': try_get(video_json, lambda x: x['image'][0]),
            'upload_date': unified_strdate(data_json.get('created')),
            'formats': formats,
            'subtitles': subtitles,
        }


class ThreeSpeakUserIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?3speak\.tv/user/(?P<id>[^/$&?#]+)'

    _TESTS = [{
        'url': 'https://3speak.tv/user/theycallmedan',
        'info_dict': {
            'id': 'theycallmedan',
        },
        'playlist_mincount': 115,
    }]

    def _real_extract(self, url):
        playlist_id = self._match_id(url)
        webpage = self._download_webpage(url, playlist_id)
        entries = [
            self.url_result(
                f'https://3speak.tv/watch?v={video}',
                ie=ThreeSpeakIE.ie_key())
            for video in re.findall(r'data-payout\s?\=\s?\"([^\"]+)\"', webpage) if video
        ]
        return self.playlist_result(entries, playlist_id)
