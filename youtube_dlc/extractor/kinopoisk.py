# coding: utf-8
from __future__ import unicode_literals

import re
import datetime

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    int_or_none,
    float_or_none,
    determine_ext,
    try_get,
)


class KinoPoiskIE(InfoExtractor):
    _GEO_COUNTRIES = ['RU']
    _VALID_URL = r'https?://(?:www\.)?kinopoisk\.ru/film/((?:[\w-])*-)?(?P<id>\d+)((?:/watch/)?(?P<seasonid>\d+)/(?P<episodeid>\d+))?'
    _TESTS = [
        {
            'url': 'https://www.kinopoisk.ru/film/81041/watch/',
            'md5': '4a39cbe1f4393eaa355ad1730d68d6a0',
            'info_dict': {
                'id': '81041',
                'ext': 'mp4',
                'title': 'Алеша Попович и Тугарин Змей',
                'alt_title': 'Алеша Попович и Тугарин Змей',
                'description': 'md5:43787e673d68b805d0aa1df5a5aea701',
                'thumbnail': r're:^https?://.*',
                'duration': 4533,
                'age_limit': 12,
                'creator': 'Константин Бронзит',
                'location': 'Россия',
                'average_rating': float,
            },
            'params': {
                'format': 'bestvideo',
            },
        },
        {
            # TV show episode
            'url': 'https://www.kinopoisk.ru/film/820638/watch/2/3',
            'md5': '41551392701a7605966fb64c55136e5e',
            'info_dict': {
                'id': '820638/2/3',
                'ext': 'mp4',
                'title': 'Мажор - Сезон 2 - Серия 3',
                'alt_title': 'Мажор',
                'thumbnail': r're:^https?://.*',
                'description': 'md5:680a1c26f837f90ffcb19f3c89a30357',
                'duration': 3101,
                'age_limit': 16,
                'release_year': 2016,
                'release_date': '20161115',
                'creator': 'Константин Статский',
                'location': 'Россия',
                'average_rating': float,
                'series': 'Мажор',
                'season_number': 2,
                'episode_number': 3,
            },
            'params': {
                'format': 'bestvideo',
            },
        },
        {
            'url': 'https://www.kinopoisk.ru/film/1111911/watch/1/2',
            'md5': 'a9dc2173f659882687e8b2c6df0063ac',
            'info_dict': {
                'id': '1111911/1/2',
                'ext': 'mp4',
                'title': 'Пикник у Висячей скалы - Сезон 1 - Серия 2',
                'alt_title': 'Picnic at Hanging Rock',
                'thumbnail': r're:^https?://.*',
                'description': 'md5:c821b6755c840761c6a1e8dff5f55188',
                'duration': 3145,
                'age_limit': 16,
                'release_year': 2018,
                'release_date': '20180506',
                'creator': 'Лариса Кондрацки, Майкл Раймер, Аманда Бротчи',
                'location': 'Австралия',
                'average_rating': float,
                'series': 'Пикник у Висячей скалы',
                'season_number': 1,
                'episode_number': 2,
                'episode': '2 серия',
            },
            'params': {
                'format': 'bestvideo',
            },
        },
        {
            'url': 'https://www.kinopoisk.ru/film/81041',
            'only_matching': True,
        },
        {
            'url': 'https://www.kinopoisk.ru/film/mazhor-2014-820638/',
            'only_matching': True,
        },
    ]

    def _extract_entries(self, video_id, items):
        return [
            self.url_result('https://www.kinopoisk.ru/film/%s/watch/%s/%s' %
                (video_id, episode['tvseries_season'], episode['tvseries_episode']), KinoPoiskIE.ie_key())
            for season in items for episode in season.get('items', [])
            if episode.get('tvseries_season') if episode.get('tvseries_episode')]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        data = self._download_json(
            'https://ott-widget.kinopoisk.ru/kinopoisk.json', video_id,
            query={'kpId': video_id})['models']

        film = data.get('film')
        if not film:
            raise ExtractorError('This video requires subscription. You may want to use --cookies.', expected=True)

        mobj = re.match(self._VALID_URL, url)
        season_number = int_or_none(mobj.group('seasonid'))
        episode_number = int_or_none(mobj.group('episodeid'))

        title = film.get('name') or film['original_name']

        # TV Show page
        if film.get('items') and not season_number and not episode_number:
            return self.playlist_result(self._extract_entries(video_id, film['items']), video_id, title)

        alt_title = film.get('original_name')
        description = film.get('comment') or film.get('short_description')
        release_year = int_or_none(film.get('years'))
        creator = film.get('directors')
        location = film.get('countries')
        average_rating = float_or_none(film.get('kinopoisk_rating')) or float_or_none(film.get('imdb_rating'))
        thumbnail = film.get('cover') or film.get('import_poster')

        series = None
        if season_number and episode_number:
            for season in film.get('items', []):
                if season_number == int_or_none(season.get('export_content_id')):
                    release_year = int_or_none(season.get('year')) or release_year
                    for episode in season.get('items', []):
                        if episode_number == episode.get('tvseries_episode'):
                            video_id = episode.get('export_content_id') or '%s/%s/%s' % (video_id,
                                                                                         season_number, episode_number)
                            film = episode
                            series = title
                            title = film.get('name') or title
                            description = film.get('comment') or description
                            thumbnail = film.get('import_thumbnail') or film.get('tv_thumbnail') or thumbnail
                            break

        duration = int_or_none(film.get('average_duration')) or int_or_none(film.get('duration'))
        age_limit = int_or_none(film.get('restriction_age'))
        episode_title = film.get('tvseries_episode_name')

        release_date = None
        release_date_timestamp = film.get('release_date')
        if release_date_timestamp:
            try:
                release_date = datetime.datetime.utcfromtimestamp(release_date_timestamp).strftime('%Y%m%d')
            except (ValueError, OverflowError, OSError):
                pass

        streams_data = self._download_json(
            'https://ott-widget.kinopoisk.ru/ott/ott-api/master-playlists/' + film['uuid'],
            video_id, 'Downloading streams JSON metadata',
            query={'serviceId': 25, 'drmSupported': 'false'})['masterPlaylist']

        subtitles = {}
        for closed_caption in film.get('subtitles', []) or try_get(streams_data,
                                                                   lambda x: x['streams']['subtitles'], list) or []:
            sub_url = closed_caption.get('url')
            if not sub_url:
                continue
            lang = closed_caption.get('language') or closed_caption.get('title') or 'rus'
            subtitles.setdefault(lang, []).append({'url': sub_url})

        formats = []
        streams = [stream['uri'] for stream in streams_data.get('allStreams', [])
                   if stream.get('uri')] or [streams_data['uri']]
        for uri in streams:
            ext = determine_ext(uri)
            if ext == 'm3u8':
                formats.extend(self._extract_m3u8_formats(uri, video_id, 'mp4', entry_protocol='m3u8_native',
                                                          m3u8_id='hls', fatal=False))
            elif ext == 'mpd':
                formats.extend(self._extract_mpd_formats(uri, video_id, mpd_id='dash', fatal=False))

        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': title,
            'alt_title': alt_title,
            'description': description,
            'thumbnail': thumbnail,
            'duration': duration,
            'age_limit': age_limit,
            'release_year': release_year,
            'release_date': release_date,
            'creator': creator,
            'location': location,
            'average_rating': average_rating,
            'series': series,
            'season_number': season_number,
            'episode_number': episode_number,
            'episode': episode_title,
            'subtitles': subtitles,
            'formats': formats,
        }
