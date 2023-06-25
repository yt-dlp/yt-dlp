import hashlib
import hmac
import json
import re
import time
import uuid

from .common import InfoExtractor
from ..compat import compat_HTTPError, compat_str
from ..utils import (
    ExtractorError,
    determine_ext,
    int_or_none,
    join_nonempty,
    str_or_none,
    traverse_obj,
    url_or_none,
)


class HotStarBaseIE(InfoExtractor):
    _BASE_URL = 'https://www.hotstar.com'
    _API_URL = 'https://api.hotstar.com'
    _AKAMAI_ENCRYPTION_KEY = b'\x05\xfc\x1a\x01\xca\xc9\x4b\xc4\x12\xfc\x53\x12\x07\x75\xf9\xee'

    def _call_api_v1(self, path, *args, **kwargs):
        return self._download_json(
            f'{self._API_URL}/o/v1/{path}', *args, **kwargs,
            headers={'x-country-code': 'IN', 'x-platform-code': 'PCTV'})

    def _call_api_impl(self, path, video_id, query, st=None, cookies=None):
        st = int_or_none(st) or int(time.time())
        exp = st + 6000
        auth = 'st=%d~exp=%d~acl=/*' % (st, exp)
        auth += '~hmac=' + hmac.new(self._AKAMAI_ENCRYPTION_KEY, auth.encode(), hashlib.sha256).hexdigest()

        if cookies and cookies.get('userUP'):
            token = cookies.get('userUP').value
        else:
            token = self._download_json(
                f'{self._API_URL}/um/v3/users',
                video_id, note='Downloading token',
                data=json.dumps({"device_ids": [{"id": compat_str(uuid.uuid4()), "type": "device_id"}]}).encode('utf-8'),
                headers={
                    'hotstarauth': auth,
                    'x-hs-platform': 'PCTV',  # or 'web'
                    'Content-Type': 'application/json',
                })['user_identity']

        response = self._download_json(
            f'{self._API_URL}/{path}', video_id, query=query,
            headers={
                'hotstarauth': auth,
                'x-hs-appversion': '6.72.2',
                'x-hs-platform': 'web',
                'x-hs-usertoken': token,
            })

        if response['message'] != "Playback URL's fetched successfully":
            raise ExtractorError(
                response['message'], expected=True)
        return response['data']

    def _call_api_v2(self, path, video_id, st=None, cookies=None):
        return self._call_api_impl(
            f'{path}/content/{video_id}', video_id, st=st, cookies=cookies, query={
                'desired-config': 'audio_channel:stereo|container:fmp4|dynamic_range:hdr|encryption:plain|ladder:tv|package:dash|resolution:fhd|subs-tag:HotstarVIP|video_codec:h265',
                'device-id': cookies.get('device_id').value if cookies.get('device_id') else compat_str(uuid.uuid4()),
                'os-name': 'Windows',
                'os-version': '10',
            })

    def _playlist_entries(self, path, item_id, root=None, **kwargs):
        results = self._call_api_v1(path, item_id, **kwargs)['body']['results']
        for video in traverse_obj(results, (('assets', None), 'items', ...)):
            if video.get('contentId'):
                yield self.url_result(
                    HotStarIE._video_url(video['contentId'], root=root), HotStarIE, video['contentId'])


class HotStarIE(HotStarBaseIE):
    IE_NAME = 'hotstar'
    _VALID_URL = r'''(?x)
        https?://(?:www\.)?hotstar\.com(?:/in)?/(?!in/)
        (?:
            (?P<type>movies|sports|episode|(?P<tv>tv|shows))/
            (?(tv)(?:[^/?#]+/){2}|[^?#]*)
        )?
        [^/?#]+/
        (?P<id>\d{10})
    '''

    _TESTS = [{
        'url': 'https://www.hotstar.com/can-you-not-spread-rumours/1000076273',
        'info_dict': {
            'id': '1000076273',
            'ext': 'mp4',
            'title': 'Can You Not Spread Rumours?',
            'description': 'md5:c957d8868e9bc793ccb813691cc4c434',
            'timestamp': 1447248600,
            'upload_date': '20151111',
            'duration': 381,
            'episode': 'Can You Not Spread Rumours?',
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://www.hotstar.com/tv/ek-bhram-sarvagun-sampanna/s-2116/janhvi-targets-suman/1000234847',
        'info_dict': {
            'id': '1000234847',
            'ext': 'mp4',
            'title': 'Janhvi Targets Suman',
            'description': 'md5:78a85509348910bd1ca31be898c5796b',
            'timestamp': 1556670600,
            'upload_date': '20190501',
            'duration': 1219,
            'channel': 'StarPlus',
            'channel_id': 3,
            'series': 'Ek Bhram - Sarvagun Sampanna',
            'season': 'Chapter 1',
            'season_number': 1,
            'season_id': 6771,
            'episode': 'Janhvi Targets Suman',
            'episode_number': 8,
        }
    }, {
        'url': 'https://www.hotstar.com/in/shows/anupama/1260022017/anupama-anuj-share-a-moment/1000282843',
        'info_dict': {
            'id': '1000282843',
            'ext': 'mp4',
            'title': 'Anupama, Anuj Share a Moment',
            'season': 'Chapter 1',
            'description': 'md5:8d74ed2248423b8b06d5c8add4d7a0c0',
            'timestamp': 1678149000,
            'channel': 'StarPlus',
            'series': 'Anupama',
            'season_number': 1,
            'season_id': 7399,
            'upload_date': '20230307',
            'episode': 'Anupama, Anuj Share a Moment',
            'episode_number': 853,
            'duration': 1272,
            'channel_id': 3,
        },
    }, {
        'url': 'https://www.hotstar.com/movies/radha-gopalam/1000057157',
        'only_matching': True,
    }, {
        'url': 'https://www.hotstar.com/in/sports/cricket/follow-the-blues-2021/recap-eng-fight-back-on-day-2/1260066104',
        'only_matching': True,
    }, {
        'url': 'https://www.hotstar.com/in/sports/football/most-costly-pl-transfers-ft-grealish/1260065956',
        'only_matching': True,
    }]
    _GEO_BYPASS = False

    _TYPE = {
        'movies': 'movie',
        'sports': 'match',
        'episode': 'episode',
        'tv': 'episode',
        'shows': 'episode',
        None: 'content',
    }

    _IGNORE_MAP = {
        'res': 'resolution',
        'vcodec': 'video_codec',
        'dr': 'dynamic_range',
    }

    _TAG_FIELDS = {
        'language': 'language',
        'acodec': 'audio_codec',
        'vcodec': 'video_codec',
    }

    @classmethod
    def _video_url(cls, video_id, video_type=None, *, slug='ignore_me', root=None):
        assert None in (video_type, root)
        if not root:
            root = join_nonempty(cls._BASE_URL, video_type, delim='/')
        return f'{root}/{slug}/{video_id}'

    def _real_extract(self, url):
        video_id, video_type = self._match_valid_url(url).group('id', 'type')
        video_type = self._TYPE.get(video_type, video_type)
        cookies = self._get_cookies(url)  # Cookies before any request

        video_data = self._call_api_v1(f'{video_type}/detail', video_id,
                                       query={'tas': 10000, 'contentId': video_id})['body']['results']['item']
        if not self.get_param('allow_unplayable_formats') and video_data.get('drmProtected'):
            self.report_drm(video_id)

        # See https://github.com/yt-dlp/yt-dlp/issues/396
        st = self._download_webpage_handle(f'{self._BASE_URL}/in', video_id)[1].headers.get('x-origin-date')

        geo_restricted = False
        formats, subs = [], {}
        headers = {'Referer': f'{self._BASE_URL}/in'}

        # change to v2 in the future
        playback_sets = self._call_api_v2('play/v1/playback', video_id, st=st, cookies=cookies)['playBackSets']
        for playback_set in playback_sets:
            if not isinstance(playback_set, dict):
                continue
            tags = str_or_none(playback_set.get('tagsCombination')) or ''
            if any(f'{prefix}:{ignore}' in tags
                   for key, prefix in self._IGNORE_MAP.items()
                   for ignore in self._configuration_arg(key)):
                continue
            tag_dict = dict((t.split(':', 1) + [None])[:2] for t in tags.split(';'))

            format_url = url_or_none(playback_set.get('playbackUrl'))
            if not format_url:
                continue
            format_url = re.sub(r'(?<=//staragvod)(\d)', r'web\1', format_url)
            ext = determine_ext(format_url)

            current_formats, current_subs = [], {}
            try:
                if 'package:hls' in tags or ext == 'm3u8':
                    current_formats, current_subs = self._extract_m3u8_formats_and_subtitles(
                        format_url, video_id, ext='mp4', headers=headers)
                elif 'package:dash' in tags or ext == 'mpd':
                    current_formats, current_subs = self._extract_mpd_formats_and_subtitles(
                        format_url, video_id, headers=headers)
                elif ext == 'f4m':
                    pass  # XXX: produce broken files
                else:
                    current_formats = [{
                        'url': format_url,
                        'width': int_or_none(playback_set.get('width')),
                        'height': int_or_none(playback_set.get('height')),
                    }]
            except ExtractorError as e:
                if isinstance(e.cause, compat_HTTPError) and e.cause.code == 403:
                    geo_restricted = True
                continue

            if tag_dict.get('encryption') not in ('plain', None):
                for f in current_formats:
                    f['has_drm'] = True
            for f in current_formats:
                for k, v in self._TAG_FIELDS.items():
                    if not f.get(k):
                        f[k] = tag_dict.get(v)
                if f.get('vcodec') != 'none' and not f.get('dynamic_range'):
                    f['dynamic_range'] = tag_dict.get('dynamic_range')
                if f.get('acodec') != 'none' and not f.get('audio_channels'):
                    f['audio_channels'] = {
                        'stereo': 2,
                        'dolby51': 6,
                    }.get(tag_dict.get('audio_channel'))
                f['format_note'] = join_nonempty(
                    tag_dict.get('ladder'),
                    tag_dict.get('audio_channel') if f.get('acodec') != 'none' else None,
                    f.get('format_note'),
                    delim=', ')

            formats.extend(current_formats)
            subs = self._merge_subtitles(subs, current_subs)

        if not formats and geo_restricted:
            self.raise_geo_restricted(countries=['IN'], metadata_available=True)
        self._remove_duplicate_formats(formats)
        for f in formats:
            f.setdefault('http_headers', {}).update(headers)

        return {
            'id': video_id,
            'title': video_data.get('title'),
            'description': video_data.get('description'),
            'duration': int_or_none(video_data.get('duration')),
            'timestamp': int_or_none(traverse_obj(video_data, 'broadcastDate', 'startDate')),
            'formats': formats,
            'subtitles': subs,
            'channel': video_data.get('channelName'),
            'channel_id': video_data.get('channelId'),
            'series': video_data.get('showName'),
            'season': video_data.get('seasonName'),
            'season_number': int_or_none(video_data.get('seasonNo')),
            'season_id': video_data.get('seasonId'),
            'episode': video_data.get('title'),
            'episode_number': int_or_none(video_data.get('episodeNo')),
        }


class HotStarPrefixIE(InfoExtractor):
    """ The "hotstar:" prefix is no longer in use, but this is kept for backward compatibility """
    IE_DESC = False
    _VALID_URL = r'hotstar:(?:(?P<type>\w+):)?(?P<id>\d+)$'
    _TESTS = [{
        'url': 'hotstar:1000076273',
        'only_matching': True,
    }, {
        'url': 'hotstar:movies:1260009879',
        'info_dict': {
            'id': '1260009879',
            'ext': 'mp4',
            'title': 'Nuvvu Naaku Nachav',
            'description': 'md5:d43701b1314e6f8233ce33523c043b7d',
            'timestamp': 1567525674,
            'upload_date': '20190903',
            'duration': 10787,
            'episode': 'Nuvvu Naaku Nachav',
        },
    }, {
        'url': 'hotstar:episode:1000234847',
        'only_matching': True,
    }, {
        # contentData
        'url': 'hotstar:sports:1260065956',
        'only_matching': True,
    }, {
        # contentData
        'url': 'hotstar:sports:1260066104',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id, video_type = self._match_valid_url(url).group('id', 'type')
        return self.url_result(HotStarIE._video_url(video_id, video_type), HotStarIE, video_id)


class HotStarPlaylistIE(HotStarBaseIE):
    IE_NAME = 'hotstar:playlist'
    _VALID_URL = r'https?://(?:www\.)?hotstar\.com(?:/in)?/(?:tv|shows)(?:/[^/]+){2}/list/[^/]+/t-(?P<id>\w+)'
    _TESTS = [{
        'url': 'https://www.hotstar.com/tv/savdhaan-india/s-26/list/popular-clips/t-3_2_26',
        'info_dict': {
            'id': '3_2_26',
        },
        'playlist_mincount': 20,
    }, {
        'url': 'https://www.hotstar.com/shows/savdhaan-india/s-26/list/popular-clips/t-3_2_26',
        'only_matching': True,
    }, {
        'url': 'https://www.hotstar.com/tv/savdhaan-india/s-26/list/extras/t-2480',
        'only_matching': True,
    }, {
        'url': 'https://www.hotstar.com/in/tv/karthika-deepam/15457/list/popular-clips/t-3_2_1272',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        id_ = self._match_id(url)
        return self.playlist_result(
            self._playlist_entries('tray/find', id_, query={'tas': 10000, 'uqId': id_}), id_)


class HotStarSeasonIE(HotStarBaseIE):
    IE_NAME = 'hotstar:season'
    _VALID_URL = r'(?P<url>https?://(?:www\.)?hotstar\.com(?:/in)?/(?:tv|shows)/[^/]+/\w+)/seasons/[^/]+/ss-(?P<id>\w+)'
    _TESTS = [{
        'url': 'https://www.hotstar.com/tv/radhakrishn/1260000646/seasons/season-2/ss-8028',
        'info_dict': {
            'id': '8028',
        },
        'playlist_mincount': 35,
    }, {
        'url': 'https://www.hotstar.com/in/tv/ishqbaaz/9567/seasons/season-2/ss-4357',
        'info_dict': {
            'id': '4357',
        },
        'playlist_mincount': 30,
    }, {
        'url': 'https://www.hotstar.com/in/tv/bigg-boss/14714/seasons/season-4/ss-8208/',
        'info_dict': {
            'id': '8208',
        },
        'playlist_mincount': 19,
    }, {
        'url': 'https://www.hotstar.com/in/shows/bigg-boss/14714/seasons/season-4/ss-8208/',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        url, season_id = self._match_valid_url(url).groups()
        return self.playlist_result(self._playlist_entries(
            'season/asset', season_id, url, query={'tao': 0, 'tas': 0, 'size': 10000, 'id': season_id}), season_id)


class HotStarSeriesIE(HotStarBaseIE):
    IE_NAME = 'hotstar:series'
    _VALID_URL = r'(?P<url>https?://(?:www\.)?hotstar\.com(?:/in)?/(?:tv|shows)/[^/]+/(?P<id>\d+))/?(?:[#?]|$)'
    _TESTS = [{
        'url': 'https://www.hotstar.com/in/tv/radhakrishn/1260000646',
        'info_dict': {
            'id': '1260000646',
        },
        'playlist_mincount': 690,
    }, {
        'url': 'https://www.hotstar.com/tv/dancee-/1260050431',
        'info_dict': {
            'id': '1260050431',
        },
        'playlist_mincount': 43,
    }, {
        'url': 'https://www.hotstar.com/in/tv/mahabharat/435/',
        'info_dict': {
            'id': '435',
        },
        'playlist_mincount': 267,
    }, {
        'url': 'https://www.hotstar.com/in/shows/anupama/1260022017/',
        'info_dict': {
            'id': '1260022017',
        },
        'playlist_mincount': 940,
    }]

    def _real_extract(self, url):
        url, series_id = self._match_valid_url(url).groups()
        id_ = self._call_api_v1(
            'show/detail', series_id, query={'contentId': series_id})['body']['results']['item']['id']

        return self.playlist_result(self._playlist_entries(
            'tray/g/1/items', series_id, url, query={'tao': 0, 'tas': 10000, 'etid': 0, 'eid': id_}), series_id)
