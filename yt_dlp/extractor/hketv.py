from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    clean_html,
    int_or_none,
    merge_dicts,
    parse_count,
    str_or_none,
    try_get,
    unified_strdate,
    urlencode_postdata,
    urljoin,
)


class HKETVIE(InfoExtractor):
    IE_NAME = 'hketv'
    IE_DESC = '香港教育局教育電視 (HKETV) Educational Television, Hong Kong Educational Bureau'
    _GEO_BYPASS = False
    _GEO_COUNTRIES = ['HK']
    _VALID_URL = r'https?://(?:www\.)?hkedcity\.net/etv/resource/(?P<id>[0-9]+)'
    _TESTS = [{
        'url': 'https://www.hkedcity.net/etv/resource/2932360618',
        'md5': 'f193712f5f7abb208ddef3c5ea6ed0b7',
        'info_dict': {
            'id': '2932360618',
            'ext': 'mp4',
            'title': '喜閱一生(共享閱讀樂) (中、英文字幕可供選擇)',
            'description': 'md5:d5286d05219ef50e0613311cbe96e560',
            'upload_date': '20181024',
            'duration': 900,
            'subtitles': 'count:2',
        },
        'skip': 'Geo restricted to HK',
    }, {
        'url': 'https://www.hkedcity.net/etv/resource/972641418',
        'md5': '1ed494c1c6cf7866a8290edad9b07dc9',
        'info_dict': {
            'id': '972641418',
            'ext': 'mp4',
            'title': '衣冠楚楚 (天使系列之一)',
            'description': 'md5:10bb3d659421e74f58e5db5691627b0f',
            'upload_date': '20070109',
            'duration': 907,
            'subtitles': {},
        },
        'params': {
            'geo_verification_proxy': '<HK proxy here>',
        },
        'skip': 'Geo restricted to HK',
    }]

    _CC_LANGS = {
        '中文（繁體中文）': 'zh-Hant',
        '中文（简体中文）': 'zh-Hans',
        'English': 'en',
        'Bahasa Indonesia': 'id',
        '\u0939\u093f\u0928\u094d\u0926\u0940': 'hi',
        '\u0928\u0947\u092a\u093e\u0932\u0940': 'ne',
        'Tagalog': 'tl',
        '\u0e44\u0e17\u0e22': 'th',
        '\u0627\u0631\u062f\u0648': 'ur',
    }
    _FORMAT_HEIGHTS = {
        'SD': 360,
        'HD': 720,
    }
    _APPS_BASE_URL = 'https://apps.hkedcity.net'

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        title = (
            self._html_search_meta(
                ('ed_title', 'search.ed_title'), webpage, default=None)
            or self._search_regex(
                r'data-favorite_title_(?:eng|chi)=(["\'])(?P<id>(?:(?!\1).)+)\1',
                webpage, 'title', default=None, group='url')
            or self._html_search_regex(
                r'<h1>([^<]+)</h1>', webpage, 'title', default=None)
            or self._og_search_title(webpage)
        )

        file_id = self._search_regex(
            r'post_var\[["\']file_id["\']\s*\]\s*=\s*(.+?);',
            webpage, 'file ID')
        curr_url = self._search_regex(
            r'post_var\[["\']curr_url["\']\s*\]\s*=\s*"(.+?)";',
            webpage, 'curr URL')
        data = {
            'action': 'get_info',
            'curr_url': curr_url,
            'file_id': file_id,
            'video_url': file_id,
        }

        response = self._download_json(
            self._APPS_BASE_URL + '/media/play/handler.php', video_id,
            data=urlencode_postdata(data),
            headers=merge_dicts({
                'Content-Type': 'application/x-www-form-urlencoded'},
                self.geo_verification_headers()))

        result = response['result']

        if not response.get('success') or not response.get('access'):
            error = clean_html(response.get('access_err_msg'))
            if 'Video streaming is not available in your country' in error:
                self.raise_geo_restricted(
                    msg=error, countries=self._GEO_COUNTRIES)
            else:
                raise ExtractorError(error, expected=True)

        formats = []

        width = int_or_none(result.get('width'))
        height = int_or_none(result.get('height'))

        playlist0 = result['playlist'][0]
        for fmt in playlist0['sources']:
            file_url = urljoin(self._APPS_BASE_URL, fmt.get('file'))
            if not file_url:
                continue
            # If we ever wanted to provide the final resolved URL that
            # does not require cookies, albeit with a shorter lifespan:
            #     urlh = self._downloader.urlopen(file_url)
            #     resolved_url = urlh.url
            label = fmt.get('label')
            h = self._FORMAT_HEIGHTS.get(label)
            w = h * width // height if h and width and height else None
            formats.append({
                'format_id': label,
                'ext': fmt.get('type'),
                'url': file_url,
                'width': w,
                'height': h,
            })

        subtitles = {}
        tracks = try_get(playlist0, lambda x: x['tracks'], list) or []
        for track in tracks:
            if not isinstance(track, dict):
                continue
            track_kind = str_or_none(track.get('kind'))
            if not track_kind or not isinstance(track_kind, str):
                continue
            if track_kind.lower() not in ('captions', 'subtitles'):
                continue
            track_url = urljoin(self._APPS_BASE_URL, track.get('file'))
            if not track_url:
                continue
            track_label = track.get('label')
            subtitles.setdefault(self._CC_LANGS.get(
                track_label, track_label), []).append({
                    'url': self._proto_relative_url(track_url),
                    'ext': 'srt',
                })

        # Likes
        emotion = self._download_json(
            'https://emocounter.hkedcity.net/handler.php', video_id,
            data=urlencode_postdata({
                'action': 'get_emotion',
                'data[bucket_id]': 'etv',
                'data[identifier]': video_id,
            }),
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            fatal=False) or {}
        like_count = int_or_none(try_get(
            emotion, lambda x: x['data']['emotion_data'][0]['count']))

        return {
            'id': video_id,
            'title': title,
            'description': self._html_search_meta(
                'description', webpage, fatal=False),
            'upload_date': unified_strdate(self._html_search_meta(
                'ed_date', webpage, fatal=False), day_first=False),
            'duration': int_or_none(result.get('length')),
            'formats': formats,
            'subtitles': subtitles,
            'thumbnail': urljoin(self._APPS_BASE_URL, result.get('image')),
            'view_count': parse_count(result.get('view_count')),
            'like_count': like_count,
        }
