import re

from .common import InfoExtractor
from ..networking import HEADRequest
from ..networking.exceptions import HTTPError
from ..utils import (
    ExtractorError,
    float_or_none,
    parse_iso8601,
    traverse_obj,
    unescapeHTML,
)


class RteRadioIE(InfoExtractor):
    IE_NAME = 'rte:radio'
    IE_DESC = 'Raidió Teilifís Éireann radio'
    _VALID_URL = r'''(?x)
        # Base URL
        https://www\.rte\.ie/radio/
        # The radio station, eg lyricfm
        (?P<station>[^/]+)
        # If not selecting the station live-stream, one of...
        (
            # 1. A clip with an ID
            (/clips/(?P<clip_id>\d+)/*)|
            # 2. A named show with an optional ID/date,
            #    (If ID missing, it's the latest show, or show's live-stream)
            (/(?P<show>[^/]+)
                (
                    (/episodes/(?P<ep_id>\d+)/*)|
                    (/(?P<date_id>\d{4}/\d{4}/\d+-[^/]+/*))
                )?
            )
        )?
        '''

    BASE_URL = 'https://www.rte.ie/radio'
    _TESTS = [{
        # A specific show by episode ID
        'url': f'{BASE_URL}/radio1/sunday-miscellany/episodes/11800551',
        'md5': 'b2e3ee98d12571aa2b1de6b0599d6cb6',
        'info_dict': {
            'id': '11800551',
            'ext': 'mp4',
            'title': 'Sunday Miscellany',
            'thumbnail': 'https://www.rte.ie/images/001f2456-512.jpg',
            'description': 'A mix of \'music and musings\'',
            'timestamp': 1780822800,
            'upload_date': '20260607',
            'duration': 2962.673,
        },
    }, {
        # A specific show by date
        'url': f'{BASE_URL}/lyricfm/vespertine/2026/0531/'
        '1576169-vespertine-with-ellen-cranitch-sunday-31-may-2026//',
        'md5': '46ae1dcabdf30382e4b8db4c49d8c013',
        'info_dict': {
            'id': '11799347',
            'ext': 'mp4',
            'title': 'Vespertine with Ellen Cranitch',
            'thumbnail': 'https://www.rte.ie/images/000e3182-512.jpg',
            'description': r'startswith:Let Ellen Cranitch be your guide',
            'timestamp': 1780261200,
            'upload_date': '20260531',
            'duration': 10830.0,
        },
    }, {
        # A clip
        'url': f'{BASE_URL}/radio1/clips/22561698/',
        'md5': '5d07ff1698c7f3ad6dada5280f17168d',
        'info_dict': {
            'id': '22561698',
            'ext': 'mp4',
            'title': 'startswith:“He died three days later. Nobody knew',
            'thumbnail': 'https://www.rte.ie/images/002385a8-512.jpg',
            'description': r'startswith:Homeless campaigner, and founder',
            'timestamp': 1763895600,
            'upload_date': '20251123',
            'duration': 1737.962,
        },
    }]

    def _real_extract(self, url):
        info_dict = {}
        formats = []

        m = self._match_valid_url(url)
        station = m.group('station')
        show = m.group('show')
        item_id = m.group('ep_id') or m.group('clip_id')
        date_id = m.group('date_id')
        if show is None and item_id is None:
            # If it's not a show or a clip, we've got a URL for the station.
            # Find the live-streaming show
            url = 'https://www.rte.ie/radio/live_stations/json'
            data = self._download_json(url, station)
            channel_ids = traverse_obj(data, (
                'stations',
                lambda _, x: x['url'] == f'/radio/{station}/',
                'liveListing',
                'stationId',
            ))
            if not channel_ids:
                raise ExtractorError(
                    f'{self.IE_NAME} said: Live stream not found for {url}',
                    expected=True)
            return self._get_live_channel(channel_ids[0])

        if item_id is None and date_id is None:
            # The URL has a show ID but not an episode. Find the latest episode
            data = self._download_webpage(url, show, note='Latest show')

            # If the latest episode is live, find the station and use its
            # live stream
            if ('<span class="on-air">On Air</span>' in data
               and '<h1>Listen Live</h1>' in data):
                regex = r'data-stationid="(\d+)"'
                m = re.search(regex, data)
                if m:
                    return self._get_live_channel(int(m.group(1)))
                raise ExtractorError(
                    f'{self.IE_NAME} said: Station ID not found for {url}',
                    expected=True)

            # Else find the first (newest) episode on the show's web page.
            # The web page URLs may be date-based or ID based, but we fall
            # through to recorded episode URL parsing next.
            regex = f'href="(/radio/{station}/{show}/[^"]+)"'
            m = re.search(regex, data)
            if m:
                url = 'https://www.rte.ie' + m.group(1)
                m = self._match_valid_url(url)
                item_id = m.group('ep_id') or m.group('clip_id')
                date_id = m.group('date_id')
            else:
                raise ExtractorError(
                    f'{self.IE_NAME} said: Latest episode not found for {url}',
                    expected=True)

        if date_id is not None:
            # The URL is date-based (rather than ID-based) so make a HTTP HEAD
            # request to follow HTTP 302 redirects to get a canonical ID.
            url = self._request_webpage(
                HEADRequest(url),
                date_id,
                note='Resolving redirects').url
            m = self._match_valid_url(url)
            if m:
                item_id = m.group('ep_id') or m.group('clip_id')
            if item_id is None:
                raise ExtractorError(
                    f'{self.IE_NAME} said: id not found for date-based {url}',
                    expected=True)

        # Finally we've got an episode/clip with an ID and can get the
        # playlist (metadata) and m3u8 for it.
        try:
            url = f'https://www.rte.ie/rteavgen/getplaylist/?id={item_id}'
            data = self._download_json(url, item_id)
        except ExtractorError as ee:
            if isinstance(ee.cause, HTTPError) and ee.cause.status == 404:
                error_info = self._parse_json(
                    ee.cause.response.read().decode(),
                    item_id,
                    fatal=False)
                if error_info:
                    raise ExtractorError(
                        f'{self.IE_NAME} said: {error_info["message"]}',
                        expected=True)
            raise

        show = traverse_obj(data, ('shows', 0))
        if show:
            info_dict = {
                'id': item_id,
                'title': unescapeHTML(show['title']),
                'description': unescapeHTML(show.get('description')),
                'thumbnail': show.get('thumbnail'),
                'timestamp': parse_iso8601(show.get('published')),
                'duration': float_or_none(show.get('duration'), 1000),
            }

        mg = traverse_obj(show, ('media:group', 0))
        if mg.get('hls_server') and mg.get('hls_url'):
            formats.extend(self._extract_m3u8_formats(
                mg['hls_server'] + mg['hls_url'], item_id, 'mp4',
                entry_protocol='m3u8_native', m3u8_id='hls', fatal=False))

        info_dict['formats'] = formats
        return info_dict

    def _get_live_channel(self, channel_id: int) -> dict:
        url_base = 'https://www.rte.ie/feeds/livelistings/playlist/?channelid='
        data = self._download_json(f'{url_base}{channel_id}', channel_id)
        show = traverse_obj(data, 0)
        if show is None:
            return {}
        m3u8_url, m3u8_id = show.get('fullUrl'), show.get('listingId')
        formats = []
        if m3u8_url is not None and m3u8_id is not None:
            formats.extend(self._extract_m3u8_formats(
                m3u8_url, m3u8_id, 'mp4', entry_protocol='m3u8_native',
                m3u8_id='hls', fatal=True))
        return {
            'id': str(show['listingId']),
            'title': show.get('progName'),
            'description': show.get('description'),
            'thumbnail': show.get('thumbnail'),
            'timstamp': parse_iso8601(show.get('progDate')),
            'is_live': 'currently_live',
            'formats': formats,
        }
