import datetime as dt

from .common import InfoExtractor
from ..utils import (
    MEDIA_EXTENSIONS,
    determine_ext,
    url_or_none,
)
from ..utils.traversal import traverse_obj


class RinseFMBaseIE(InfoExtractor):
    _API_BASE = 'https://rinse.fm/api/query/v1'

    # Offsets from UTC in hours, no DST
    _TZ_OFFSETS = {
        'Europe/London': 0,
        'Europe/Paris': 1,
    }

    def _parse_entry(self, entry):
        return {
            **traverse_obj(entry, {
                'id': ('id', {str}),
                'title': ('title', {str}),
                'url': ('fileUrl', {url_or_none}),
                'release_timestamp': {self._extract_episode_timestamp},
                'thumbnail': ('featuredImage', 0, 'filename', {str},
                              {lambda x: x and f'https://rinse.imgix.net/media/{x}'}),
                'webpage_url': ('slug', {str},
                                {lambda x: x and f'https://rinse.fm/episodes/{x}'}),
            }),
            'vcodec': 'none',
            'extractor_key': RinseFMIE.ie_key(),
            'extractor': RinseFMIE.IE_NAME,
        }

    def _extract_episode_timestamp(self, entry):
        # episodeDate contains the local date of the episode with the time set to 00:00:00
        # _or_ the date of the previous day with the time set to 23:00:00 if DST was in effect
        # at the time of the episode; the TZ offset is always set to +00:00 and should be ignored
        episode_date = traverse_obj(entry, ('episodeDate', {dt.datetime.fromisoformat}))
        if episode_date is None:
            return None
        if episode_date.hour not in [23, 0] or episode_date.minute != 0 or episode_date.second != 0:
            self.report_warning(f'Unexpected episodeDate time: {episode_date}', entry.get('slug'))
            return None
        if episode_date.tzinfo not in [dt.timezone.utc, None]:
            self.report_warning(
                f'Unexpected episodeDate time zone: {episode_date.tzinfo}', entry.get('slug'))
            return None
        # episodeTime contains some random date (usually the current date) with the local time
        # of the episode; both the date and the TZ offset should be ignored
        episode_time = traverse_obj(entry, ('episodeTime', {dt.datetime.fromisoformat}))
        if episode_time is None:
            return None
        tz_name = traverse_obj(entry, ('channel', 0, 'defaultTimezoneOffset'))
        if not tz_name:
            return None
        # As episodeDate is already adjusted for DST, we should always use a "winter" time zone
        tz_offset = self._TZ_OFFSETS.get(tz_name)
        if tz_offset is None:
            self.report_warning(f'Unknown channel time zone: {tz_name}', entry.get('slug'))
            return None
        episode_time_as_delta = dt.timedelta(
            hours=episode_time.hour, minutes=episode_time.minute, seconds=episode_time.second)
        return (episode_date + episode_time_as_delta - dt.timedelta(hours=tz_offset)).timestamp()


class RinseFMIE(RinseFMBaseIE):
    _VALID_URL = r'https?://(?:www\.)?rinse\.fm/episodes/(?P<id>[^/?#]+)'
    _TESTS = [{
        'url': 'https://rinse.fm/episodes/club-glow-15-12-2023-2000/',
        'md5': '76ee0b719315617df42e15e710f46c7b',
        'info_dict': {
            'id': '1536535',
            'ext': 'mp3',
            'title': 'Club Glow - 15/12/2023 - 20:00',
            'thumbnail': r're:^https://.+\.(?:jpg|JPG)$',
            'release_timestamp': 1702670400.0,
            'release_date': '20231215',
        },
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)

        entry = self._download_json(
            f'{self._API_BASE}/episodes/{display_id}', display_id,
            note='Downloading episode data from API')['entry']

        return self._parse_entry(entry)


class RinseFMArtistPlaylistIE(RinseFMBaseIE):
    _VALID_URL = r'https?://(?:www\.)?rinse\.fm/shows/(?P<id>[^/?#]+)'
    _TESTS = [{
        'url': 'https://rinse.fm/shows/resources/',
        'info_dict': {
            'id': 'resources',
            'title': '[re]sources',
            'description': 'md5:fd6a7254e8273510e6d49fbf50edf392',
        },
        'playlist_mincount': 40,
    }, {
        'url': 'https://www.rinse.fm/shows/esk',
        'info_dict': {
            'id': 'esk',
            'title': 'Esk',
            'description': 'md5:5893d7c1d411ae8dea7fba12f109aa98',
        },
        'playlist_mincount': 139,
    }]

    def _entries(self, data):
        for episode in traverse_obj(data, (
            'episodes', lambda _, v: determine_ext(v['fileUrl']) in MEDIA_EXTENSIONS.audio),
        ):
            yield self._parse_entry(episode)

    def _real_extract(self, url):
        playlist_id = self._match_id(url)

        api_data = self._download_json(
            f'{self._API_BASE}/shows/{playlist_id}', playlist_id,
            note='Downloading show data from API')

        return self.playlist_result(
            self._entries(api_data), playlist_id,
            **traverse_obj(api_data, ('entry', {
                'title': ('title', {str}),
                'description': ('description', {str}),
            })))
