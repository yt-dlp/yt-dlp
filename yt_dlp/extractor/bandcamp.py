import random
import re
import time

from .common import InfoExtractor
from ..utils import (
    KNOWN_EXTENSIONS,
    ExtractorError,
    float_or_none,
    int_or_none,
    parse_filesize,
    str_or_none,
    try_get,
    unified_strdate,
    unified_timestamp,
    update_url_query,
    url_or_none,
    urljoin,
)


class BandcampIE(InfoExtractor):
    _VALID_URL = r'https?://(?P<uploader>[^/]+)\.bandcamp\.com/track/(?P<id>[^/?#&]+)'
    _EMBED_REGEX = [r'<meta property="og:url"[^>]*?content="(?P<url>.*?bandcamp\.com.*?)"']
    _TESTS = [{
        'url': 'http://youtube-dl.bandcamp.com/track/youtube-dl-test-song',
        'md5': 'c557841d5e50261777a6585648adf439',
        'info_dict': {
            'id': '1812978515',
            'ext': 'mp3',
            'title': 'youtube-dl "\'/\\ä↭ - youtube-dl "\'/\\ä↭ - youtube-dl test song "\'/\\ä↭',
            'duration': 9.8485,
            'uploader': 'youtube-dl "\'/\\ä↭',
            'upload_date': '20121129',
            'timestamp': 1354224127,
            'track': 'youtube-dl "\'/\\ä↭ - youtube-dl test song "\'/\\ä↭',
            'album_artist': 'youtube-dl "\'/\\ä↭',
            'track_id': '1812978515',
            'artist': 'youtube-dl "\'/\\ä↭',
            'uploader_url': 'https://youtube-dl.bandcamp.com',
            'uploader_id': 'youtube-dl',
            'thumbnail': 'https://f4.bcbits.com/img/a3216802731_5.jpg',
        },
        '_skip': 'There is a limit of 200 free downloads / month for the test song',
    }, {
        # free download
        'url': 'http://benprunty.bandcamp.com/track/lanius-battle',
        'info_dict': {
            'id': '2650410135',
            'ext': 'm4a',
            'acodec': r're:[fa]lac',
            'title': 'Ben Prunty - Lanius (Battle)',
            'thumbnail': r're:^https?://.*\.jpg$',
            'uploader': 'Ben Prunty',
            'timestamp': 1396508491,
            'upload_date': '20140403',
            'release_timestamp': 1396483200,
            'release_date': '20140403',
            'duration': 260.877,
            'track': 'Lanius (Battle)',
            'track_number': 1,
            'track_id': '2650410135',
            'artist': 'Ben Prunty',
            'album_artist': 'Ben Prunty',
            'album': 'FTL: Advanced Edition Soundtrack',
            'uploader_url': 'https://benprunty.bandcamp.com',
            'uploader_id': 'benprunty',
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
            'release_timestamp': 1076112000,
            'release_date': '20040207',
            'duration': 120.79,
            'track': 'Hail to Fire',
            'track_number': 5,
            'track_id': '2584466013',
            'artist': 'Mastodon',
            'album_artist': 'Mastodon',
            'album': 'Call of the Mastodon',
            'uploader_url': 'https://relapsealumni.bandcamp.com',
            'uploader_id': 'relapsealumni',
        },
    }, {
        # track from compilation album (artist/album_artist difference)
        'url': 'https://diskotopia.bandcamp.com/track/safehouse',
        'md5': '19c5337bca1428afa54129f86a2f6a69',
        'info_dict': {
            'id': '1978174799',
            'ext': 'mp3',
            'title': 'submerse - submerse - Safehouse',
            'thumbnail': r're:^https?://.*\.jpg$',
            'uploader': 'submerse',
            'timestamp': 1480779297,
            'upload_date': '20161203',
            'release_timestamp': 1481068800,
            'release_date': '20161207',
            'duration': 154.066,
            'track': 'submerse - Safehouse',
            'track_number': 3,
            'track_id': '1978174799',
            'artist': 'submerse',
            'album_artist': 'Diskotopia',
            'album': 'DSK F/W 2016-2017 Free Compilation',
            'uploader_url': 'https://diskotopia.bandcamp.com',
            'uploader_id': 'diskotopia',
        },
    }]

    def _extract_data_attr(self, webpage, video_id, attr='tralbum', fatal=True):
        return self._parse_json(self._html_search_regex(
            rf'data-{attr}=(["\'])({{.+?}})\1', webpage,
            attr + ' data', group=2), video_id, fatal=fatal)

    def _real_extract(self, url):
        title, uploader = self._match_valid_url(url).group('id', 'uploader')
        webpage = self._download_webpage(url, title)
        tralbum = self._extract_data_attr(webpage, title)
        thumbnail = self._og_search_thumbnail(webpage)

        track_id = None
        track = None
        track_number = None
        duration = None

        formats = []
        track_info = try_get(tralbum, lambda x: x['trackinfo'][0], dict)
        if track_info:
            file_ = track_info.get('file')
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
            track = track_info.get('title')
            track_id = str_or_none(
                track_info.get('track_id') or track_info.get('id'))
            track_number = int_or_none(track_info.get('track_num'))
            duration = float_or_none(track_info.get('duration'))

        embed = self._extract_data_attr(webpage, title, 'embed', False)
        current = tralbum.get('current') or {}
        artist = embed.get('artist') or current.get('artist') or tralbum.get('artist')
        album_artist = self._html_search_regex(
            r'<h3 class="albumTitle">[\S\s]*?by\s*<span>\s*<a href="[^>]+">\s*([^>]+?)\s*</a>',
            webpage, 'album artist', fatal=False)
        timestamp = unified_timestamp(
            current.get('publish_date') or tralbum.get('album_publish_date'))

        download_link = tralbum.get('freeDownloadPage')
        if download_link:
            track_id = str(tralbum['id'])

            download_webpage = self._download_webpage(
                download_link, track_id, 'Downloading free downloads page')

            blob = self._extract_data_attr(download_webpage, track_id, 'blob')

            info = try_get(
                blob, (lambda x: x['digital_items'][0],
                       lambda x: x['download_items'][0]), dict)
            if info:
                downloads = info.get('downloads')
                if isinstance(downloads, dict):
                    if not track:
                        track = info.get('title')
                    if not artist:
                        artist = info.get('artist')
                    if not thumbnail:
                        thumbnail = info.get('thumb_url')

                    download_formats = {}
                    download_formats_list = blob.get('download_formats')
                    if isinstance(download_formats_list, list):
                        for f in blob['download_formats']:
                            name, ext = f.get('name'), f.get('file_extension')
                            if all(isinstance(x, str) for x in (name, ext)):
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
                            stat_url, track_id, f'Downloading {format_id} JSON',
                            transform_source=lambda s: s[s.index('{'):s.rindex('}') + 1],
                            fatal=False)
                        if not stat:
                            continue
                        retry_url = url_or_none(stat.get('retry_url'))
                        if not retry_url:
                            continue
                        formats.append({
                            'url': self._proto_relative_url(retry_url, 'http:'),
                            'ext': download_formats.get(format_id),
                            'format_id': format_id,
                            'format_note': f.get('description'),
                            'filesize': parse_filesize(f.get('size_mb')),
                            'vcodec': 'none',
                            'acodec': format_id.split('-')[0],
                        })

        title = f'{artist} - {track}' if artist else track

        if not duration:
            duration = float_or_none(self._html_search_meta(
                'duration', webpage, default=None))

        return {
            'id': track_id,
            'title': title,
            'thumbnail': thumbnail,
            'uploader': artist,
            'uploader_id': uploader,
            'uploader_url': f'https://{uploader}.bandcamp.com',
            'timestamp': timestamp,
            'release_timestamp': unified_timestamp(tralbum.get('album_release_date')),
            'duration': duration,
            'track': track,
            'track_number': track_number,
            'track_id': track_id,
            'artist': artist,
            'album': embed.get('album_title'),
            'album_artist': album_artist,
            'formats': formats,
        }


class BandcampAlbumIE(BandcampIE):  # XXX: Do not subclass from concrete IE
    IE_NAME = 'Bandcamp:album'
    _VALID_URL = r'https?://(?:(?P<subdomain>[^.]+)\.)?bandcamp\.com/album/(?P<id>[^/?#&]+)'

    _TESTS = [{
        'url': 'http://blazo.bandcamp.com/album/jazz-format-mixtape-vol-1',
        'playlist': [
            {
                'md5': '39bc1eded3476e927c724321ddf116cf',
                'info_dict': {
                    'id': '1353101989',
                    'ext': 'mp3',
                    'title': 'Blazo - Intro',
                    'timestamp': 1311756226,
                    'upload_date': '20110727',
                    'uploader': 'Blazo',
                },
            },
            {
                'md5': '1a2c32e2691474643e912cc6cd4bffaa',
                'info_dict': {
                    'id': '38097443',
                    'ext': 'mp3',
                    'title': 'Blazo - Kero One - Keep It Alive (Blazo remix)',
                    'timestamp': 1311757238,
                    'upload_date': '20110727',
                    'uploader': 'Blazo',
                },
            },
        ],
        'info_dict': {
            'title': 'Jazz Format Mixtape vol.1',
            'id': 'jazz-format-mixtape-vol-1',
            'uploader_id': 'blazo',
        },
        'params': {
            'playlistend': 2,
        },
        'skip': 'Bandcamp imposes download limits.',
    }, {
        'url': 'http://nightbringer.bandcamp.com/album/hierophany-of-the-open-grave',
        'info_dict': {
            'title': 'Hierophany of the Open Grave',
            'uploader_id': 'nightbringer',
            'id': 'hierophany-of-the-open-grave',
        },
        'playlist_mincount': 9,
    }, {
        # with escaped quote in title
        'url': 'https://jstrecords.bandcamp.com/album/entropy-ep',
        'info_dict': {
            'title': '"Entropy" EP',
            'uploader_id': 'jstrecords',
            'id': 'entropy-ep',
            'description': 'md5:0ff22959c943622972596062f2f366a5',
        },
        'playlist_mincount': 3,
    }, {
        # not all tracks have songs
        'url': 'https://insulters.bandcamp.com/album/we-are-the-plague',
        'info_dict': {
            'id': 'we-are-the-plague',
            'title': 'WE ARE THE PLAGUE',
            'uploader_id': 'insulters',
            'description': 'md5:b3cf845ee41b2b1141dc7bde9237255f',
        },
        'playlist_count': 2,
    }]

    @classmethod
    def suitable(cls, url):
        return (False
                if BandcampWeeklyIE.suitable(url) or BandcampIE.suitable(url)
                else super().suitable(url))

    def _real_extract(self, url):
        uploader_id, album_id = self._match_valid_url(url).groups()
        playlist_id = album_id or uploader_id
        webpage = self._download_webpage(url, playlist_id)
        tralbum = self._extract_data_attr(webpage, playlist_id)
        track_info = tralbum.get('trackinfo')
        if not track_info:
            raise ExtractorError('The page doesn\'t contain any tracks')
        # Only tracks with duration info have songs
        entries = [
            self.url_result(
                urljoin(url, t['title_link']), BandcampIE.ie_key(),
                str_or_none(t.get('track_id') or t.get('id')), t.get('title'))
            for t in track_info
            if t.get('duration')]

        current = tralbum.get('current') or {}

        return {
            '_type': 'playlist',
            'uploader_id': uploader_id,
            'id': playlist_id,
            'title': current.get('title'),
            'description': current.get('about'),
            'entries': entries,
        }


class BandcampWeeklyIE(BandcampIE):  # XXX: Do not subclass from concrete IE
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
            'episode_id': '224',
        },
        'params': {
            'format': 'opus-lo',
        },
    }, {
        'url': 'https://bandcamp.com/?blah/blah@&show=228',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        show_id = self._match_id(url)
        webpage = self._download_webpage(url, show_id)

        blob = self._extract_data_attr(webpage, show_id, 'blob')

        show = blob['bcw_data'][show_id]

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

        title = show.get('audio_title') or 'Bandcamp Weekly'
        subtitle = show.get('subtitle')
        if subtitle:
            title += f' - {subtitle}'

        return {
            'id': show_id,
            'title': title,
            'description': show.get('desc') or show.get('short_desc'),
            'duration': float_or_none(show.get('audio_duration')),
            'is_live': False,
            'release_date': unified_strdate(show.get('published_date')),
            'series': 'Bandcamp Weekly',
            'episode': show.get('subtitle'),
            'episode_id': show_id,
            'formats': formats,
        }


class BandcampUserIE(InfoExtractor):
    IE_NAME = 'Bandcamp:user'
    _VALID_URL = r'https?://(?!www\.)(?P<id>[^.]+)\.bandcamp\.com(?:/music)?/?(?:[#?]|$)'

    _TESTS = [{
        # Type 1 Bandcamp user page.
        'url': 'https://adrianvonziegler.bandcamp.com',
        'info_dict': {
            'id': 'adrianvonziegler',
            'title': 'Discography of adrianvonziegler',
        },
        'playlist_mincount': 23,
    }, {
        # Bandcamp user page with only one album
        'url': 'http://dotscale.bandcamp.com',
        'info_dict': {
            'id': 'dotscale',
            'title': 'Discography of dotscale',
        },
        'playlist_count': 1,
    }, {
        # Type 2 Bandcamp user page.
        'url': 'https://nightcallofficial.bandcamp.com',
        'info_dict': {
            'id': 'nightcallofficial',
            'title': 'Discography of nightcallofficial',
        },
        'playlist_count': 4,
    }, {
        'url': 'https://steviasphere.bandcamp.com/music',
        'playlist_mincount': 47,
        'info_dict': {
            'id': 'steviasphere',
            'title': 'Discography of steviasphere',
        },
    }, {
        'url': 'https://coldworldofficial.bandcamp.com/music',
        'playlist_mincount': 10,
        'info_dict': {
            'id': 'coldworldofficial',
            'title': 'Discography of coldworldofficial',
        },
    }, {
        'url': 'https://nuclearwarnowproductions.bandcamp.com/music',
        'playlist_mincount': 399,
        'info_dict': {
            'id': 'nuclearwarnowproductions',
            'title': 'Discography of nuclearwarnowproductions',
        },
    }]

    def _real_extract(self, url):
        uploader = self._match_id(url)
        webpage = self._download_webpage(url, uploader)

        discography_data = (re.findall(r'<li data-item-id=["\'][^>]+>\s*<a href=["\'](?![^"\'/]*?/merch)([^"\']+)', webpage)
                            or re.findall(r'<div[^>]+trackTitle["\'][^"\']+["\']([^"\']+)', webpage))

        return self.playlist_from_matches(
            discography_data, uploader, f'Discography of {uploader}', getter=lambda x: urljoin(url, x))
