import json
import time
from turtle import width

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
    traverse_obj,
    try_get,
)


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
            'ext': 'mp4',
            'title': 'Rick and Morty',
            'description': 'An infinite loop of Rick and Morty. You\'re welcome. (Marathon available in select regions)',
            'series': 'Rick and Morty',
            # Live episode changes periodically
            'season': str,
            'episode': str,
            'season_number': int,
            'episode_number': int,
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
    }]

    def _fragment_url_builder(self, episode_start_time, m3u8_feed):
        '''Returns function that translates a fragment index to its valid url path'''

        match = re.search(r'^https?:\/\/adultswim-vodlive.cdn.turner.com\/.*\/seg[^_]+_(?P<digit>\d+)\.ts$', m3u8_feed, re.MULTILINE)
        if not match:
            return None
        if not match.group('digit'):
            return None
        
        digit_str_length = len(match.group('digit'))
        digit_str_index = match.span('digit')[0] - match.group(0)[0]
        if digit_str_index + digit_str_length > len(fragment_url_template):
            return None
        fragment_url_template = match.group(0)[:digit_str_index] + '%s' + match.group(0)[:digit_str_index+digit_str_length]

        def _url_builder(fragment_url_template, digit_str_length, fragment_index):
            return fragment_url_template % '{0:0{width}}'.format(fragment_index, width=digit_str_length)

        return functools.partial(_url_builder, fragment_url_template, digit_str_length)

    def _live_m3u8_fragments(self, episode_start_time, episode_duration, m3u8_feed, ctx):
        FRAGMENT_DURATION = 10.0100
        fragment_url = self._fragment_url_builder(episode_start_time, m3u8_feed)

        

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

                title = stream.get('title')
                description = stream.get('description')

                vod_to_live_id = stream.get('vod_to_live_id')
                episodes_data = traverse_obj(root, ('marathon', vod_to_live_id))

                if not episodes_data:
                    marathon = root.get('marathon')
                    if type(marathon) != dict:
                        pass
                    elif len(marathon.values()) > 0:
                        episodes_data = list(marathon.values())[0]

                live_episode_data = {}

                start_time = None
                for e in episodes_data:
                    start_time = start_time or e.get('startTime')
                    duration = e.get('duration') * 1e3

                    if start_time < timestamp and timestamp < start_time + duration:
                        live_episode_data = e
                        break

                    # If currently in an in-between episode pause live episode is considered the one after that pause
                    s = e.get('startTime')
                    if s:
                        start_time = s + duration
                    else:
                        start_time = None

                episode = live_episode_data.get('episodeName')
                episode_number = live_episode_data.get('episodeNumber')
                season_number = live_episode_data.get('seasonNumber')

        formats = self._extract_m3u8_formats(
            'https://adultswim-vodlive.cdn.turner.com/live/%s/stream_de.m3u8?hdnts=' % stream_id, stream_id)
        self._sort_formats(formats)

        info = {
            'id': stream_id,
            'title': title,
            'description': description,
            'series': title,
            'episode': episode,
            'season_number': season_number,
            'episode_number': episode_number,
            'formats': formats,
        }

        print(formats)

        return info
