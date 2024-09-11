import base64
import math
import time

from .common import InfoExtractor
from .videa import VideaIE
from ..utils import (
    InAdvancePagedList,
    int_or_none,
    str_or_none,
    traverse_obj,
    try_call,
    update_url_query,
)


class XimalayaBaseIE(InfoExtractor):
    _GEO_COUNTRIES = ['CN']


class XimalayaIE(XimalayaBaseIE):
    IE_NAME = 'ximalaya'
    IE_DESC = '喜马拉雅FM'
    _VALID_URL = r'https?://(?:www\.|m\.)?ximalaya\.com/(:?(?P<uid>\d+)/)?sound/(?P<id>[0-9]+)'
    _TESTS = [
        {
            'url': 'http://www.ximalaya.com/sound/47740352/',
            'info_dict': {
                'id': '47740352',
                'ext': 'm4a',
                'uploader': '小彬彬爱听书',
                'uploader_id': '61425525',
                'uploader_url': 'http://www.ximalaya.com/zhubo/61425525/',
                'title': '261.唐诗三百首.卷八.送孟浩然之广陵.李白',
                'description': 'contains:《送孟浩然之广陵》\n作者：李白\n故人西辞黄鹤楼，烟花三月下扬州。\n孤帆远影碧空尽，惟见长江天际流。',
                'thumbnail': r're:^https?://.*\.jpg',
                'thumbnails': [
                    {
                        'name': 'cover_url',
                        'url': r're:^https?://.*\.jpg',
                    },
                    {
                        'name': 'cover_url_142',
                        'url': r're:^https?://.*\.jpg',
                        'width': 180,
                        'height': 180,
                    },
                ],
                'categories': ['其他'],
                'duration': 93,
                'view_count': int,
                'like_count': int,
            },
        },
        {
            'url': 'http://m.ximalaya.com/61425525/sound/47740352/',
            'info_dict': {
                'id': '47740352',
                'ext': 'm4a',
                'uploader': '小彬彬爱听书',
                'uploader_id': '61425525',
                'uploader_url': 'http://www.ximalaya.com/zhubo/61425525/',
                'title': '261.唐诗三百首.卷八.送孟浩然之广陵.李白',
                'description': 'contains:《送孟浩然之广陵》\n作者：李白\n故人西辞黄鹤楼，烟花三月下扬州。\n孤帆远影碧空尽，惟见长江天际流。',
                'thumbnail': r're:^https?://.*\.jpg',
                'thumbnails': [
                    {
                        'name': 'cover_url',
                        'url': r're:^https?://.*\.jpg',
                    },
                    {
                        'name': 'cover_url_142',
                        'url': r're:^https?://.*\.jpg',
                        'width': 180,
                        'height': 180,
                    },
                ],
                'categories': ['人文'],
                'duration': 93,
                'view_count': int,
                'like_count': int,
            },
        },
        {
            # VIP-restricted audio
            'url': 'https://www.ximalaya.com/sound/562111701',
            'only_matching': True,
        },
    ]

    @staticmethod
    def _decrypt_filename(file_id, seed):
        cgstr = ''
        key = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ/\\:._-1234567890'
        for _ in key:
            seed = float(int(211 * seed + 30031) % 65536)
            r = int(seed / 65536 * len(key))
            cgstr += key[r]
            key = key.replace(key[r], '')
        parts = file_id.split('*')
        filename = ''.join(cgstr[int(part)] for part in parts if part.isdecimal())
        if not filename.startswith('/'):
            filename = '/' + filename
        return filename

    @staticmethod
    def _decrypt_url_params(encrypted_params):
        params = VideaIE.rc4(
            base64.b64decode(encrypted_params), 'xkt3a41psizxrh9l').split('-')
        # sign, token, timestamp
        return params[1], params[2], params[3]

    def _real_extract(self, url):
        scheme = 'https' if url.startswith('https') else 'http'

        audio_id = self._match_id(url)
        audio_info = self._download_json(
            f'{scheme}://m.ximalaya.com/tracks/{audio_id}.json', audio_id,
            'Downloading info json', 'Unable to download info file')

        formats = []
        # NOTE: VIP-restricted audio
        if audio_info.get('is_paid'):
            ts = int(time.time())
            vip_info = self._download_json(
                f'{scheme}://mpay.ximalaya.com/mobile/track/pay/{audio_id}/{ts}',
                audio_id, 'Downloading VIP info json', 'Unable to download VIP info file',
                query={'device': 'pc', 'isBackend': 'true', '_': ts})
            filename = self._decrypt_filename(vip_info['fileId'], vip_info['seed'])
            sign, token, timestamp = self._decrypt_url_params(vip_info['ep'])
            vip_url = update_url_query(
                f'{vip_info["domain"]}/download/{vip_info["apiVersion"]}{filename}', {
                    'sign': sign,
                    'token': token,
                    'timestamp': timestamp,
                    'buy_key': vip_info['buyKey'],
                    'duration': vip_info['duration'],
                })
            fmt = {
                'format_id': 'vip',
                'url': vip_url,
                'vcodec': 'none',
            }
            if '_preview_' in vip_url:
                self.report_warning(
                    f'This tracks requires a VIP account. Using a sample instead. {self._login_hint()}')
                fmt.update({
                    'format_note': 'Sample',
                    'preference': -10,
                    **traverse_obj(vip_info, {
                        'filesize': ('sampleLength', {int_or_none}),
                        'duration': ('sampleDuration', {int_or_none}),
                    }),
                })
            else:
                fmt.update(traverse_obj(vip_info, {
                    'filesize': ('totalLength', {int_or_none}),
                    'duration': ('duration', {int_or_none}),
                }))

            fmt['abr'] = try_call(lambda: fmt['filesize'] * 8 / fmt['duration'] / 1024)
            formats.append(fmt)

        formats.extend([{
            'format_id': f'{bps}k',
            'url': audio_info[k],
            'abr': bps,
            'vcodec': 'none',
        } for bps, k in ((24, 'play_path_32'), (64, 'play_path_64')) if audio_info.get(k)])

        thumbnails = []
        for k in audio_info:
            # cover pics kyes like: cover_url', 'cover_url_142'
            if k.startswith('cover_url'):
                thumbnail = {'name': k, 'url': audio_info[k]}
                if k == 'cover_url_142':
                    thumbnail['width'] = 180
                    thumbnail['height'] = 180
                thumbnails.append(thumbnail)

        audio_uploader_id = audio_info.get('uid')

        audio_description = try_call(
            lambda: audio_info['intro'].replace('\r\n\r\n\r\n ', '\n').replace('\r\n', '\n'))

        return {
            'id': audio_id,
            'uploader': audio_info.get('nickname'),
            'uploader_id': str_or_none(audio_uploader_id),
            'uploader_url': f'{scheme}://www.ximalaya.com/zhubo/{audio_uploader_id}/' if audio_uploader_id else None,
            'title': audio_info['title'],
            'thumbnails': thumbnails,
            'description': audio_description,
            'categories': list(filter(None, [audio_info.get('category_name')])),
            'duration': audio_info.get('duration'),
            'view_count': audio_info.get('play_count'),
            'like_count': audio_info.get('favorites_count'),
            'formats': formats,
        }


class XimalayaAlbumIE(XimalayaBaseIE):
    IE_NAME = 'ximalaya:album'
    IE_DESC = '喜马拉雅FM 专辑'
    _VALID_URL = r'https?://(?:www\.|m\.)?ximalaya\.com/(?:\d+/)?album/(?P<id>[0-9]+)'
    _TESTS = [{
        'url': 'http://www.ximalaya.com/61425525/album/5534601/',
        'info_dict': {
            'title': '唐诗三百首（含赏析）',
            'id': '5534601',
        },
        'playlist_mincount': 323,
    }, {
        'url': 'https://www.ximalaya.com/album/6912905',
        'info_dict': {
            'title': '埃克哈特《修炼当下的力量》',
            'id': '6912905',
        },
        'playlist_mincount': 41,
    }]

    def _real_extract(self, url):
        playlist_id = self._match_id(url)

        first_page = self._fetch_page(playlist_id, 1)
        page_count = math.ceil(first_page['trackTotalCount'] / first_page['pageSize'])

        entries = InAdvancePagedList(
            lambda idx: self._get_entries(self._fetch_page(playlist_id, idx + 1) if idx else first_page),
            page_count, first_page['pageSize'])

        title = traverse_obj(first_page, ('tracks', 0, 'albumTitle'), expected_type=str)

        return self.playlist_result(entries, playlist_id, title)

    def _fetch_page(self, playlist_id, page_idx):
        return self._download_json(
            'https://www.ximalaya.com/revision/album/v1/getTracksList',
            playlist_id, note=f'Downloading tracks list page {page_idx}',
            query={'albumId': playlist_id, 'pageNum': page_idx})['data']

    def _get_entries(self, page_data):
        for e in page_data['tracks']:
            yield self.url_result(
                self._proto_relative_url(f'//www.ximalaya.com{e["url"]}'),
                XimalayaIE, e.get('trackId'), e.get('title'))
