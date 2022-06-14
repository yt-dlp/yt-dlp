import json
import math
import time
from copy import deepcopy

from ..compat import functools, re
from .common import InfoExtractor
from .turner import TurnerBaseIE
from ..utils import (
    determine_ext,
    float_or_none,
    int_or_none,
    mimetype2ext,
    parse_age_limit,
    parse_iso8601,
    strip_or_none,
    timetuple_from_msec,
    traverse_obj,
    try_get,
)
from ..downloader.hls import HlsFD


class AdultSwimVideoIE(TurnerBaseIE):
    IE_NAME = 'adultswim:video'
    _VALID_URL = r'https?://(?:www\.)?adultswim\.com/videos/(?P<show_path>[^/?#]+)(?:/(?P<episode_path>[^/?#]+))?'

    _TESTS = [{
        'url': 'http://adultswim.com/videos/rick-and-morty/pilot',
        'info_dict': {
            'id': 'rQxZvXQ4ROaSOqq-or2Mow',
            'ext': 'mp4',
            'title': 'Rick and Morty - Pilot',
            'description': 'Rick moves in with his daughter\'s family and establishes himself as a bad influence on his grandson, Morty.',
            'timestamp': 1543294800,
            'upload_date': '20181127',
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
        'expected_warnings': ['Unable to download f4m manifest'],
    }, {
        'url': 'http://www.adultswim.com/videos/tim-and-eric-awesome-show-great-job/dr-steve-brule-for-your-wine/',
        'info_dict': {
            'id': 'sY3cMUR_TbuE4YmdjzbIcQ',
            'ext': 'mp4',
            'title': 'Tim and Eric Awesome Show Great Job! - Dr. Steve Brule, For Your Wine',
            'description': 'Dr. Brule reports live from Wine Country with a special report on wines.  \nWatch Tim and Eric Awesome Show Great Job! episode #20, "Embarrassed" on Adult Swim.',
            'upload_date': '20080124',
            'timestamp': 1201150800,
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
        'skip': '404 Not Found',
    }, {
        'url': 'http://www.adultswim.com/videos/decker/inside-decker-a-new-hero/',
        'info_dict': {
            'id': 'I0LQFQkaSUaFp8PnAWHhoQ',
            'ext': 'mp4',
            'title': 'Decker - Inside Decker: A New Hero',
            'description': 'The guys recap the conclusion of the season. They announce a new hero, take a peek into the Victorville Film Archive and welcome back the talented James Dean.',
            'timestamp': 1469480460,
            'upload_date': '20160725',
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
        'expected_warnings': ['Unable to download f4m manifest'],
    }, {
        'url': 'http://www.adultswim.com/videos/attack-on-titan',
        'info_dict': {
            'id': 'attack-on-titan',
            'title': 'Attack on Titan',
            'description': 'md5:41caa9416906d90711e31dc00cb7db7e',
        },
        'playlist_mincount': 12,
    }, {
        'url': 'http://www.adultswim.com/videos/streams/williams-stream',
        'info_dict': {
            'id': 'd8DEBj7QRfetLsRgFnGEyg',
            'ext': 'mp4',
            'title': r're:^Williams Stream \d{4}-\d{2}-\d{2} \d{2}:\d{2}$',
            'description': 'original programming',
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
        'skip': '404 Not Found',
    }]

    def _real_extract(self, url):
        show_path, episode_path = self._match_valid_url(url).groups()
        display_id = episode_path or show_path
        query = '''query {
  getShowBySlug(slug:"%s") {
    %%s
  }
}''' % show_path
        if episode_path:
            query = query % '''title
    getVideoBySlug(slug:"%s") {
      _id
      auth
      description
      duration
      episodeNumber
      launchDate
      mediaID
      seasonNumber
      poster
      title
      tvRating
    }''' % episode_path
            ['getVideoBySlug']
        else:
            query = query % '''metaDescription
    title
    videos(first:1000,sort:["episode_number"]) {
      edges {
        node {
           _id
           slug
        }
      }
    }'''
        show_data = self._download_json(
            'https://www.adultswim.com/api/search', display_id,
            data=json.dumps({'query': query}).encode(),
            headers={'Content-Type': 'application/json'})['data']['getShowBySlug']
        if episode_path:
            video_data = show_data['getVideoBySlug']
            video_id = video_data['_id']
            episode_title = title = video_data['title']
            series = show_data.get('title')
            if series:
                title = '%s - %s' % (series, title)
            info = {
                'id': video_id,
                'title': title,
                'description': strip_or_none(video_data.get('description')),
                'duration': float_or_none(video_data.get('duration')),
                'formats': [],
                'subtitles': {},
                'age_limit': parse_age_limit(video_data.get('tvRating')),
                'thumbnail': video_data.get('poster'),
                'timestamp': parse_iso8601(video_data.get('launchDate')),
                'series': series,
                'season_number': int_or_none(video_data.get('seasonNumber')),
                'episode': episode_title,
                'episode_number': int_or_none(video_data.get('episodeNumber')),
            }

            auth = video_data.get('auth')
            media_id = video_data.get('mediaID')
            if media_id:
                info.update(self._extract_ngtv_info(media_id, {
                    # CDN_TOKEN_APP_ID from:
                    # https://d2gg02c3xr550i.cloudfront.net/assets/asvp.e9c8bef24322d060ef87.bundle.js
                    'appId': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhcHBJZCI6ImFzLXR2ZS1kZXNrdG9wLXB0enQ2bSIsInByb2R1Y3QiOiJ0dmUiLCJuZXR3b3JrIjoiYXMiLCJwbGF0Zm9ybSI6ImRlc2t0b3AiLCJpYXQiOjE1MzI3MDIyNzl9.BzSCk-WYOZ2GMCIaeVb8zWnzhlgnXuJTCu0jGp_VaZE',
                }, {
                    'url': url,
                    'site_name': 'AdultSwim',
                    'auth_required': auth,
                }))

            if not auth:
                extract_data = self._download_json(
                    'https://www.adultswim.com/api/shows/v1/videos/' + video_id,
                    video_id, query={'fields': 'stream'}, fatal=False) or {}
                assets = try_get(extract_data, lambda x: x['data']['video']['stream']['assets'], list) or []
                for asset in assets:
                    asset_url = asset.get('url')
                    if not asset_url:
                        continue
                    ext = determine_ext(asset_url, mimetype2ext(asset.get('mime_type')))
                    if ext == 'm3u8':
                        info['formats'].extend(self._extract_m3u8_formats(
                            asset_url, video_id, 'mp4', m3u8_id='hls', fatal=False))
                    elif ext == 'f4m':
                        continue
                        # info['formats'].extend(self._extract_f4m_formats(
                        #     asset_url, video_id, f4m_id='hds', fatal=False))
                    elif ext in ('scc', 'ttml', 'vtt'):
                        info['subtitles'].setdefault('en', []).append({
                            'url': asset_url,
                        })
            self._sort_formats(info['formats'])

            return info
        else:
            entries = []
            for edge in show_data.get('videos', {}).get('edges', []):
                video = edge.get('node') or {}
                slug = video.get('slug')
                if not slug:
                    continue
                entries.append(self.url_result(
                    'http://adultswim.com/videos/%s/%s' % (show_path, slug),
                    'AdultSwim', video.get('_id')))
            return self.playlist_result(
                entries, show_path, show_data.get('title'),
                strip_or_none(show_data.get('metaDescription')))


class AdultSwimStreamIE(InfoExtractor):
    IE_NAME = 'adultswim:stream'
    _VALID_URL = r'https?://(?:www\.)?adultswim\.com/streams/(?P<id>[^/?#]+)'

    _TESTS = [{
        'url': 'https://www.adultswim.com/streams/rick-and-morty',
        'info_dict': {
            'id': 'rick-and-morty',
            'title': 'Rick and Morty',
            'description': 'An infinite loop of Rick and Morty. You\'re welcome. (Marathon available in select regions)',
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
        'playlist_mincount': 40,
    }]

    def _live_hls_fragments(self, episode_start_time, episode_duration, video_id, hls_url, content):
        FRAGMENT_DURATION = 10.010

        sleep_until = episode_start_time + min(60, episode_duration)
        if time.time() - sleep_until < 0:
            format_dur = lambda dur: '%02d:%02d:%02d' % timetuple_from_msec(dur * 1000)[:-1]
            last_msg = ''

            def progress(msg):
                nonlocal last_msg
                self.to_screen(msg + ' ' * (len(last_msg) - len(msg)) + '\r', skip_eol=True)
                last_msg = msg

            while time.time() <= sleep_until:
                progress('Waiting for next episode to air (%s) - Press Ctrl+C to cancel' % format_dur(sleep_until - time.time()))
                time.sleep(1)
            progress('')

            content = self._download_webpage(hls_url, video_id, note='Downloading m3u8 manifest')
        elif time.time() - sleep_until > episode_duration:
            self.report_warning('Skipping episode as new episode has already aired')
            return []

        fragments, error_msg = HlsFD._parse_m3u8(content, {'url': hls_url})
        if not fragments:
            self.report_warning(error_msg)
            return []

        for f in reversed(fragments):
            match = re.search(r'^https?:\/\/adultswim-vodlive.cdn.turner.com\/.*\/seg[^_]+_(?P<index>\d+)\.ts$', f['url'])
            if match:
                fragment_template = f
                break
        else:
            self.report_warning('Could not find any valid stream segments')
            return []

        digit_str_index, digit_str_length = match.span('index')[0], len(match.group('index'))
        fragment_url_template = fragment_template['url'][:digit_str_index] + '%s' + fragment_template['url'][digit_str_index + digit_str_length:]
        fragment_count = math.ceil(episode_duration / FRAGMENT_DURATION)
        for i in reversed(range(fragment_count)):
            try:
                self._downloader.urlopen(fragment_url_template % '{0:0{width}}'.format(i, width=digit_str_length))
                break
            except Exception:
                fragment_count -= 1

        return [{'frag_index': i,
                 'url': fragment_url_template % '{0:0{width}}'.format(i, width=digit_str_length),
                 'decrypt_info': fragment_template['decrypt_info'],
                 'byte_range': fragment_template['byte_range'],
                 'media_sequence': fragment_template['media_sequence']} for i in range(fragment_count)]

    def _real_extract(self, url):
        stream_id = self._match_id(url)

        webpage = self._download_webpage(url, stream_id)
        stream_data_json = self._search_regex(r'<script[^>]+id=["\']__NEXT_DATA__["\'][^>]*>(?P<json>[^<]+)', webpage, 'stream data json', group='json')

        remote_ts_json = self._download_json('https://www.adultswim.com/api/schedule/live/', stream_id, note=False, fatal=False)
        timestamp = remote_ts_json.get("timestamp") or time.time() * 1e3

        if stream_data_json:

            stream_data = self._parse_json(stream_data_json, stream_id, fatal=False)

            if stream_data:
                if not stream_id:
                    stream_id = traverse_obj(stream_data, ('query', 'stream'))

                root = traverse_obj(stream_data, ('props', '__REDUX_STATE__')) or {}
                stream = {}

                for s in root.get('streams') or []:
                    if s.get('id') == stream_id:
                        stream = s
                        break

                series = stream.get('title')
                description = stream.get('description')

                vod_to_live_id = stream.get('vod_to_live_id')
                episodes_data = traverse_obj(root, ('marathon', vod_to_live_id))

                if not episodes_data:
                    marathon = root.get('marathon')
                    if type(marathon) == dict and len(marathon.values()) > 0:
                        episodes_data = list(marathon.values())[0]

                for i, e in enumerate(episodes_data):
                    start_time = e.get('startTime')
                    if start_time <= timestamp:
                        episodes_data = episodes_data[i:]
                        break

                for i in range(1, len(episodes_data)):
                    if episodes_data[0].get('episodeName') == episodes_data[i].get('episodeName'):
                        episodes_data = episodes_data[:i]
                        break

        formats = self._extract_m3u8_formats(
            'https://adultswim-vodlive.cdn.turner.com/live/%s/stream_de.m3u8?hdnts=' % stream_id, stream_id)
        self._sort_formats(formats)

        for f in formats:
            f['protocol'] = 'm3u8_native_generator'

        def entries():
            for episode_data in episodes_data:
                title = episode_data.get('episodeName')
                duration = episode_data.get('duration')
                season_number = episode_data.get('seasonNumber')
                episode_number = episode_data.get('episodeNumber')

                _formats = deepcopy(formats)
                for f in _formats:
                    f['fragments'] = functools.partial(
                        self._live_hls_fragments, episode_data.get('startTime') / 1e3, duration, f.get('id'), f.get('url'))

                yield {
                    'id': f'{season_number}-{episode_number}',
                    'title': f'{series} S{season_number} EP{episode_number} {title}',
                    'duration': duration,
                    'series': series,
                    'episode': title,
                    'season_number': season_number,
                    'episode_number': episode_number,
                    'formats': _formats,
                }

        return self.playlist_result(entries(), stream_id, series, description, multi_video=True)
