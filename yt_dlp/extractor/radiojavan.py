import re

from .common import InfoExtractor
from ..utils import (
    parse_resolution,
    str_to_int,
    unified_strdate,
    urlencode_postdata,
    urljoin,
)


class RadioJavanPodcastsIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?radiojavan\.com/podcasts/podcast/(?P<id>[^/]+)/?'
    _TEST = {
        'url': 'https://www.radiojavan.com/podcasts/podcast/Abo-Atash-118',
        'md5': 'c74b6a5adbd99c4b38a0f266dd6fdf4a',
        'info_dict': {
            'id': 'Abo-Atash-118',
            'ext': 'mp3',
            'title': 'DJ Taba - Abo Atash 118',
            'alt_title': 'DJ Taba - Abo Atash 118 Podcast',
            'track': 'Abo Atash 118',
            'artist': 'DJ Taba',
            'thumbnail': r're:^https?://.*\.jpe?g$',
            'upload_date': '20210126',
            'view_count': int,
            'like_count': int,
        }
    }

    def _real_extract(self, url):
        podcast_id = self._match_id(url)

        download_host = self._download_json(
            'https://www.radiojavan.com/podcasts/podcast_host', podcast_id,
            data=urlencode_postdata({'id': podcast_id}),
            headers={
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'Referer': url,
            }).get('host', 'https://host2.rj-mw1.com')

        mp3_url = self._download_json(
            f'https://www.radiojavan.com/podcasts/podcast/{podcast_id}?setup=1', None,
            data=b'',
            headers={
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'X-Requested-With': 'XMLHttpRequest',
                'Referer': url,
            }).get('currentMP3Url')

        webpage = self._download_webpage(url, podcast_id)

        # For Podcasts, RJ displays artist with "song" class!!
        artist = self._search_regex(
            r'<span class="song">([^<]+?)<',
            webpage, 'artist', fatal=False)

        # For Podcasts, RJ displays song title with "artist" class!!
        song = self._search_regex(
            r'<span class="artist">([^<]+?)<',
            webpage, 'song', fatal=False)

        title = f'{artist} - {song}'
        alt_title = self._og_search_title(webpage)
        thumbnail = self._og_search_thumbnail(webpage)

        upload_date = unified_strdate(self._search_regex(
            r'class="dateAdded">Date added: ([^<]+)<',
            webpage, 'upload date', fatal=False))

        view_count = str_to_int(self._search_regex(
            r'class="views">Plays: ([\d,]+)',
            webpage, 'view count', fatal=False))
        like_count = str_to_int(self._search_regex(
            r'class="rating">([\d,]+) likes',
            webpage, 'like count', fatal=False))

        return {
            'id': podcast_id,
            'title': title,
            'alt_title': alt_title,
            'track': song,
            'artist': artist,
            'url': f'{download_host}/media/{mp3_url}.mp3',
            'thumbnail': thumbnail,
            'upload_date': upload_date,
            'view_count': view_count,
            'like_count': like_count,
        }


class RadioJavanIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?radiojavan\.com/videos/video/(?P<id>[^/]+)/?'
    _TEST = {
        'url': 'http://www.radiojavan.com/videos/video/chaartaar-ashoobam',
        'md5': 'e85208ffa3ca8b83534fca9fe19af95b',
        'info_dict': {
            'id': 'chaartaar-ashoobam',
            'ext': 'mp4',
            'title': 'Chaartaar - Ashoobam',
            'alt_title': 'Chaartaar - Ashoobam Video | چارتار آشوبم',
            'cast': ['Chaartaar'],
            'track': 'Ashoobam',
            'artist': 'Chaartaar',
            'thumbnail': r're:^https?://.*\.jpe?g$',
            'upload_date': '20150215',
            'view_count': int,
            'like_count': int,
        }
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)

        download_host = self._download_json(
            'https://www.radiojavan.com/videos/video_host', video_id,
            data=urlencode_postdata({'id': video_id}),
            headers={
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'Referer': url,
            }).get('host', 'https://host1.rjmusicmedia.com')

        webpage = self._download_webpage(url, video_id)

        formats = []
        for format_id, _, video_path in re.findall(
                r'RJ\.video(?P<format_id>\d+[pPkK])\s*=\s*(["\'])(?P<url>(?:(?!\2).)+)\2',
                webpage):
            f = parse_resolution(format_id)
            f.update({
                'url': urljoin(download_host, video_path),
                'format_id': format_id,
            })
            formats.append(f)

        artist = self._search_regex(
            r'<span class="artist">([^<]+?)<',
            webpage, 'artist', fatal=False)

        song = self._search_regex(
            r'<span class="song">([^<]+?)<',
            webpage, 'song', fatal=False)

        title = f'{artist} - {song}'
        alt_title = self._og_search_title(webpage)
        thumbnail = self._og_search_thumbnail(webpage)

        upload_date = unified_strdate(self._search_regex(
            r'class="date_added">Date added: ([^<]+)<',
            webpage, 'upload date', fatal=False))

        view_count = str_to_int(self._search_regex(
            r'class="views">Plays: ([\d,]+)',
            webpage, 'view count', fatal=False))
        like_count = str_to_int(self._search_regex(
            r'class="rating">([\d,]+) likes',
            webpage, 'like count', fatal=False))

        return {
            'id': video_id,
            'title': title,
            'alt_title': alt_title,
            'cast': [artist],
            'track': song,
            'artist': artist,
            'thumbnail': thumbnail,
            'upload_date': upload_date,
            'view_count': view_count,
            'like_count': like_count,
            'formats': formats,
        }
