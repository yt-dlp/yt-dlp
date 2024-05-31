from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    clean_html,
    format_field,
    get_element_by_class,
    int_or_none,
    parse_iso8601,
    smuggle_url,
    str_or_none,
    strip_or_none,
    try_get,
    unsmuggle_url,
    urlencode_postdata,
)


class VidioBaseIE(InfoExtractor):
    _LOGIN_URL = 'https://www.vidio.com/users/login'
    _NETRC_MACHINE = 'vidio'

    def _perform_login(self, username, password):
        def is_logged_in():
            res = self._download_json(
                'https://www.vidio.com/interactions.json', None, 'Checking if logged in', fatal=False) or {}
            return bool(res.get('current_user'))

        if is_logged_in():
            return

        login_page = self._download_webpage(
            self._LOGIN_URL, None, 'Downloading log in page')

        login_form = self._form_hidden_inputs("login-form", login_page)
        login_form.update({
            'user[login]': username,
            'user[password]': password,
        })
        login_post, login_post_urlh = self._download_webpage_handle(
            self._LOGIN_URL, None, 'Logging in', data=urlencode_postdata(login_form), expected_status=[302, 401])

        if login_post_urlh.status == 401:
            if get_element_by_class('onboarding-content-register-popup__title', login_post):
                raise ExtractorError(
                    'Unable to log in: The provided email has not registered yet.', expected=True)

            reason = get_element_by_class('onboarding-form__general-error', login_post) or get_element_by_class('onboarding-modal__title', login_post)
            if 'Akun terhubung ke' in reason:
                raise ExtractorError(
                    'Unable to log in: Your account is linked to a social media account. '
                    'Use --cookies to provide account credentials instead', expected=True)
            elif reason:
                subreason = get_element_by_class('onboarding-modal__description-text', login_post) or ''
                raise ExtractorError(
                    'Unable to log in: %s. %s' % (reason, clean_html(subreason)), expected=True)
            raise ExtractorError('Unable to log in')

    def _initialize_pre_login(self):
        self._api_key = self._download_json(
            'https://www.vidio.com/auth', None, data=b'')['api_key']

    def _call_api(self, url, video_id, note=None):
        return self._download_json(url, video_id, note=note, headers={
            'Content-Type': 'application/vnd.api+json',
            'X-API-KEY': self._api_key,
        })


class VidioIE(VidioBaseIE):
    _VALID_URL = r'https?://(?:www\.)?vidio\.com/(watch|embed)/(?P<id>\d+)-(?P<display_id>[^/?#&]+)'
    _TESTS = [{
        'url': 'http://www.vidio.com/watch/165683-dj_ambred-booyah-live-2015',
        'md5': 'abac81b1a205a8d94c609a473b5ea62a',
        'info_dict': {
            'id': '165683',
            'display_id': 'dj_ambred-booyah-live-2015',
            'ext': 'mp4',
            'title': 'DJ_AMBRED - Booyah (Live 2015)',
            'description': 'md5:27dc15f819b6a78a626490881adbadf8',
            'thumbnail': r're:^https?://.*\.jpg$',
            'duration': 149,
            'like_count': int,
            'uploader': 'TWELVE Pic',
            'timestamp': 1444902800,
            'upload_date': '20151015',
            'uploader_id': 'twelvepictures',
            'channel': 'Cover Music Video',
            'channel_id': '280236',
            'view_count': int,
            'dislike_count': int,
            'comment_count': int,
            'tags': 'count:3',
            'uploader_url': 'https://www.vidio.com/@twelvepictures',
        },
    }, {
        'url': 'https://www.vidio.com/watch/77949-south-korea-test-fires-missile-that-can-strike-all-of-the-north',
        'only_matching': True,
    }, {
        # Premier-exclusive video
        'url': 'https://www.vidio.com/watch/1550718-stand-by-me-doraemon',
        'only_matching': True
    }, {
        # embed url from https://enamplus.liputan6.com/read/5033648/video-fakta-temuan-suspek-cacar-monyet-di-jawa-tengah
        'url': 'https://www.vidio.com/embed/7115874-fakta-temuan-suspek-cacar-monyet-di-jawa-tengah',
        'info_dict': {
            'id': '7115874',
            'ext': 'mp4',
            'channel_id': '40172876',
            'comment_count': int,
            'uploader_id': 'liputan6',
            'view_count': int,
            'dislike_count': int,
            'upload_date': '20220804',
            'uploader': 'Liputan6.com',
            'display_id': 'fakta-temuan-suspek-cacar-monyet-di-jawa-tengah',
            'channel': 'ENAM PLUS 165',
            'timestamp': 1659605520,
            'title': 'Fakta Temuan Suspek Cacar Monyet di Jawa Tengah',
            'duration': 59,
            'like_count': int,
            'tags': ['monkeypox indonesia', 'cacar monyet menyebar', 'suspek cacar monyet di indonesia', 'fakta', 'hoax atau bukan?', 'jawa tengah'],
            'thumbnail': 'https://thumbor.prod.vidiocdn.com/83PN-_BKm5sS7emLtRxl506MLqQ=/640x360/filters:quality(70)/vidio-web-prod-video/uploads/video/image/7115874/fakta-suspek-cacar-monyet-di-jawa-tengah-24555a.jpg',
            'uploader_url': 'https://www.vidio.com/@liputan6',
            'description': 'md5:6d595a18d3b19ee378e335a6f288d5ac',
        },
    }]

    def _real_extract(self, url):
        match = self._match_valid_url(url).groupdict()
        video_id, display_id = match.get('id'), match.get('display_id')
        data = self._call_api('https://api.vidio.com/videos/' + video_id, display_id)
        video = data['videos'][0]
        title = video['title'].strip()
        is_premium = video.get('is_premium')

        if is_premium:
            sources = self._download_json(
                'https://www.vidio.com/interactions_stream.json?video_id=%s&type=videos' % video_id,
                display_id, note='Downloading premier API JSON')
            if not (sources.get('source') or sources.get('source_dash')):
                self.raise_login_required('This video is only available for registered users with the appropriate subscription')

            formats, subs = [], {}
            if sources.get('source'):
                hls_formats, hls_subs = self._extract_m3u8_formats_and_subtitles(
                    sources['source'], display_id, 'mp4', 'm3u8_native')
                formats.extend(hls_formats)
                subs.update(hls_subs)
            if sources.get('source_dash'):  # TODO: Find video example with source_dash
                dash_formats, dash_subs = self._extract_mpd_formats_and_subtitles(
                    sources['source_dash'], display_id, 'dash')
                formats.extend(dash_formats)
                subs.update(dash_subs)
        else:
            hls_url = data['clips'][0]['hls_url']
            formats, subs = self._extract_m3u8_formats_and_subtitles(
                hls_url, display_id, 'mp4', 'm3u8_native')

        get_first = lambda x: try_get(data, lambda y: y[x + 's'][0], dict) or {}
        channel = get_first('channel')
        user = get_first('user')
        username = user.get('username')
        get_count = lambda x: int_or_none(video.get('total_' + x))

        return {
            'id': video_id,
            'display_id': display_id,
            'title': title,
            'description': strip_or_none(video.get('description')),
            'thumbnail': video.get('image_url_medium'),
            'duration': int_or_none(video.get('duration')),
            'like_count': get_count('likes'),
            'formats': formats,
            'subtitles': subs,
            'uploader': user.get('name'),
            'timestamp': parse_iso8601(video.get('created_at')),
            'uploader_id': username,
            'uploader_url': format_field(username, None, 'https://www.vidio.com/@%s'),
            'channel': channel.get('name'),
            'channel_id': str_or_none(channel.get('id')),
            'view_count': get_count('view_count'),
            'dislike_count': get_count('dislikes'),
            'comment_count': get_count('comments'),
            'tags': video.get('tag_list'),
        }


class VidioPremierIE(VidioBaseIE):
    _VALID_URL = r'https?://(?:www\.)?vidio\.com/premier/(?P<id>\d+)/(?P<display_id>[^/?#&]+)'
    _TESTS = [{
        'url': 'https://www.vidio.com/premier/2885/badai-pasti-berlalu',
        'playlist_mincount': 14,
    }, {
        # Series with both free and premier-exclusive videos
        'url': 'https://www.vidio.com/premier/2567/sosmed',
        'only_matching': True,
    }]

    def _playlist_entries(self, playlist_url, display_id):
        index = 1
        while playlist_url:
            playlist_json = self._call_api(playlist_url, display_id, 'Downloading API JSON page %s' % index)
            for video_json in playlist_json.get('data', []):
                link = video_json['links']['watchpage']
                yield self.url_result(link, 'Vidio', video_json['id'])
            playlist_url = try_get(playlist_json, lambda x: x['links']['next'])
            index += 1

    def _real_extract(self, url):
        url, idata = unsmuggle_url(url, {})
        playlist_id, display_id = self._match_valid_url(url).groups()

        playlist_url = idata.get('url')
        if playlist_url:  # Smuggled data contains an API URL. Download only that playlist
            playlist_id = idata['id']
            return self.playlist_result(
                self._playlist_entries(playlist_url, playlist_id),
                playlist_id=playlist_id, playlist_title=idata.get('title'))

        playlist_data = self._call_api('https://api.vidio.com/content_profiles/%s/playlists' % playlist_id, display_id)

        return self.playlist_from_matches(
            playlist_data.get('data', []), playlist_id=playlist_id, ie=self.ie_key(),
            getter=lambda data: smuggle_url(url, {
                'url': data['relationships']['videos']['links']['related'],
                'id': data['id'],
                'title': try_get(data, lambda x: x['attributes']['name'])
            }))


class VidioLiveIE(VidioBaseIE):
    _VALID_URL = r'https?://(?:www\.)?vidio\.com/live/(?P<id>\d+)-(?P<display_id>[^/?#&]+)'
    _TESTS = [{
        'url': 'https://www.vidio.com/live/204-sctv',
        'info_dict': {
            'id': '204',
            'title': 'SCTV',
            'uploader': 'SCTV',
            'uploader_id': 'sctv',
            'thumbnail': r're:^https?://.*\.jpg$',
        },
    }, {
        # Premier-exclusive livestream
        'url': 'https://www.vidio.com/live/6362-tvn',
        'only_matching': True,
    }, {
        # DRM premier-exclusive livestream
        'url': 'https://www.vidio.com/live/6299-bein-1',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id, display_id = self._match_valid_url(url).groups()
        stream_data = self._call_api(
            'https://www.vidio.com/api/livestreamings/%s/detail' % video_id, display_id)
        stream_meta = stream_data['livestreamings'][0]
        user = stream_data.get('users', [{}])[0]

        title = stream_meta.get('title')
        username = user.get('username')

        formats = []
        if stream_meta.get('is_drm'):
            if not self.get_param('allow_unplayable_formats'):
                self.report_drm(video_id)
        if stream_meta.get('is_premium'):
            sources = self._download_json(
                'https://www.vidio.com/interactions_stream.json?video_id=%s&type=livestreamings' % video_id,
                display_id, note='Downloading premier API JSON')
            if not (sources.get('source') or sources.get('source_dash')):
                self.raise_login_required('This video is only available for registered users with the appropriate subscription')

            if str_or_none(sources.get('source')):
                token_json = self._download_json(
                    'https://www.vidio.com/live/%s/tokens' % video_id,
                    display_id, note='Downloading HLS token JSON', data=b'')
                formats.extend(self._extract_m3u8_formats(
                    sources['source'] + '?' + token_json.get('token', ''), display_id, 'mp4', 'm3u8_native'))
            if str_or_none(sources.get('source_dash')):
                pass
        else:
            if stream_meta.get('stream_token_url'):
                token_json = self._download_json(
                    'https://www.vidio.com/live/%s/tokens' % video_id,
                    display_id, note='Downloading HLS token JSON', data=b'')
                formats.extend(self._extract_m3u8_formats(
                    stream_meta['stream_token_url'] + '?' + token_json.get('token', ''),
                    display_id, 'mp4', 'm3u8_native'))
            if stream_meta.get('stream_dash_url'):
                pass
            if stream_meta.get('stream_url'):
                formats.extend(self._extract_m3u8_formats(
                    stream_meta['stream_url'], display_id, 'mp4', 'm3u8_native'))

        return {
            'id': video_id,
            'display_id': display_id,
            'title': title,
            'is_live': True,
            'description': strip_or_none(stream_meta.get('description')),
            'thumbnail': stream_meta.get('image'),
            'like_count': int_or_none(stream_meta.get('like')),
            'dislike_count': int_or_none(stream_meta.get('dislike')),
            'formats': formats,
            'uploader': user.get('name'),
            'timestamp': parse_iso8601(stream_meta.get('start_time')),
            'uploader_id': username,
            'uploader_url': format_field(username, None, 'https://www.vidio.com/@%s'),
        }
