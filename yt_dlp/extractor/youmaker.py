# coding: utf-8
import re
from operator import itemgetter
from urllib.parse import urlparse, parse_qsl

from .common import InfoExtractor
from ..utils import (
    parse_iso8601,
    ExtractorError,
    try_get,
    OnDemandPagedList,
    traverse_obj
)


class ParsedURL(object):
    """
    This class provides a unified interface for urlparse(),
    parse_qsl() and regular expression groups
    """

    def __init__(self, url, regex=None):
        self._match = None
        self._groups = {}
        self._query = query = {}
        self._parts = parts = urlparse(url)

        for key, value in parse_qsl(parts.query):
            query[key] = int(value) if value.isdigit() else value

        if regex:
            self._match = re.match(regex, url)
            assert self._match, 'regex does not match url'

    def __getattr__(self, item):
        """
        forward the attributes from urlparse.ParsedResult
        thus providing scheme, netloc, url, params, fragment

        note that .query is shadowed by a different method
        """
        return getattr(self._parts, item)

    def query(self, key=None, default=None):
        if key is None:
            return dict(self._query)

        return self._query.get(key, default)

    def regex_group(self, key=None):
        assert self._match, 'no regex provided'
        if key is None:
            return self._match.groupdict()

        return self._match.group(key)


class YoumakerIE(InfoExtractor):
    _VALID_URL = r"""(?x)
                    https?://(?:[a-z][a-z0-9]+\.)?youmaker\.com/
                    (?:v|video|embed|channel|playlist)/
                    (?P<id>[0-9a-zA-Z-]+)
                    """

    _TESTS = [{
        # single video with playlist subtitles
        'url': 'https://www.youmaker.com/video/8edd428d-74be-4eb0-b3fd-7b277e508adb',
        'info_dict': {
            'id': '8edd428d-74be-4eb0-b3fd-7b277e508adb',
            'ext': 'mp4',
            'title': 'x22 Report Ep. 2597b - Trump Never Conceded, Space Force Going...',
            'description': r're:(?s)^https://t\.me/realx22report\.+',
            'thumbnail': r're:^https?://.*\.(?:jpg|png)$',
            'duration': 2697,
            'upload_date': '20211011',
            'uploader': 'user_d94db024048d1d562eaa479eeedfc0bf6a8a8a3b',
            'timestamp': 1633915895,
            'channel': 'Channel 17',
            'channel_id': 'e92d56c8-249f-4f61-b7d0-75c4e05ecb4f',
            'channel_url': r're:https?://(:?[a-z][a-z0-9]+\.)?youmaker.com/channel/e92d56c8-249f-4f61-b7d0-75c4e05ecb4f',
            'tags': ['qanon', 'trump', 'usa', 'maga'],
            'categories': ['News'],
            'subtitles': {
                'en': [{
                    'url': r're:https?://[a-z1-3]+.youmaker.com/assets/2021/1011/8edd428d-74be-4eb0-b3fd-7b277e508adb/subtitles_en.m3u8'
                }]
            },
        },
        'params': {'skip_download': True, 'listsubtitles': True},
    }, {
        # test video with JSON requested subtitles
        'url': 'https://www.youmaker.com/video/b58f88fe-4ddb-4c11-bccf-46f579b7d978',
        'info_dict': {
            'id': 'b58f88fe-4ddb-4c11-bccf-46f579b7d978',
            'ext': 'mp4',
            'title': 'Snow cone vendor in Antigua, Guatemala',
            'description': r're:(?s)^We call it "Gola" here in India\.\.\..*',
            'upload_date': '20211001',
            'uploader': 'user_71885a31e113614751e14bba45d3bdcfd10d3f08',
            'timestamp': 1633055950,
            'subtitles': {
                'en': [{
                    'url': r're:https?://[a-z1-3]+.youmaker.com/assets/2021/1001/b58f88fe-4ddb-4c11-bccf-46f579b7d978/subtitle_1633055993844.auto.en.vtt'
                }]
            },
        },
        'params': {'skip_download': True, 'listsubtitles': True},
    }, {
        # all videos from channel
        'url': 'http://www.youmaker.com/channel/f06b2e8d-219e-4069-9003-df343ac5fcf3',
        'playlist_mincount': 30,
        'info_dict': {
            'id': 'f06b2e8d-219e-4069-9003-df343ac5fcf3',
            'title': 'YoYo Cello',
            'description': 'Connect the World Through Music. \nConnect Our Hearts with Music.',
        },
    }, {
        # all videos from channel playlist
        'url': 'https://www.youmaker.com/channel/f8d585f8-2ff7-4c3c-b1ea-a78d77640d54/playlists/f99a120c-7a5e-47b2-9235-3817d1c12662',
        'playlist_mincount': 9,
        'info_dict': {
            'id': 'f99a120c-7a5e-47b2-9235-3817d1c12662',
            'title': 'Mini Cakes',
        },
    }, {
        'url': 'https://www.youmaker.com/embed/Dnnrq0lw8062/',
        'only_matching': True,
    }, {
        'url': 'https://vs.youmaker.com/v/Dnnrq0lw8062/',
        'only_matching': True,
    }, {
        'url': 'https://youmaker.com/playlist/v6aLJnrqkoXO/',
        'only_matching': True,
    }, {
        'url': 'http://youmaker.com/channel/ntd/',
        'only_matching': True,
    }]
    REQUEST_LIMIT = 50

    def __init__(self, downloader=None):
        """Constructor. Receives an optional downloader."""
        super(YoumakerIE, self).__init__(downloader=downloader)
        self._protocol = 'https'
        self._category_map = None
        self._cache = {}

    @staticmethod
    def _extract_url(webpage):
        match = re.search(
            r"""(?x)
                <iframe[^>]+src="
                (?P<url>
                    https?://(?:[a-z][a-z0-9]+\.)?
                    youmaker\.com/embed/[0-9a-zA-Z-]+
                )
                [^"]*"
                """, webpage)
        return match.group('url') if match else None

    def _fix_url(self, url):
        if url.startswith('//'):
            return f'{self._protocol}:{url}'
        return url

    @property
    def _base_url(self):
        return self._fix_url('//www.youmaker.com')

    @property
    def _asset_url(self):
        # as this url might change in the future
        # it needs to be extracted from some js magic...
        return self._fix_url('//vs.youmaker.com/assets')

    def _live_url(self, video_id):
        return self._fix_url(f'//live.youmaker.com/{video_id}/playlist.m3u8')

    @staticmethod
    def _try_server_urls(url):
        """ as some playlist urls are invalid
            we can generate possible candidates to try
        """
        if not url:
            return []

        match_replace = (("//vs.youmaker.com/", "//vs1.youmaker.com/"),
                         ("//vs1.youmaker.com/", "//vs.youmaker.com/"),)
        candidates = [url]

        for match, replace in match_replace:
            other_url = url.replace(match, replace)
            if url != other_url:
                candidates.append(other_url)

        return candidates

    def _call_api(self, uid, path, what='JSON metadata', fatal=True, **kwargs):
        """
        call the YouMaker JSON API and return a valid data object

        path:       API endpoint
        what:       query description
        fatal:      if True might raise ExtractorError otherwise warn and return None
        **kwargs:   parameters passed to _download_json()
        """
        url = f'{self._base_url}/v1/api/{path}'
        kwargs.setdefault('note', f'Downloading {what}')
        kwargs.setdefault('errnote', f'Failed to download {what}')
        info = self._download_json(url, uid, fatal=fatal, **kwargs)

        # soft error already reported
        if info is False:
            return None

        status = try_get(info, itemgetter('status'), str)
        data = try_get(info, itemgetter('data'), (list, dict))

        if status != 'ok':
            msg = f'{what} - {status or "Bad JSON response"}'
            if fatal or status is None:
                raise ExtractorError(msg, video_id=uid, expected=isinstance(status, str))
            self.report_warning(msg, video_id=uid)

        return data

    @property
    def _categories(self):
        if self._category_map is None:
            category_list = self._call_api(
                None, 'video/category/list', what='categories', fatal=False) or ()
            self._category_map = {item['category_id']: item for item in category_list}
        return self._category_map

    def _categories_by_id(self, cid):
        categories = []
        if cid is None:
            return categories

        while True:
            item = self._categories.get(cid)
            if item is None or item['category_name'] in categories:
                break
            categories.insert(0, item['category_name'])
            cid = item['parent_category_id']

        return categories

    def _get_subtitles(self, system_id):
        if system_id is None:
            return {}

        subs_list = (self._call_api(
            system_id, 'video/subtitle', what='subtitle info',
            query={'systemid': system_id}, fatal=False) or ())

        subtitles = {}
        for item in subs_list:
            lang, url = itemgetter('language_code', 'url')(item)
            subtitles.setdefault(lang, []).append(
                {'url': f'{self._asset_url}/{url}'})

        return subtitles

    def _video_entry_by_metadata(self, info):
        try:
            video_uid, title = itemgetter('video_uid', 'title')(info)
        except KeyError as exc:
            raise ExtractorError(f'{exc!s} not found in video metadata')

        video_info = info.get('data', {})
        tag_str = info.get('tag')
        tags = [tag.strip() for tag in tag_str.strip('[]').split(',')] if tag_str else None
        channel_url = (
            f'{self._base_url}/channel/{info["channel_uid"]}' if 'channel_uid' in info else None)
        duration = video_info.get('duration')

        playlist_url = traverse_obj(video_info, ['videoAssets', 'Stream'], expected_type=str)
        if info.get('live') and playlist_url is None:
            is_live = True
            playlist_url = self._live_url(video_uid)
            if info.get('live_status') != 'start':
                self.report_warning('Live stream might not be ready yet.', video_id=video_uid)
        else:
            is_live = False

        formats = []
        playlist_subtitles = {}
        for count, candidate_url in enumerate(self._try_server_urls(playlist_url)):
            if count > 0:
                self.report_warning(
                    f"Missing m3u8 info. Trying alternative server ({count})")
            formats, playlist_subtitles = self._extract_m3u8_formats_and_subtitles(
                self._fix_url(candidate_url), video_uid, ext='mp4',
                entry_protocol='m3u8' if is_live else 'm3u8_native',
                errnote=False, fatal=False)
            if formats:
                break

        if not formats:
            # as there are some videos on the platform with missing playlist
            # expected is set True if the playlist url is valid
            raise ExtractorError(
                'No video formats found!',
                video_id=video_uid,
                expected=playlist_url is not None)

        # sometimes there are duplicate entries, so filter we them out
        format_mapping = {item['url']: item for item in formats}
        formats = list(format_mapping.values())

        self._sort_formats(formats)
        for item in formats:
            height = try_get(item, itemgetter('height'), int)
            if height:
                item['format_id'] = f'{height}p'
            tbr = try_get(item, itemgetter('tbr'), (int, float))
            if duration and tbr:
                item['filesize_approx'] = 128 * tbr * duration

        return {
            'id': video_uid,
            'title': title,
            'description': info.get('description'),
            'formats': formats,
            'is_live': is_live,
            'timestamp': parse_iso8601(info.get('uploaded_at')),
            'uploader': info.get('uploaded_by'),
            'duration': duration,
            'categories': self._categories_by_id(info.get('category_id')),
            'tags': tags,
            'channel': info.get('channel_name'),
            'channel_id': info.get('channel_uid'),
            'channel_url': channel_url,
            'thumbnail': info.get('thumbmail_path'),
            'view_count': info.get('click'),
            'subtitles': playlist_subtitles or self.extract_subtitles(info.get('system_id')),
        }

    def _video_entry_by_id(self, uid):
        info = (self._cache.get(uid)
                or self._call_api(uid, f'video/metadata/{uid}', what='video metadata'))

        return self._video_entry_by_metadata(info)

    def _paged_playlist_entries(self, uid, page_size=REQUEST_LIMIT):
        def fetch_page(page_number):
            offset = page_number * page_size
            info = self._call_api(
                uid,
                path='playlist/video',
                what=f'playlist entries {offset + 1}-{offset + page_size}',
                query={'playlist_uid': uid, 'offset': offset, 'limit': page_size})
            if not isinstance(info, list):
                raise ExtractorError('Unexpected playlist entries', uid, expected=False)

            for item in info:
                video_uid, title = itemgetter('video_uid', 'video_title')(item)
                yield self.url_result(
                    f'{self._base_url}/video/{video_uid}',
                    ie=self.ie_key(),
                    video_id=video_uid,
                    video_title=title)

        _ = self._categories  # preload categories
        return OnDemandPagedList(fetch_page, page_size)

    def _paged_channel_entries(self, uid, page_size=REQUEST_LIMIT):
        def fetch_page(page_number):
            offset = page_number * page_size
            info = self._call_api(
                uid,
                path=f'video/channel/{uid}',
                what=f'channel entries {offset + 1}-{offset + page_size}',
                query={'offset': offset, 'limit': page_size})
            if not isinstance(info, list):
                raise ExtractorError('Unexpected channel entries', uid, expected=False)

            for item in info:
                video_uid, title = itemgetter('video_uid', 'title')(item)
                self._cache[video_uid] = item
                yield self.url_result(
                    f'{self._base_url}/video/{video_uid}',
                    ie=self.ie_key(),
                    video_id=video_uid,
                    video_title=title)

        _ = self._categories  # preload categories
        return OnDemandPagedList(fetch_page, page_size)

    def _playlist_entries_by_id(self, uid):
        _ = self._categories  # preload categories
        info = self._call_api(uid, f'playlist/{uid}', what='playlist metadata')
        return self.playlist_result(
            self._paged_playlist_entries(info['playlist_uid']),
            playlist_id=info['playlist_uid'],
            playlist_title=info.get('name'),
            playlist_description=None)

    def _channel_entries_by_id(self, uid):
        _ = self._categories  # preload categories
        info = self._call_api(
            uid,
            path=f'video/channel/metadata/{uid}',
            what='channel metadata')
        return self.playlist_result(
            self._paged_channel_entries(info['channel_uid']),
            playlist_id=info['channel_uid'],
            playlist_title=info.get('name'),
            playlist_description=info.get('description'))

    def _real_extract(self, url):
        parsed_url = ParsedURL(url)
        self._protocol = parsed_url.scheme

        dispatch = (
            (r'/(?:v|video|embed)/(?P<uid>[a-zA-z0-9-]+)', self._video_entry_by_id),
            (r'(/channel/[a-zA-z0-9-]+)?/playlists?/(?P<uid>[a-zA-z0-9-]+)',
             self._playlist_entries_by_id),
            (r'/channel/(?P<uid>[a-zA-z0-9-]+)/?$', self._channel_entries_by_id),
        )

        for regex, func in dispatch:
            match = re.match(regex, parsed_url.path)
            if not match:
                continue
            return func(**match.groupdict())
        else:
            raise ExtractorError(f'unsupported {self.ie_key()} url', expected=True)
