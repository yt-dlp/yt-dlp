from .common import InfoExtractor
from ..utils import (
    int_or_none,
    str_or_none,
    try_get,
    url_or_none,
)


class XinpianchangIE(InfoExtractor):
    _VALID_URL = r'https?://(www\.)?xinpianchang\.com/(?P<id>a\d+)'
    IE_DESC = '新片场'
    _TESTS = [{
        'url': 'https://www.xinpianchang.com/a11766551',
        'info_dict': {
            'id': 'a11766551',
            'ext': 'mp4',
            'title': '北京2022冬奥会闭幕式再见短片-冰墩墩下班了',
            'description': 'md5:4a730c10639a82190fabe921c0fa4b87',
            'duration': 151,
            'thumbnail': r're:^https?://oss-xpc0\.xpccdn\.com.+/assets/',
            'uploader': '正时文创',
            'uploader_id': '10357277',
            'categories': ['宣传片', '国家城市', '广告', '其他'],
            'tags': ['北京冬奥会', '冰墩墩', '再见', '告别', '冰墩墩哭了', '感动', '闭幕式', '熄火'],
        },
    }, {
        'url': 'https://www.xinpianchang.com/a11762904',
        'info_dict': {
            'id': 'a11762904',
            'ext': 'mp4',
            'title': '冬奥会决胜时刻《法国派出三只鸡？》',
            'description': 'md5:55cb139ef8f48f0c877932d1f196df8b',
            'duration': 136,
            'thumbnail': r're:^https?://oss-xpc0\.xpccdn\.com.+/assets/',
            'uploader': '精品动画',
            'uploader_id': '10858927',
            'categories': ['动画', '三维CG'],
            'tags': ['France Télévisions', '法国3台', '蠢萌', '冬奥会'],
        },
    }, {
        'url': 'https://www.xinpianchang.com/a11779743?from=IndexPick&part=%E7%BC%96%E8%BE%91%E7%B2%BE%E9%80%89&index=2',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id=video_id, headers={'Referer': url})
        video_data = self._search_nextjs_data(webpage, video_id)['props']['pageProps']['detail']['video']

        data = self._download_json(
            f'https://mod-api.xinpianchang.com/mod/api/v2/media/{video_data["vid"]}', video_id,
            query={'appKey': video_data['appKey']})['data']
        formats, subtitles = [], {}
        for k, v in data.get('resource').items():
            if k in ('dash', 'hls'):
                v_url = v.get('url')
                if not v_url:
                    continue
                if k == 'dash':
                    fmts, subs = self._extract_mpd_formats_and_subtitles(v_url, video_id=video_id)
                elif k == 'hls':
                    fmts, subs = self._extract_m3u8_formats_and_subtitles(v_url, video_id=video_id)
                formats.extend(fmts)
                subtitles = self._merge_subtitles(subtitles, subs)
            elif k == 'progressive':
                formats.extend([{
                    'url': url_or_none(prog.get('url')),
                    'width': int_or_none(prog.get('width')),
                    'height': int_or_none(prog.get('height')),
                    'ext': 'mp4',
                    'http_headers': {
                        # NB: Server returns 403 without the Range header
                        'Range': 'bytes=0-',
                    },
                } for prog in v if prog.get('url') or []])

        return {
            'id': video_id,
            'title': data.get('title'),
            'description': data.get('description'),
            'duration': int_or_none(data.get('duration')),
            'categories': data.get('categories'),
            'tags': data.get('keywords'),
            'thumbnail': data.get('cover'),
            'uploader': try_get(data, lambda x: x['owner']['username']),
            'uploader_id': str_or_none(try_get(data, lambda x: x['owner']['id'])),
            'formats': formats,
            'subtitles': subtitles,
        }
