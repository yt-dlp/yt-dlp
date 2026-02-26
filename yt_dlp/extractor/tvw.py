import json

from .common import InfoExtractor
from ..utils import (
    clean_html,
    extract_attributes,
    parse_qs,
    remove_end,
    require,
    unified_timestamp,
    url_or_none,
)
from ..utils.traversal import find_element, find_elements, traverse_obj


class TvwIE(InfoExtractor):
    IE_NAME = 'tvw'
    _VALID_URL = [
        r'https?://(?:www\.)?tvw\.org/video/(?P<id>[^/?#]+)',
        r'https?://(?:www\.)?tvw\.org/watch/?\?(?:[^#]+&)?eventID=(?P<id>\d+)',
    ]
    _TESTS = [{
        'url': 'https://tvw.org/video/billy-frank-jr-statue-maquette-unveiling-ceremony-2024011211/',
        'md5': '9ceb94fe2bb7fd726f74f16356825703',
        'info_dict': {
            'id': '2024011211',
            'ext': 'mp4',
            'title': 'Billy Frank Jr. Statue Maquette Unveiling Ceremony',
            'thumbnail': r're:^https?://.*\.(?:jpe?g|png)$',
            'description': 'md5:58a8150017d985b4f377e11ee8f6f36e',
            'timestamp': 1704902400,
            'upload_date': '20240110',
            'location': 'Legislative Building',
            'display_id': 'billy-frank-jr-statue-maquette-unveiling-ceremony-2024011211',
            'categories': ['General Interest'],
        },
    }, {
        'url': 'https://tvw.org/video/ebeys-landing-state-park-2024081007/',
        'md5': '71e87dae3deafd65d75ff3137b9a32fc',
        'info_dict': {
            'id': '2024081007',
            'ext': 'mp4',
            'title': 'Ebey\'s Landing State Park',
            'thumbnail': r're:^https?://.*\.(?:jpe?g|png)$',
            'description': 'md5:50c5bd73bde32fa6286a008dbc853386',
            'timestamp': 1724310900,
            'upload_date': '20240822',
            'location': 'Ebey’s Landing State Park',
            'display_id': 'ebeys-landing-state-park-2024081007',
            'categories': ['Washington State Parks'],
        },
    }, {
        'url': 'https://tvw.org/video/home-warranties-workgroup-2',
        'md5': 'f678789bf94d07da89809f213cf37150',
        'info_dict': {
            'id': '1999121000',
            'ext': 'mp4',
            'title': 'Home Warranties Workgroup',
            'thumbnail': r're:^https?://.*\.(?:jpe?g|png)$',
            'description': 'md5:861396cc523c9641d0dce690bc5c35f3',
            'timestamp': 946389600,
            'upload_date': '19991228',
            'display_id': 'home-warranties-workgroup-2',
            'categories': ['Legislative'],
        },
    }, {
        'url': 'https://tvw.org/video/washington-to-washington-a-new-space-race-2022041111/?eventID=2022041111',
        'md5': '6f5551090b351aba10c0d08a881b4f30',
        'info_dict': {
            'id': '2022041111',
            'ext': 'mp4',
            'title': 'Washington to Washington - A New Space Race',
            'thumbnail': r're:^https?://.*\.(?:jpe?g|png)$',
            'description': 'md5:f65a24eec56107afbcebb3aa5cd26341',
            'timestamp': 1650394800,
            'upload_date': '20220419',
            'location': 'Hayner Media Center',
            'display_id': 'washington-to-washington-a-new-space-race-2022041111',
            'categories': ['Washington to Washington', 'General Interest'],
        },
    }, {
        'url': 'https://tvw.org/watch?eventID=2025041235',
        'md5': '7d697c02f110b37d6a47622ea608ca90',
        'info_dict': {
            'id': '2025041235',
            'ext': 'mp4',
            'title': 'Legislative Review - Medicaid Postpartum Bill Sparks Debate & Senate Approves Automatic Voter Registration',
            'thumbnail': r're:^https?://.*\.(?:jpe?g|png)$',
            'description': 'md5:37d0f3a9187ae520aac261b3959eaee6',
            'timestamp': 1745006400,
            'upload_date': '20250418',
            'location': 'Hayner Media Center',
            'categories': ['Legislative Review'],
        },
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)

        client_id = self._html_search_meta('clientID', webpage, fatal=True)
        video_id = self._html_search_meta('eventID', webpage, fatal=True)

        video_data = self._download_json(
            'https://api.v3.invintus.com/v2/Event/getDetailed', video_id,
            headers={
                'authorization': 'embedder',
                'wsc-api-key': '7WhiEBzijpritypp8bqcU7pfU9uicDR',
            },
            data=json.dumps({
                'clientID': client_id,
                'eventID': video_id,
                'showStreams': True,
            }).encode())['data']

        formats = []
        subtitles = {}
        for stream_url in traverse_obj(video_data, ('streamingURIs', ..., {url_or_none})):
            fmts, subs = self._extract_m3u8_formats_and_subtitles(
                stream_url, video_id, 'mp4', m3u8_id='hls', fatal=False)
            formats.extend(fmts)
            self._merge_subtitles(subs, target=subtitles)
        if caption_url := traverse_obj(video_data, ('captionPath', {url_or_none})):
            subtitles.setdefault('en', []).append({'url': caption_url, 'ext': 'vtt'})

        return {
            'id': video_id,
            'display_id': display_id,
            'formats': formats,
            'subtitles': subtitles,
            'title': remove_end(self._og_search_title(webpage, default=None), ' - TVW'),
            'description': self._og_search_description(webpage, default=None),
            **traverse_obj(video_data, {
                'title': ('title', {str}),
                'description': ('description', {clean_html}),
                'categories': ('categories', ..., {str}),
                'thumbnail': ('videoThumbnail', {url_or_none}),
                'timestamp': ('startDateTime', {unified_timestamp}),
                'location': ('locationName', {str}),
                'is_live': ('eventStatus', {lambda x: x == 'live'}),
            }),
        }


class TvwNewsIE(InfoExtractor):
    IE_NAME = 'tvw:news'
    _VALID_URL = r'https?://(?:www\.)?tvw\.org/\d{4}/\d{2}/(?P<id>[^/?#]+)'
    _TESTS = [{
        'url': 'https://tvw.org/2024/01/the-impact-issues-to-watch-in-the-2024-legislative-session/',
        'info_dict': {
            'id': 'the-impact-issues-to-watch-in-the-2024-legislative-session',
            'title': 'The Impact - Issues to Watch in the 2024 Legislative Session',
            'description': 'md5:65f0b33ec8f18ff1cd401c5547aa5441',
        },
        'playlist_count': 6,
    }, {
        'url': 'https://tvw.org/2024/06/the-impact-water-rights-and-the-skookumchuck-dam-debate/',
        'info_dict': {
            'id': 'the-impact-water-rights-and-the-skookumchuck-dam-debate',
            'title': 'The Impact - Water Rights and the Skookumchuck Dam Debate',
            'description': 'md5:185f3a2350ef81e3fa159ac3e040a94b',
        },
        'playlist_count': 1,
    }]

    def _real_extract(self, url):
        playlist_id = self._match_id(url)
        webpage = self._download_webpage(url, playlist_id)

        video_ids = traverse_obj(webpage, (
            {find_elements(cls='invintus-player', html=True)}, ..., {extract_attributes}, 'data-eventid'))

        return self.playlist_from_matches(
            video_ids, playlist_id,
            playlist_title=remove_end(self._og_search_title(webpage, default=None), ' - TVW'),
            playlist_description=self._og_search_description(webpage, default=None),
            getter=lambda x: f'https://tvw.org/watch?eventID={x}', ie=TvwIE)


class TvwTvChannelsIE(InfoExtractor):
    IE_NAME = 'tvw:tvchannels'
    _VALID_URL = r'https?://(?:www\.)?tvw\.org/tvchannels/(?P<id>[^/?#]+)'
    _TESTS = [{
        'url': 'https://tvw.org/tvchannels/air/',
        'info_dict': {
            'id': 'air',
            'ext': 'mp4',
            'title': r're:TVW Cable Channel Live Stream',
            'thumbnail': r're:https?://.+/.+\.(?:jpe?g|png)$',
            'live_status': 'is_live',
        },
    }, {
        'url': 'https://tvw.org/tvchannels/tvw2/',
        'info_dict': {
            'id': 'tvw2',
            'ext': 'mp4',
            'title': r're:TVW-2 Broadcast Channel',
            'thumbnail': r're:https?://.+/.+\.(?:jpe?g|png)$',
            'live_status': 'is_live',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        m3u8_url = traverse_obj(webpage, (
            {find_element(id='invintus-persistent-stream-frame', html=True)}, {extract_attributes},
            'src', {parse_qs}, 'encoder', 0, {json.loads}, 'live247URI', {url_or_none}, {require('stream url')}))

        return {
            'id': video_id,
            'formats': self._extract_m3u8_formats(m3u8_url, video_id, 'mp4', m3u8_id='hls', live=True),
            'title': remove_end(self._og_search_title(webpage, default=None), ' - TVW'),
            'thumbnail': self._og_search_thumbnail(webpage, default=None),
            'is_live': True,
        }
