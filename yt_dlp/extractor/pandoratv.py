from .common import InfoExtractor
from ..compat import (
    compat_str,
)
from ..utils import (
    ExtractorError,
    float_or_none,
    parse_duration,
    parse_qs,
    str_to_int,
    urlencode_postdata,
)


class PandoraTVIE(InfoExtractor):
    IE_NAME = 'pandora.tv'
    IE_DESC = '판도라TV'
    _VALID_URL = r'''(?x)
                        https?://
                            (?:
                                (?:www\.)?pandora\.tv/view/(?P<user_id>[^/]+)/(?P<id>\d+)|  # new format
                                (?:.+?\.)?channel\.pandora\.tv/channel/video\.ptv\?|        # old format
                                m\.pandora\.tv/?\?                                          # mobile
                            )
                    '''
    _TESTS = [{
        'url': 'http://jp.channel.pandora.tv/channel/video.ptv?c1=&prgid=53294230&ch_userid=mikakim&ref=main&lot=cate_01_2',
        'info_dict': {
            'id': '53294230',
            'ext': 'flv',
            'title': '頭を撫でてくれる？',
            'description': '頭を撫でてくれる？',
            'thumbnail': r're:^https?://.*\.jpg$',
            'duration': 39,
            'upload_date': '20151218',
            'uploader': 'カワイイ動物まとめ',
            'uploader_id': 'mikakim',
            'view_count': int,
            'like_count': int,
        }
    }, {
        'url': 'http://channel.pandora.tv/channel/video.ptv?ch_userid=gogoucc&prgid=54721744',
        'info_dict': {
            'id': '54721744',
            'ext': 'flv',
            'title': '[HD] JAPAN COUNTDOWN 170423',
            'description': '[HD] JAPAN COUNTDOWN 170423',
            'thumbnail': r're:^https?://.*\.jpg$',
            'duration': 1704.9,
            'upload_date': '20170423',
            'uploader': 'GOGO_UCC',
            'uploader_id': 'gogoucc',
            'view_count': int,
            'like_count': int,
        },
        'params': {
            # Test metadata only
            'skip_download': True,
        },
    }, {
        'url': 'http://www.pandora.tv/view/mikakim/53294230#36797454_new',
        'only_matching': True,
    }, {
        'url': 'http://m.pandora.tv/?c=view&ch_userid=mikakim&prgid=54600346',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        user_id = mobj.group('user_id')
        video_id = mobj.group('id')

        if not user_id or not video_id:
            qs = parse_qs(url)
            video_id = qs.get('prgid', [None])[0]
            user_id = qs.get('ch_userid', [None])[0]
            if any(not f for f in (video_id, user_id,)):
                raise ExtractorError('Invalid URL', expected=True)

        data = self._download_json(
            'http://m.pandora.tv/?c=view&m=viewJsonApi&ch_userid=%s&prgid=%s'
            % (user_id, video_id), video_id)

        info = data['data']['rows']['vod_play_info']['result']

        formats = []
        for format_id, format_url in info.items():
            if not format_url:
                continue
            height = self._search_regex(
                r'^v(\d+)[Uu]rl$', format_id, 'height', default=None)
            if not height:
                continue

            play_url = self._download_json(
                'http://m.pandora.tv/?c=api&m=play_url', video_id,
                data=urlencode_postdata({
                    'prgid': video_id,
                    'runtime': info.get('runtime'),
                    'vod_url': format_url,
                }),
                headers={
                    'Origin': url,
                    'Content-Type': 'application/x-www-form-urlencoded',
                })
            format_url = play_url.get('url')
            if not format_url:
                continue

            formats.append({
                'format_id': '%sp' % height,
                'url': format_url,
                'height': int(height),
            })
        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': info['subject'],
            'description': info.get('body'),
            'thumbnail': info.get('thumbnail') or info.get('poster'),
            'duration': float_or_none(info.get('runtime'), 1000) or parse_duration(info.get('time')),
            'upload_date': info['fid'].split('/')[-1][:8] if isinstance(info.get('fid'), compat_str) else None,
            'uploader': info.get('nickname'),
            'uploader_id': info.get('upload_userid'),
            'view_count': str_to_int(info.get('hit')),
            'like_count': str_to_int(info.get('likecnt')),
            'formats': formats,
        }
