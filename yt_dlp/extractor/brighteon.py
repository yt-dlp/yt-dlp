# coding: utf-8
import json
from operator import itemgetter

from .common import InfoExtractor
from ..compat import (
    compat_urllib_parse_urlparse,
    compat_parse_qs,
)
from ..utils import (
    get_element_by_id,
    int_or_none,
    parse_duration,
    parse_iso8601,
    traverse_obj,
    ExtractorError,
    update_url_query,
    OnDemandPagedList,
)


class BrighteonIE(InfoExtractor):
    IE_NAME = 'brighteon'
    _VALID_URL = r'''(?x)
                    https?://
                        (?:www\.)?
                        (?:brighteon\.com/)
                        (?:channels/|categories/|watch/)?
                        (?P<id>[a-zA-z0-9-]+)
                    '''
    _BASE_URL = 'https://www.brighteon.com'

    _TESTS = [{
        'url': 'https://www.brighteon.com/9e12fa99-a6fb-41e9-9ed9-c2aa0a166a1a',
        'info_dict': {
            "id": "9e12fa99-a6fb-41e9-9ed9-c2aa0a166a1a",
            "title": "Christopher James joins Mike Adams to discuss Common Law and corporate \"personhood\" global enslavement",
            "ext": "mp4",
            "description": "md5:a35cb44d7c50d673ce48e6cd661e74ac",
            "timestamp": 1635894109,
            "upload_date": "20211102",
            "duration": 2895.0,
            "channel": "Health Ranger Report",
            "channel_id": "8c536b2f-e9a1-4e4c-a422-3867d0e472e4",
            "channel_url": "https://www.brighteon.com/channels/hrreport",
            "tags": [
                "america",
                "brighteon",
                "christopher james",
                "common law",
                "conversations",
                "current events",
                "expert",
                "health ranger",
                "hrr",
                "humanity",
                "interview",
                "law",
                "mike adams",
                "natural news",
                "personhood"
            ],
            "thumbnail": "re:https?://[a-z]+.brighteon.com/thumbnail/[a-z0-9-]+",
            "view_count": int,
            "like_count": int,
        },
        'params': {
            'skip_download': True,
        },
    }, {
        # playlist
        'url': 'https://www.brighteon.com/watch/21824dea-3564-40af-a972-d014b987261b',
        'info_dict': {
            'id': '21824dea-3564-40af-a972-d014b987261b',
            'title': 'U.S. Senate Impeachment Trial',
        },
        'params': {'skip_download': True},
        'playlist_mincount': 10,
    }, {
        # channel
        'url': 'https://www.brighteon.com/channels/johntheo',
        'info_dict': {
            'id': '005e4477-e415-4515-b661-48e974f4a26d',
            'title': 'JohnTheo-Author',
        },
        'params': {'skip_download': True, 'playlistend': 3},
        'playlist_count': 3,
    }, {
        # categories
        'url': 'https://www.brighteon.com/categories/4ad59df9-25ce-424d-8ac4-4f92d58322b9/videos',
        'info_dict': {
            'id': '4ad59df9-25ce-424d-8ac4-4f92d58322b9',
            'title': 'Health & Medicine',
            'description': None,
        },
        'params': {'skip_download': True, 'playlistend': 3},
        'playlist_count': 3,
    }]

    @staticmethod
    def page_props_path(suffix=None):
        path = ['props', 'initialProps', 'pageProps']
        if suffix:
            path.extend(suffix.split("."))
        return path

    @staticmethod
    def _json_extract(webpage, video_id):
        json_string = get_element_by_id('__NEXT_DATA__', webpage)
        if not json_string:
            raise ExtractorError('Missing HTML metadata', video_id=video_id, expected=True)

        try:
            return json.loads(json_string or '{}')
        except json.JSONDecodeError:
            raise ExtractorError('Bad JSON metadata', video_id=video_id, expected=False)

    @staticmethod
    def _rename_formats(formats, prefix):
        for item in formats:
            if 'vcodec' in item and item['vcodec'] == 'none':
                language = item.get('language')
                suffix = f'audio-{language}' if language else 'audio'
            else:
                suffix = f'{item["height"]}p' if item.get('height') else item['format_id']
            item['format_id'] = f'{prefix}-{suffix}'

    def _entry_from_info(self, video_info, channel_info):
        video_id = video_info['id']

        formats = []
        for source in video_info.get('source', ()):
            try:
                url, typ = itemgetter('src', 'type')(source)
            except KeyError:
                continue
            media_formats = ()
            if url.endswith('.m3u8'):
                media_formats = self._extract_m3u8_formats(url, video_id=video_id, fatal=False)
                self._rename_formats(media_formats, 'hls')
            elif url.endswith('.mpd'):
                media_formats = self._extract_mpd_formats(url, video_id=video_id, fatal=False)
                self._rename_formats(media_formats, 'dash')
            else:
                self.report_warning(f'unknown video format {typ}')
            formats.extend(media_formats)

        self._sort_formats(formats)
        channel_short_url = video_info.get('channelShortUrl', channel_info.get('shortUrl'))

        return {
            'id': video_id,
            'title': video_info.get('name'),
            'description': video_info.get('description'),
            'timestamp': parse_iso8601(video_info.get('createdAt')),
            'duration': parse_duration(video_info.get('duration')),
            'channel': video_info.get('channelName', channel_info.get('name')),
            'channel_id': video_info.get('channelId', channel_info.get('id')),
            'channel_url': channel_short_url and f'{self._BASE_URL}/channels/{channel_short_url}',
            'tags': video_info.get('tags', []),
            'thumbnail': video_info.get('thumbnail'),
            'view_count': traverse_obj(video_info, ('analytics', 'videoView'), default=None),
            'like_count': int_or_none(video_info.get('likes')),
            'formats': formats,
        }

    def _paged_url_entries(self, page_id, url, start_page=None):
        page_cache = {}

        def load_page(page_number):
            page_url = update_url_query(url, {'page': page_number})
            try:
                webpage = self._download_webpage(
                    page_url, video_id=page_id, note=f'Downloading page {page_number}')
                json_obj = self._json_extract(webpage, video_id=page_id)
                return traverse_obj(json_obj, self.page_props_path('data'), default={})
            except ExtractorError:
                return {}

        data = load_page(start_page or 1)
        channel_info = data.get('channel', {})
        initial_video_list = data.get('videos', None)
        if initial_video_list is None:
            raise ExtractorError("This page contains no playlist videos",
                                 video_id=page_id, expected=True)
        page_cache[1] = initial_video_list
        page_size = len(initial_video_list)
        if not page_size:
            return None

        def fetch_entry(index):
            page_idx, offset = divmod(index, page_size)
            page_number = page_idx + 1
            if page_number not in page_cache and start_page is None:
                video_list = load_page(page_number).get('videos', ())
                page_cache[page_number] = video_list

            video_list = page_cache.get(page_number, ())
            if len(video_list) > offset:
                yield self._entry_from_info(video_list[offset], channel_info)

        playlist_info = channel_info or data
        return self.playlist_result(
            entries=OnDemandPagedList(fetch_entry, 1),
            playlist_id=playlist_info.get('id', page_id),
            playlist_title=playlist_info.get('name'),
        )

    def _playlist_entries(self, playlist_info, url):
        entries = (self.url_result(update_url_query(url, {'index': idx}))
                   for idx, video in enumerate(playlist_info.get('videosInPlaylist', ()), 1))
        return self.playlist_result(
            entries=entries,
            playlist_id=playlist_info.get('playlistId'),
            playlist_title=playlist_info.get('playlistName'),
        )

    def _real_extract(self, url):
        video_id = self._match_id(url)
        parsed_url = compat_urllib_parse_urlparse(url)
        url_query = {
            key.lower(): value[0] for key, value in compat_parse_qs(parsed_url.query).items()}

        if parsed_url.path.startswith("/channels/") or parsed_url.path.startswith("/categories/"):
            return self._paged_url_entries(video_id, url, start_page=url_query.get('page'))

        webpage = self._download_webpage(url, video_id=video_id)
        json_obj = self._json_extract(webpage, video_id=video_id)

        page_props = traverse_obj(json_obj, self.page_props_path(), default={})
        playlist = page_props.get('playlist', {})
        channel_info = page_props.get('channel', {})
        video_info = page_props.get('video', {})

        if video_info and (not playlist or 'index' in url_query):
            return self._entry_from_info(video_info, channel_info)
        if playlist:
            return self._playlist_entries(playlist, url)

        raise ExtractorError("This page contains no playlist videos",
                             video_id=video_id, expected=True)
