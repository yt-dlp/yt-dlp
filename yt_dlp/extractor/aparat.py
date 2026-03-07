from .common import InfoExtractor
from ..utils import (
    get_element_by_id,
    int_or_none,
    merge_dicts,
    mimetype2ext,
    str_or_none,
    url_or_none,
)
from ..utils.traversal import traverse_obj


class AparatIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?aparat\.com/(?:v/|video/video/embed/videohash/)(?P<id>[a-zA-Z0-9]+)'
    _EMBED_REGEX = [r'<iframe .*?src="(?P<url>http://www\.aparat\.com/video/[^"]+)"']

    _TESTS = [{
        'url': 'http://www.aparat.com/v/wP8On',
        'md5': '131aca2e14fe7c4dcb3c4877ba300c89',
        'info_dict': {
            'id': 'wP8On',
            'ext': 'mp4',
            'title': 'تیم گلکسی 11 - زومیت',
            'description': 'md5:096bdabcdcc4569f2b8a5e903a3b3028',
            'duration': 231,
            'timestamp': 1387394859,
            'upload_date': '20131218',
            'view_count': int,
            'thumbnail': r're:https://static\.cdn\.asset\.aparat\.cloud/.+',
            'like_count': int,
        },
    }, {
        # multiple formats
        'url': 'https://www.aparat.com/v/8dflw/',
        'only_matching': True,
    }]

    def _parse_options(self, webpage, video_id, fatal=True):
        return self._parse_json(self._search_regex(
            r'options\s*=\s*({.+?})\s*;', webpage, 'options', default='{}'), video_id)

    def _real_extract(self, url):
        video_id = self._match_id(url)

        # If available, provides more metadata
        webpage = self._download_webpage(url, video_id, fatal=False)
        options = self._parse_options(webpage, video_id, fatal=False)

        if not options:
            webpage = self._download_webpage(
                'http://www.aparat.com/video/video/embed/vt/frame/showvideo/yes/videohash/' + video_id,
                video_id, 'Downloading embed webpage')
            options = self._parse_options(webpage, video_id)

        formats = []
        for sources in (options.get('multiSRC') or []):
            for item in sources:
                if not isinstance(item, dict):
                    continue
                file_url = url_or_none(item.get('src'))
                if not file_url:
                    continue
                item_type = item.get('type')
                if item_type == 'application/vnd.apple.mpegurl':
                    formats.extend(self._extract_m3u8_formats(
                        file_url, video_id, 'mp4',
                        entry_protocol='m3u8_native', m3u8_id='hls',
                        fatal=False))
                else:
                    ext = mimetype2ext(item.get('type'))
                    label = item.get('label')
                    formats.append({
                        'url': file_url,
                        'ext': ext,
                        'format_id': 'http-%s' % (label or ext),
                        'height': int_or_none(self._search_regex(
                            r'(\d+)[pP]', label or '', 'height',
                            default=None)),
                    })

        info = self._search_json_ld(webpage, video_id, default={})

        if not info.get('title'):
            info['title'] = get_element_by_id('videoTitle', webpage) or \
                self._html_search_meta(['og:title', 'twitter:title', 'DC.Title', 'title'], webpage, fatal=True)

        return merge_dicts(info, {
            'id': video_id,
            'thumbnail': url_or_none(options.get('poster')),
            'duration': int_or_none(options.get('duration')),
            'formats': formats,
        })


class AparatPlaylistIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?aparat\.com/playlist/(?P<id>\d+)'

    _TESTS = [{
        'url': 'https://www.aparat.com/playlist/1001307',
        'info_dict': {
            'id': '1001307',
            'title': 'مبانی یادگیری عمیق',
            'description': '',
            'thumbnails': 'count:2',
            'channel': 'mrmohammadi_iust',
            'channel_id': '6463423',
            'channel_url': 'https://www.aparat.com/mrmohammadi_iust',
            'channel_follower_count': int,
        },
        'playlist_mincount': 1,
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'https://www.aparat.com/playlist/1234567',
        'info_dict': {
            'id': '1234567',
            'title': 'ساخت اکانت',
            'description': '',
            'thumbnails': 'count:0',
            'channel': 'reza.shadow',
            'channel_id': '8159952',
            'channel_url': 'https://www.aparat.com/reza.shadow',
            'channel_follower_count': int,
        },
        'playlist_count': 0,
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'https://www.aparat.com/playlist/1256882',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        playlist_id = self._match_id(url)
        info = self._download_json(
            f'https://www.aparat.com/api/fa/v1/video/playlist/one/playlist_id/{playlist_id}',
            playlist_id, note='Getting playlist info', errnote='Failed to get playlist info')

        info_dict = {
            **traverse_obj(info, ('data', 'attributes', {
                'title': 'title',
                'description': 'description',
                'thumbnails': (('big_poster', 'small_poster'), all, ..., {url_or_none}, {lambda x: {'url': x}}),
            }), default={}),
            'id': playlist_id,
            'entries': traverse_obj(info, (
                'included', lambda _, v: v['type'] == 'Video', 'attributes', 'uid',
                {lambda x: self.url_result(f'https://www.aparat.com/v/{x}?playlist={playlist_id}')},
            ), default=[]),
        }

        if username := traverse_obj(
                info, ('included', lambda _, v: v['type'] == 'channel', 'attributes', 'username'), get_all=False):
            user_info = self._download_json(
                f'https://www.aparat.com/api/fa/v1/user/user/information/username/{username}', playlist_id,
                fatal=False, note=f'Getting channel info ({username})', errnote=f'Failed to get channel info ({username})',
            )
            info_dict.update({
                **traverse_obj(user_info, ('data', 'attributes', {
                    'channel_id': ('id', {str_or_none}),
                    'channel_follower_count': ('follower_cnt_num', {int_or_none}),
                })),
                'channel': username,
                'channel_url': f'https://www.aparat.com/{username}',
            })

        return self.playlist_result(**info_dict)
