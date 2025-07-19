import hashlib
import time

from .common import InfoExtractor
from yt_dlp.utils import ExtractorError


class AiyifanIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?(yfsp|iyf|aiyifan)\.tv/play/(?P<id>[^/?#]+)(?:\?id=(?P<alt_id>[^&#]+))?'
    _TESTS = [
        {
            'url': 'https://www.yfsp.tv/play/tFAWlkx5kr9?id=GB7vRUxjOn5',
            'info_dict': {
                'id': 'GB7vRUxjOn5',
                'title': '工作细胞_06',
                'ext': 'mp4',
            },
            'params': {'skip_download': True},
        },
        {
            'url': 'https://www.yfsp.tv/play/tFAWlkx5kr9',
            'info_dict': {
                'id': 'tFAWlkx5kr9',
                'title': '工作细胞_01',
                'ext': 'mp4',
            },
            'params': {'skip_download': True},
        },
        {
            'url': 'https://www.yfsp.tv/play/TtAyF6XpjfC',
            'info_dict': {
                'id': 'TtAyF6XpjfC',
                'title': '大猿魂_dhp-dyh-01-008FFFF84',
                'ext': 'mp4',
            },
            'params': {'skip_download': True},
        },
        {
            'url': 'https://www.yfsp.tv/play/hezikWmgrKC?id=8u1rb9IxuQE',
            'info_dict': {
                'id': 'hezikWmgrKC',
                'title': 'NBA美国职业篮球赛_20210515qishivsqicai',
                'ext': 'mp4',
            },
            'params': {'skip_download': True},
        },
    ]

    def compute_vv(self, query_str):
        public_key = int(time.time() * 1000)
        private_keys = [
            'version001', 'vers1on001', 'vers1on00i', 'bersion001',
            'vcrsion001', 'versi0n001', 'versio_001', 'version0o1',
        ]
        private_key = private_keys[public_key % len(private_keys)]
        merge_str = f'{public_key}&{query_str.lower()}&{private_key}'
        return hashlib.md5(merge_str.encode('utf-8')).hexdigest(), public_key

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        collection_id = mobj.group('id')
        video_key = mobj.group('alt_id')

        if not video_key:
            vv, pub = self.compute_vv(f'vid={collection_id}&cid=0,')
            playlist_data = self._download_json(
                'https://m10.yfsp.tv/v3/video/languagesplaylist',
                collection_id, query={
                    'vid': collection_id,
                    'cid':'0,',
                    'vv': vv,
                    'pub': pub,
                }, note='Downloading playlist info')
            play_list = playlist_data['data']['info'][0]['playList']
            if not play_list:
                raise ExtractorError('No videos found in playlist')

            if self._yes_playlist(url, collection_id):
                entries = []
                for video in play_list:
                    key = video['key']
                    entries.append(self.url_result(
                        f'https://www.yfsp.tv/play/{collection_id}?id={key}',
                        ie=self.ie_key(), video_id=key))
                return self.playlist_result(entries, collection_id)

            video_key = play_list[0]['key']

        detail_query = f'tech=HLS&id={collection_id}'
        detail_vv, detail_pub = self.compute_vv(detail_query)
        detail_params = {
            'tech': 'HLS',
            'id': collection_id,
            'vv': detail_vv,
            'pub': detail_pub,
        }

        detail_json = self._download_json(
            'https://m10.yfsp.tv/v3/video/detail', collection_id,
            note='Downloading detail info', query=detail_params)

        title = detail_json['data']['info'][0]['title']

        a = 1 if collection_id == video_key else 0
        download_query = f'id={video_key}&a={a}&usersign=1'
        download_vv, download_pub = self.compute_vv(download_query)
        download_params = {
            'id': video_key,
            'a': a,
            'usersign': 1,
            'vv': download_vv,
            'pub': download_pub,
        }

        info = self._download_webpage(
            'https://m10.yfsp.tv/v3/video/play', video_key,
            note='Downloading playback info', query=download_params)

        info_json = self._parse_json(info, video_key)
        m3u8_url = info_json['data']['info'][0]['clarity'][-1]['path']['rtmp']

        episode = self._search_regex(
            r'[A-Za-z0-9]+-[A-Za-z0-9]+-([A-Za-z0-9]*)-[A-Za-z0-9]+\.',
            m3u8_url, 'episode', default=None)
        if episode:
            title = f'{title}_{episode}'

        formats = self._extract_m3u8_formats(
            m3u8_url, video_key, 'mp4',
            entry_protocol='m3u8_native',
            m3u8_id='hls', fatal=True)

        return {
            'id': video_key,
            'title': title,
            'formats': formats,
        }

