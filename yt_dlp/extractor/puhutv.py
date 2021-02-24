# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..compat import (
    compat_HTTPError,
    compat_str,
)
from ..utils import (
    ExtractorError,
    int_or_none,
    float_or_none,
    parse_resolution,
    str_or_none,
    try_get,
    unified_timestamp,
    url_or_none,
    urljoin,
)


class PuhuTVIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?puhutv\.com/(?P<id>[^/?#&]+)-izle'
    IE_NAME = 'puhutv'
    _TESTS = [{
        # film
        'url': 'https://puhutv.com/sut-kardesler-izle',
        'md5': 'a347470371d56e1585d1b2c8dab01c96',
        'info_dict': {
            'id': '5085',
            'display_id': 'sut-kardesler',
            'ext': 'mp4',
            'title': 'Süt Kardeşler',
            'description': 'md5:ca09da25b7e57cbb5a9280d6e48d17aa',
            'thumbnail': r're:^https?://.*\.jpg$',
            'duration': 4832.44,
            'creator': 'Arzu Film',
            'timestamp': 1561062602,
            'upload_date': '20190620',
            'release_year': 1976,
            'view_count': int,
            'tags': list,
        },
    }, {
        # episode, geo restricted, bypassable with --geo-verification-proxy
        'url': 'https://puhutv.com/jet-sosyete-1-bolum-izle',
        'only_matching': True,
    }, {
        # 4k, with subtitles
        'url': 'https://puhutv.com/dip-1-bolum-izle',
        'only_matching': True,
    }]
    _SUBTITLE_LANGS = {
        'English': 'en',
        'Deutsch': 'de',
        'عربى': 'ar'
    }

    def _real_extract(self, url):
        display_id = self._match_id(url)

        info = self._download_json(
            urljoin(url, '/api/slug/%s-izle' % display_id),
            display_id)['data']

        video_id = compat_str(info['id'])
        show = info.get('title') or {}
        title = info.get('name') or show['name']
        if info.get('display_name'):
            title = '%s %s' % (title, info['display_name'])

        try:
            videos = self._download_json(
                'https://puhutv.com/api/assets/%s/videos' % video_id,
                display_id, 'Downloading video JSON',
                headers=self.geo_verification_headers())
        except ExtractorError as e:
            if isinstance(e.cause, compat_HTTPError) and e.cause.code == 403:
                self.raise_geo_restricted()
            raise

        urls = []
        formats = []

        for video in videos['data']['videos']:
            media_url = url_or_none(video.get('url'))
            if not media_url or media_url in urls:
                continue
            urls.append(media_url)

            playlist = video.get('is_playlist')
            if (video.get('stream_type') == 'hls' and playlist is True) or 'playlist.m3u8' in media_url:
                formats.extend(self._extract_m3u8_formats(
                    media_url, video_id, 'mp4', entry_protocol='m3u8_native',
                    m3u8_id='hls', fatal=False))
                continue

            quality = int_or_none(video.get('quality'))
            f = {
                'url': media_url,
                'ext': 'mp4',
                'height': quality
            }
            video_format = video.get('video_format')
            is_hls = (video_format == 'hls' or '/hls/' in media_url or '/chunklist.m3u8' in media_url) and playlist is False
            if is_hls:
                format_id = 'hls'
                f['protocol'] = 'm3u8_native'
            elif video_format == 'mp4':
                format_id = 'http'
            else:
                continue
            if quality:
                format_id += '-%sp' % quality
            f['format_id'] = format_id
            formats.append(f)
        self._sort_formats(formats)

        creator = try_get(
            show, lambda x: x['producer']['name'], compat_str)

        content = info.get('content') or {}

        images = try_get(
            content, lambda x: x['images']['wide'], dict) or {}
        thumbnails = []
        for image_id, image_url in images.items():
            if not isinstance(image_url, compat_str):
                continue
            if not image_url.startswith(('http', '//')):
                image_url = 'https://%s' % image_url
            t = parse_resolution(image_id)
            t.update({
                'id': image_id,
                'url': image_url
            })
            thumbnails.append(t)

        tags = []
        for genre in show.get('genres') or []:
            if not isinstance(genre, dict):
                continue
            genre_name = genre.get('name')
            if genre_name and isinstance(genre_name, compat_str):
                tags.append(genre_name)

        subtitles = {}
        for subtitle in content.get('subtitles') or []:
            if not isinstance(subtitle, dict):
                continue
            lang = subtitle.get('language')
            sub_url = url_or_none(subtitle.get('url') or subtitle.get('file'))
            if not lang or not isinstance(lang, compat_str) or not sub_url:
                continue
            subtitles[self._SUBTITLE_LANGS.get(lang, lang)] = [{
                'url': sub_url
            }]

        return {
            'id': video_id,
            'display_id': display_id,
            'title': title,
            'description': info.get('description') or show.get('description'),
            'season_id': str_or_none(info.get('season_id')),
            'season_number': int_or_none(info.get('season_number')),
            'episode_number': int_or_none(info.get('episode_number')),
            'release_year': int_or_none(show.get('released_at')),
            'timestamp': unified_timestamp(info.get('created_at')),
            'creator': creator,
            'view_count': int_or_none(content.get('watch_count')),
            'duration': float_or_none(content.get('duration_in_ms'), 1000),
            'tags': tags,
            'subtitles': subtitles,
            'thumbnails': thumbnails,
            'formats': formats
        }


class PuhuTVSerieIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?puhutv\.com/(?P<id>[^/?#&]+)-detay'
    IE_NAME = 'puhutv:serie'
    _TESTS = [{
        'url': 'https://puhutv.com/deniz-yildizi-detay',
        'info_dict': {
            'title': 'Deniz Yıldızı',
            'id': 'deniz-yildizi',
        },
        'playlist_mincount': 205,
    }, {
        # a film detail page which is using same url with serie page
        'url': 'https://puhutv.com/kaybedenler-kulubu-detay',
        'only_matching': True,
    }]

    def _extract_entries(self, seasons):
        for season in seasons:
            season_id = season.get('id')
            if not season_id:
                continue
            page = 1
            has_more = True
            while has_more is True:
                season = self._download_json(
                    'https://galadriel.puhutv.com/seasons/%s' % season_id,
                    season_id, 'Downloading page %s' % page, query={
                        'page': page,
                        'per': 40,
                    })
                episodes = season.get('episodes')
                if isinstance(episodes, list):
                    for ep in episodes:
                        slug_path = str_or_none(ep.get('slugPath'))
                        if not slug_path:
                            continue
                        video_id = str_or_none(int_or_none(ep.get('id')))
                        yield self.url_result(
                            'https://puhutv.com/%s' % slug_path,
                            ie=PuhuTVIE.ie_key(), video_id=video_id,
                            video_title=ep.get('name') or ep.get('eventLabel'))
                page += 1
                has_more = season.get('hasMore')

    def _real_extract(self, url):
        playlist_id = self._match_id(url)

        info = self._download_json(
            urljoin(url, '/api/slug/%s-detay' % playlist_id),
            playlist_id)['data']

        seasons = info.get('seasons')
        if seasons:
            return self.playlist_result(
                self._extract_entries(seasons), playlist_id, info.get('name'))

        # For films, these are using same url with series
        video_id = info.get('slug') or info['assets'][0]['slug']
        return self.url_result(
            'https://puhutv.com/%s-izle' % video_id,
            PuhuTVIE.ie_key(), video_id)
