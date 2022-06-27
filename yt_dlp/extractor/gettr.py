from .common import InfoExtractor
from ..utils import (
    bool_or_none,
    ExtractorError,
    dict_get,
    float_or_none,
    int_or_none,
    str_or_none,
    traverse_obj,
    try_get,
    url_or_none,
    urljoin,
)


class GettrBaseIE(InfoExtractor):
    _BASE_REGEX = r'https?://(www\.)?gettr\.com/'
    _MEDIA_BASE_URL = 'https://media.gettr.com/'

    def _call_api(self, path, video_id, *args, **kwargs):
        return self._download_json(urljoin('https://api.gettr.com/u/', path), video_id, *args, **kwargs)['result']


class GettrIE(GettrBaseIE):
    _VALID_URL = GettrBaseIE._BASE_REGEX + r'post/(?P<id>[a-z0-9]+)'

    _TESTS = [{
        'url': 'https://www.gettr.com/post/pcf6uv838f',
        'info_dict': {
            'id': 'pcf6uv838f',
            'title': 'md5:9086a646bbd06c41c4fe8e52b3c93454',
            'description': 'md5:be0577f1e4caadc06de4a002da2bf287',
            'ext': 'mp4',
            'uploader': 'EpochTV',
            'uploader_id': 'epochtv',
            'upload_date': '20210927',
            'thumbnail': r're:^https?://.+/out\.jpg',
            'timestamp': 1632782451.058,
            'duration': 58.5585,
            'tags': ['hornofafrica', 'explorations'],
        }
    }, {
        'url': 'https://gettr.com/post/p4iahp',
        'info_dict': {
            'id': 'p4iahp',
            'title': 'md5:b03c07883db6fbc1aab88877a6c3b149',
            'description': 'md5:741b7419d991c403196ed2ea7749a39d',
            'ext': 'mp4',
            'uploader': 'Neues Forum Freiheit',
            'uploader_id': 'nf_freiheit',
            'upload_date': '20210718',
            'thumbnail': r're:^https?://.+/out\.jpg',
            'timestamp': 1626594455.017,
            'duration': 23,
            'tags': 'count:12',
        }
    }, {
        # quote post
        'url': 'https://gettr.com/post/pxn5b743a9',
        'only_matching': True,
    }, {
        # quote with video
        'url': 'https://gettr.com/post/pxtiiz5ca2',
        'only_matching': True,
    }, {
        # streaming embed
        'url': 'https://gettr.com/post/pxlu8p3b13',
        'only_matching': True,
    }, {
        # youtube embed
        'url': 'https://gettr.com/post/pv6wp9e24c',
        'only_matching': True,
        'add_ie': ['Youtube'],
    }]

    def _real_extract(self, url):
        post_id = self._match_id(url)
        webpage = self._download_webpage(url, post_id)
        api_data = self._call_api('post/%s?incl="poststats|userinfo"' % post_id, post_id)

        post_data = api_data.get('data')
        user_data = try_get(api_data, lambda x: x['aux']['uinf'][post_data['uid']], dict) or {}

        vid = post_data.get('vid')
        ovid = post_data.get('ovid')

        if post_data.get('p_type') == 'stream':
            return self.url_result(f'https://gettr.com/streaming/{post_id}', ie='GettrStreaming', video_id=post_id)

        if not (ovid or vid):
            embed_url = url_or_none(post_data.get('prevsrc'))
            shared_post_id = traverse_obj(api_data, ('aux', 'shrdpst', '_id'), ('data', 'rpstIds', 0), expected_type=str)

            if embed_url:
                return self.url_result(embed_url)
            elif shared_post_id:
                return self.url_result(f'https://gettr.com/post/{shared_post_id}', ie='Gettr', video_id=shared_post_id)
            else:
                raise ExtractorError('There\'s no video in this post.')

        title = description = str_or_none(
            post_data.get('txt') or self._og_search_description(webpage))

        uploader = str_or_none(
            user_data.get('nickname')
            or self._search_regex(r'^(.+?) on GETTR', self._og_search_title(webpage, default=''), 'uploader', fatal=False))

        if uploader:
            title = '%s - %s' % (uploader, title)

        formats, subtitles = self._extract_m3u8_formats_and_subtitles(
            urljoin(self._MEDIA_BASE_URL, vid), post_id, 'mp4',
            entry_protocol='m3u8_native', m3u8_id='hls', fatal=False) if vid else ([], {})

        if ovid:
            formats.append({
                'url': urljoin(self._MEDIA_BASE_URL, ovid),
                'format_id': 'ovid',
                'ext': 'mp4',
                'width': int_or_none(post_data.get('vid_wid')),
                'height': int_or_none(post_data.get('vid_hgt')),
            })

        self._sort_formats(formats)

        return {
            'id': post_id,
            'title': title,
            'description': description,
            'formats': formats,
            'subtitles': subtitles,
            'uploader': uploader,
            'uploader_id': str_or_none(
                dict_get(user_data, ['_id', 'username'])
                or post_data.get('uid')),
            'thumbnail': url_or_none(
                urljoin(self._MEDIA_BASE_URL, post_data.get('main'))
                or self._html_search_meta(['og:image', 'image'], webpage, 'thumbnail', fatal=False)),
            'timestamp': float_or_none(dict_get(post_data, ['cdate', 'udate']), scale=1000),
            'duration': float_or_none(post_data.get('vid_dur')),
            'tags': post_data.get('htgs'),
        }


class GettrStreamingIE(GettrBaseIE):
    _VALID_URL = GettrBaseIE._BASE_REGEX + r'streaming/(?P<id>[a-z0-9]+)'

    _TESTS = [{
        'url': 'https://gettr.com/streaming/psoiulc122',
        'info_dict': {
            'id': 'psoiulc122',
            'ext': 'mp4',
            'description': 'md5:56bca4b8f48f1743d9fd03d49c723017',
            'view_count': int,
            'uploader': 'Corona Investigative Committee',
            'uploader_id': 'coronacommittee',
            'duration': 5180.184,
            'thumbnail': r're:^https?://.+',
            'title': 'Day 1: Opening Session of the Grand Jury Proceeding',
            'timestamp': 1644080997.164,
            'upload_date': '20220205',
        }
    }, {
        'url': 'https://gettr.com/streaming/psfmeefcc1',
        'info_dict': {
            'id': 'psfmeefcc1',
            'ext': 'mp4',
            'title': 'Session 90: "The Virus Of Power"',
            'view_count': int,
            'uploader_id': 'coronacommittee',
            'description': 'md5:98986acdf656aa836bf36f9c9704c65b',
            'uploader': 'Corona Investigative Committee',
            'thumbnail': r're:^https?://.+',
            'duration': 21872.507,
            'timestamp': 1643976662.858,
            'upload_date': '20220204',
        }
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        video_info = self._call_api('live/join/%s' % video_id, video_id, data={})

        live_info = video_info['broadcast']
        live_url = url_or_none(live_info.get('url'))

        formats, subtitles = self._extract_m3u8_formats_and_subtitles(
            live_url, video_id, ext='mp4',
            entry_protocol='m3u8_native', m3u8_id='hls', fatal=False) if live_url else ([], {})

        thumbnails = [{
            'url': urljoin(self._MEDIA_BASE_URL, thumbnail),
        } for thumbnail in try_get(video_info, lambda x: x['postData']['imgs'], list) or []]

        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': try_get(video_info, lambda x: x['postData']['ttl'], str),
            'description': try_get(video_info, lambda x: x['postData']['dsc'], str),
            'formats': formats,
            'subtitles': subtitles,
            'thumbnails': thumbnails,
            'uploader': try_get(video_info, lambda x: x['liveHostInfo']['nickname'], str),
            'uploader_id': try_get(video_info, lambda x: x['liveHostInfo']['_id'], str),
            'view_count': int_or_none(live_info.get('viewsCount')),
            'timestamp': float_or_none(live_info.get('startAt'), scale=1000),
            'duration': float_or_none(live_info.get('duration'), scale=1000),
            'is_live': bool_or_none(live_info.get('isLive')),
        }
