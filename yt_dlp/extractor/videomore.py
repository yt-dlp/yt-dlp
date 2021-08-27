# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..compat import (
    compat_str,
)
from ..utils import (
    int_or_none,
    parse_qs,
)


class VideomoreBaseIE(InfoExtractor):
    _API_BASE_URL = 'https://more.tv/api/v3/web/'
    _VALID_URL_BASE = r'https?://(?:videomore\.ru|more\.tv)/'

    def _download_page_data(self, display_id):
        return self._download_json(
            self._API_BASE_URL + 'PageData', display_id, query={
                'url': '/' + display_id,
            })['attributes']['response']['data']

    def _track_url_result(self, track):
        track_vod = track['trackVod']
        video_url = track_vod.get('playerLink') or track_vod['link']
        return self.url_result(
            video_url, VideomoreIE.ie_key(), track_vod.get('hubId'))


class VideomoreIE(InfoExtractor):
    IE_NAME = 'videomore'
    _VALID_URL = r'''(?x)
                    videomore:(?P<sid>\d+)$|
                    https?://
                        (?:
                            videomore\.ru/
                            (?:
                                embed|
                                [^/]+/[^/]+
                            )/|
                            (?:
                                (?:player\.)?videomore\.ru|
                                siren\.more\.tv/player
                            )/[^/]*\?.*?\btrack_id=|
                            odysseus\.more.tv/player/(?P<partner_id>\d+)/
                        )
                        (?P<id>\d+)
                        (?:[/?#&]|\.(?:xml|json)|$)
                    '''
    _TESTS = [{
        'url': 'http://videomore.ru/kino_v_detalayah/5_sezon/367617',
        'md5': '44455a346edc0d509ac5b5a5b531dc35',
        'info_dict': {
            'id': '367617',
            'ext': 'flv',
            'title': 'Кино в деталях 5 сезон В гостях Алексей Чумаков и Юлия Ковальчук',
            'series': 'Кино в деталях',
            'episode': 'В гостях Алексей Чумаков и Юлия Ковальчук',
            'thumbnail': r're:^https?://.*\.jpg',
            'duration': 2910,
            'view_count': int,
            'comment_count': int,
            'age_limit': 16,
        },
        'skip': 'The video is not available for viewing.',
    }, {
        'url': 'http://videomore.ru/embed/259974',
        'info_dict': {
            'id': '259974',
            'ext': 'mp4',
            'title': 'Молодежка 2 сезон 40 серия',
            'series': 'Молодежка',
            'season': '2 сезон',
            'episode': '40 серия',
            'thumbnail': r're:^https?://.*\.jpg',
            'duration': 2789,
            'view_count': int,
            'age_limit': 16,
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'http://videomore.ru/molodezhka/sezon_promo/341073',
        'info_dict': {
            'id': '341073',
            'ext': 'flv',
            'title': 'Промо Команда проиграла из-за Бакина?',
            'episode': 'Команда проиграла из-за Бакина?',
            'thumbnail': r're:^https?://.*\.jpg',
            'duration': 29,
            'age_limit': 16,
            'view_count': int,
        },
        'params': {
            'skip_download': True,
        },
        'skip': 'The video is not available for viewing.',
    }, {
        'url': 'http://videomore.ru/elki_3?track_id=364623',
        'only_matching': True,
    }, {
        'url': 'http://videomore.ru/embed/364623',
        'only_matching': True,
    }, {
        'url': 'http://videomore.ru/video/tracks/364623.xml',
        'only_matching': True,
    }, {
        'url': 'http://videomore.ru/video/tracks/364623.json',
        'only_matching': True,
    }, {
        'url': 'http://videomore.ru/video/tracks/158031/quotes/33248',
        'only_matching': True,
    }, {
        'url': 'videomore:367617',
        'only_matching': True,
    }, {
        'url': 'https://player.videomore.ru/?partner_id=97&track_id=736234&autoplay=0&userToken=',
        'only_matching': True,
    }, {
        'url': 'https://odysseus.more.tv/player/1788/352317',
        'only_matching': True,
    }, {
        'url': 'https://siren.more.tv/player/config?track_id=352317&partner_id=1788&user_token=',
        'only_matching': True,
    }]
    _GEO_BYPASS = False

    @staticmethod
    def _extract_url(webpage):
        mobj = re.search(
            r'<object[^>]+data=(["\'])https?://videomore\.ru/player\.swf\?.*config=(?P<url>https?://videomore\.ru/(?:[^/]+/)+\d+\.xml).*\1',
            webpage)
        if not mobj:
            mobj = re.search(
                r'<iframe[^>]+src=([\'"])(?P<url>https?://videomore\.ru/embed/\d+)',
                webpage)

        if mobj:
            return mobj.group('url')

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        video_id = mobj.group('sid') or mobj.group('id')
        partner_id = mobj.group('partner_id') or parse_qs(url).get('partner_id', [None])[0] or '97'

        item = self._download_json(
            'https://siren.more.tv/player/config', video_id, query={
                'partner_id': partner_id,
                'track_id': video_id,
            })['data']['playlist']['items'][0]

        title = item.get('title')
        series = item.get('project_name')
        season = item.get('season_name')
        episode = item.get('episode_name')
        if not title:
            title = []
            for v in (series, season, episode):
                if v:
                    title.append(v)
            title = ' '.join(title)

        streams = item.get('streams') or []
        for protocol in ('DASH', 'HLS'):
            stream_url = item.get(protocol.lower() + '_url')
            if stream_url:
                streams.append({'protocol': protocol, 'url': stream_url})

        formats = []
        for stream in streams:
            stream_url = stream.get('url')
            if not stream_url:
                continue
            protocol = stream.get('protocol')
            if protocol == 'DASH':
                formats.extend(self._extract_mpd_formats(
                    stream_url, video_id, mpd_id='dash', fatal=False))
            elif protocol == 'HLS':
                formats.extend(self._extract_m3u8_formats(
                    stream_url, video_id, 'mp4', 'm3u8_native',
                    m3u8_id='hls', fatal=False))
            elif protocol == 'MSS':
                formats.extend(self._extract_ism_formats(
                    stream_url, video_id, ism_id='mss', fatal=False))

        if not formats:
            error = item.get('error')
            if error:
                if error in ('Данное видео недоступно для просмотра на территории этой страны', 'Данное видео доступно для просмотра только на территории России'):
                    self.raise_geo_restricted(countries=['RU'], metadata_available=True)
                self.raise_no_formats(error, expected=True)
        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': title,
            'series': series,
            'season': season,
            'episode': episode,
            'thumbnail': item.get('thumbnail_url'),
            'duration': int_or_none(item.get('duration')),
            'view_count': int_or_none(item.get('views')),
            'age_limit': int_or_none(item.get('min_age')),
            'formats': formats,
        }


class VideomoreVideoIE(VideomoreBaseIE):
    IE_NAME = 'videomore:video'
    _VALID_URL = VideomoreBaseIE._VALID_URL_BASE + r'(?P<id>(?:(?:[^/]+/){2})?[^/?#&]+)(?:/*|[?#&].*?)$'
    _TESTS = [{
        # single video with og:video:iframe
        'url': 'http://videomore.ru/elki_3',
        'info_dict': {
            'id': '364623',
            'ext': 'flv',
            'title': 'Ёлки 3',
            'description': '',
            'thumbnail': r're:^https?://.*\.jpg',
            'duration': 5579,
            'age_limit': 6,
            'view_count': int,
        },
        'params': {
            'skip_download': True,
        },
        'skip': 'Requires logging in',
    }, {
        # season single series with og:video:iframe
        'url': 'http://videomore.ru/poslednii_ment/1_sezon/14_seriya',
        'info_dict': {
            'id': '352317',
            'ext': 'mp4',
            'title': 'Последний мент 1 сезон 14 серия',
            'series': 'Последний мент',
            'season': '1 сезон',
            'episode': '14 серия',
            'thumbnail': r're:^https?://.*\.jpg',
            'duration': 2464,
            'age_limit': 16,
            'view_count': int,
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'http://videomore.ru/sejchas_v_seti/serii_221-240/226_vypusk',
        'only_matching': True,
    }, {
        # single video without og:video:iframe
        'url': 'http://videomore.ru/marin_i_ego_druzya',
        'info_dict': {
            'id': '359073',
            'ext': 'flv',
            'title': '1 серия. Здравствуй, Аквавилль!',
            'description': 'md5:c6003179538b5d353e7bcd5b1372b2d7',
            'thumbnail': r're:^https?://.*\.jpg',
            'duration': 754,
            'age_limit': 6,
            'view_count': int,
        },
        'params': {
            'skip_download': True,
        },
        'skip': 'redirects to https://more.tv/'
    }, {
        'url': 'https://videomore.ru/molodezhka/6_sezon/29_seriya?utm_so',
        'only_matching': True,
    }, {
        'url': 'https://more.tv/poslednii_ment/1_sezon/14_seriya',
        'only_matching': True,
    }]

    @classmethod
    def suitable(cls, url):
        return False if VideomoreIE.suitable(url) else super(VideomoreVideoIE, cls).suitable(url)

    def _real_extract(self, url):
        display_id = self._match_id(url)
        return self._track_url_result(self._download_page_data(display_id))


class VideomoreSeasonIE(VideomoreBaseIE):
    IE_NAME = 'videomore:season'
    _VALID_URL = VideomoreBaseIE._VALID_URL_BASE + r'(?!embed)(?P<id>[^/]+/[^/?#&]+)(?:/*|[?#&].*?)$'
    _TESTS = [{
        'url': 'http://videomore.ru/molodezhka/film_o_filme',
        'info_dict': {
            'id': 'molodezhka/film_o_filme',
            'title': 'Фильм о фильме',
        },
        'playlist_mincount': 3,
    }, {
        'url': 'http://videomore.ru/molodezhka/sezon_promo?utm_so',
        'only_matching': True,
    }, {
        'url': 'https://more.tv/molodezhka/film_o_filme',
        'only_matching': True,
    }]

    @classmethod
    def suitable(cls, url):
        return (False if (VideomoreIE.suitable(url) or VideomoreVideoIE.suitable(url))
                else super(VideomoreSeasonIE, cls).suitable(url))

    def _real_extract(self, url):
        display_id = self._match_id(url)
        season = self._download_page_data(display_id)
        season_id = compat_str(season['id'])
        tracks = self._download_json(
            self._API_BASE_URL + 'seasons/%s/tracks' % season_id,
            season_id)['data']
        entries = []
        for track in tracks:
            entries.append(self._track_url_result(track))
        return self.playlist_result(entries, display_id, season.get('title'))
