import math
import time

from .common import InfoExtractor
from ..utils import InAdvancePagedList, float_or_none, int_or_none, str_or_none, traverse_obj, try_call


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
            'url': 'https://www.ximalaya.com/album/70349771',
            'only_matching': True,
        },
    ]

    @staticmethod
    def _decrypt_filename(audio_info):
        seed = float_or_none(audio_info['seed'])
        file_id = audio_info['fileId']
        cgstr = ''
        key = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ/\\:._-1234567890'
        for _ in range(len(key)):
            j = 211 * seed + 30031
            seed = float_or_none(int_or_none(j) % 65536)
            ran = seed / float_or_none(65536)
            r = int_or_none(ran * float_or_none(len(key)))
            cgstr += key[r]
            key = key.replace(key[r], '')
        strs = file_id.split('*')
        filename = ''
        for n in range(len(strs) - 1):
            if strs[n] != '':
                index = int_or_none(strs[n])
                filename += cgstr[index]
        if filename[0] != '/':
            filename = '/' + filename
        return filename

    @staticmethod
    def _decrypt_url_params(audio_info):
        def char_code_at(s: str, n: int) -> int:
            return ord(s[n]) if n < len(s) else 0

        def decrypt(e: str, t: list) -> str:
            r = list(range(256))
            a = 0
            s = ''

            for o in range(256):
                a = (a + r[o] + int_or_none(char_code_at(e, o % len(e)))) % 256
                r[o], r[a] = r[a], r[o]

            a, o = 0, 0
            for u in range(len(t)):
                o = (o + 1) % 256
                a = (a + r[o]) % 256
                r[o], r[a] = r[a], r[o]
                s += chr(t[u] ^ r[(r[o] + r[a]) % 256])

            return s

        def decrypt2(key: str, key2: list) -> str:
            n = []
            for r in range(len(key)):
                a = ord('a')
                if ord('a') <= ord(key[r]) <= ord('z'):
                    a = ord(key[r]) - 97
                else:
                    a = ord(key[r]) - 48 + 26

                for i in range(36):
                    if key2[i] == a:
                        a = i
                        break

                if a > 25:
                    n.append(chr(a - 26 + 48))
                else:
                    n.append(chr(a + 97))

            return ''.join(n)

        def decrypt3(s: str) -> list:
            t = 0
            n = 0
            r = 0
            s_len = len(s)
            i = []
            o = [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
                 -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
                 -1, -1, -1, 62, -1, -1, -1, 63, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, -1, -1,
                 -1, -1, -1, -1, -1, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16,
                 17, 18, 19, 20, 21, 22, 23, 24, 25, -1, -1, -1, -1, -1, -1, 26, 27, 28, 29, 30,
                 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50,
                 51, -1, -1, -1, -1, -1]

            while r < s_len:
                t = o[char_code_at(s, r) & 255]
                r += 1
                while r < s_len and t == -1:
                    t = o[char_code_at(s, r) & 255]
                    r += 1
                if t == -1:
                    break

                n = o[char_code_at(s, r) & 255]
                r += 1
                while r < s_len and n == -1:
                    n = o[char_code_at(s, r) & 255]
                    r += 1
                if t == -1:
                    break

                i.append((t << 2) | ((n & 48) >> 4))

                t = int_or_none(char_code_at(s, r)) & 255
                r += 1
                if t == 61:
                    return i
                t = o[t]
                while r < s_len and t == -1:
                    t = int_or_none(char_code_at(s, r)) & 255
                    r += 1
                    if t == 61:
                        return i
                    t = o[t]
                if t == -1:
                    break

                i.append(((n & 15) << 4) | ((t & 60) >> 2))

                n = int_or_none(char_code_at(s, r)) & 255
                r += 1
                if n == 61:
                    return i
                n = o[n]
                while r < s_len and n == -1:
                    n = int_or_none(char_code_at(s, r)) & 255
                    r += 1
                    if n == 61:
                        return i
                    n = o[n]
                if n == -1:
                    break
                i.append(((t & 3) << 6) | n)

            return i

        o = 'g3utf1k6yxdwi0'
        u = [19, 1, 4, 7, 30, 14, 28, 8, 24, 17, 6, 35, 34, 16, 9, 10, 13, 22,
             32, 29, 31, 21, 18, 3, 2, 23, 25, 27, 11, 20, 5, 15, 12, 0, 33, 26]
        s1 = decrypt3(audio_info['ep'])
        s2 = decrypt(decrypt2('d' + o + '9', u), s1)
        ss = s2.split('-')
        sign = ss[1]
        token = ss[2]
        timestamp = ss[3]
        return sign, token, timestamp

    def _real_extract(self, url):
        scheme = 'https' if url.startswith('https') else 'http'

        audio_id = self._match_id(url)
        audio_info_file = f'{scheme}://m.ximalaya.com/tracks/{audio_id}.json'
        audio_info = self._download_json(
            audio_info_file, audio_id,
            f'Downloading info json {audio_info_file}', 'Unable to download info file')

        # NOTE(xcsong): VIP-restricted audio
        if audio_info.get('is_paid', False):
            ts = int_or_none(time.time())
            audio_info_file = f'{scheme}://mpay.ximalaya.com/mobile/track/pay/{audio_id}/{ts}?device=pc&isBackend=true&_={ts}'
            audio_info = self._download_json(
                audio_info_file, audio_id,
                f'Downloading VIP info json {audio_info_file}', 'Unable to download VIP info file')
            filename = self._decrypt_filename(audio_info)
            sign, token, timestamp = self._decrypt_url_params(audio_info)
            buy_key = audio_info.get('buyKey')
            duration = audio_info.get('duration')
            domain = audio_info.get('domain')
            api_version = audio_info.get('apiVersion')
            args = f'?sign={sign}&buy_key={buy_key}&token={token}&timestamp={timestamp}&duration={duration}'
            audio_info['play_path_64'] = f'{domain}/download/{api_version}{filename}{args}'
            if '_preview_' in audio_info['play_path_64']:
                self.report_warning('Please use correct cookies to download VIP audios!')

        formats = [{
            'format_id': f'{bps}k',
            'url': audio_info[k],
            'abr': bps,
            'vcodec': 'none',
        } for bps, k in ((24, 'play_path_32'), (64, 'play_path_64')) if audio_info.get(k)]

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
