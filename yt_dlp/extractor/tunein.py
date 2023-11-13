import urllib.parse

from .common import InfoExtractor
from ..utils import (
    OnDemandPagedList,
    determine_ext,
    parse_iso8601,
    traverse_obj,
)


class TuneInBaseIE(InfoExtractor):
    _VALID_URL_BASE = r'https?://(?:www\.)?tunein\.com'

    def _extract_metadata(self, webpage, content_id):
        return self._search_json(r'window.INITIAL_STATE=', webpage, 'hydration', content_id, fatal=False)

    def _extract_formats_and_subtitles(self, content_id):
        streams = self._download_json(
            f'https://opml.radiotime.com/Tune.ashx?render=json&formats=mp3,aac,ogg,flash,hls&id={content_id}',
            content_id)['body']

        formats, subtitles = [], {}
        for stream in streams:
            if stream.get('media_type') == 'hls':
                fmts, subs = self._extract_m3u8_formats_and_subtitles(stream['url'], content_id, fatal=False)
                formats.extend(fmts)
                self._merge_subtitles(subs, target=subtitles)
            elif determine_ext(stream['url']) == 'pls':
                playlist_content = self._download_webpage(stream['url'], content_id)
                formats.append({
                    'url': self._search_regex(r'File1=(.*)', playlist_content, 'url', fatal=False),
                    'abr': stream.get('bitrate'),
                    'ext': stream.get('media_type'),
                })
            else:
                formats.append({
                    'url': stream['url'],
                    'abr': stream.get('bitrate'),
                    'ext': stream.get('media_type'),
                })

        return formats, subtitles


class TuneInStationIE(TuneInBaseIE):
    _VALID_URL = TuneInBaseIE._VALID_URL_BASE + r'(?:/radio/[^?#]+-|/embed/player/)(?P<id>s\d+)'
    _EMBED_REGEX = [r'<iframe[^>]+src=["\'](?P<url>(?:https?://)?tunein\.com/embed/player/s\d+)']

    _TESTS = [{
        'url': 'https://tunein.com/radio/Jazz24-885-s34682/',
        'info_dict': {
            'id': 's34682',
            'title': 're:^Jazz24',
            'description': 'md5:d6d0b89063fd68d529fa7058ee98619b',
            'thumbnail': 're:^https?://[^?&]+/s34682',
            'location': 'Seattle-Tacoma, US',
            'ext': 'mp3',
            'live_status': 'is_live',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'https://tunein.com/embed/player/s6404/',
        'only_matching': True,
    }, {
        'url': 'https://tunein.com/radio/BBC-Radio-1-988-s24939/',
        'info_dict': {
            'id': 's24939',
            'title': 're:^BBC Radio 1',
            'description': 'md5:f3f75f7423398d87119043c26e7bfb84',
            'thumbnail': 're:^https?://[^?&]+/s24939',
            'location': 'London, UK',
            'ext': 'mp3',
            'live_status': 'is_live',
        },
        'params': {
            'skip_download': True,
        },
    }]

    def _real_extract(self, url):
        station_id = self._match_id(url)

        webpage = self._download_webpage(url, station_id)
        metadata = self._extract_metadata(webpage, station_id)

        formats, subtitles = self._extract_formats_and_subtitles(station_id)
        return {
            'id': station_id,
            'title': traverse_obj(metadata, ('profiles', station_id, 'title')),
            'description': traverse_obj(metadata, ('profiles', station_id, 'description')),
            'thumbnail': traverse_obj(metadata, ('profiles', station_id, 'image')),
            'timestamp': parse_iso8601(
                traverse_obj(metadata, ('profiles', station_id, 'actions', 'play', 'publishTime'))),
            'location': traverse_obj(
                metadata, ('profiles', station_id, 'metadata', 'properties', 'location', 'displayName'),
                ('profiles', station_id, 'properties', 'location', 'displayName')),
            'formats': formats,
            'subtitles': subtitles,
            'is_live': traverse_obj(metadata, ('profiles', station_id, 'actions', 'play', 'isLive')),
        }


class TuneInPodcastIE(TuneInBaseIE):
    _VALID_URL = TuneInBaseIE._VALID_URL_BASE + r'/(?:podcasts/[^?#]+-|embed/player/)(?P<id>p\d+)/?(?:#|$)'
    _EMBED_REGEX = [r'<iframe[^>]+src=["\'](?P<url>(?:https?://)?tunein\.com/embed/player/p\d+)']

    _TESTS = [{
        'url': 'https://tunein.com/podcasts/Technology-Podcasts/Artificial-Intelligence-p1153019',
        'info_dict': {
            'id': 'p1153019',
            'title': 'Lex Fridman Podcast',
            'description': 'md5:bedc4e5f1c94f7dec6e4317b5654b00d',
        },
        'playlist_mincount': 200,
    }, {
        'url': 'https://tunein.com/embed/player/p191660/',
        'only_matching': True
    }, {
        'url': 'https://tunein.com/podcasts/World-News/BBC-News-p14/',
        'info_dict': {
            'id': 'p14',
            'title': 'BBC News',
            'description': 'md5:1218e575eeaff75f48ed978261fa2068',
        },
        'playlist_mincount': 200,
    }]

    _PAGE_SIZE = 30

    def _real_extract(self, url):
        podcast_id = self._match_id(url)

        webpage = self._download_webpage(url, podcast_id, fatal=False)
        metadata = self._extract_metadata(webpage, podcast_id)

        def page_func(page_num):
            api_response = self._download_json(
                f'https://api.tunein.com/profiles/{podcast_id}/contents', podcast_id,
                note=f'Downloading page {page_num + 1}', query={
                    'filter': 't:free',
                    'offset': page_num * self._PAGE_SIZE,
                    'limit': self._PAGE_SIZE,
                })

            return [
                self.url_result(
                    f'https://tunein.com/podcasts/{podcast_id}?topicId={episode["GuideId"][1:]}',
                    TuneInPodcastEpisodeIE, title=episode.get('Title'))
                for episode in api_response['Items']]

        entries = OnDemandPagedList(page_func, self._PAGE_SIZE)
        return self.playlist_result(
            entries, playlist_id=podcast_id, title=traverse_obj(metadata, ('profiles', podcast_id, 'title')),
            description=traverse_obj(metadata, ('profiles', podcast_id, 'description')))


class TuneInPodcastEpisodeIE(TuneInBaseIE):
    _VALID_URL = TuneInBaseIE._VALID_URL_BASE + r'/podcasts/(?:[^?&]+-)?(?P<podcast_id>p\d+)/?\?topicId=(?P<id>\w\d+)'

    _TESTS = [{
        'url': 'https://tunein.com/podcasts/Technology-Podcasts/Artificial-Intelligence-p1153019/?topicId=236404354',
        'info_dict': {
            'id': 't236404354',
            'title': '#351 \u2013 MrBeast: Future of YouTube, Twitter, TikTok, and Instagram',
            'description': 'md5:e1734db6f525e472c0c290d124a2ad77',
            'thumbnail': 're:^https?://[^?&]+/p1153019',
            'timestamp': 1673458571,
            'upload_date': '20230111',
            'series_id': 'p1153019',
            'series': 'Lex Fridman Podcast',
            'ext': 'mp3',
        },
    }]

    def _real_extract(self, url):
        podcast_id, episode_id = self._match_valid_url(url).group('podcast_id', 'id')
        episode_id = f't{episode_id}'

        webpage = self._download_webpage(url, episode_id)
        metadata = self._extract_metadata(webpage, episode_id)

        formats, subtitles = self._extract_formats_and_subtitles(episode_id)
        return {
            'id': episode_id,
            'title': traverse_obj(metadata, ('profiles', episode_id, 'title')),
            'description': traverse_obj(metadata, ('profiles', episode_id, 'description')),
            'thumbnail': traverse_obj(metadata, ('profiles', episode_id, 'image')),
            'timestamp': parse_iso8601(
                traverse_obj(metadata, ('profiles', episode_id, 'actions', 'play', 'publishTime'))),
            'series_id': podcast_id,
            'series': traverse_obj(metadata, ('profiles', podcast_id, 'title')),
            'formats': formats,
            'subtitles': subtitles,
        }


class TuneInShortenerIE(InfoExtractor):
    IE_NAME = 'tunein:shortener'
    IE_DESC = False  # Do not list
    _VALID_URL = r'https?://tun\.in/(?P<id>[A-Za-z0-9]+)'

    _TEST = {
        # test redirection
        'url': 'http://tun.in/ser7s',
        'info_dict': {
            'id': 's34682',
            'title': 're:^Jazz24',
            'description': 'md5:d6d0b89063fd68d529fa7058ee98619b',
            'thumbnail': 're:^https?://[^?&]+/s34682',
            'location': 'Seattle-Tacoma, US',
            'ext': 'mp3',
            'live_status': 'is_live',
        },
        'params': {
            'skip_download': True,  # live stream
        },
    }

    def _real_extract(self, url):
        redirect_id = self._match_id(url)
        # The server doesn't support HEAD requests
        urlh = self._request_webpage(
            url, redirect_id, note='Downloading redirect page')

        url = urlh.url
        url_parsed = urllib.parse.urlparse(url)
        if url_parsed.port == 443:
            url = url_parsed._replace(netloc=url_parsed.hostname).url

        self.to_screen('Following redirect: %s' % url)
        return self.url_result(url)
