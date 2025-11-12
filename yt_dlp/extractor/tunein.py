import functools
import urllib.parse

from .common import InfoExtractor
from ..utils import (
    OnDemandPagedList,
    UnsupportedError,
    clean_html,
    int_or_none,
    join_nonempty,
    parse_iso8601,
    update_url_query,
    url_or_none,
)
from ..utils.traversal import traverse_obj


class TuneInBaseIE(InfoExtractor):
    def _call_api(self, item_id, endpoint=None, note='Downloading JSON metadata', fatal=False, query=None):
        return self._download_json(
            join_nonempty('https://api.tunein.com/profiles', item_id, endpoint, delim='/'),
            item_id, note=note, fatal=fatal, query=query) or {}

    def _extract_formats_and_subtitles(self, content_id):
        streams = self._download_json(
            'https://opml.radiotime.com/Tune.ashx', content_id, query={
                'formats': 'mp3,aac,ogg,flash,hls',
                'id': content_id,
                'render': 'json',
            })

        formats, subtitles = [], {}
        for stream in traverse_obj(streams, ('body', lambda _, v: url_or_none(v['url']))):
            if stream.get('media_type') == 'hls':
                fmts, subs = self._extract_m3u8_formats_and_subtitles(stream['url'], content_id, fatal=False)
                formats.extend(fmts)
                self._merge_subtitles(subs, target=subtitles)
            else:
                formats.append(traverse_obj(stream, {
                    'abr': ('bitrate', {int_or_none}),
                    'ext': ('media_type', {str}),
                    'url': ('url', {self._proto_relative_url}),
                }))

        return formats, subtitles


class TuneInStationIE(TuneInBaseIE):
    IE_NAME = 'tunein:station'
    _VALID_URL = r'https?://tunein\.com/radio/[^/?#]+(?P<id>s\d+)'
    _TESTS = [{
        'url': 'https://tunein.com/radio/Jazz24-885-s34682/',
        'info_dict': {
            'id': 's34682',
            'ext': 'mp3',
            'title': str,
            'alt_title': 'World Class Jazz',
            'channel_follower_count': int,
            'description': 'md5:d6d0b89063fd68d529fa7058ee98619b',
            'location': r're:Seattle-Tacoma, (?:US|WA)',
            'live_status': 'is_live',
            'thumbnail': r're:https?://.+',
        },
        'params': {'skip_download': 'Livestream'},
    }, {
        'url': 'https://tunein.com/radio/BBC-Radio-1-988-s24939/',
        'info_dict': {
            'id': 's24939',
            'ext': 'm4a',
            'title': str,
            'alt_title': 'The biggest new pop and all-day vibes',
            'channel_follower_count': int,
            'description': 'md5:ee2c56794844610d045f8caf5ff34d0c',
            'location': 'London, UK',
            'live_status': 'is_live',
            'thumbnail': r're:https?://.+',
        },
        'params': {'skip_download': 'Livestream'},
    }]

    def _real_extract(self, url):
        station_id = self._match_id(url)
        formats, subtitles = self._extract_formats_and_subtitles(station_id)

        return {
            'id': station_id,
            'formats': formats,
            'subtitles': subtitles,
            **traverse_obj(self._call_api(station_id), ('Item', {
                'title': ('Title', {clean_html}),
                'alt_title': ('Subtitle', {clean_html}, filter),
                'channel_follower_count': ('Actions', 'Follow', 'FollowerCount', {int_or_none}),
                'description': ('Description', {clean_html}, filter),
                'is_live': ('Actions', 'Play', 'IsLive', {bool}),
                'location': ('Properties', 'Location', 'DisplayName', {str}),
                'thumbnail': ('Image', {url_or_none}),
            })),
        }


class TuneInPodcastIE(TuneInBaseIE):
    IE_NAME = 'tunein:podcast:program'
    _PAGE_SIZE = 20
    _VALID_URL = r'https?://tunein\.com/podcasts(?:/[^/?#]+){1,2}(?P<id>p\d+)'
    _TESTS = [{
        'url': 'https://tunein.com/podcasts/Technology-Podcasts/Artificial-Intelligence-p1153019/',
        'info_dict': {
            'id': 'p1153019',
            'title': 'Lex Fridman Podcast',
        },
        'playlist_mincount': 200,
    }, {
        'url': 'https://tunein.com/podcasts/World-News/BBC-News-p14/',
        'info_dict': {
            'id': 'p14',
            'title': 'BBC News',
        },
        'playlist_mincount': 35,
    }]

    @classmethod
    def suitable(cls, url):
        return False if TuneInPodcastEpisodeIE.suitable(url) else super().suitable(url)

    def _fetch_page(self, url, podcast_id, page=0):
        items = self._call_api(
            podcast_id, 'contents', f'Downloading page {page + 1}', query={
                'filter': 't:free',
                'limit': self._PAGE_SIZE,
                'offset': page * self._PAGE_SIZE,
            },
        )['Items']

        for item in traverse_obj(items, (..., 'GuideId', {str}, filter)):
            yield self.url_result(update_url_query(url, {'topicId': item[1:]}))

    def _real_extract(self, url):
        podcast_id = self._match_id(url)

        return self.playlist_result(OnDemandPagedList(
            functools.partial(self._fetch_page, url, podcast_id), self._PAGE_SIZE),
            podcast_id, traverse_obj(self._call_api(podcast_id), ('Item', 'Title', {str})))


class TuneInPodcastEpisodeIE(TuneInBaseIE):
    IE_NAME = 'tunein:podcast'
    _VALID_URL = r'https?://tunein\.com/podcasts(?:/[^/?#]+){1,2}(?P<series_id>p\d+)/?\?(?:[^#]+&)?(?i:topicid)=(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://tunein.com/podcasts/Technology-Podcasts/Artificial-Intelligence-p1153019/?topicId=236404354',
        'info_dict': {
            'id': 't236404354',
            'ext': 'mp3',
            'title': '#351 – MrBeast: Future of YouTube, Twitter, TikTok, and Instagram',
            'alt_title': 'Technology Podcasts >',
            'cast': 'count:1',
            'description': 'md5:1029895354ef073ff00f20b82eb6eb71',
            'display_id': '236404354',
            'duration': 8330,
            'thumbnail': r're:https?://.+',
            'timestamp': 1673458571,
            'upload_date': '20230111',
            'series': 'Lex Fridman Podcast',
            'series_id': 'p1153019',
        },
    }, {
        'url': 'https://tunein.com/podcasts/The-BOB--TOM-Show-Free-Podcast-p20069/?topicId=174556405',
        'info_dict': {
            'id': 't174556405',
            'ext': 'mp3',
            'title': 'B&T Extra: Ohhh Yeah, It\'s Sexy Time',
            'alt_title': 'Westwood One >',
            'cast': 'count:2',
            'description': 'md5:6828234f410ab88c85655495c5fcfa88',
            'display_id': '174556405',
            'duration': 1203,
            'series': 'The BOB & TOM Show Free Podcast',
            'series_id': 'p20069',
            'thumbnail': r're:https?://.+',
            'timestamp': 1661799600,
            'upload_date': '20220829',
        },
    }]

    def _real_extract(self, url):
        series_id, display_id = self._match_valid_url(url).group('series_id', 'id')
        episode_id = f't{display_id}'
        formats, subtitles = self._extract_formats_and_subtitles(episode_id)

        return {
            'id': episode_id,
            'display_id': display_id,
            'formats': formats,
            'series': traverse_obj(self._call_api(series_id), ('Item', 'Title', {clean_html})),
            'series_id': series_id,
            'subtitles': subtitles,
            **traverse_obj(self._call_api(episode_id), ('Item', {
                'title': ('Title', {clean_html}),
                'alt_title': ('Subtitle', {clean_html}, filter),
                'cast': (
                    'Properties', 'ParentProgram', 'Hosts', {clean_html},
                    {lambda x: x.split(';')}, ..., {str.strip}, filter, all, filter),
                'description': ('Description', {clean_html}, filter),
                'duration': ('Actions', 'Play', 'Duration', {int_or_none}),
                'thumbnail': ('Image', {url_or_none}),
                'timestamp': ('Actions', 'Play', 'PublishTime', {parse_iso8601}),
            })),
        }


class TuneInEmbedIE(TuneInBaseIE):
    IE_NAME = 'tunein:embed'
    _VALID_URL = r'https?://tunein\.com/embed/player/(?P<id>[^/?#]+)'
    _EMBED_REGEX = [r'<iframe\b[^>]+\bsrc=["\'](?P<url>(?:https?:)?//tunein\.com/embed/player/[^/?#"\']+)']
    _TESTS = [{
        'url': 'https://tunein.com/embed/player/s6404/',
        'info_dict': {
            'id': 's6404',
            'ext': 'mp3',
            'title': str,
            'alt_title': 'South Africa\'s News and Information Leader',
            'channel_follower_count': int,
            'live_status': 'is_live',
            'location': 'Johannesburg, South Africa',
            'thumbnail': r're:https?://.+',
        },
        'params': {'skip_download': 'Livestream'},
    }, {
        'url': 'https://tunein.com/embed/player/t236404354/',
        'info_dict': {
            'id': 't236404354',
            'ext': 'mp3',
            'title': '#351 – MrBeast: Future of YouTube, Twitter, TikTok, and Instagram',
            'alt_title': 'Technology Podcasts >',
            'cast': 'count:1',
            'description': 'md5:1029895354ef073ff00f20b82eb6eb71',
            'display_id': '236404354',
            'duration': 8330,
            'series': 'Lex Fridman Podcast',
            'series_id': 'p1153019',
            'thumbnail': r're:https?://.+',
            'timestamp': 1673458571,
            'upload_date': '20230111',
        },
    }, {
        'url': 'https://tunein.com/embed/player/p191660/',
        'info_dict': {
            'id': 'p191660',
            'title': 'SBS Tamil',
        },
        'playlist_mincount': 195,
    }]
    _WEBPAGE_TESTS = [{
        'url': 'https://www.martiniinthemorning.com/',
        'info_dict': {
            'id': 's55412',
            'ext': 'mp3',
            'title': str,
            'alt_title': 'Now that\'s music!',
            'channel_follower_count': int,
            'description': 'md5:41588a3e2cf34b3eafc6c33522fa611a',
            'live_status': 'is_live',
            'location': 'US',
            'thumbnail': r're:https?://.+',
        },
        'params': {'skip_download': 'Livestream'},
    }]

    def _real_extract(self, url):
        embed_id = self._match_id(url)
        kind = {
            'p': 'program',
            's': 'station',
            't': 'topic',
        }.get(embed_id[:1])

        return self.url_result(
            f'https://tunein.com/{kind}/?{kind}id={embed_id[1:]}')


class TuneInShortenerIE(InfoExtractor):
    IE_NAME = 'tunein:shortener'
    IE_DESC = False  # Do not list
    _VALID_URL = r'https?://tun\.in/(?P<id>[^/?#]+)'
    _TESTS = [{
        'url': 'http://tun.in/ser7s',
        'info_dict': {
            'id': 's34682',
            'title': str,
            'ext': 'mp3',
            'alt_title': 'World Class Jazz',
            'channel_follower_count': int,
            'description': 'md5:d6d0b89063fd68d529fa7058ee98619b',
            'location': r're:Seattle-Tacoma, (?:US|WA)',
            'live_status': 'is_live',
            'thumbnail': r're:https?://.+',
        },
        'params': {'skip_download': 'Livestream'},
    }, {
        'url': 'http://tun.in/tqeeFw',
        'info_dict': {
            'id': 't236404354',
            'title': str,
            'ext': 'mp3',
            'alt_title': 'Technology Podcasts >',
            'cast': 'count:1',
            'description': 'md5:1029895354ef073ff00f20b82eb6eb71',
            'display_id': '236404354',
            'duration': 8330,
            'series': 'Lex Fridman Podcast',
            'series_id': 'p1153019',
            'thumbnail': r're:https?://.+',
            'timestamp': 1673458571,
            'upload_date': '20230111',
        },
        'params': {'skip_download': 'Livestream'},
    }, {
        'url': 'http://tun.in/pei6i',
        'info_dict': {
            'id': 'p14',
            'title': 'BBC News',
        },
        'playlist_mincount': 35,
    }]

    def _real_extract(self, url):
        redirect_id = self._match_id(url)
        # The server doesn't support HEAD requests
        urlh = self._request_webpage(url, redirect_id, 'Downloading redirect page')
        # Need to strip port from URL
        parsed = urllib.parse.urlparse(urlh.url)
        new_url = parsed._replace(netloc=parsed.hostname).geturl()
        # Prevent infinite loop in case redirect fails
        if self.suitable(new_url):
            raise UnsupportedError(new_url)
        return self.url_result(new_url)
