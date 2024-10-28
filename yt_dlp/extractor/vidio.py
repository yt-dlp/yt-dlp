import json

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    clean_html,
    extract_attributes,
    get_element_by_class,
    get_element_html_by_id,
    int_or_none,
    parse_iso8601,
    remove_end,
    smuggle_url,
    str_or_none,
    str_to_int,
    try_get,
    unsmuggle_url,
    url_or_none,
    urlencode_postdata,
)
from ..utils.traversal import traverse_obj


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

        login_form = self._form_hidden_inputs('login-form', login_page)
        login_form.update({
            'user[login]': username,
            'user[password]': password,
            'authenticity_token': self._html_search_meta('csrf-token', login_page, fatal=True),
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
                    f'Unable to log in: {reason}. {clean_html(subreason)}', expected=True)
            raise ExtractorError('Unable to log in')

    def _initialize_pre_login(self):
        self._api_key = self._download_json(
            'https://www.vidio.com/auth', None, data=b'')['api_key']
        self._ua = self.get_param('http_headers')['User-Agent']

    def _call_api(self, url, video_id, note=None):
        return self._download_json(url, video_id, note=note, headers={
            'Content-Type': 'application/vnd.api+json',
            'X-API-KEY': self._api_key,
        })


class VidioIE(VidioBaseIE):
    _GEO_COUNTRIES = ['ID']
    _VALID_URL = r'https?://(?:www\.)?vidio\.com/(watch|embed)/(?P<id>\d+)-(?P<display_id>[^/?#&]+)'
    _EMBED_REGEX = [rf'(?x)<iframe[^>]+\bsrc=[\'"](?P<url>{_VALID_URL})']
    _TESTS = [{
        'url': 'http://www.vidio.com/watch/165683-dj_ambred-booyah-live-2015',
        'md5': 'abac81b1a205a8d94c609a473b5ea62a',
        'info_dict': {
            'id': '165683',
            'display_id': 'dj_ambred-booyah-live-2015',
            'ext': 'mp4',
            'title': 'DJ_AMBRED - Booyah (Live 2015)',
            'description': 'md5:27dc15f819b6a78a626490881adbadf8',
            'thumbnail': r're:^https?://thumbor\.prod\.vidiocdn\.com/.+\.jpg$',
            'duration': 149,
            'uploader': 'twelvepictures',
            'timestamp': 1444902960,
            'upload_date': '20151015',
            'uploader_id': '270115',
            'channel': 'cover-music-video',
            'channel_id': '280236',
            'channel_url': 'https://www.vidio.com/@twelvepictures/channels/280236-cover-music-video',
            'tags': 'count:3',
            'uploader_url': 'https://www.vidio.com/@twelvepictures',
            'live_status': 'not_live',
            'genres': ['vlog', 'comedy', 'edm'],
            'season_id': '',
            'season_name': '',
            'age_limit': 13,
            'comment_count': int,
        },
        'params': {
            'getcomments': True,
        },
    }, {
        # DRM protected
        'url': 'https://www.vidio.com/watch/7095853-ep-04-sketch-book',
        'md5': 'abac81b1a205a8d94c609a473b5ea62a',
        'info_dict': {
            'id': '7095853',
            'display_id': 'ep-04-sketch-book',
            'ext': 'mp4',
            'title': 'Ep 04 - Sketch Book',
            'description': 'md5:9e22b4b1dbd65209c143d7009e899830',
            'thumbnail': r're:^https?://thumbor\.prod\.vidiocdn\.com/.+\.jpg$',
            'duration': 2784,
            'uploader': 'vidiooriginal',
            'timestamp': 1658509200,
            'upload_date': '20220722',
            'uploader_id': '31052580',
            'channel': 'cupcake-untuk-rain',
            'channel_id': '52332655',
            'channel_url': 'https://www.vidio.com/@vidiooriginal/channels/52332655-cupcake-untuk-rain',
            'tags': [],
            'uploader_url': 'https://www.vidio.com/@vidiooriginal',
            'live_status': 'not_live',
            'genres': ['romance', 'drama', 'comedy', 'Teen', 'love triangle'],
            'season_id': '8220',
            'season_name': 'Season 1',
            'age_limit': 13,
            'availability': 'premium_only',
            'comment_count': int,
        },
        'expected_warnings': ['This video is DRM protected'],
        'params': {
            'getcomments': True,
            'skip_download': True,
            'ignore_no_formats_error': True,
        },
    }, {
        'url': 'https://www.vidio.com/watch/7439193-episode-1-magic-5',
        'md5': 'b1644c574aeb20c91503be367ac2d211',
        'info_dict': {
            'id': '7439193',
            'display_id': 'episode-1-magic-5',
            'ext': 'mp4',
            'title': 'Episode 1 - Magic 5',
            'description': 'md5:367255f9e8e7ad7192c26218f01b6260',
            'thumbnail': r're:^https?://thumbor\.prod\.vidiocdn\.com/.+\.jpg$',
            'duration': 6126,
            'uploader': 'indosiar',
            'timestamp': 1679315400,
            'upload_date': '20230320',
            'uploader_id': '12',
            'channel': 'magic-5',
            'channel_id': '52350795',
            'channel_url': 'https://www.vidio.com/@indosiar/channels/52350795-magic-5',
            'tags': ['basmalah', 'raden-rakha', 'eby-da-5', 'sinetron', 'afan-da-5', 'sridevi-da5'],
            'uploader_url': 'https://www.vidio.com/@indosiar',
            'live_status': 'not_live',
            'genres': ['drama', 'fantasy', 'friendship'],
            'season_id': '11017',
            'season_name': 'Episode',
            'age_limit': 13,
        },
    }, {
        'url': 'https://www.vidio.com/watch/1716926-mas-suka-masukin-aja',
        'md5': 'acc4009eeac0033328419aada7bc6925',
        'info_dict': {
            'id': '1716926',
            'display_id': 'mas-suka-masukin-aja',
            'ext': 'mp4',
            'title': 'Mas Suka, Masukin Aja',
            'description': 'md5:667093b08e07b6fb92f68037f81f2267',
            'thumbnail': r're:^https?://thumbor\.prod\.vidiocdn\.com/.+\.jpg$',
            'duration': 5080,
            'uploader': 'vidiopremier',
            'timestamp': 1564735560,
            'upload_date': '20190802',
            'uploader_id': '26094842',
            'channel': 'mas-suka-masukin-aja',
            'channel_id': '34112289',
            'channel_url': 'https://www.vidio.com/@vidiopremier/channels/34112289-mas-suka-masukin-aja',
            'tags': [],
            'uploader_url': 'https://www.vidio.com/@vidiopremier',
            'live_status': 'not_live',
            'genres': ['comedy', 'romance'],
            'season_id': '663',
            'season_name': '',
            'age_limit': 18,
            'availability': 'premium_only',
        },
        'params': {
            'ignore_no_formats_error': True,
        },
        'expected_warnings': ['This show isn\'t available in your country'],
    }, {
        'url': 'https://www.vidio.com/watch/2372948-first-day-of-school-kindergarten-life-song-beabeo-nursery-rhymes-kids-songs',
        'md5': 'c6d1bde08eee88bea27cca9dc38bc3df',
        'info_dict': {
            'id': '2372948',
            'display_id': 'first-day-of-school-kindergarten-life-song-beabeo-nursery-rhymes-kids-songs',
            'ext': 'mp4',
            'title': 'First Day of School | Kindergarten Life Song | BeaBeo Nursery Rhymes & Kids Songs',
            'description': 'md5:d505486a67415903f7f3ab61adfd5a91',
            'thumbnail': r're:^https?://thumbor\.prod\.vidiocdn\.com/.+\.jpg$',
            'duration': 517,
            'uploader': 'kidsstartv',
            'timestamp': 1638518400,
            'upload_date': '20211203',
            'uploader_id': '38247189',
            'channel': 'beabeo-school-series',
            'channel_id': '52311987',
            'channel_url': 'https://www.vidio.com/@kidsstartv/channels/52311987-beabeo-school-series',
            'tags': [],
            'uploader_url': 'https://www.vidio.com/@kidsstartv',
            'live_status': 'not_live',
            'genres': ['animation', 'Cartoon'],
            'season_id': '6023',
            'season_name': 'school series',
        },
    }, {
        'url': 'https://www.vidio.com/watch/1550718-stand-by-me-doraemon',
        'md5': '405b61a2f06c74e052e0bd67cad6b891',
        'info_dict': {
            'id': '1550718',
            'display_id': 'stand-by-me-doraemon',
            'ext': 'mp4',
            'title': 'Stand by Me Doraemon',
            'description': 'md5:673d899f6a58dd4b0d18aebe30545e2a',
            'thumbnail': r're:^https?://thumbor\.prod\.vidiocdn\.com/.+\.jpg$',
            'duration': 5429,
            'uploader': 'vidiopremier',
            'timestamp': 1545815634,
            'upload_date': '20181226',
            'uploader_id': '26094842',
            'channel': 'stand-by-me-doraemon',
            'channel_id': '29750953',
            'channel_url': 'https://www.vidio.com/@vidiopremier/channels/29750953-stand-by-me-doraemon',
            'tags': ['anime-lucu', 'top-10-this-week', 'kids', 'stand-by-me-doraemon-2'],
            'uploader_url': 'https://www.vidio.com/@vidiopremier',
            'live_status': 'not_live',
            'genres': ['anime', 'family', 'adventure', 'comedy', 'coming of age'],
            'season_id': '237',
            'season_name': '',
            'age_limit': 7,
            'availability': 'premium_only',
        },
        'params': {
            'ignore_no_formats_error': True,
        },
        'expected_warnings': ['This show isn\'t available in your country'],
    }, {
        # 404 Not Found
        'url': 'https://www.vidio.com/watch/77949-south-korea-test-fires-missile-that-can-strike-all-of-the-north',
        'only_matching': True,
    }]
    _WEBPAGE_TESTS = [{
        # embed player: https://www.vidio.com/embed/7115874-fakta-temuan-suspek-cacar-monyet-di-jawa-tengah
        'url': 'https://enamplus.liputan6.com/read/5033648/video-fakta-temuan-suspek-cacar-monyet-di-jawa-tengah',
        'info_dict': {
            'id': '7115874',
            'display_id': 'fakta-temuan-suspek-cacar-monyet-di-jawa-tengah',
            'ext': 'mp4',
            'title': 'Fakta Temuan Suspek Cacar Monyet di Jawa Tengah',
            'description': 'md5:6d595a18d3b19ee378e335a6f288d5ac',
            'thumbnail': r're:^https?://thumbor\.prod\.vidiocdn\.com/.+\.jpg$',
            'duration': 59,
            'uploader': 'liputan6',
            'timestamp': 1659605693,
            'upload_date': '20220804',
            'uploader_id': '139',
            'channel': 'enam-plus-165',
            'channel_id': '40172876',
            'channel_url': 'https://www.vidio.com/@liputan6/channels/40172876-enam-plus-165',
            'tags': ['monkeypox-indonesia', 'cacar-monyet-menyebar', 'suspek-cacar-monyet-di-indonesia', 'fakta', 'hoax-atau-bukan', 'jawa-tengah'],
            'uploader_url': 'https://www.vidio.com/@liputan6',
            'live_status': 'not_live',
            'genres': ['health'],
            'season_id': '',
            'season_name': '',
            'age_limit': 13,
            'comment_count': int,
        },
        'params': {
            'getcomments': True,
        },
    }]

    def _real_extract(self, url):
        video_id, display_id = self._match_valid_url(url).groups()

        webpage = self._download_webpage(url, video_id)
        api_data = self._call_api(f'https://api.vidio.com/videos/{video_id}', display_id, 'Downloading API data')
        interactions_stream = self._download_json(
            'https://www.vidio.com/interactions_stream.json', video_id,
            query={'video_id': video_id, 'type': 'videos'}, note='Downloading stream info',
            errnote='Unable to download stream info')

        attrs = extract_attributes(get_element_html_by_id(f'player-data-{video_id}', webpage))

        if traverse_obj(attrs, ('data-drm-enabled', {lambda x: x == 'true'})):
            self.report_drm(video_id)
        if traverse_obj(attrs, ('data-geoblock', {lambda x: x == 'true'})):
            self.raise_geo_restricted(
                'This show isn\'t available in your country', countries=['ID'], metadata_available=True)

        subtitles = dict(traverse_obj(attrs, ('data-subtitles', {json.loads}, ..., {
            lambda x: (x['language'], [{'url': x['file']['url']}]),
        })))
        formats = []

        # There are time-based strings in the playlist URL,
        # so try the other URL iff no formats extracted from the prior one.

        for m3u8_url in traverse_obj([
                interactions_stream.get('source'),
                attrs.get('data-vjs-clip-hls-url')], (..., {url_or_none})):
            fmt, subs = self._extract_m3u8_formats_and_subtitles(m3u8_url, video_id, ext='mp4', m3u8_id='hls')
            formats.extend(fmt)
            self._merge_subtitles(subs, target=subtitles)
            if fmt:
                break

        for mpd_url in traverse_obj([
                interactions_stream.get('source_dash'),
                attrs.get('data-vjs-clip-dash-url')], (..., {url_or_none})):
            fmt, subs = self._extract_mpd_formats_and_subtitles(mpd_url, video_id, mpd_id='dash')
            formats.extend(fmt)
            self._merge_subtitles(subs, target=subtitles)
            if fmt:
                break

        # TODO: extract also short previews of premier-exclusive videos from "attrs['data-content-preview-url']".

        uploader = attrs.get('data-video-username')
        uploader_url = f'https://www.vidio.com/@{uploader}'
        channel = attrs.get('data-video-channel')
        channel_id = attrs.get('data-video-channel-id')

        return {
            'id': video_id,
            'display_id': display_id,
            'title': (traverse_obj(api_data, ('videos', 0, 'title'))
                      or attrs.get('data-video-title')
                      or self._html_extract_title(webpage)),
            'live_status': 'not_live',
            'formats': formats,
            'subtitles': subtitles,
            'channel': channel,
            'channel_id': channel_id,
            'channel_url': f'{uploader_url}/channels/{channel_id}-{channel}',
            'genres': traverse_obj(attrs, ('data-genres', {str}, {lambda x: x.split(',') if x else []}), default=[]),
            'season_id': traverse_obj(attrs, ('data-season-id', {str_or_none})),
            'season_name': traverse_obj(attrs, ('data-season-name', {str})),
            'uploader': uploader,
            'uploader_id': traverse_obj(attrs, ('data-video-user-id', {str_or_none})),
            'uploader_url': uploader_url,
            'thumbnail': traverse_obj(attrs, ('data-video-image-url', {url_or_none})),
            'duration': traverse_obj(attrs, ('data-video-duration', {str_to_int})),
            'description': traverse_obj(attrs, ('data-video-description', {str})),
            'availability': self._availability(needs_premium=(attrs.get('data-access-type') == 'premium')),
            'tags': traverse_obj(attrs, ('data-video-tags', {str}, {lambda x: x.split(',') if x else []}), default=[]),
            'timestamp': traverse_obj(attrs, ('data-video-publish-date', {lambda x: parse_iso8601(x, ' ')})),
            'age_limit': (traverse_obj(attrs, ('data-adult', {lambda x: 18 if x == 'true' else 0}))
                          or traverse_obj(attrs, ('data-content-rating-option', {lambda x: remove_end(x, ' or more')}, {str_to_int}))),
            '__post_extractor': self.extract_comments(video_id),
        }

    def _get_comments(self, video_id):
        # TODO: extract replies under comments

        def extract_comments(comments_data):
            users = dict(traverse_obj(comments_data, ('included', ..., {
                lambda x: (x['id'], {
                    'author': x['attributes']['username'],
                    'author_thumbnail': url_or_none(x['attributes']['avatar_url_big'] or x['attributes']['avatar_url_small']),
                    'author_url': url_or_none(x['links']['self']),
                }),
            })))
            yield from traverse_obj(comments_data, ('data', ..., {
                'id': 'id',
                'text': ('attributes', 'content'),
                'timestamp': ('attributes', 'created_at', {parse_iso8601}),
                'like_count': ('attributes', 'likes'),
                'author_id': ('attributes', 'user_id'),
            }, {lambda x: {**x, **users.get(x['author_id'])}}))

        comment_page_url = f'https://api.vidio.com/videos/{video_id}/comments'
        while comment_page_url:
            comments_data = self._call_api(comment_page_url, video_id, 'Downloading comments')
            comment_page_url = traverse_obj(comments_data, ('links', 'next', {url_or_none}))
            yield from extract_comments(comments_data)


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
            playlist_json = self._call_api(playlist_url, display_id, f'Downloading API JSON page {index}')
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

        playlist_data = self._call_api(f'https://api.vidio.com/content_profiles/{playlist_id}/playlists', display_id)

        return self.playlist_from_matches(
            playlist_data.get('data', []), playlist_id=playlist_id, ie=self.ie_key(),
            getter=lambda data: smuggle_url(url, {
                'url': data['relationships']['videos']['links']['related'],
                'id': data['id'],
                'title': try_get(data, lambda x: x['attributes']['name']),
            }))


class VidioLiveIE(VidioBaseIE):
    _VALID_URL = r'https?://(?:www\.)?vidio\.com/live/(?P<id>\d+)-(?P<display_id>[^/?#&]+)'
    _TESTS = [{
        'url': 'https://www.vidio.com/live/204-sctv',
        'info_dict': {
            'id': '204',
            'ext': 'mp4',
            'title': r're:SCTV \d{4}-\d{2}-\d{2} \d{2}:\d{2}',
            'display_id': 'sctv',
            'uploader': 'sctv',
            'uploader_id': '4',
            'uploader_url': 'https://www.vidio.com/@sctv',
            'thumbnail': r're:^https?://thumbor\.prod\.vidiocdn\.com/.+\.jpg$',
            'live_status': 'is_live',
            'description': r're:^SCTV merupakan stasiun televisi nasional terkemuka di Indonesia.+',
            'like_count': int,
            'dislike_count': int,
            'timestamp': 1461258000,
            'upload_date': '20160421',
            'tags': [],
            'genres': [],
            'age_limit': 13,
        },
    }, {
        'url': 'https://vidio.com/live/733-trans-tv',
        'info_dict': {
            'id': '733',
            'ext': 'mp4',
            'title': r're:TRANS TV \d{4}-\d{2}-\d{2} \d{2}:\d{2}',
            'display_id': 'trans-tv',
            'uploader': 'transtv',
            'uploader_id': '551300',
            'uploader_url': 'https://www.vidio.com/@transtv',
            'thumbnail': r're:^https?://thumbor\.prod\.vidiocdn\.com/.+\.jpg$',
            'live_status': 'is_live',
            'description': r're:^Trans TV adalah stasiun televisi swasta Indonesia.+',
            'like_count': int,
            'dislike_count': int,
            'timestamp': 1461355080,
            'upload_date': '20160422',
            'tags': [],
            'genres': [],
            'age_limit': 13,
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

        webpage = self._download_webpage(url, video_id)
        stream_meta = traverse_obj(self._call_api(
            f'https://www.vidio.com/api/livestreamings/{video_id}/detail', video_id),
            ('livestreamings', 0, {dict}), default={})
        tokenized_playlist_urls = self._download_json(
            f'https://www.vidio.com/live/{video_id}/tokens', video_id,
            query={'type': 'dash'}, note='Downloading tokenized playlist',
            errnote='Unable to download tokenized playlist', data=b'')
        interactions_stream = self._download_json(
            'https://www.vidio.com/interactions_stream.json', video_id,
            query={'video_id': video_id, 'type': 'videos'}, note='Downloading stream info',
            errnote='Unable to download stream info')

        attrs = extract_attributes(get_element_html_by_id(f'player-data-{video_id}', webpage))

        if traverse_obj(attrs, ('data-drm-enabled', {lambda x: x == 'true'})):
            self.report_drm(video_id)
        if traverse_obj(attrs, ('data-geoblock', {lambda x: x == 'true'})):
            self.raise_geo_restricted(
                'This show isn\'t available in your country', countries=['ID'], metadata_available=True)

        formats = []

        for m3u8_url in traverse_obj([
                tokenized_playlist_urls.get('hls_url'),
                interactions_stream.get('source')], (..., {url_or_none})):
            formats.extend(self._extract_m3u8_formats(m3u8_url, video_id, ext='mp4', m3u8_id='hls'))

        for mpd_url in traverse_obj([
                tokenized_playlist_urls.get('dash_url'),
                interactions_stream.get('source_dash')], (..., {url_or_none})):
            formats.extend(self._extract_mpd_formats(mpd_url, video_id, mpd_id='dash'))

        uploader = attrs.get('data-video-username')
        uploader_url = f'https://www.vidio.com/@{uploader}'

        return {
            'id': video_id,
            'display_id': display_id,
            'title': attrs.get('data-video-title'),
            'live_status': 'is_live',
            'formats': formats,
            'genres': traverse_obj(attrs, ('data-genres', {str}, {lambda x: x.split(',') if x else []}), default=[]),
            'uploader': uploader,
            'uploader_id': traverse_obj(attrs, ('data-video-user-id', {str_or_none})),
            'uploader_url': uploader_url,
            'thumbnail': traverse_obj(attrs, ('data-video-image-url', {url_or_none})),
            'description': traverse_obj(attrs, ('data-video-description', {str})),
            'availability': self._availability(needs_premium=(attrs.get('data-access-type') == 'premium')),
            'tags': traverse_obj(attrs, ('data-video-tags', {str}, {lambda x: x.split(',') if x else []}), default=[]),
            'age_limit': (traverse_obj(attrs, ('data-adult', {lambda x: 18 if x == 'true' else 0}))
                          or traverse_obj(attrs, ('data-content-rating-option', {lambda x: remove_end(x, ' or more')}, {str_to_int}))),
            'like_count': int_or_none(stream_meta.get('like')),
            'dislike_count': int_or_none(stream_meta.get('dislike')),
            'timestamp': parse_iso8601(stream_meta.get('start_time')),
        }
