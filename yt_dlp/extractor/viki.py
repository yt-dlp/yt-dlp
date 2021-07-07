# coding: utf-8
from __future__ import unicode_literals
import hashlib
import hmac
import json
import re
import time

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    int_or_none,
    parse_age_limit,
    parse_iso8601,
    try_get,
)

class VikiBaseIE(InfoExtractor):
    _VALID_URL_BASE = r'https?://(?:www\.)?viki\.(?:com|net|mx|jp|fr)/'
    _API_QUERY_TEMPLATE = '/v5/%sapp=%s'
    _API_URL_TEMPLATE = 'https://api.viki.io%s'
    
    _DEVICE_ID = '86085977d' #use for android api
    _APP = '100005a'
    _APP_VERSION = '6.11.3'
    _APP_SECRET = 'd96704b180208dbb2efa30fe44c48bd8690441af9f567ba8fd710a72badc85198f7472'

    _GEO_BYPASS = False
    _NETRC_MACHINE = 'viki'

    _token = None

    _ERRORS = {
        'geo': 'Sorry, this content is not available in your region.',
        'upcoming': 'Sorry, this content is not yet available.',
        'paywall': 'Sorry, this content is only available to Viki Pass Plus subscribers',
    }

    def _stream_headers(self, timestamp, sig):
        return {
            'X-Viki-manufacturer': 'vivo',
            'X-Viki-device-model': 'vivo 1606',
            'X-Viki-device-os-ver': '6.0.1',
            'X-Viki-connection-type': 'WIFI',
            'X-Viki-carrier': '',
            'X-Viki-as-id': '100005a-1625321982-3932',
            'timestamp': str(timestamp),
            'signature': str(sig),
            'x-viki-app-ver': self._APP_VERSION
        }
    
    def _prepare_call(self, path, timestamp=None):
        path += '?' if '?' not in path else '&'
        if not timestamp:
            timestamp = int(time.time())
            
        query = self._API_QUERY_TEMPLATE % (path, self._APP)
        if self._token:
            query += '&token=%s' % self._token
        sig = hmac.new(self._APP_SECRET.encode('ascii'), f'{query}&t={timestamp}'.encode('ascii'), 
                       hashlib.sha1).hexdigest()
        return sig, self._API_URL_TEMPLATE % query

    def _call_api(self, path, video_id, note, post_data=None):
        timestamp = int(time.time())
        sig, url = self._prepare_call(path, timestamp)
        
        headers = {'x-viki-app-ver': self._APP_VERSION} if post_data else self._stream_headers(timestamp, sig)
        
        resp = self._download_json(url, video_id, note, data=json.dumps(post_data).encode('utf-8') if post_data else None, headers=headers)

        error = resp.get('error')
        if error:
            self._raise_error(resp['error'])
        return resp

    def _raise_error(self, error):
        raise ExtractorError(
            '%s returned error: %s' % (self.IE_NAME, error),
            expected=True)

    def _check_errors(self, data):
        for reason, status in (data.get('blocking') or {}).items():
            if status and reason in self._ERRORS:
                message = self._ERRORS[reason]
                if reason == 'geo':
                    self.raise_geo_restricted(msg=message)
                elif reason == 'paywall':
                    if data['paywallable']['tvod']:
                        self._raise_error('TVOD (Transactional Video On demand) or for rent video only')
                    self.raise_login_required(message)
                raise ExtractorError('%s said: %s' % (
                    self.IE_NAME, message), expected=True)

    def _real_initialize(self):
        self._login()

    def _login(self):
        username, password = self._get_login_info()
        if username is None:
            return

        login_form = {'username': username, 'password': password}

        login = self._call_api(
            'sessions.json', None,
            'Logging in', post_data=login_form)

        self._token = login.get('token')
        if not self._token:
            self.report_warning('Unable to get session token, login has probably failed')

    @staticmethod
    def dict_selection(dict_obj, preferred_key, allow_fallback=True):
        if preferred_key in dict_obj:
            return dict_obj.get(preferred_key)

        if not allow_fallback:
            return

        filtered_dict = list(filter(None, [dict_obj.get(k) for k in dict_obj.keys()]))
        return filtered_dict[0] if filtered_dict else None


class VikiIE(VikiBaseIE):
    IE_NAME = 'viki'
    _VALID_URL = r'%s(?:videos|player)/(?P<id>[0-9]+v)' % VikiBaseIE._VALID_URL_BASE
    _TESTS = [{
        'note': 'Free non-DRM video with storyboards in MPD',
        'url': 'https://www.viki.com/videos/1175236v-choosing-spouse-by-lottery-episode-1',
        'info_dict': {
            'id': '1175236v',
            'ext': 'mp4',
            'title': 'Choosing Spouse by Lottery - Episode 1',
            'timestamp': 1606463239,
            'age_limit': 13,
            'uploader': 'FCC',
            'upload_date': '20201127',
        },
        'params': {
            'format': 'bestvideo',
        },
    }, {
        'url': 'http://www.viki.com/videos/1023585v-heirs-episode-14',
        'info_dict': {
            'id': '1023585v',
            'ext': 'mp4',
            'title': 'Heirs - Episode 14',
            'uploader': 'SBS Contents Hub',
            'timestamp': 1385047627,
            'upload_date': '20131121',
            'age_limit': 13,
            'duration': 3570,
            'episode_number': 14,
        },
        'params': {
            'format': 'bestvideo',
        },
        'skip': 'Blocked in the US',
    }, {
        # clip
        'url': 'http://www.viki.com/videos/1067139v-the-avengers-age-of-ultron-press-conference',
        'md5': '86c0b5dbd4d83a6611a79987cc7a1989',
        'info_dict': {
            'id': '1067139v',
            'ext': 'mp4',
            'title': "'The Avengers: Age of Ultron' Press Conference",
            'description': 'md5:d70b2f9428f5488321bfe1db10d612ea',
            'duration': 352,
            'timestamp': 1430380829,
            'upload_date': '20150430',
            'uploader': 'Arirang TV',
            'like_count': int,
            'age_limit': 0,
        },
        'skip': 'Sorry. There was an error loading this video',
    }, {
        'url': 'http://www.viki.com/videos/1048879v-ankhon-dekhi',
        'info_dict': {
            'id': '1048879v',
            'ext': 'mp4',
            'title': 'Ankhon Dekhi',
            'duration': 6512,
            'timestamp': 1408532356,
            'upload_date': '20140820',
            'uploader': 'Spuul',
            'like_count': int,
            'age_limit': 13,
        },
        'skip': 'Blocked in the US',
    }, {
        # episode
        'url': 'http://www.viki.com/videos/44699v-boys-over-flowers-episode-1',
        'md5': '0a53dc252e6e690feccd756861495a8c',
        'info_dict': {
            'id': '44699v',
            'ext': 'mp4',
            'title': 'Boys Over Flowers - Episode 1',
            'description': 'md5:b89cf50038b480b88b5b3c93589a9076',
            'duration': 4172,
            'timestamp': 1270496524,
            'upload_date': '20100405',
            'uploader': 'group8',
            'like_count': int,
            'age_limit': 13,
            'episode_number': 1,
        },
        'params': {
            'format': 'bestvideo',
        },
    }, {
        # youtube external
        'url': 'http://www.viki.com/videos/50562v-poor-nastya-complete-episode-1',
        'md5': '63f8600c1da6f01b7640eee7eca4f1da',
        'info_dict': {
            'id': '50562v',
            'ext': 'webm',
            'title': 'Poor Nastya [COMPLETE] - Episode 1',
            'description': '',
            'duration': 606,
            'timestamp': 1274949505,
            'upload_date': '20101213',
            'uploader': 'ad14065n',
            'uploader_id': 'ad14065n',
            'like_count': int,
            'age_limit': 13,
        },
        'skip': 'Page not found!',
    }, {
        'url': 'http://www.viki.com/player/44699v',
        'only_matching': True,
    }, {
        # non-English description
        'url': 'http://www.viki.com/videos/158036v-love-in-magic',
        'md5': '41faaba0de90483fb4848952af7c7d0d',
        'info_dict': {
            'id': '158036v',
            'ext': 'mp4',
            'uploader': 'I Planet Entertainment',
            'upload_date': '20111122',
            'timestamp': 1321985454,
            'description': 'md5:44b1e46619df3a072294645c770cef36',
            'title': 'Love In Magic',
            'age_limit': 13,
        },
        'params': {
            'format': 'bestvideo',
        },
    }]

    def _search_another_mpd_url(self, mpd_url, video_id):
        mpd_content = self._download_webpage(mpd_url, video_id, note='Checking for another mpd url')
        #Usually for flat manifest, 1080p is hidden in another mpd which can be found in the current manifest content
        url = re.search(r'<BaseURL>(http.+.mpd)', mpd_content, re.M | re.IGNORECASE)
        if url is None:
            return mpd_url
        
        new_mpd_url = url.group(1) 
        return new_mpd_url 
    
    def _real_extract(self, url):
        video_id = self._match_id(url)
        
        #metadata doesn't required any headers
        video = self._download_json(
            'https://api.viki.io/v4/videos/%s.json?app=%s&token=%s' % (video_id, self._APP, self._token),
            video_id, 'Downloading video JSON')  

        self._check_errors(video)
        
        title = self.dict_selection(video.get('titles', {}), 'en', allow_fallback=False)
        episode_number = int_or_none(video.get('number'))
        if not title:
            title = 'Episode %d' % episode_number if video.get('type') == 'episode' else video.get('id') or video_id
            container_titles = try_get(video, lambda x: x['container']['titles'], dict) or {}
            container_title = self.dict_selection(container_titles, 'en')
            title = '%s - %s' % (container_title, title)

        description = self.dict_selection(video.get('descriptions', {}), 'en')

        like_count = int_or_none(try_get(video, lambda x: x['likes']['count']))

        thumbnails = []
        for thumbnail_id, thumbnail in (video.get('images') or {}).items():
            thumbnails.append({
                'id': thumbnail_id,
                'url': thumbnail.get('url'),
            })
        
        stream_url = 'playback_streams/%s.json?drms=dt1,dt2&device_id=%s&token=%s' % (video_id, self._DEVICE_ID, self._token)
        resp = self._call_api(stream_url, video_id, 'Downloading video streams JSON')

        stream_id = resp['main'][0]['properties']['track']['stream_id']
        
        subtitle_format = 'https://api.viki.io/v4/videos/%s/auth_subtitles/%s.%s?app=%s&stream_id=%s'
        subtitles = {}
        for subtitle_lang, _ in (video.get('subtitle_completions') or {}).items():

            subtitles[subtitle_lang] = [{
                'ext': subtitles_format,
                'url': subtitle_format % (video_id, subtitle_lang, subtitle_format, self._APP, stream_id)
            } for subtitles_format in ('srt', 'vtt')]

        format_url = self._search_another_mpd_url(resp['main'][0]['url'], video_id)

        formats = []
        formats.append({
            'url': format_url,
            'format_id': '%s-%s' % ('dash', 'https'),
        })
        formats.extend(self._extract_mpd_formats(format_url, video_id))
        self._sort_formats(formats)

        return {
            'id': video_id,
            'formats': formats,
            'title': title,
            'description': description,
            'duration': int_or_none(video.get('duration')),
            'timestamp': parse_iso8601(video.get('created_at')),
            'uploader': video.get('author'),
            'uploader_url': video.get('author_url'),
            'like_count': like_count,
            'age_limit': parse_age_limit(video.get('rating')),
            'thumbnails': thumbnails,
            'subtitles': subtitles,
            'episode_number': episode_number,
        }

class VikiChannelIE(VikiBaseIE):
    IE_NAME = 'viki:channel'
    _VALID_URL = r'%s(?:tv|news|movies|artists)/(?P<id>[0-9]+c)' % VikiBaseIE._VALID_URL_BASE
    _TESTS = [{
        'url': 'http://www.viki.com/tv/50c-boys-over-flowers',
        'info_dict': {
            'id': '50c',
            'title': 'Boys Over Flowers',
            'description': 'md5:804ce6e7837e1fd527ad2f25420f4d59',
        },
        'playlist_mincount': 71,
    }, {
        'url': 'http://www.viki.com/tv/1354c-poor-nastya-complete',
        'info_dict': {
            'id': '1354c',
            'title': 'Poor Nastya [COMPLETE]',
            'description': 'md5:05bf5471385aa8b21c18ad450e350525',
        },
        'playlist_count': 127,
        'skip': 'Page not found',
    }, {
        'url': 'http://www.viki.com/news/24569c-showbiz-korea',
        'only_matching': True,
    }, {
        'url': 'http://www.viki.com/movies/22047c-pride-and-prejudice-2005',
        'only_matching': True,
    }, {
        'url': 'http://www.viki.com/artists/2141c-shinee',
        'only_matching': True,
    }]

    _PER_PAGE = 25

    def _real_extract(self, url):
        channel_id = self._match_id(url)

        channel = self._call_api('containers/%s.json' % channel_id, channel_id, 'Downloading channel JSON')

        self._check_errors(channel)

        title = self.dict_selection(channel['titles'], 'en')
        description = self.dict_selection(channel['descriptions'], 'en')
        
        max_page = 30
        page_num = 1
        entries = []
        
        is_movie = True if channel['type'] == 'film' else False
        video_type = 'movies' if is_movie else 'episodes'
        params = {'app': self._APP, 'token': self._token}
        
        #get only video ids
        while True:
            if is_movie:
                params.update({'blocked': 'true', 'only_ids':'true'})
            else:
                params.update({
                    'direction': 'desc', 'sort': 'number', 'only_ids': 'true',
                    'with_upcoming': 'true', 'page': page_num, 'per_page': max_page,
                    'with_paging': 'true', 'blocked': 'true', 'with_kcp': 'true',
                })

            url = self._API_URL_TEMPLATE % '/v4/{}/{}/{}.json?'.format('films' if is_movie else 'series', channel_id, video_type)
            res = self._download_json(url, channel_id, query=params)

            for video_id in res['response']: 
                entries.append(self.url_result('https://www.viki.com/videos/%s' % video_id, 'Viki', video_id))
            
            if not res['more']:
                break
            page_num += 1
            self.to_screen('Downloading %s JSON page #%d' % (video_type, page_num))
        
        return self.playlist_result(entries, channel_id, title, description)
