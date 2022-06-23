import json
from tarfile import ExtractError
import time
import functools
import re
import copy

from .common import InfoExtractor
from .turner import TurnerBaseIE
from ..utils import (
    HEADRequest,
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
from ..downloader.hls import HlsFD


class AdultSwimIE(TurnerBaseIE):
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
            'id': r're:^rick-and-morty-[1-4]-\d{1,2}$',
            'ext': 'mp4',
            'title': r're:^Rick and Morty S[1-4] EP\d{1,2} .+$',
            'description': 'An infinite loop of Rick and Morty. You\'re welcome. (Marathon available in select regions)',
            'series': 'Rick and Morty',
            # Live episode changes periodically
            'season': str,
            'episode': str,
            'season_number': int,
            'episode_number': int,
            'duration': float,
        },
        # 'params': {
        #     'skip_download': True,
        # },
    }]

    def _live_hls_fragments(self, episode_start_time, episode_duration, video_id, hls_url, hls_content):
        FRAGMENT_DURATION = 10.010

        timestamp = time.time()
        if timestamp < episode_start_time:
            raise ExtractError('Episode has not aired yet')
        if timestamp > episode_start_time + episode_duration:
            raise ExtractError('Skipping episode as new episode has already aired')

        fragments, error_msg = HlsFD._parse_m3u8(hls_content, {'url': hls_url})
        if not fragments:
            raise ExtractError(error_msg)

        for f in reversed(fragments):
            match = re.search(r'^https?:\/\/adultswim-vodlive.cdn.turner.com\/.*\/seg[^_]+_(?P<index>\d+)\.ts$', f['url'])
            if match:
                fragment_template = f
                break
        else:
            raise ExtractError('Could not find any valid stream segments')

        digit_str_index, digit_str_length = match.span('index')[0], len(match.group('index'))
        fragment_url_template = fragment_template['url'][:digit_str_index] + '%s' + fragment_template['url'][digit_str_index + digit_str_length:]
        fragment_count = int(episode_duration // FRAGMENT_DURATION) + 1

        for i in reversed(range(fragment_count)):
            if self._request_webpage(HEADRequest(fragment_url_template % f'{i:0{digit_str_length}}'),
                                     video_id, note=f'Determining availability of segments (count: {fragment_count})',
                                     errnote=False):
                break
            fragment_count = i

        for i in range(fragment_count):
            yield {'frag_index': i,
                   'url': fragment_url_template % f'{i:0{digit_str_length}}',
                   'decrypt_info': fragment_template['decrypt_info'],
                   'byte_range': fragment_template['byte_range'],
                   'media_sequence': fragment_template['media_sequence']}

    def _get_stream_data(self, url, stream_id):
        webpage = self._download_webpage(url, stream_id)
        stream_data = self._search_nextjs_data(webpage, stream_id)
        timestamp = time.time()

        def get_episodes(root, stream):
            first_episode_name = None
            for e in traverse_obj(root, (
                    'marathon', (stream.get('vod_to_live_id'), ...)), get_all=False) or []:
                if e['startTime'] / 1000 + e['duration'] < timestamp:
                    continue
                if first_episode_name is None:
                    first_episode_name = e['episodeName']
                elif e['episodeName'] == first_episode_name:
                    break
                yield e

        root = traverse_obj(stream_data, ('props', '__REDUX_STATE__')) or {}
        stream = traverse_obj(root.get('streams'), (lambda _, v: v['id'] == stream_id), get_all=False) or {}
        return stream, list(get_episodes(root, stream))

    def _real_extract(self, url):
        stream_id = self._match_id(url)

        stream, episodes = self._get_stream_data(url, stream_id)
        if len(episodes) == 0:
            raise ExtractError('No episodes found')

        formats = self._extract_m3u8_formats(
            f'https://adultswim-vodlive.cdn.turner.com/live/{stream_id}/stream_de.m3u8?hdnts=', stream_id)
        self._sort_formats(formats)

        def invalid_episode(episode):
            return type(episode.get('seasonNumber')) != int or type(episode.get('episodeNumber')) != int

        def update_episodes():
            _, new_episodes = self._get_stream_data(url, stream_id)
            for ep in episodes:
                for n_ep in new_episodes:
                    if ep['episodeName'] == n_ep['episodeName'] and invalid_episode(ep):
                        ep.update(n_ep)
                        break

        def get_episode_entry(idx, show_not_aired_message=False):
            entry = {}
            episode = episodes[idx]

            release_timestamp = episode['startTime'] / 1000 + min(60, episode['duration'] / 2)
            if release_timestamp <= time.time():
                if invalid_episode(episode):
                    update_episodes()
                    episode = episodes[idx]

                _formats = copy.deepcopy(formats)
                for f in _formats:
                    f['protocol'] = 'm3u8_native_generator'
                    f['fragments'] = functools.partial(
                        self._live_hls_fragments, episode['startTime'] / 1000, episode['duration'], stream_id, f['url'])
                entry['formats'] = _formats
            else:
                if show_not_aired_message:
                    self.to_screen('Episode "%s" has not aired yet' % episode.get('episodeName'))
                entry['release_timestamp'] = release_timestamp
                entry['reextractor'] = functools.partial(get_episode_entry, idx, True)

            return {
                **entry,
                'id': '%s-%s-%s' % (stream_id, episode.get('seasonNumber'), episode.get('episodeNumber')),
                'title': '%s S%s EP%s %s' % (stream.get('title'), episode.get('seasonNumber'), episode.get('episodeNumber'), episode.get('episodeName')),
                'duration': episode.get('duration'),
                'series': stream.get('title'),
                'episode': episode.get('episodeName'),
                'season_number': episode.get('seasonNumber'),
                'episode_number': episode.get('episodeNumber'),
            }

        can_download_playlist = False
        no_playlist_reason = 'Downloading only currently live %s episode' % stream.get('title', stream_id)
        if self.get_param('noplaylist'):
            no_playlist_reason += ' because of --no-playlist'
        elif not self.get_param('wait_for_video'):
            no_playlist_reason += ' because --wait-for-video 0 is not set'
        else:
            can_download_playlist = True

        if can_download_playlist:
            self.to_screen('Downloading all %s episodes; add --no-playlist to only download currently live episode' % stream.get('title', stream_id))
            entries = [get_episode_entry(idx) for idx in range(len(episodes))]

            return self.playlist_result(entries, stream_id, stream.get('title'),
                                        stream.get('description'), multi_video=True)
        else:
            self.to_screen(no_playlist_reason)
            entry = get_episode_entry(0)
            return {
                **entry,
                'description': stream.get('description'),
            }
