from .common import InfoExtractor
from .kaltura import KalturaIE
from ..utils import (
    ExtractorError,
    int_or_none,
    smuggle_url,
    traverse_obj,
    unified_strdate,
    url_or_none,
)


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
                'release_date': '20190106',
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
                'series': 'Pentulive 2024 | Pentulive',
                'thumbnail': r're:https://images\.cdn\.yle\.fi/image/upload/.+\.jpg',
                'live_status': 'is_live',
            },
            'params': {
                'skip_download': 'livestream',
            },
        },
    ]

    def _real_extract(self, url):
        video_id, is_podcast = self._match_valid_url(url).group('id', 'podcast')
        info = self._search_json_ld(self._download_webpage(url, video_id), video_id, default={})
        video_data = self._download_json(
            f'https://player.api.yle.fi/v1/preview/{video_id}.json?app_id=player_static_prod&app_key=8930d72170e48303cf5f3867780d549b',
            video_id, headers={
                'origin': 'https://areena.yle.fi',
                'referer': 'https://areena.yle.fi/',
                'content-type': 'application/json',
            })

        # Example title: 'K1, J2: Pouchit | Modernit miehet'
        season_number, episode_number, episode, series = self._search_regex(
            r'K(?P<season_no>\d+),\s*J(?P<episode_no>\d+):?\s*\b(?P<episode>[^|]+)\s*|\s*(?P<series>.+)',
            info.get('title') or '', 'episode metadata', group=('season_no', 'episode_no', 'episode', 'series'),
            default=(None, None, None, None))
        description = traverse_obj(video_data, ('data', 'ongoing_ondemand', 'description', 'fin'), expected_type=str)

        subtitles = {}
        for sub in traverse_obj(video_data, ('data', 'ongoing_ondemand', 'subtitles', ...)):
            if url_or_none(sub.get('uri')):
                subtitles.setdefault(sub.get('language') or 'und', []).append({
                    'url': sub['uri'],
                    'ext': 'srt',
                    'name': sub.get('kind'),
                })

        is_live = False
        if is_podcast:
            info_dict = {
                'url': video_data['data']['ongoing_ondemand']['media_url'],
            }
        elif kaltura_id := traverse_obj(video_data, ('data', 'ongoing_ondemand', 'kaltura', 'id', {str})):
            info_dict = {
                '_type': 'url_transparent',
                'url': smuggle_url(f'kaltura:1955031:{kaltura_id}', {'source_url': url}),
                'ie_key': KalturaIE.ie_key(),
            }
        else:
            if traverse_obj(video_data, ('data', 'ongoing_ondemand', 'manifest_url', {url_or_none})):
                manifest_url = video_data['data']['ongoing_ondemand']['manifest_url']
            elif traverse_obj(video_data, ('data', 'ongoing_event', 'manifest_url', {url_or_none})):
                manifest_url = video_data['data']['ongoing_event']['manifest_url']
                is_live = True
            else:
                raise ExtractorError('Unable to extract manifest URL')
            formats, subs = self._extract_m3u8_formats_and_subtitles(
                manifest_url, video_id, 'mp4', m3u8_id='hls', live=is_live)
            self._merge_subtitles(subs, target=subtitles)
            info_dict = {'formats': formats}

        return {
            **info_dict,
            'id': video_id,
            'title': (traverse_obj(video_data, ('data', 'ongoing_ondemand', 'title', 'fin'), expected_type=str)
                      or episode or info.get('title')),
            'description': description,
            'series': (traverse_obj(video_data, ('data', 'ongoing_ondemand', 'series', 'title', 'fin'), expected_type=str)
                       or series),
            'season_number': (int_or_none(self._search_regex(r'Kausi (\d+)', description, 'season number', default=None))
                              or int_or_none(season_number)),
            'episode_number': (traverse_obj(video_data, ('data', 'ongoing_ondemand', 'episode_number'), expected_type=int_or_none)
                               or int_or_none(episode_number)),
            'thumbnails': traverse_obj(info, ('thumbnails', ..., {'url': 'url'})),
            'age_limit': traverse_obj(video_data, ('data', 'ongoing_ondemand', 'content_rating', 'age_restriction'), expected_type=int_or_none),
            'subtitles': subtitles or None,
            'release_date': unified_strdate(traverse_obj(video_data, ('data', 'ongoing_ondemand', 'start_time'), expected_type=str)),
            'is_live': is_live,
        }
