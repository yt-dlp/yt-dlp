import collections
import hashlib
import re
import urllib.parse

from .common import InfoExtractor
from .dailymotion import DailymotionIE
from .odnoklassniki import OdnoklassnikiIE
from .sibnet import SibnetEmbedIE
from .vimeo import VimeoIE
from .youtube import YoutubeIE
from ..jsinterp import JSInterpreter
from ..utils import (
    ExtractorError,
    UserNotLive,
    clean_html,
    get_element_by_class,
    get_element_html_by_id,
    int_or_none,
    join_nonempty,
    parse_qs,
    parse_resolution,
    str_or_none,
    str_to_int,
    try_call,
    unescapeHTML,
    unified_timestamp,
    update_url_query,
    url_or_none,
    urlencode_postdata,
    urljoin,
)
from ..utils.traversal import require, traverse_obj


class VKBaseIE(InfoExtractor):
    _NETRC_MACHINE = 'vk'
    _BASE64_CHARS = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMN0PQRSTUVWXYZO123456789+/='

    def _decode(self, enc):
        dec = ''
        e = n = 0
        for c in enc:
            r = self._BASE64_CHARS.index(c)
            cond = n % 4
            e = 64 * e + r if cond else r
            n += 1
            if cond:
                dec += chr(255 & e >> (-2 * n & 6))
        return dec

    def _unmask_audio_url(self, mask_url, vk_id):
        if 'audio_api_unavailable' in mask_url:
            extra = mask_url.split('?extra=')[1].split('#')
            _, base = self._decode(extra[1]).split(chr(11))
            mask_url = list(self._decode(extra[0]))
            url_len = len(mask_url)
            indexes = [None] * url_len
            index = int(base) ^ vk_id
            for n in range(url_len - 1, -1, -1):
                index = (url_len * (n + 1) ^ index + n) % url_len
                indexes[n] = index
            for n in range(1, url_len):
                c = mask_url[n]
                index = indexes[url_len - 1 - n]
                mask_url[n] = mask_url[index]
                mask_url[index] = c
            mask_url = ''.join(mask_url)
        return mask_url

    def _download_webpage_handle(self, url_or_request, video_id, *args, fatal=True, **kwargs):
        response = super()._download_webpage_handle(url_or_request, video_id, *args, fatal=fatal, **kwargs)
        if response is False:
            return response

        webpage, urlh = response
        challenge_url = urlh.url
        if urllib.parse.urlparse(challenge_url).path != '/challenge.html':
            return response

        self.to_screen(join_nonempty(
            video_id and f'[{video_id}]',
            'Received a JS challenge response',
            delim=' '))

        challenge_hash = traverse_obj(challenge_url, (
            {parse_qs}, 'hash429', -1, {require('challenge hash')}))

        func_code = self._search_regex(
            r'(?s)var\s+salt\s*=\s*\(\s*function\s*\(\)\s*(\{.+?\})\s*\)\(\);\s*var\s+hash',
            webpage, 'JS challenge salt function')

        jsi = JSInterpreter(f'function salt() {func_code}')
        salt = jsi.extract_function('salt')([])
        self.write_debug(f'Generated salt with native JS interpreter: {salt}')

        key_hash = hashlib.md5(f'{challenge_hash}:{salt}'.encode()).hexdigest()
        self.write_debug(f'JS challenge key hash: {key_hash}')

        # Request with the challenge key and the response should set a 'solution429' cookie
        self._request_webpage(
            update_url_query(challenge_url, {'key': key_hash}), video_id,
            'Submitting JS challenge solution', 'Unable to solve JS challenge', fatal=True)

        return super()._download_webpage_handle(url_or_request, video_id, *args, fatal=True, **kwargs)

    def _perform_login(self, username, password):
        login_page, url_handle = self._download_webpage_handle(
            'https://vk.com', None, 'Downloading login page')

        login_form = self._hidden_inputs(login_page)

        login_form.update({
            'email': username.encode('cp1251'),
            'pass': password.encode('cp1251'),
        })

        # vk serves two same remixlhk cookies in Set-Cookie header and expects
        # first one to be actually set
        self._apply_first_set_cookie_header(url_handle, 'remixlhk')

        login_page = self._download_webpage(
            'https://vk.com/login', None,
            note='Logging in',
            data=urlencode_postdata(login_form))

        if re.search(r'onLoginFailed', login_page):
            raise ExtractorError(
                'Unable to login, incorrect username and/or password', expected=True)

    def _download_payload(self, path, video_id, data, fatal=True):
        endpoint = f'https://vk.com/{path}.php'
        data['al'] = 1
        code, payload = self._download_json(
            endpoint, video_id, data=urlencode_postdata(data), fatal=fatal,
            headers={
                'Referer': endpoint,
                'X-Requested-With': 'XMLHttpRequest',
            })['payload']
        if code == '3':
            self.raise_login_required()
        elif code == '8':
            raise ExtractorError(clean_html(payload[0][1:-1]), expected=True)
        return payload


class VKIE(VKBaseIE):
    IE_NAME = 'vk'
    IE_DESC = 'VK'
    _EMBED_REGEX = [r'<iframe[^>]+?src=(["\'])(?P<url>https?://vk(?:(?:video)?\.ru|\.com)/video_ext\.php.+?)\1']
    _VALID_URL = r'''(?x)
                    https?://
                        (?:
                            (?:
                                (?:(?:m|new|vksport)\.)?vk(?:(?:video)?\.ru|\.com)/video_|
                                (?:www\.)?daxab\.com/
                            )
                            ext\.php\?(?P<embed_query>.*?\boid=(?P<oid>-?\d+).*?\bid=(?P<id>\d+).*)|
                            (?:
                                (?:(?:m|new|vksport)\.)?vk(?:(?:video)?\.ru|\.com)/(?:.+?\?.*?z=)?(?:video|clip)|
                                (?:www\.)?daxab\.com/embed/
                            )
                            (?P<videoid>-?\d+_\d+)(?:.*\blist=(?P<list_id>([\da-f]+)|(ln-[\da-zA-Z]+)))?
                        )
                    '''

    _TESTS = [
        {
            'url': 'https://vk.com/videos-77521?z=video-77521_162222515%2Fclub77521',
            'info_dict': {
                'id': '-77521_162222515',
                'ext': 'mp4',
                'title': 'ProtivoGunz - Хуёвая песня',
                'description': 'Видео из официальной группы Noize MC\nhttp://vk.com/noizemc',
                'uploader': 're:(?:Noize MC|Alexander Ilyashenko).*',
                'uploader_id': '39545378',
                'duration': 195,
                'timestamp': 1329049880,
                'upload_date': '20120212',
                'comment_count': int,
                'like_count': int,
                'thumbnail': r're:https?://.+(?:\.jpg|getVideoPreview.*)$',
            },
            'params': {'skip_download': 'm3u8'},
        },
        {
            'url': 'https://vk.com/video205387401_165548505',
            'info_dict': {
                'id': '205387401_165548505',
                'ext': 'mp4',
                'title': 'No name',
                'uploader': 'Tom Cruise',
                'uploader_id': '205387401',
                'duration': 9,
                'timestamp': 1374364108,
                'upload_date': '20130720',
                'comment_count': int,
                'like_count': int,
                'thumbnail': r're:https?://.+(?:\.jpg|getVideoPreview.*)$',
            },
        },
        {
            'note': 'Embedded video',
            'url': 'https://vk.com/video_ext.php?oid=-77521&id=162222515&hash=87b046504ccd8bfa',
            'info_dict': {
                'id': '-77521_162222515',
                'ext': 'mp4',
                'uploader': 're:(?:Noize MC|Alexander Ilyashenko).*',
                'title': 'ProtivoGunz - Хуёвая песня',
                'duration': 195,
                'upload_date': '20120212',
                'timestamp': 1329049880,
                'uploader_id': '39545378',
                'thumbnail': r're:https?://.+(?:\.jpg|getVideoPreview.*)$',
            },
            'params': {'skip_download': 'm3u8'},
        },
        {
            'url': 'https://vk.com/video-93049196_456239755?list=ln-cBjJ7S4jYYx3ADnmDT',
            'info_dict': {
                'id': '-93049196_456239755',
                'ext': 'mp4',
                'title': '8 серия (озвучка)',
                'description': 'Видео из официальной группы Noize MC\nhttp://vk.com/noizemc',
                'duration': 8383,
                'comment_count': int,
                'uploader': 'Dizi2021',
                'like_count': int,
                'timestamp': 1640162189,
                'upload_date': '20211222',
                'uploader_id': '-93049196',
                'thumbnail': r're:https?://.+(?:\.jpg|getVideoPreview.*)$',
            },
        },
        {
            'note': 'youtube embed',
            'url': 'https://vk.com/video276849682_170681728',
            'info_dict': {
                'id': 'V3K4mi0SYkc',
                'ext': 'mp4',
                'title': "DSWD Awards 'Children's Joy Foundation, Inc.' Certificate of Registration and License to Operate",
                'description': 'md5:bf9c26cfa4acdfb146362682edd3827a',
                'duration': 179,
                'upload_date': '20130117',
                'uploader': "Children's Joy Foundation Inc.",
                'uploader_id': '@CJFIofficial',
                'view_count': int,
                'channel_id': 'UCgzCNQ11TmR9V97ECnhi3gw',
                'availability': 'public',
                'like_count': int,
                'live_status': 'not_live',
                'playable_in_embed': True,
                'channel': 'Children\'s Joy Foundation Inc.',
                'uploader_url': 'https://www.youtube.com/@CJFIofficial',
                'thumbnail': r're:https?://.+\.jpg$',
                'tags': 'count:27',
                'start_time': 0.0,
                'categories': ['Nonprofits & Activism'],
                'channel_url': 'https://www.youtube.com/channel/UCgzCNQ11TmR9V97ECnhi3gw',
                'channel_follower_count': int,
                'age_limit': 0,
                'timestamp': 1358394935,
            },
        },
        {
            'note': 'dailymotion embed',
            'url': 'https://vk.com/video-95168827_456239103?list=cca524a0f0d5557e16',
            'info_dict': {
                'id': 'x8gfli0',
                'ext': 'mp4',
                'title': 'md5:45410f60ccd4b2760da98cb5fc777d70',
                'description': 'md5:2e71c5c9413735cfa06cf1a166f16c84',
                'uploader': 'Movies and cinema.',
                'upload_date': '20221218',
                'uploader_id': 'x1jdavv',
                'timestamp': 1671387617,
                'age_limit': 0,
                'duration': 2918,
                'like_count': int,
                'view_count': int,
                'thumbnail': r're:https?://.+x1080$',
                'tags': list,
            },
            'skip': 'This video has been deleted and is no longer available.',
        },
        {
            'url': 'https://vk.com/clips-74006511?z=clip-74006511_456247211',
            'info_dict': {
                'id': '-74006511_456247211',
                'ext': 'mp4',
                'comment_count': int,
                'duration': 9,
                'like_count': int,
                'thumbnail': r're:https?://.+(?:\.jpg|getVideoPreview.*)$',
                'timestamp': 1664995597,
                'title': 'Clip by @madempress',
                'upload_date': '20221005',
                'uploader': 'Шальная Императрица',
                'uploader_id': '-74006511',
                'description': 'md5:f9315f7786fa0e84e75e4f824a48b056',
            },
        },
        {
            # video key is extra_data not url\d+
            'url': 'https://vk.com/video-110305615_171782105',
            'md5': 'e13fcda136f99764872e739d13fac1d1',
            'info_dict': {
                'id': '-110305615_171782105',
                'ext': 'mp4',
                'title': 'S-Dance, репетиции к The way show',
                'uploader': 'THE WAY SHOW | 17 апреля',
                'uploader_id': '-110305615',
                'timestamp': 1454859345,
                'upload_date': '20160207',
            },
            'skip': 'Removed',
        },
        {
            'note': 'finished live stream, postlive_mp4',
            'url': 'https://vk.com/videos-387766?z=video-387766_456242764%2Fpl_-387766_-2',
            'info_dict': {
                'id': '-387766_456242764',
                'ext': 'mp4',
                'title': 'ИгроМир 2016 День 1 — Игромания Утром',
                'uploader': 'Игромания',
                'duration': 5239,
                'upload_date': '20160929',
                'uploader_id': '-387766',
                'timestamp': 1475137527,
                'thumbnail': r're:https?://.+\.jpg$',
                'comment_count': int,
                'like_count': int,
            },
            'params': {
                'skip_download': True,
            },
            'skip': 'No formats found',
        },
        {
            'note': 'video has chapters',
            'url': 'https://vkvideo.ru/video-18403220_456239696',
            'info_dict': {
                'id': '-18403220_456239696',
                'ext': 'mp4',
                'title': 'Трамп отменяет гранты // DeepSeek - Революция в ИИ // Илон Маск читер',
                'description': 'md5:b112ea9de53683b6d03d29076f62eec2',
                'uploader': 'Руслан Усачев',
                'uploader_id': '-18403220',
                'comment_count': int,
                'like_count': int,
                'duration': 1983,
                'thumbnail': r're:https?://.+\.jpg',
                'chapters': 'count:21',
                'timestamp': 1738252883,
                'upload_date': '20250130',
            },
        },
        {
            'url': 'https://vkvideo.ru/video-50883936_456244102',
            'info_dict': {
                'id': '-50883936_456244102',
                'ext': 'mp4',
                'title': 'Добивание Украины // Техник в коме // МОЯ ЗЛОСТЬ №140',
                'description': 'md5:a9bc46181e9ebd0fdd82cef6c0191140',
                'uploader': 'Стас Ай, Как Просто!',
                'uploader_id': '-50883936',
                'comment_count': int,
                'like_count': int,
                'duration': 4651,
                'thumbnail': r're:https?://.+\.jpg',
                'chapters': 'count:59',
                'timestamp': 1743333869,
                'upload_date': '20250330',
            },
        },
        {
            # live stream, hls and rtmp links, most likely already finished live
            # stream by the time you are reading this comment
            'url': 'https://vk.com/video-140332_456239111',
            'only_matching': True,
        },
        {
            # removed video, just testing that we match the pattern
            'url': 'http://vk.com/feed?z=video-43215063_166094326%2Fbb50cacd3177146d7a',
            'only_matching': True,
        },
        {
            # age restricted video, requires vk account credentials
            'url': 'https://vk.com/video205387401_164765225',
            'only_matching': True,
        },
        {
            'url': 'http://new.vk.com/video205387401_165548505',
            'only_matching': True,
        },
        {
            # This video is no longer available, because its author has been blocked.
            'url': 'https://vk.com/video-10639516_456240611',
            'only_matching': True,
        },
        {
            # The video is not available in your region.
            'url': 'https://vk.com/video-51812607_171445436',
            'only_matching': True,
        },
        {
            'url': 'https://vk.com/clip30014565_456240946',
            'only_matching': True,
        },
        {
            'url': 'https://vkvideo.ru/video-127553155_456242961',
            'only_matching': True,
        },
        {
            'url': 'https://vk.ru/video-220754053_456242564',
            'only_matching': True,
        },
        {
            'url': 'https://vksport.vkvideo.ru/video-124096712_456240773',
            'only_matching': True,
        },
    ]

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        video_id = mobj.group('videoid')

        mv_data = {}
        if video_id:
            data = {
                'act': 'show',
                'video': video_id,
            }
            # Some videos (removed?) can only be downloaded with list id specified
            list_id = mobj.group('list_id')
            if list_id:
                data['list'] = list_id

            payload = self._download_payload('al_video', video_id, data)
            info_page = payload[1]
            opts = payload[-1]
            mv_data = opts.get('mvData') or {}
            player = opts.get('player') or {}
        else:
            video_id = '{}_{}'.format(mobj.group('oid'), mobj.group('id'))

            info_page = self._download_webpage(
                'https://vk.com/video_ext.php?' + mobj.group('embed_query'), video_id)

            error_message = self._html_search_regex(
                [r'(?s)<!><div[^>]+class="video_layer_message"[^>]*>(.+?)</div>',
                    r'(?s)<div[^>]+id="video_ext_msg"[^>]*>(.+?)</div>'],
                info_page, 'error message', default=None)
            if error_message:
                raise ExtractorError(error_message, expected=True)

            if re.search(r'<!>/login\.php\?.*\bact=security_check', info_page):
                raise ExtractorError(
                    'You are trying to log in from an unusual location. You should confirm ownership at vk.com to log in with this IP.',
                    expected=True)

            ERROR_COPYRIGHT = 'Video %s has been removed from public access due to rightholder complaint.'

            ERRORS = {
                r'>Видеозапись .*? была изъята из публичного доступа в связи с обращением правообладателя.<':
                ERROR_COPYRIGHT,

                r'>The video .*? was removed from public access by request of the copyright holder.<':
                ERROR_COPYRIGHT,

                r'<!>Please log in or <':
                'Video %s is only available for registered users, '
                'use --username and --password options to provide account credentials.',

                r'<!>Unknown error':
                'Video %s does not exist.',

                r'<!>Видео временно недоступно':
                'Video %s is temporarily unavailable.',

                r'<!>Access denied':
                'Access denied to video %s.',

                r'<!>Видеозапись недоступна, так как её автор был заблокирован.':
                'Video %s is no longer available, because its author has been blocked.',

                r'<!>This video is no longer available, because its author has been blocked.':
                'Video %s is no longer available, because its author has been blocked.',

                r'<!>This video is no longer available, because it has been deleted.':
                'Video %s is no longer available, because it has been deleted.',

                r'<!>The video .+? is not available in your region.':
                'Video %s is not available in your region.',
            }

            for error_re, error_msg in ERRORS.items():
                if re.search(error_re, info_page):
                    raise ExtractorError(error_msg % video_id, expected=True)

            player = self._parse_json(self._search_regex(
                r'var\s+playerParams\s*=\s*({.+?})\s*;\s*\n',
                info_page, 'player params'), video_id)

        youtube_url = YoutubeIE._extract_url(info_page)
        if youtube_url:
            return self.url_result(youtube_url, YoutubeIE.ie_key())

        vimeo_url = VimeoIE._extract_url(url, info_page)
        if vimeo_url is not None:
            return self.url_result(vimeo_url, VimeoIE.ie_key())

        m_rutube = re.search(
            r'\ssrc="((?:https?:)?//rutube\.ru\\?/(?:video|play)\\?/embed(?:.*?))\\?"', info_page)
        if m_rutube is not None:
            rutube_url = self._proto_relative_url(
                m_rutube.group(1).replace('\\', ''))
            return self.url_result(rutube_url)

        dailymotion_url = next(DailymotionIE._extract_embed_urls(url, info_page), None)
        if dailymotion_url:
            return self.url_result(dailymotion_url, DailymotionIE.ie_key())

        odnoklassniki_url = OdnoklassnikiIE._extract_url(info_page)
        if odnoklassniki_url:
            return self.url_result(odnoklassniki_url, OdnoklassnikiIE.ie_key())

        sibnet_url = next(SibnetEmbedIE._extract_embed_urls(url, info_page), None)
        if sibnet_url:
            return self.url_result(sibnet_url)

        m_opts = re.search(r'(?s)var\s+opts\s*=\s*({.+?});', info_page)
        if m_opts:
            m_opts_url = re.search(r"url\s*:\s*'((?!/\b)[^']+)", m_opts.group(1))
            if m_opts_url:
                opts_url = m_opts_url.group(1)
                if opts_url.startswith('//'):
                    opts_url = 'https:' + opts_url
                return self.url_result(opts_url)

        data = player['params'][0]

        # 2 = live
        # 3 = post live (finished live)
        is_live = data.get('live') == 2

        timestamp = unified_timestamp(self._html_search_regex(
            r'class=["\']mv_info_date[^>]+>([^<]+)(?:<|from)', info_page,
            'upload date', default=None)) or int_or_none(data.get('date'))

        view_count = str_to_int(self._search_regex(
            r'class=["\']mv_views_count[^>]+>\s*([\d,.]+)',
            info_page, 'view count', default=None))

        formats = []
        subtitles = {}
        for format_id, format_url in data.items():
            format_url = url_or_none(format_url)
            if not format_url or not format_url.startswith(('http', '//', 'rtmp')):
                continue
            if (format_id.startswith(('url', 'cache'))
                    or format_id in ('extra_data', 'live_mp4', 'postlive_mp4')):
                height = int_or_none(self._search_regex(
                    r'^(?:url|cache)(\d+)', format_id, 'height', default=None))
                formats.append({
                    'format_id': format_id,
                    'url': format_url,
                    'ext': 'mp4',
                    'source_preference': 1,
                    'height': height,
                })
            elif format_id.startswith('hls') and format_id != 'hls_live_playback':
                fmts, subs = self._extract_m3u8_formats_and_subtitles(
                    format_url, video_id, 'mp4', 'm3u8_native',
                    m3u8_id=format_id, fatal=False, live=is_live)
                formats.extend(fmts)
                self._merge_subtitles(subs, target=subtitles)
            elif format_id.startswith('dash') and format_id not in ('dash_live_playback', 'dash_uni'):
                fmts, subs = self._extract_mpd_formats_and_subtitles(
                    format_url, video_id, mpd_id=format_id, fatal=False)
                formats.extend(fmts)
                self._merge_subtitles(subs, target=subtitles)
            elif format_id == 'rtmp':
                formats.append({
                    'format_id': format_id,
                    'url': format_url,
                    'ext': 'flv',
                })

        for sub in data.get('subs') or {}:
            subtitles.setdefault(sub.get('lang', 'en'), []).append({
                'ext': sub.get('title', '.srt').split('.')[-1],
                'url': url_or_none(sub.get('url')),
            })

        return {
            'id': video_id,
            'formats': formats,
            'subtitles': subtitles,
            **traverse_obj(mv_data, {
                'title': ('title', {str}, {unescapeHTML}),
                'description': ('desc', {clean_html}, filter),
                'duration': ('duration', {int_or_none}),
                'like_count': ('likes', {int_or_none}),
                'comment_count': ('commcount', {int_or_none}),
            }),
            **traverse_obj(data, {
                'title': ('md_title', {str}, {unescapeHTML}),
                'description': ('description', {clean_html}, filter),
                'thumbnail': ('jpg', {url_or_none}),
                'uploader': ('md_author', {str}, {unescapeHTML}),
                'uploader_id': (('author_id', 'authorId'), {str_or_none}, any),
                'duration': ('duration', {int_or_none}),
                'chapters': ('time_codes', lambda _, v: isinstance(v['time'], int), {
                    'title': ('text', {str}, {unescapeHTML}),
                    'start_time': 'time',
                }),
            }),
            'timestamp': timestamp,
            'view_count': view_count,
            'is_live': is_live,
            '_format_sort_fields': ('res', 'source'),
        }


class VKUserVideosIE(VKBaseIE):
    IE_NAME = 'vk:uservideos'
    IE_DESC = "VK - User's Videos"
    _BASE_URL_RE = r'https?://(?:(?:m|new)\.)?vk(?:video\.ru|\.com/video)'
    _VALID_URL = [
        rf'{_BASE_URL_RE}/playlist/(?P<id>-?\d+_-?\d+)',
        rf'{_BASE_URL_RE}/(?P<id>@[^/?#]+)(?:/all)?/?(?!\?.*\bz=video)(?:[?#]|$)',
    ]
    _TESTS = [{
        'url': 'https://vk.com/video/@mobidevices',
        'info_dict': {
            'id': '-17892518_all',
        },
        'playlist_mincount': 1355,
    }, {
        'url': 'https://vk.com/video/@mobidevices?section=uploaded',
        'info_dict': {
            'id': '-17892518_uploaded',
        },
        'playlist_mincount': 182,
    }, {
        'url': 'https://vkvideo.ru/playlist/-204353299_426',
        'info_dict': {
            'id': '-204353299_playlist_426',
        },
        'playlist_mincount': 33,
    }, {
        'url': 'https://vk.com/video/@gorkyfilmstudio/all',
        'only_matching': True,
    }, {
        'url': 'https://vkvideo.ru/@mobidevices',
        'only_matching': True,
    }, {
        'url': 'https://vk.com/video/playlist/-174476437_2',
        'only_matching': True,
    }, {
        'url': 'https://vkvideo.ru/playlist/-51890028_-2',
        'only_matching': True,
    }]
    _VIDEO = collections.namedtuple('Video', ['owner_id', 'id'])

    def _entries(self, page_id, section):
        video_list_json = self._download_payload('al_video', page_id, {
            'act': 'load_videos_silent',
            'offset': 0,
            'oid': page_id,
            'section': section,
        })[0][section]
        count = video_list_json['count']
        total = video_list_json['total']
        video_list = video_list_json['list']

        while True:
            for video in video_list:
                v = self._VIDEO._make(video[:2])
                video_id = '%d_%d' % (v.owner_id, v.id)
                yield self.url_result(
                    'https://vk.com/video' + video_id, VKIE.ie_key(), video_id)
            if count >= total:
                break
            video_list_json = self._download_payload('al_video', page_id, {
                'act': 'load_videos_silent',
                'offset': count,
                'oid': page_id,
                'section': section,
            })[0][section]
            new_count = video_list_json['count']
            if not new_count:
                self.to_screen(f'{page_id}: Skipping {total - count} unavailable videos')
                break
            count += new_count
            video_list = video_list_json['list']

    def _real_extract(self, url):
        u_id = self._match_id(url)
        webpage = self._download_webpage(url, u_id)

        if u_id.startswith('@'):
            page_id = traverse_obj(
                self._search_json(r'\bvar newCur\s*=', webpage, 'cursor data', u_id),
                ('oid', {int}, {str_or_none}, {require('page id')}))
            section = traverse_obj(parse_qs(url), ('section', 0)) or 'all'
        else:
            page_id, _, section = u_id.partition('_')
            section = f'playlist_{section}'

        playlist_title = clean_html(get_element_by_class('VideoInfoPanel__title', webpage))
        return self.playlist_result(self._entries(page_id, section), f'{page_id}_{section}', playlist_title)


class VKWallPostIE(VKBaseIE):
    IE_NAME = 'vk:wallpost'
    _VALID_URL = r'https?://(?:(?:(?:(?:m|new)\.)?vk\.com/(?:[^?]+\?.*\bw=)?wall(?P<id>-?\d+_\d+)))'
    _TESTS = [{
        # public page URL, audio playlist
        'url': 'https://vk.com/bs.official?w=wall-23538238_35',
        'info_dict': {
            'id': '-23538238_35',
            'title': 'Black Shadow - Wall post -23538238_35',
            'description': 'md5:190c78f905a53e0de793d83933c6e67f',
        },
        'playlist': [{
            'md5': '5ba93864ec5b85f7ce19a9af4af080f6',
            'info_dict': {
                'id': '135220665_111806521',
                'ext': 'm4a',
                'title': 'Black Shadow - Слепое Верование',
                'duration': 370,
                'uploader': 'Black Shadow',
                'artist': 'Black Shadow',
                'track': 'Слепое Верование',
            },
        }, {
            'md5': '4cc7e804579122b17ea95af7834c9233',
            'info_dict': {
                'id': '135220665_111802303',
                'ext': 'm4a',
                'title': 'Black Shadow - Война - Негасимое Бездны Пламя!',
                'duration': 423,
                'uploader': 'Black Shadow',
                'artist': 'Black Shadow',
                'track': 'Война - Негасимое Бездны Пламя!',
            },
        }],
        'params': {
            'skip_download': True,
        },
    }, {
        # single YouTube embed with irrelevant reaction videos
        'url': 'https://vk.com/wall-32370614_7173954',
        'info_dict': {
            'id': '-32370614_7173954',
            'title': 'md5:9f93c405bbc00061d34007d78c75e3bc',
            'description': 'md5:953b811f26fa9f21ee5856e2ea8e68fc',
        },
        'playlist_count': 1,
    }, {
        # wall page URL
        'url': 'https://vk.com/wall-23538238_35',
        'only_matching': True,
    }, {
        # mobile wall page URL
        'url': 'https://m.vk.com/wall-23538238_35',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        post_id = self._match_id(url)

        webpage = self._download_payload('wkview', post_id, {
            'act': 'show',
            'w': 'wall' + post_id,
        })[1]

        uploader = clean_html(get_element_by_class('PostHeaderTitle__authorName', webpage))

        entries = []

        for audio in re.findall(r'data-audio="([^"]+)', webpage):
            audio = self._parse_json(unescapeHTML(audio), post_id)
            if not audio['url']:
                continue
            title = unescapeHTML(audio.get('title'))
            artist = unescapeHTML(audio.get('artist'))
            entries.append({
                'id': f'{audio["owner_id"]}_{audio["id"]}',
                'title': join_nonempty(artist, title, delim=' - '),
                'thumbnails': try_call(lambda: [{'url': u} for u in audio['coverUrl'].split(',')]),
                'duration': int_or_none(audio.get('duration')),
                'uploader': uploader,
                'artist': artist,
                'track': title,
                'formats': [{
                    'url': self._unmask_audio_url(audio['url'], audio['owner_id']),
                    'ext': 'm4a',
                    'vcodec': 'none',
                    'acodec': 'mp3',
                    'container': 'm4a_dash',
                }],
            })

        entries.extend(self.url_result(urljoin(url, entry), VKIE) for entry in set(re.findall(
            r'<a[^>]+href=(?:["\'])(/video(?:-?[\d_]+)[^"\']*)',
            get_element_html_by_id('wl_post_body', webpage))))

        return self.playlist_result(
            entries, post_id, join_nonempty(uploader, f'Wall post {post_id}', delim=' - '),
            clean_html(get_element_by_class('wall_post_text', webpage)))


class VKAudioIE(VKBaseIE):
    IE_NAME = 'vk:audio'
    IE_DESC = 'VK - Single audio track'
    _VALID_URL = r'https?://(?:(?:m|new)\.)?vk\.com/audio(?P<id>-?\d+_\d+_[a-f0-9]+)'
    _TESTS = [{
        'url': 'https://m.vk.com/audio-2001280873_122880873_4b0d2b43f0e5ba0f71',
        'only_matching': True,
    }, {
        'url': 'https://vk.com/audio-2001280873_122880873_4b0d2b43f0e5ba0f71',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        audio_id = self._match_id(url)
        webpage = self._download_webpage(f'https://m.vk.com/audio{audio_id}', audio_id)

        audio_data = None
        for audio in re.findall(r'data-audio="([^"]+)', webpage):
            audio_json = self._parse_json(unescapeHTML(audio), audio_id)
            if audio_json and audio_json.get('id'):
                audio_data = audio_json
                break

        if not audio_data or not audio_data.get('url'):
            raise ExtractorError('Unable to extract audio data')

        title = unescapeHTML(audio_data.get('title'))
        artist = unescapeHTML(audio_data.get('artist'))
        owner_id = audio_data.get('owner_id')

        return {
            'id': f'{audio_data["owner_id"]}_{audio_data["id"]}',
            'title': join_nonempty(artist, title, delim=' - '),
            'thumbnails': try_call(lambda: [{'url': u} for u in audio_data['coverUrl'].split(',')]),
            'duration': int_or_none(audio_data.get('duration')),
            'artist': artist,
            'track': title,
            'formats': [{
                'url': self._unmask_audio_url(audio_data['url'], owner_id),
                'ext': 'm4a',
                'vcodec': 'none',
                'acodec': 'mp3',
                'container': 'm4a_dash',
            }],
        }


class VKAudiosIE(VKBaseIE):
    IE_NAME = 'vk:audios'
    IE_DESC = "VK - User's or group's audio collection"
    _VALID_URL = r'https?://(?:(?:m|new)\.)?vk\.com/audios(?P<id>-?\d+)'
    _TESTS = [{
        'url': 'https://vk.com/audios-23538238',
        'info_dict': {
            'id': '-23538238',
            'title': 'Audios of -23538238',
        },
        'playlist_mincount': 1,
    }, {
        'url': 'https://m.vk.com/audios-23538238',
        'only_matching': True,
    }]
    _PAGE_SIZE = 100

    def _entries(self, owner_id):
        offset = 0
        while True:
            webpage = self._download_webpage(
                f'https://m.vk.com/audios{owner_id}?offset={offset}', owner_id)

            entries = []
            for audio in re.findall(r'data-audio="([^"]+)', webpage):
                audio_data = self._parse_json(unescapeHTML(audio), owner_id)
                if not audio_data or not audio_data.get('url'):
                    continue

                title = unescapeHTML(audio_data.get('title'))
                artist = unescapeHTML(audio_data.get('artist'))
                audio_owner_id = audio_data.get('owner_id')

                entries.append({
                    'id': f'{audio_data["owner_id"]}_{audio_data["id"]}',
                    'title': join_nonempty(artist, title, delim=' - '),
                    'thumbnails': try_call(lambda: [{'url': u} for u in audio_data['coverUrl'].split(',')]),
                    'duration': int_or_none(audio_data.get('duration')),
                    'artist': artist,
                    'track': title,
                    'formats': [{
                        'url': self._unmask_audio_url(audio_data['url'], audio_owner_id),
                        'ext': 'm4a',
                        'vcodec': 'none',
                        'acodec': 'mp3',
                        'container': 'm4a_dash',
                    }],
                })

            if not entries:
                break

            for entry in entries:
                yield entry

            offset += self._PAGE_SIZE

            # Check if there are more pages
            if len(entries) < self._PAGE_SIZE:
                break

    def _real_extract(self, url):
        owner_id = self._match_id(url)
        return self.playlist_result(
            self._entries(owner_id), owner_id, f'Audios of {owner_id}')


class VKMusicPlaylistIE(VKBaseIE):
    IE_NAME = 'vk:music:playlist'
    IE_DESC = 'VK - Music playlist/album'
    _VALID_URL = r'''(?x)
        https?://(?:(?:m|new)\.)?vk\.com/
        (?:
            music/playlist/(?P<owner_id>-?\d+)_(?P<playlist_id>\d+)(?:_(?P<access_hash>[a-f0-9]+))?|
            audio\?.*?z=audio_playlist(?P<legacy_id>-?\d+_\d+)(?:%2F|%2f|/)(?P<legacy_hash>[a-f0-9]+)?
        )
    '''
    _TESTS = [{
        'url': 'https://vk.com/music/playlist/-23538238_12345',
        'only_matching': True,
    }, {
        'url': 'https://vk.com/audio?z=audio_playlist-23538238_12345%2Fabcdef123',
        'only_matching': True,
    }, {
        'url': 'https://m.vk.com/music/playlist/-23538238_12345',
        'only_matching': True,
    }]
    _PAGE_SIZE = 100

    def _entries(self, owner_id, playlist_id, access_hash=None):
        offset = 0
        while True:
            url = f'https://m.vk.com/music/playlist/{owner_id}_{playlist_id}?offset={offset}'
            if access_hash:
                url += f'&access_hash={access_hash}'

            webpage = self._download_webpage(url, f'{owner_id}_{playlist_id}')

            entries = []
            for audio in re.findall(r'data-audio="([^"]+)', webpage):
                audio_data = self._parse_json(unescapeHTML(audio), f'{owner_id}_{playlist_id}')
                if not audio_data or not audio_data.get('url'):
                    continue

                title = unescapeHTML(audio_data.get('title'))
                artist = unescapeHTML(audio_data.get('artist'))
                audio_owner_id = audio_data.get('owner_id')

                entries.append({
                    'id': f'{audio_data["owner_id"]}_{audio_data["id"]}',
                    'title': join_nonempty(artist, title, delim=' - '),
                    'thumbnails': try_call(lambda: [{'url': u} for u in audio_data['coverUrl'].split(',')]),
                    'duration': int_or_none(audio_data.get('duration')),
                    'artist': artist,
                    'track': title,
                    'formats': [{
                        'url': self._unmask_audio_url(audio_data['url'], audio_owner_id),
                        'ext': 'm4a',
                        'vcodec': 'none',
                        'acodec': 'mp3',
                        'container': 'm4a_dash',
                    }],
                })

            if not entries:
                break

            for entry in entries:
                yield entry

            offset += self._PAGE_SIZE

            if len(entries) < self._PAGE_SIZE:
                break

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        legacy_id = mobj.group('legacy_id')

        if legacy_id:
            owner_id, playlist_id = legacy_id.split('_')
            access_hash = mobj.group('legacy_hash')
        else:
            owner_id = mobj.group('owner_id')
            playlist_id = mobj.group('playlist_id')
            access_hash = mobj.group('access_hash')

        playlist_id = f'{owner_id}_{playlist_id}'

        # Try to get playlist title from the page
        webpage = self._download_webpage(
            f'https://m.vk.com/music/playlist/{playlist_id}', playlist_id, fatal=False)
        title = None
        if webpage:
            title = clean_html(get_element_by_class('AudioPlaylist__title', webpage))

        return self.playlist_result(
            self._entries(owner_id, playlist_id.split('_')[1], access_hash),
            playlist_id, title or f'Playlist {playlist_id}')


class VKMusicAlbumsIE(VKBaseIE):
    IE_NAME = 'vk:music:albums'
    IE_DESC = "VK - User's or group's playlists/albums"
    _VALID_URL = r'https?://(?:(?:m|new)\.)?vk\.com/audio\?act=audio_playlists(?P<id>-?\d+)'
    _TESTS = [{
        'url': 'https://vk.com/audio?act=audio_playlists-23538238',
        'only_matching': True,
    }, {
        'url': 'https://m.vk.com/audio?act=audio_playlists-23538238',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        owner_id = self._match_id(url)
        webpage = self._download_webpage(
            f'https://m.vk.com/audio?act=audio_playlists{owner_id}', owner_id)

        entries = []
        # Look for playlist links in the page
        for playlist_match in re.finditer(
                r'href="/music/playlist/(?P<playlist_id>-?\d+_\d+)(?:\?|"|#)',
                webpage):
            playlist_id = playlist_match.group('playlist_id')
            entries.append(self.url_result(
                f'https://vk.com/music/playlist/{playlist_id}',
                VKMusicPlaylistIE.ie_key(), playlist_id))

        return self.playlist_result(entries, owner_id, f'Playlists of {owner_id}')


class VKPlayBaseIE(InfoExtractor):
    _BASE_URL_RE = r'https?://(?:vkplay\.live|live\.vk(?:play|video)\.ru)/'
    _RESOLUTIONS = {
        'tiny': '256x144',
        'lowest': '426x240',
        'low': '640x360',
        'medium': '852x480',
        'high': '1280x720',
        'full_hd': '1920x1080',
        'quad_hd': '2560x1440',
    }

    def _extract_from_initial_state(self, url, video_id, path):
        webpage = self._download_webpage(url, video_id)
        video_info = traverse_obj(self._search_json(
            r'<script[^>]+\bid="initial-state"[^>]*>', webpage, 'initial state', video_id),
            path, expected_type=dict)
        if not video_info:
            raise ExtractorError('Unable to extract video info from html inline initial state')
        return video_info

    def _extract_formats(self, stream_info, video_id):
        formats = []
        for stream in traverse_obj(stream_info, (
                'data', 0, 'playerUrls', lambda _, v: url_or_none(v['url']) and v['type'])):
            url = stream['url']
            format_id = str_or_none(stream['type'])
            if format_id in ('hls', 'live_hls', 'live_playback_hls') or '.m3u8' in url:
                formats.extend(self._extract_m3u8_formats(url, video_id, m3u8_id=format_id, fatal=False))
            elif format_id == 'dash':
                formats.extend(self._extract_mpd_formats(url, video_id, mpd_id=format_id, fatal=False))
            elif format_id in ('live_dash', 'live_playback_dash'):
                self.write_debug(f'Not extracting unsupported format "{format_id}"')
            else:
                formats.append({
                    'url': url,
                    'ext': 'mp4',
                    'format_id': format_id,
                    **parse_resolution(self._RESOLUTIONS.get(format_id)),
                })
        return formats

    def _extract_common_meta(self, stream_info):
        return traverse_obj(stream_info, {
            'id': ('id', {str_or_none}),
            'title': ('title', {str}),
            'release_timestamp': ('startTime', {int_or_none}),
            'thumbnail': ('previewUrl', {url_or_none}),
            'view_count': ('count', 'views', {int_or_none}),
            'like_count': ('count', 'likes', {int_or_none}),
            'categories': ('category', 'title', {str}, {lambda x: [x] if x else None}),
            'uploader': (('user', ('blog', 'owner')), 'nick', {str}),
            'uploader_id': (('user', ('blog', 'owner')), 'id', {str_or_none}),
            'duration': ('duration', {int_or_none}),
            'is_live': ('isOnline', {bool}),
            'concurrent_view_count': ('count', 'viewers', {int_or_none}),
        }, get_all=False)


class VKPlayIE(VKPlayBaseIE):
    _VALID_URL = rf'{VKPlayBaseIE._BASE_URL_RE}(?P<username>[^/#?]+)/record/(?P<id>[\da-f-]+)'
    _TESTS = [{
        'url': 'https://vkplay.live/zitsmann/record/f5e6e3b5-dc52-4d14-965d-0680dd2882da',
        'info_dict': {
            'id': 'f5e6e3b5-dc52-4d14-965d-0680dd2882da',
            'ext': 'mp4',
            'title': 'Atomic Heart (пробуем!) спасибо подписчику EKZO!',
            'uploader': 'ZitsmanN',
            'uploader_id': '13159830',
            'release_timestamp': 1683461378,
            'release_date': '20230507',
            'thumbnail': r're:https://[^/]+/public_video_stream/record/f5e6e3b5-dc52-4d14-965d-0680dd2882da/preview',
            'duration': 10608,
            'view_count': int,
            'like_count': int,
            'categories': ['Atomic Heart'],
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://live.vkplay.ru/lebwa/record/33a4e4ce-e3ef-49db-bb14-f006cc6fabc9/records',
        'only_matching': True,
    }, {
        'url': 'https://live.vkvideo.ru/lebwa/record/33a4e4ce-e3ef-49db-bb14-f006cc6fabc9/records',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        username, video_id = self._match_valid_url(url).groups()

        record_info = traverse_obj(self._download_json(
            f'https://api.vkplay.live/v1/blog/{username}/public_video_stream/record/{video_id}', video_id, fatal=False),
            ('data', 'record', {dict}))
        if not record_info:
            record_info = self._extract_from_initial_state(url, video_id, ('record', 'currentRecord', 'data'))

        return {
            **self._extract_common_meta(record_info),
            'id': video_id,
            'formats': self._extract_formats(record_info, video_id),
        }


class VKPlayLiveIE(VKPlayBaseIE):
    _VALID_URL = rf'{VKPlayBaseIE._BASE_URL_RE}(?P<id>[^/#?]+)/?(?:[#?]|$)'
    _TESTS = [{
        'url': 'https://vkplay.live/bayda',
        'info_dict': {
            'id': 'f02c321e-427b-408d-b12f-ae34e53e0ea2',
            'ext': 'mp4',
            'title': r're:эскапизм крута .*',
            'uploader': 'Bayda',
            'uploader_id': '12279401',
            'release_timestamp': 1687209962,
            'release_date': '20230619',
            'thumbnail': r're:https://[^/]+/public_video_stream/12279401/preview',
            'view_count': int,
            'concurrent_view_count': int,
            'like_count': int,
            'categories': ['EVE Online'],
            'live_status': 'is_live',
        },
        'skip': 'livestream',
        'params': {'skip_download': True},
    }, {
        'url': 'https://live.vkplay.ru/lebwa',
        'only_matching': True,
    }, {
        'url': 'https://live.vkvideo.ru/panterka',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        username = self._match_id(url)

        stream_info = self._download_json(
            f'https://api.vkplay.live/v1/blog/{username}/public_video_stream', username, fatal=False)
        if not stream_info:
            stream_info = self._extract_from_initial_state(url, username, ('stream', 'stream', 'data', 'stream'))

        formats = self._extract_formats(stream_info, username)
        if not formats and not traverse_obj(stream_info, ('isOnline', {bool})):
            raise UserNotLive(video_id=username)

        return {
            **self._extract_common_meta(stream_info),
            'formats': formats,
        }


class VKAudioIE(VKBaseIE):
    IE_NAME = 'vk:audio'
    IE_DESC = 'VK Music - Single audio track'
    _VALID_URL = r'https?://(?:(?:m|new)\.)?vk\.com/audio(?P<id>-?\d+_\d+_[a-f0-9]+)'
    _TESTS = [{
        'url': 'https://vk.com/audio147077690_456242502_d1585835ba07303880',
        'only_matching': True,
    }, {
        'url': 'https://m.vk.com/audio268477373_456240878_506fca1eb4b2be42c8',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        audio_id = self._match_id(url)
        # Extract owner_id and audio_id from the full ID
        parts = audio_id.split('_')
        owner_id = parts[0]
        track_id = parts[1]
        
        webpage = self._download_webpage(f'https://m.vk.com/audio{audio_id}', audio_id)
        
        # Find audio data in the page
        audio_data = None
        for audio in re.findall(r'data-audio="([^"]+)', webpage):
            try:
                data = self._parse_json(unescapeHTML(audio), audio_id)
                if str(data.get('owner_id')) == owner_id and str(data.get('id')) == track_id:
                    audio_data = data
                    break
            except Exception:
                continue
        
        if not audio_data:
            raise ExtractorError('Could not find audio data in page')
        
        title = unescapeHTML(audio_data.get('title', ''))
        artist = unescapeHTML(audio_data.get('artist', ''))
        audio_url = audio_data.get('url', '')
        
        # Unmask the URL if needed
        if audio_url and 'audio_api_unavailable' in audio_url:
            vk_id = int(owner_id)
            audio_url = self._unmask_audio_url(audio_url, vk_id)
        
        return {
            'id': f'{owner_id}_{track_id}',
            'title': join_nonempty(artist, title, delim=' - '),
            'artist': artist,
            'track': title,
            'duration': int_or_none(audio_data.get('duration')),
            'thumbnails': try_call(lambda: [{'url': u} for u in audio_data['coverUrl'].split(',')]),
            'formats': [{
                'url': audio_url,
                'ext': 'm4a',
                'vcodec': 'none',
                'acodec': 'mp3',
                'container': 'm4a_dash',
            }] if audio_url else [],
        }


class VKAudiosIE(VKBaseIE):
    IE_NAME = 'vk:audios'
    IE_DESC = "VK Music - User's or group's audio collection"
    _VALID_URL = r'https?://(?:(?:m|new)\.)?vk\.com/audios(?P<id>-?\d+)'
    _TESTS = [{
        'url': 'https://vk.com/audios-173441691',
        'only_matching': True,
    }, {
        'url': 'https://vk.com/audios573558507',
        'only_matching': True,
    }]

    def _entries(self, owner_id):
        offset = 0
        while True:
            webpage = self._download_webpage(
                f'https://m.vk.com/audios{owner_id}', 
                owner_id,
                query={'offset': offset}
            )
            
            entries = []
            for audio in re.findall(r'data-audio="([^"]+)', webpage):
                try:
                    data = self._parse_json(unescapeHTML(audio), owner_id)
                    if not data.get('url'):
                        continue
                    
                    title = unescapeHTML(data.get('title', ''))
                    artist = unescapeHTML(data.get('artist', ''))
                    audio_url = data.get('url', '')
                    track_owner_id = str(data.get('owner_id', ''))
                    track_id = str(data.get('id', ''))
                    
                    # Unmask the URL if needed
                    if audio_url and 'audio_api_unavailable' in audio_url:
                        vk_id = int(track_owner_id)
                        audio_url = self._unmask_audio_url(audio_url, vk_id)
                    
                    entries.append({
                        'id': f'{track_owner_id}_{track_id}',
                        'title': join_nonempty(artist, title, delim=' - '),
                        'artist': artist,
                        'track': title,
                        'duration': int_or_none(data.get('duration')),
                        'thumbnails': try_call(lambda: [{'url': u} for u in data['coverUrl'].split(',')]),
                        'formats': [{
                            'url': audio_url,
                            'ext': 'm4a',
                            'vcodec': 'none',
                            'acodec': 'mp3',
                            'container': 'm4a_dash',
                        }],
                    })
                except Exception:
                    continue
            
            if not entries:
                break
            
            for entry in entries:
                yield entry
            
            offset += len(entries)
            
            # Check if there are more tracks
            if len(entries) < 20:  # Typical page size
                break

    def _real_extract(self, url):
        owner_id = self._match_id(url)
        return self.playlist_result(self._entries(owner_id), owner_id)


class VKMusicPlaylistIE(VKBaseIE):
    IE_NAME = 'vk:music:playlist'
    IE_DESC = 'VK Music - Playlist/Album'
    _VALID_URL = [
        r'https?://(?:(?:m|new)\.)?vk\.com/music/playlist/(?P<id>-?\d+_\d+)',
        r'https?://(?:(?:m|new)\.)?vk\.com/audio\?.*?z=audio_playlist(?P<id>-?\d+_\d+)',
    ]
    _TESTS = [{
        'url': 'https://vk.com/music/playlist/-173441691_44',
        'only_matching': True,
    }, {
        'url': 'https://vk.com/music/playlist/573558507_20',
        'only_matching': True,
    }, {
        'url': 'https://vk.com/audio?z=audio_playlist573558507_20',
        'only_matching': True,
    }]

    def _entries(self, owner_id, playlist_id):
        offset = 0
        while True:
            webpage = self._download_webpage(
                f'https://m.vk.com/audio',
                f'{owner_id}_{playlist_id}',
                query={
                    'act': 'audio_playlist',
                    'owner_id': owner_id,
                    'playlist_id': playlist_id,
                    'offset': offset
                }
            )
            
            entries = []
            for audio in re.findall(r'data-audio="([^"]+)', webpage):
                try:
                    data = self._parse_json(unescapeHTML(audio), f'{owner_id}_{playlist_id}')
                    if not data.get('url'):
                        continue
                    
                    title = unescapeHTML(data.get('title', ''))
                    artist = unescapeHTML(data.get('artist', ''))
                    audio_url = data.get('url', '')
                    track_owner_id = str(data.get('owner_id', ''))
                    track_id = str(data.get('id', ''))
                    
                    # Unmask the URL if needed
                    if audio_url and 'audio_api_unavailable' in audio_url:
                        vk_id = int(track_owner_id)
                        audio_url = self._unmask_audio_url(audio_url, vk_id)
                    
                    entries.append({
                        'id': f'{track_owner_id}_{track_id}',
                        'title': join_nonempty(artist, title, delim=' - '),
                        'artist': artist,
                        'track': title,
                        'duration': int_or_none(data.get('duration')),
                        'thumbnails': try_call(lambda: [{'url': u} for u in data['coverUrl'].split(',')]),
                        'formats': [{
                            'url': audio_url,
                            'ext': 'm4a',
                            'vcodec': 'none',
                            'acodec': 'mp3',
                            'container': 'm4a_dash',
                        }],
                    })
                except Exception:
                    continue
            
            if not entries:
                break
            
            for entry in entries:
                yield entry
            
            offset += len(entries)
            
            if len(entries) < 20:
                break

    def _real_extract(self, url):
        playlist_id = self._match_id(url)
        owner_id, _, pl_id = playlist_id.partition('_')
        
        webpage = self._download_webpage(url, playlist_id)
        
        # Try to extract playlist title
        playlist_title = self._html_search_regex(
            r'class=["\']audioPlaylistSnippet__title["\'][^\u003e]*\u003e([^\u003c]+)',
            webpage, 'playlist title', default=None)
        
        return self.playlist_result(
            self._entries(owner_id, pl_id), 
            playlist_id,
            playlist_title
        )


class VKMusicAlbumsIE(VKBaseIE):
    IE_NAME = 'vk:music:albums'
    IE_DESC = "VK Music - User's or group's playlists/albums list"
    _VALID_URL = r'https?://(?:(?:m|new)\.)?vk\.com/audio\?act=audio_playlists(?P<id>-?\d+)'
    _TESTS = [{
        'url': 'https://vk.com/audio?act=audio_playlists573558507',
        'only_matching': True,
    }, {
        'url': 'https://vk.com/audio?act=audio_playlists-173441691',
        'only_matching': True,
    }]

    def _entries(self, owner_id):
        offset = 0
        while True:
            webpage = self._download_webpage(
                f'https://m.vk.com/audio?act=audio_playlists{owner_id}',
                owner_id,
                query={'offset': offset}
            )
            
            # Find album/playlist links
            albums = re.findall(
                r'href=["\'][^"\']*audio_playlist(-?\d+_\d+)["\']',
                webpage
            )
            
            if not albums:
                break
            
            for album_id in set(albums):
                yield self.url_result(
                    f'https://vk.com/music/playlist/{album_id}',
                    VKMusicPlaylistIE.ie_key(),
                    album_id
                )
            
            offset += len(set(albums))
            
            if len(set(albums)) < 10:
                break

    def _real_extract(self, url):
        owner_id = self._match_id(url)
        return self.playlist_result(self._entries(owner_id), owner_id)
