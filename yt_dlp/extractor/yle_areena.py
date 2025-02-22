from .common import InfoExtractor
from .kaltura import KalturaIE
from ..utils import (
    ExtractorError,
    int_or_none,
    parse_iso8601,
    smuggle_url,
    url_or_none,
)
from ..utils.traversal import traverse_obj


class YleAreenaIE(InfoExtractor):
    _VALID_URL = r'https?://areena\.yle\.fi/(?P<podcast>podcastit/)?(?P<id>[\d-]+)'
    _GEO_COUNTRIES = ['FI']
    _TESTS = [
        {
            'url': 'https://areena.yle.fi/1-4371942',
            'md5': 'd87e9a1e74e67e009990ddd413e426b4',
            'info_dict': {
                'id': '1-4371942',
                'ext': 'mp4',
                'title': 'Pouchit',
                'description': 'md5:01071d7056ceec375f63960f90c35366',
                'series': 'Modernit miehet',
                'season': 'Season 1',
                'season_number': 1,
                'episode': 'Episode 2',
                'episode_number': 2,
                'thumbnail': r're:https://images\.cdn\.yle\.fi/image/upload/.+\.jpg',
                'age_limit': 7,
                'release_date': '20190105',
                'release_timestamp': 1546725660,
                'duration': 1435,
            },
        },
        {
            'url': 'https://areena.yle.fi/1-2158940',
            'md5': '6369ddc5e07b5fdaeda27a495184143c',
            'info_dict': {
                'id': '1-2158940',
                'ext': 'mp4',
                'title': 'Albi haluaa vessan',
                'description': 'Albi haluaa vessan.',
                'series': 'Albi Lumiukko',
                'thumbnail': r're:https://images\.cdn\.yle\.fi/image/upload/.+\.jpg',
                'age_limit': 0,
                'release_date': '20211215',
                'release_timestamp': 1639555200,
                'duration': 319,
            },
        },
        {
            'url': 'https://areena.yle.fi/1-64829589',
            'info_dict': {
                'id': '1-64829589',
                'ext': 'mp4',
                'title': 'HKO & Mälkki & Tanner',
                'description': 'md5:b4f1b1af2c6569b33f75179a86eea156',
                'series': 'Helsingin kaupunginorkesterin konsertteja',
                'thumbnail': r're:https://images\.cdn\.yle\.fi/image/upload/.+\.jpg',
                'release_date': '20230120',
                'release_timestamp': 1674242079,
                'duration': 8004,
            },
            'params': {
                'skip_download': 'm3u8',
            },
        },
        {
            'url': 'https://areena.yle.fi/1-72251830',
            'info_dict': {
                'id': '1-72251830',
                'ext': 'mp4',
                'title': r're:Pentulive 2024 | Pentulive \d{4}-\d{2}-\d{2} \d{2}:\d{2}',
                'description': 'md5:1f118707d9093bf894a34fbbc865397b',
                'series': 'Pentulive',
                'thumbnail': r're:https://images\.cdn\.yle\.fi/image/upload/.+\.jpg',
                'live_status': 'is_live',
                'release_date': '20241025',
                'release_timestamp': 1729875600,
            },
            'params': {
                'skip_download': 'livestream',
            },
        },
        {
            'url': 'https://areena.yle.fi/podcastit/1-71022852',
            'info_dict': {
                'id': '1-71022852',
                'ext': 'mp3',
                'title': 'Värityspäivä',
                'description': 'md5:c3a02b0455ec71d32cbe09d32ec161e2',
                'series': 'Murun ja Paukun ikioma kaupunki',
                'episode': 'Episode 1',
                'episode_number': 1,
                'release_date': '20240607',
                'release_timestamp': 1717736400,
                'duration': 442,
            },
        },
    ]

    def _real_extract(self, url):
        video_id, is_podcast = self._match_valid_url(url).group('id', 'podcast')
        json_ld = self._search_json_ld(self._download_webpage(url, video_id), video_id, default={})
        video_data = self._download_json(
            f'https://player.api.yle.fi/v1/preview/{video_id}.json?app_id=player_static_prod&app_key=8930d72170e48303cf5f3867780d549b',
            video_id, headers={
                'origin': 'https://areena.yle.fi',
                'referer': 'https://areena.yle.fi/',
                'content-type': 'application/json',
            })['data']

        # Example title: 'K1, J2: Pouchit | Modernit miehet'
        season_number, episode_number, episode, series = self._search_regex(
            r'K(?P<season_no>\d+),\s*J(?P<episode_no>\d+):?\s*\b(?P<episode>[^|]+)\s*|\s*(?P<series>.+)',
            json_ld.get('title') or '', 'episode metadata', group=('season_no', 'episode_no', 'episode', 'series'),
            default=(None, None, None, None))
        description = traverse_obj(video_data, ('ongoing_ondemand', 'description', 'fin', {str}))

        subtitles = {}
        for sub in traverse_obj(video_data, ('ongoing_ondemand', 'subtitles', lambda _, v: url_or_none(v['uri']))):
            subtitles.setdefault(sub.get('language') or 'und', []).append({
                'url': sub['uri'],
                'ext': 'srt',
                'name': sub.get('kind'),
            })

        info_dict, metadata = {}, {}
        if is_podcast and traverse_obj(video_data, ('ongoing_ondemand', 'media_url', {url_or_none})):
            metadata = video_data['ongoing_ondemand']
            info_dict['url'] = metadata['media_url']
        elif traverse_obj(video_data, ('ongoing_event', 'manifest_url', {url_or_none})):
            metadata = video_data['ongoing_event']
            metadata.pop('duration', None)  # Duration is not accurate for livestreams
            info_dict['live_status'] = 'is_live'
        elif traverse_obj(video_data, ('ongoing_ondemand', 'manifest_url', {url_or_none})):
            metadata = video_data['ongoing_ondemand']
        # XXX: Has all externally-hosted Kaltura content been moved to native hosting?
        elif kaltura_id := traverse_obj(video_data, ('ongoing_ondemand', 'kaltura', 'id', {str})):
            metadata = video_data['ongoing_ondemand']
            info_dict.update({
                '_type': 'url_transparent',
                'url': smuggle_url(f'kaltura:1955031:{kaltura_id}', {'source_url': url}),
                'ie_key': KalturaIE.ie_key(),
            })
        elif traverse_obj(video_data, ('gone', {dict})):
            self.raise_no_formats('The content is no longer available', expected=True, video_id=video_id)
            metadata = video_data['gone']
        else:
            raise ExtractorError('Unable to extract content')

        if not info_dict.get('url') and metadata.get('manifest_url'):
            info_dict['formats'], subs = self._extract_m3u8_formats_and_subtitles(
                metadata['manifest_url'], video_id, 'mp4', m3u8_id='hls')
            self._merge_subtitles(subs, target=subtitles)

        return {
            **traverse_obj(json_ld, {
                'title': 'title',
                'thumbnails': ('thumbnails', ..., {'url': 'url'}),
            }),
            'id': video_id,
            'title': episode,
            'description': description,
            'series': series,
            'season_number': (int_or_none(self._search_regex(r'Kausi (\d+)', description, 'season number', default=None))
                              or int_or_none(season_number)),
            'episode_number': int_or_none(episode_number),
            'subtitles': subtitles or None,
            **traverse_obj(metadata, {
                'title': ('title', 'fin', {str}),
                'description': ('description', 'fin', {str}),
                'series': ('series', 'title', 'fin', {str}),
                'episode_number': ('episode_number', {int_or_none}),
                'age_limit': ('content_rating', 'age_restriction', {int_or_none}),
                'release_timestamp': ('start_time', {parse_iso8601}),
                'duration': ('duration', 'duration_in_seconds', {int_or_none}),
            }),
            **info_dict,
        }
