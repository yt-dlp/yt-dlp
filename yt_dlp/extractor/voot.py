# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    int_or_none,
    try_get,
    unified_timestamp,
)


class VootIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?voot\.com/(?:[^/]+/)+(?P<id>\d+)'
    _GEO_COUNTRIES = ['IN']
    _TESTS = [{
        'url': 'https://www.voot.com/shows/ishq-ka-rang-safed/1/360558/is-this-the-end-of-kamini-/441353',
        'info_dict': {
            'id': '0_8ledb18o',
            'ext': 'mp4',
            'title': 'Ishq Ka Rang Safed - Season 01 - Episode 340',
            'description': 'md5:06291fbbbc4dcbe21235c40c262507c1',
            'timestamp': 1472162937,
            'upload_date': '20160825',
            'duration': 1146,
            'series': 'Ishq Ka Rang Safed',
            'season_number': 1,
            'episode': 'Is this the end of Kamini?',
            'episode_number': 340,
            'view_count': int,
            'like_count': int,
        },
        'params': {
            'skip_download': True,
        },
        'expected_warnings': ['Failed to download m3u8 information'],
    }, {
        'url': 'https://www.voot.com/kids/characters/mighty-cat-masked-niyander-e-/400478/school-bag-disappears/440925',
        'only_matching': True,
    }, {
        'url': 'https://www.voot.com/movies/pandavas-5/424627',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        media_info = self._download_json(
            'https://wapi.voot.com/ws/ott/getMediaInfo.json', video_id,
            query={
                'platform': 'Web',
                'pId': 2,
                'mediaId': video_id,
            })

        status_code = try_get(media_info, lambda x: x['status']['code'], int)
        if status_code != 0:
            raise ExtractorError(media_info['status']['message'], expected=True)

        media = media_info['assets']

        entry_id = media['EntryId']
        title = media['MediaName']
        formats = self._extract_m3u8_formats(
            'https://cdnapisec.kaltura.com/p/1982551/playManifest/pt/https/f/applehttp/t/web/e/' + entry_id,
            video_id, 'mp4', m3u8_id='hls')
        self._sort_formats(formats)

        description, series, season_number, episode, episode_number = [None] * 5

        for meta in try_get(media, lambda x: x['Metas'], list) or []:
            key, value = meta.get('Key'), meta.get('Value')
            if not key or not value:
                continue
            if key == 'ContentSynopsis':
                description = value
            elif key == 'RefSeriesTitle':
                series = value
            elif key == 'RefSeriesSeason':
                season_number = int_or_none(value)
            elif key == 'EpisodeMainTitle':
                episode = value
            elif key == 'EpisodeNo':
                episode_number = int_or_none(value)

        return {
            'extractor_key': 'Kaltura',
            'id': entry_id,
            'title': title,
            'description': description,
            'series': series,
            'season_number': season_number,
            'episode': episode,
            'episode_number': episode_number,
            'timestamp': unified_timestamp(media.get('CreationDate')),
            'duration': int_or_none(media.get('Duration')),
            'view_count': int_or_none(media.get('ViewCounter')),
            'like_count': int_or_none(media.get('like_counter')),
            'formats': formats,
        }
