import collections
import hashlib
import re

from .common import InfoExtractor
from .dailymotion import DailymotionIE
from .odnoklassniki import OdnoklassnikiIE
from .pladform import PladformIE
from .sibnet import SibnetEmbedIE
from .vimeo import VimeoIE
from .youtube import YoutubeIE
from ..utils import (
    ExtractorError,
    UserNotLive,
    clean_html,
    get_element_by_class,
    get_element_html_by_id,
    int_or_none,
    join_nonempty,
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
    traverse_obj,
)


class VKBaseIE(InfoExtractor):
    _NETRC_MACHINE = 'vk'

    def _download_webpage_handle(self, url_or_request, video_id, *args, fatal=True, **kwargs):
        response = super()._download_webpage_handle(url_or_request, video_id, *args, fatal=fatal, **kwargs)
        challenge_url, cookie = response[1].url if response else '', None
        if challenge_url.startswith('https://vk.com/429.html?'):
            cookie = self._get_cookies(challenge_url).get('hash429')
        if not cookie:
            return response

        hash429 = hashlib.md5(cookie.value.encode('ascii')).hexdigest()
        self._request_webpage(
            update_url_query(challenge_url, {'key': hash429}), video_id, fatal=fatal,
            note='Resolving WAF challenge', errnote='Failed to bypass WAF challenge')
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
    _EMBED_REGEX = [r'<iframe[^>]+?src=(["\'])(?P<url>https?://vk\.com/video_ext\.php.+?)\1']
    _VALID_URL = r'''(?x)
                    https?://
                        (?:
                            (?:
                                (?:(?:m|new)\.)?vk\.com/video_|
                                (?:www\.)?daxab\.com/
                            )
                            ext\.php\?(?P<embed_query>.*?\boid=(?P<oid>-?\d+).*?\bid=(?P<id>\d+).*)|
                            (?:
                                (?:(?:m|new)\.)?vk\.com/(?:.+?\?.*?z=)?(?:video|clip)|
                                (?:www\.)?daxab\.com/embed/
                            )
                            (?P<videoid>-?\d+_\d+)(?:.*\blist=(?P<list_id>([\da-f]+)|(ln-[\da-zA-Z]+)))?
                        )
                    '''

    _TESTS = [
        {
            'url': 'http://vk.com/videos-77521?z=video-77521_162222515%2Fclub77521',
            'info_dict': {
                'id': '-77521_162222515',
                'ext': 'mp4',
                'title': 'ProtivoGunz - Хуёвая песня',
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
            'url': 'http://vk.com/video205387401_165548505',
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
            }
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
                'duration': 178,
                'upload_date': '20130117',
                'uploader': "Children's Joy Foundation Inc.",
                'uploader_id': 'thecjf',
                'view_count': int,
                'channel_id': 'UCgzCNQ11TmR9V97ECnhi3gw',
                'availability': 'public',
                'like_count': int,
                'live_status': 'not_live',
                'playable_in_embed': True,
                'channel': 'Children\'s Joy Foundation Inc.',
                'uploader_url': 'http://www.youtube.com/user/thecjf',
                'thumbnail': r're:https?://.+\.jpg$',
                'tags': 'count:27',
                'start_time': 0.0,
                'categories': ['Nonprofits & Activism'],
                'channel_url': 'https://www.youtube.com/channel/UCgzCNQ11TmR9V97ECnhi3gw',
                'channel_follower_count': int,
                'age_limit': 0,
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
                'tags': list
            },
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
                'uploader': 'Шальная императрица',
                'uploader_id': '-74006511',
            },
        },
        {
            # video key is extra_data not url\d+
            'url': 'http://vk.com/video-110305615_171782105',
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
            # pladform embed
            'url': 'https://vk.com/video-76116461_171554880',
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
        }]

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
            video_id = '%s_%s' % (mobj.group('oid'), mobj.group('id'))

            info_page = self._download_webpage(
                'http://vk.com/video_ext.php?' + mobj.group('embed_query'), video_id)

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

        pladform_url = PladformIE._extract_url(info_page)
        if pladform_url:
            return self.url_result(pladform_url, PladformIE.ie_key())

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
                    opts_url = 'http:' + opts_url
                return self.url_result(opts_url)

        data = player['params'][0]
        title = unescapeHTML(data['md_title'])

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
                    'height': height,
                })
            elif format_id == 'hls':
                formats.extend(self._extract_m3u8_formats(
                    format_url, video_id, 'mp4', 'm3u8_native',
                    m3u8_id=format_id, fatal=False, live=is_live))
            elif format_id == 'rtmp':
                formats.append({
                    'format_id': format_id,
                    'url': format_url,
                    'ext': 'flv',
                })

        subtitles = {}
        for sub in data.get('subs') or {}:
            subtitles.setdefault(sub.get('lang', 'en'), []).append({
                'ext': sub.get('title', '.srt').split('.')[-1],
                'url': url_or_none(sub.get('url')),
            })

        return {
            'id': video_id,
            'formats': formats,
            'title': title,
            'thumbnail': data.get('jpg'),
            'uploader': data.get('md_author'),
            'uploader_id': str_or_none(data.get('author_id') or mv_data.get('authorId')),
            'duration': int_or_none(data.get('duration') or mv_data.get('duration')),
            'timestamp': timestamp,
            'view_count': view_count,
            'like_count': int_or_none(mv_data.get('likes')),
            'comment_count': int_or_none(mv_data.get('commcount')),
            'is_live': is_live,
            'subtitles': subtitles,
        }


class VKUserVideosIE(VKBaseIE):
    IE_NAME = 'vk:uservideos'
    IE_DESC = "VK - User's Videos"
    _VALID_URL = r'https?://(?:(?:m|new)\.)?vk\.com/video/(?:playlist/)?(?P<id>[^?$#/&]+)(?!\?.*\bz=video)(?:[/?#&](?:.*?\bsection=(?P<section>\w+))?|$)'
    _TEMPLATE_URL = 'https://vk.com/videos'
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
        'url': 'https://vk.com/video/playlist/-174476437_2',
        'info_dict': {
            'id': '-174476437_playlist_2',
            'title': 'Анонсы'
        },
        'playlist_mincount': 108,
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
                    'http://vk.com/video' + video_id, VKIE.ie_key(), video_id)
            if count >= total:
                break
            video_list_json = self._download_payload('al_video', page_id, {
                'act': 'load_videos_silent',
                'offset': count,
                'oid': page_id,
                'section': section,
            })[0][section]
            count += video_list_json['count']
            video_list = video_list_json['list']

    def _real_extract(self, url):
        u_id, section = self._match_valid_url(url).groups()
        webpage = self._download_webpage(url, u_id)

        if u_id.startswith('@'):
            page_id = self._search_regex(r'data-owner-id\s?=\s?"([^"]+)"', webpage, 'page_id')
        elif '_' in u_id:
            page_id, section = u_id.split('_', 1)
            section = f'playlist_{section}'
        else:
            raise ExtractorError('Invalid URL', expected=True)

        if not section:
            section = 'all'

        playlist_title = clean_html(get_element_by_class('VideoInfoPanel__title', webpage))
        return self.playlist_result(self._entries(page_id, section), '%s_%s' % (page_id, section), playlist_title)


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
    _BASE64_CHARS = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMN0PQRSTUVWXYZO123456789+/='
    _AUDIO = collections.namedtuple('Audio', ['id', 'owner_id', 'url', 'title', 'performer', 'duration', 'album_id', 'unk', 'author_link', 'lyrics', 'flags', 'context', 'extra', 'hashes', 'cover_url', 'ads'])

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

    def _unmask_url(self, mask_url, vk_id):
        if 'audio_api_unavailable' in mask_url:
            extra = mask_url.split('?extra=')[1].split('#')
            func, base = self._decode(extra[1]).split(chr(11))
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
                    'url': audio['url'],
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


class VKPlayBaseIE(InfoExtractor):
    _BASE_URL_RE = r'https?://(?:vkplay\.live|live\.vkplay\.ru)/'
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
