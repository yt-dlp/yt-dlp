from __future__ import unicode_literals

import random
import re
import time

from .common import InfoExtractor
from ..compat import (
    compat_str,
    compat_urlparse,
)
from ..utils import (
    ExtractorError,
    float_or_none,
    int_or_none,
    KNOWN_EXTENSIONS,
    parse_filesize,
    str_or_none,
    try_get,
    unescapeHTML,
    update_url_query,
    unified_strdate,
    unified_timestamp,
    url_or_none,
)


class BandcampBaseIE(InfoExtractor):
    """Provide base functions for Bandcamp extractors"""

    def _extract_json_from_html_data_attribute(self, webpage, suffix, video_id):
        json_string = self._html_search_regex(
            r' data-%s="([^"]*)' % suffix,
            webpage, '%s json' % suffix, default='{}')

        return self._parse_json(json_string, video_id)

    def _parse_json_track(self, json):
        formats = []
        file_ = json.get('file')
        if isinstance(file_, dict):
            for format_id, format_url in file_.items():
                if not url_or_none(format_url):
                    continue
                ext, abr_str = format_id.split('-', 1)
                formats.append({
                    'format_id': format_id,
                    'url': self._proto_relative_url(format_url, 'http:'),
                    'ext': ext,
                    'vcodec': 'none',
                    'acodec': ext,
                    'abr': int_or_none(abr_str),
                })

        return {
            'duration': float_or_none(json.get('duration')),
            'id': str_or_none(json.get('track_id') or json.get('id')),
            'title': json.get('title'),
            'title_link': json.get('title_link'),
            'number': int_or_none(json.get('track_num')),
            'formats': formats
        }


class BandcampIE(BandcampBaseIE):
    IE_NAME = "Bandcamp:track"
    _VALID_URL = r'https?://[^/]+\.bandcamp\.com/track/(?P<title>[^/?#&]+)'
    _TESTS = [{
        'url': 'http://youtube-dl.bandcamp.com/track/youtube-dl-test-song',
        'md5': 'c557841d5e50261777a6585648adf439',
        'info_dict': {
            'id': '1812978515',
            'ext': 'mp3',
            'title': "youtube-dl  \"'/\\\u00e4\u21ad - youtube-dl  \"'/\\\u00e4\u21ad - youtube-dl test song \"'/\\\u00e4\u21ad",
            'duration': 9.8485,
            'uploader': "youtube-dl  \"'/\\\u00e4\u21ad",
            'timestamp': 1354224127,
            'upload_date': '20121129',
        },
        '_skip': 'There is a limit of 200 free downloads / month for the test song'
    }, {
        # free download
        'url': 'http://benprunty.bandcamp.com/track/lanius-battle',
        'md5': '5d92af55811e47f38962a54c30b07ef0',
        'info_dict': {
            'id': '2650410135',
            'ext': 'aiff',
            'title': 'Ben Prunty - Lanius (Battle)',
            'thumbnail': r're:^https?://.*\.jpg$',
            'uploader': 'Ben Prunty',
            'timestamp': 1396508491,
            'upload_date': '20140403',
            'release_date': '20140403',
            'duration': 260.877,
            'track': 'Lanius (Battle)',
            'track_number': 1,
            'track_id': '2650410135',
            'artist': 'Ben Prunty',
            'album': 'FTL: Advanced Edition Soundtrack',
        },
    }, {
        # no free download, mp3 128
        'url': 'https://relapsealumni.bandcamp.com/track/hail-to-fire',
        'md5': 'fec12ff55e804bb7f7ebeb77a800c8b7',
        'info_dict': {
            'id': '2584466013',
            'ext': 'mp3',
            'title': 'Mastodon - Hail to Fire',
            'thumbnail': r're:^https?://.*\.jpg$',
            'uploader': 'Mastodon',
            'timestamp': 1322005399,
            'upload_date': '20111122',
            'release_date': '20040207',
            'duration': 120.79,
            'track': 'Hail to Fire',
            'track_number': 5,
            'track_id': '2584466013',
            'artist': 'Mastodon',
            'album': 'Call of the Mastodon',
        },
    }]

    def _real_extract(self, url):
        mobj = re.match(self._VALID_URL, url)
        title = mobj.group('title')
        url_track_title = title
        webpage = self._download_webpage(url, title)
        thumbnail = self._html_search_meta('og:image', webpage, default=None)

        json_tralbum = self._extract_json_from_html_data_attribute(webpage, "tralbum", url_track_title)
        json_embed = self._extract_json_from_html_data_attribute(webpage, "embed", url_track_title)

        json_tracks = json_tralbum.get('trackinfo')
        if not json_tracks:
            raise ExtractorError('Could not extract track')

        track = self._parse_json_track(json_tracks[0])
        artist = json_tralbum.get('artist')
        album_title = json_embed.get('album_title')

        json_album = json_tralbum.get('packages')
        if json_album:
            json_album = json_album[0]
            album_publish_date = json_album.get('album_publish_date')
            album_release_date = json_album.get('album_release_date')
        else:
            album_publish_date = None
            album_release_date = json_tralbum.get('album_release_date')

        timestamp = unified_timestamp(json_tralbum.get('current', {}).get('publish_date') or album_publish_date)
        release_date = unified_strdate(album_release_date)

        download_link = self._search_regex(
            r'freeDownloadPage(?:["\']|&quot;):\s*(["\']|&quot;)(?P<url>(?:(?!\1).)+)\1', webpage,
            'download link', default=None, group='url')
        if download_link:
            track_id = self._search_regex(
                r'\?id=(?P<id>\d+)&',
                download_link, 'track id')

            download_webpage = self._download_webpage(
                download_link, track_id, 'Downloading free downloads page')

            blob = self._parse_json(
                self._search_regex(
                    r'data-blob=(["\'])(?P<blob>{.+?})\1', download_webpage,
                    'blob', group='blob'),
                track_id, transform_source=unescapeHTML)

            info = try_get(
                blob, (lambda x: x['digital_items'][0],
                       lambda x: x['download_items'][0]), dict)
            if info:
                downloads = info.get('downloads')
                if isinstance(downloads, dict):
                    if not artist:
                        artist = info.get('artist')
                    if not thumbnail:
                        thumbnail = info.get('thumb_url')

                    download_formats = {}
                    download_formats_list = blob.get('download_formats')
                    if isinstance(download_formats_list, list):
                        for f in blob['download_formats']:
                            name, ext = f.get('name'), f.get('file_extension')
                            if all(isinstance(x, compat_str) for x in (name, ext)):
                                download_formats[name] = ext.strip('.')

                    for format_id, f in downloads.items():
                        format_url = f.get('url')
                        if not format_url:
                            continue
                        # Stat URL generation algorithm is reverse engineered from
                        # download_*_bundle_*.js
                        stat_url = update_url_query(
                            format_url.replace('/download/', '/statdownload/'), {
                                '.rand': int(time.time() * 1000 * random.random()),
                            })
                        format_id = f.get('encoding_name') or format_id
                        stat = self._download_json(
                            stat_url, track_id, 'Downloading %s JSON' % format_id,
                            transform_source=lambda s: s[s.index('{'):s.rindex('}') + 1],
                            fatal=False)
                        if not stat:
                            continue
                        retry_url = url_or_none(stat.get('retry_url'))
                        if not retry_url:
                            continue
                        track['formats'].append({
                            'url': self._proto_relative_url(retry_url, 'http:'),
                            'ext': download_formats.get(format_id),
                            'format_id': format_id,
                            'format_note': f.get('description'),
                            'filesize': parse_filesize(f.get('size_mb')),
                            'vcodec': 'none',
                        })

        self._sort_formats(track['formats'])

        title = '%s - %s' % (artist, track.get('title')) if artist else track.get('title')

        return {
            'album': album_title,
            'artist': artist,
            'duration': track['duration'],
            'formats': track['formats'],
            'id': track['id'],
            'release_date': release_date,
            'thumbnail': thumbnail,
            'timestamp': timestamp,
            'title': title,
            'track': track['title'],
            'track_id': track['id'],
            'track_number': track['number'],
            'uploader': artist
        }


class BandcampAlbumIE(BandcampBaseIE):
    IE_NAME = 'Bandcamp:album'
    _VALID_URL = r'https?://(?:(?P<subdomain>[^.]+)\.)?bandcamp\.com(?:/album/(?P<album_id>[^/?#&]+))?'

    _TESTS = [{
        'url': 'http://blazo.bandcamp.com/album/jazz-format-mixtape-vol-1',
        'playlist': [
            {
                'md5': '39bc1eded3476e927c724321ddf116cf',
                'info_dict': {
                    'id': '1353101989',
                    'ext': 'mp3',
                    'title': 'Intro',
                }
            },
            {
                'md5': '1a2c32e2691474643e912cc6cd4bffaa',
                'info_dict': {
                    'id': '38097443',
                    'ext': 'mp3',
                    'title': 'Kero One - Keep It Alive (Blazo remix)',
                }
            },
        ],
        'info_dict': {
            'title': 'Jazz Format Mixtape vol.1',
            'id': 'jazz-format-mixtape-vol-1',
            'uploader_id': 'blazo',
        },
        'params': {
            'playlistend': 2
        },
        'skip': 'Bandcamp imposes download limits.'
    }, {
        'url': 'http://nightbringer.bandcamp.com/album/hierophany-of-the-open-grave',
        'info_dict': {
            'title': 'Hierophany of the Open Grave',
            'uploader_id': 'nightbringer',
            'id': 'hierophany-of-the-open-grave',
        },
        'playlist_mincount': 9,
    }, {
        'url': 'http://dotscale.bandcamp.com',
        'info_dict': {
            'title': 'Loom',
            'id': 'dotscale',
            'uploader_id': 'dotscale',
        },
        'playlist_mincount': 7,
    }, {
        # with escaped quote in title
        'url': 'https://jstrecords.bandcamp.com/album/entropy-ep',
        'info_dict': {
            'title': '"Entropy" EP',
            'uploader_id': 'jstrecords',
            'id': 'entropy-ep',
        },
        'playlist_mincount': 3,
    }, {
        # not all tracks have songs
        'url': 'https://insulters.bandcamp.com/album/we-are-the-plague',
        'info_dict': {
            'id': 'we-are-the-plague',
            'title': 'WE ARE THE PLAGUE',
            'uploader_id': 'insulters',
        },
        'playlist_count': 2,
    }]

    @classmethod
    def suitable(cls, url):
        return (False
                if BandcampWeeklyIE.suitable(url) or BandcampIE.suitable(url)
                else super(BandcampAlbumIE, cls).suitable(url))

    def _real_extract(self, url):
        mobj = re.match(self._VALID_URL, url)
        uploader_id = mobj.group('subdomain')
        album_id = mobj.group('album_id')
        playlist_id = album_id or uploader_id
        webpage = self._download_webpage(url, playlist_id)

        json_tralbum = self._extract_json_from_html_data_attribute(webpage, "tralbum", playlist_id)
        json_embed = self._extract_json_from_html_data_attribute(webpage, "embed", playlist_id)

        json_tracks = json_tralbum.get('trackinfo')
        if not json_tracks:
            raise ExtractorError('Could not extract album tracks')

        album_title = json_embed.get('album_title')

        # Only tracks with duration info have songs
        tracks = [self._parse_json_track(track) for track in json_tracks]
        entries = [
            self.url_result(
                compat_urlparse.urljoin(url, track['title_link']),
                ie=BandcampIE.ie_key(), video_id=track['id'],
                video_title=track['title'])
            for track in tracks
            if track.get('duration')]

        return {
            '_type': 'playlist',
            'uploader_id': uploader_id,
            'id': playlist_id,
            'title': album_title,
            'entries': entries
        }


class BandcampWeeklyIE(InfoExtractor):
    IE_NAME = 'Bandcamp:weekly'
    _VALID_URL = r'https?://(?:www\.)?bandcamp\.com/?\?(?:.*?&)?show=(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://bandcamp.com/?show=224',
        'md5': 'b00df799c733cf7e0c567ed187dea0fd',
        'info_dict': {
            'id': '224',
            'ext': 'opus',
            'title': 'BC Weekly April 4th 2017 - Magic Moments',
            'description': 'md5:5d48150916e8e02d030623a48512c874',
            'duration': 5829.77,
            'release_date': '20170404',
            'series': 'Bandcamp Weekly',
            'episode': 'Magic Moments',
            'episode_number': 208,
            'episode_id': '224',
        }
    }, {
        'url': 'https://bandcamp.com/?blah/blah@&show=228',
        'only_matching': True
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        blob = self._parse_json(
            self._search_regex(
                r'data-blob=(["\'])(?P<blob>{.+?})\1', webpage,
                'blob', group='blob'),
            video_id, transform_source=unescapeHTML)

        show = blob['bcw_show']

        # This is desired because any invalid show id redirects to `bandcamp.com`
        # which happens to expose the latest Bandcamp Weekly episode.
        show_id = int_or_none(show.get('show_id')) or int_or_none(video_id)

        formats = []
        for format_id, format_url in show['audio_stream'].items():
            if not url_or_none(format_url):
                continue
            for known_ext in KNOWN_EXTENSIONS:
                if known_ext in format_id:
                    ext = known_ext
                    break
            else:
                ext = None
            formats.append({
                'format_id': format_id,
                'url': format_url,
                'ext': ext,
                'vcodec': 'none',
            })
        self._sort_formats(formats)

        title = show.get('audio_title') or 'Bandcamp Weekly'
        subtitle = show.get('subtitle')
        if subtitle:
            title += ' - %s' % subtitle

        episode_number = None
        seq = blob.get('bcw_seq')

        if seq and isinstance(seq, list):
            try:
                episode_number = next(
                    int_or_none(e.get('episode_number'))
                    for e in seq
                    if isinstance(e, dict) and int_or_none(e.get('id')) == show_id)
            except StopIteration:
                pass

        return {
            'id': video_id,
            'title': title,
            'description': show.get('desc') or show.get('short_desc'),
            'duration': float_or_none(show.get('audio_duration')),
            'is_live': False,
            'release_date': unified_strdate(show.get('published_date')),
            'series': 'Bandcamp Weekly',
            'episode': show.get('subtitle'),
            'episode_number': episode_number,
            'episode_id': compat_str(video_id),
            'formats': formats
        }
