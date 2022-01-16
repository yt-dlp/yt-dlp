# coding: utf-8
from __future__ import unicode_literals

from ..compat import compat_str
from ..utils import (
    determine_ext,
    dict_get,
    int_or_none,
    parse_age_limit,
    parse_iso8601,
    str_or_none,
    try_get,
    url_or_none,
)

from .common import InfoExtractor


class ERTFlixBaseIE(InfoExtractor):
    _VALID_URL = r'ertflix:(?P<id>[\w-]+)'
    _TESTS = [{
        'url': 'ertflix:monogramma-praxitelis-tzanoylinos',
        'md5': '5b9c2cd171f09126167e4082fc1dd0ef',
        'info_dict': {
            'id': 'monogramma-praxitelis-tzanoylinos',
            'ext': 'mp4',
            'title': 'md5:ef0b439902963d56c43ac83c3f41dd0e',
        },
    },
    ]

    def _call_api(self, video_id, method='Player/AcquireContent', **params):
        query = {'platformCodename': 'www', }
        query.update(params)
        json = self._download_json(
            'https://api.app.ertflix.gr/v1/%s' % (method, ),
            video_id, fatal=False, query=query)
        if try_get(json, lambda x: x['Result']['Success']) is True:
            return json

    def _extract_formats(self, video_id, allow_none=True):
        media_info = self._call_api(video_id, codename=video_id)
        formats = []
        for media_file in try_get(media_info, lambda x: x['MediaFiles'], list) or []:
            for media in try_get(media_file, lambda x: x['Formats'], list) or []:
                fmt_url = url_or_none(try_get(media, lambda x: x['Url']))
                if not fmt_url:
                    continue
                ext = determine_ext(fmt_url)
                if ext == 'm3u8':
                    formats.extend(self._extract_m3u8_formats(fmt_url, video_id, m3u8_id='hls', ext='mp4', entry_protocol='m3u8_native', fatal=False))
                elif ext == 'mpd':
                    formats.extend(self._extract_mpd_formats(fmt_url, video_id, mpd_id='dash', fatal=False))
                else:
                    formats.append({
                        'url': fmt_url,
                        'format_id': str_or_none(media.get('Id')),
                    })

        if formats or not allow_none:
            self._sort_formats(formats)
        return formats

    def _real_extract(self, url):
        video_id = self._match_id(url)

        formats = self._extract_formats(video_id)

        if formats:
            return {
                'id': video_id,
                'formats': formats,
                'title': self._generic_title(url),
            }


class ERTFlixIE(ERTFlixBaseIE):
    _VALID_URL = r'https?://www\.ertflix\.gr/(?:series|vod)/(?P<id>[a-z]{3}\.\d+)'
    _TESTS = [{
        'url': 'https://www.ertflix.gr/vod/vod.173258-aoratoi-ergates',
        'md5': '388f47a70e1935c8dabe454e871446bb',
        'info_dict': {
            'id': 'aoratoi-ergates',
            'ext': 'mp4',
            'title': 'md5:c1433d598fbba0211b0069021517f8b4',
            'description': 'md5:8cc02e5cdb31058c8f6e0423db813770',
            'thumbnail': r're:https?://.+\.jpg',
        },
    }, {
        'url': 'https://www.ertflix.gr/series/ser.3448-monogramma',
        'info_dict': {
            'id': 'ser.3448',
            'age_limit': 8,
            'description': 'Η εκπομπή σαράντα ετών που σημάδεψε τον πολιτισμό μας.',
            'title': 'Μονόγραμμα',
        },
        'playlist_mincount': 64,
    },
    ]

    def _extract_series(self, video_id):
        media_info = self._call_api(video_id, method='Tile/GetSeriesDetails', id=video_id)

        series = try_get(media_info, lambda x: x['Series'], dict) or {}
        series_info = {
            'age_limit': parse_age_limit(series.get('AgeRating', series.get('IsAdultContent') and 18)),
            'title': series.get('Title'),
            'description': dict_get(series, ('ShortDescription', 'TinyDescription', )),
        }

        def gen_episode(m_info):
            for episode_group in try_get(m_info, lambda x: x['EpisodeGroups'], list) or []:
                episodes = try_get(episode_group, lambda x: x['Episodes'], list)
                if not episodes:
                    continue
                season_info = {
                    'season': episode_group.get('Title'),
                    'season_number': int_or_none(episode_group.get('SeasonNumber')),
                }
                for n, episode in enumerate(episodes, 1):
                    codename = try_get(episode, lambda x: x['Codename'], compat_str)
                    title = episode.get('Title')
                    if not codename and title and episode.get('HasPlayableStream', True):
                        continue
                    info = {
                        '_type': 'url_transparent',
                        'thumbnail': url_or_none(try_get(episode, lambda x: x['Image']['Url'])),
                        'id': codename,
                        'episode_id': episode.get('Id'),
                        'title': title,
                        'alt_title': episode.get('Subtitle'),
                        'description': episode.get('ShortDescription'),
                        'timestamp': parse_iso8601(episode.get('PublishDate')),
                        'episode_number': n,
                        'age_limit': parse_age_limit(episode.get('AgeRating', episode.get('IsAdultContent') and 18)) or series_info.get('age_limit'),
                        'url': 'ertflix:%s' % (codename, ),
                    }
                    info.update(season_info)
                    yield info

        result = self.playlist_result((e for e in gen_episode(media_info)), playlist_id=video_id)
        result.update(series_info)
        return result

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        if video_id.startswith('ser'):
            return self._extract_series(video_id)

        video_id = self._search_regex(
            r'"codenameToId"\s*:\s*\{\s*"([\w-]+)"\s*:\s*"%s"' % (video_id, ),
            webpage, video_id, default=False) or video_id

        title = self._og_search_title(webpage)

        formats = self._extract_formats(video_id, False)

        return {
            'id': video_id,
            'title': title,
            'description': self._og_search_description(webpage),
            'thumbnail': self._og_search_thumbnail(webpage),
            'formats': formats,
        }
