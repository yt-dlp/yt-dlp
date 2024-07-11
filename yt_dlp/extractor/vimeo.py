import base64
import functools
import itertools
import json
import re
import urllib.parse

from .common import InfoExtractor
from ..networking import HEADRequest, Request
from ..networking.exceptions import HTTPError
from ..utils import (
    ExtractorError,
    OnDemandPagedList,
    clean_html,
    determine_ext,
    get_element_by_class,
    int_or_none,
    join_nonempty,
    js_to_json,
    merge_dicts,
    parse_filesize,
    parse_iso8601,
    parse_qs,
    smuggle_url,
    str_or_none,
    traverse_obj,
    try_get,
    unified_timestamp,
    unsmuggle_url,
    urlencode_postdata,
    urlhandle_detect_ext,
    urljoin,
)


class VimeoBaseInfoExtractor(InfoExtractor):
    _NETRC_MACHINE = 'vimeo'
    _LOGIN_REQUIRED = False
    _LOGIN_URL = 'https://vimeo.com/log_in'

    @staticmethod
    def _smuggle_referrer(url, referrer_url):
        return smuggle_url(url, {'referer': referrer_url})

    def _unsmuggle_headers(self, url):
        """@returns (url, smuggled_data, headers)"""
        url, data = unsmuggle_url(url, {})
        headers = self.get_param('http_headers').copy()
        if 'referer' in data:
            headers['Referer'] = data['referer']
        return url, data, headers

    def _perform_login(self, username, password):
        viewer = self._download_json('https://vimeo.com/_next/viewer', None, 'Downloading login token')
        data = {
            'action': 'login',
            'email': username,
            'password': password,
            'service': 'vimeo',
            'token': viewer['xsrft'],
        }
        self._set_vimeo_cookie('vuid', viewer['vuid'])
        try:
            self._download_webpage(
                self._LOGIN_URL, None, 'Logging in',
                data=urlencode_postdata(data), headers={
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Referer': self._LOGIN_URL,
                })
        except ExtractorError as e:
            if isinstance(e.cause, HTTPError) and e.cause.status == 418:
                raise ExtractorError(
                    'Unable to log in: bad username or password',
                    expected=True)
            raise ExtractorError('Unable to log in')

    def _real_initialize(self):
        if self._LOGIN_REQUIRED and not self._get_cookies('https://vimeo.com').get('vuid'):
            self._raise_login_required()

    def _get_video_password(self):
        password = self.get_param('videopassword')
        if password is None:
            raise ExtractorError(
                'This video is protected by a password, use the --video-password option',
                expected=True)
        return password

    def _verify_video_password(self, video_id, password, token):
        url = f'https://vimeo.com/{video_id}'
        try:
            return self._download_webpage(
                f'{url}/password', video_id,
                'Submitting video password', data=json.dumps({
                    'password': password,
                    'token': token,
                }, separators=(',', ':')).encode(), headers={
                    'Accept': '*/*',
                    'Content-Type': 'application/json',
                    'Referer': url,
                }, impersonate=True)
        except ExtractorError as error:
            if isinstance(error.cause, HTTPError) and error.cause.status == 418:
                raise ExtractorError('Wrong password', expected=True)
            raise

    def _extract_vimeo_config(self, webpage, video_id, *args, **kwargs):
        vimeo_config = self._search_regex(
            r'vimeo\.config\s*=\s*(?:({.+?})|_extend\([^,]+,\s+({.+?})\));',
            webpage, 'vimeo config', *args, **kwargs)
        if vimeo_config:
            return self._parse_json(vimeo_config, video_id)

    def _set_vimeo_cookie(self, name, value):
        self._set_cookie('vimeo.com', name, value)

    def _parse_config(self, config, video_id):
        video_data = config['video']
        video_title = video_data.get('title')
        live_event = video_data.get('live_event') or {}
        live_status = {
            'pending': 'is_upcoming',
            'active': 'is_upcoming',
            'started': 'is_live',
            'ended': 'post_live',
        }.get(live_event.get('status'))
        is_live = live_status == 'is_live'
        request = config.get('request') or {}

        formats = []
        subtitles = {}

        config_files = video_data.get('files') or request.get('files') or {}
        for f in (config_files.get('progressive') or []):
            video_url = f.get('url')
            if not video_url:
                continue
            formats.append({
                'url': video_url,
                'format_id': 'http-{}'.format(f.get('quality')),
                'source_preference': 10,
                'width': int_or_none(f.get('width')),
                'height': int_or_none(f.get('height')),
                'fps': int_or_none(f.get('fps')),
                'tbr': int_or_none(f.get('bitrate')),
            })

        # TODO: fix handling of 308 status code returned for live archive manifest requests
        sep_pattern = r'/sep/video/'
        for files_type in ('hls', 'dash'):
            for cdn_name, cdn_data in (try_get(config_files, lambda x: x[files_type]['cdns']) or {}).items():
                manifest_url = cdn_data.get('url')
                if not manifest_url:
                    continue
                format_id = f'{files_type}-{cdn_name}'
                sep_manifest_urls = []
                if re.search(sep_pattern, manifest_url):
                    for suffix, repl in (('', 'video'), ('_sep', 'sep/video')):
                        sep_manifest_urls.append((format_id + suffix, re.sub(
                            sep_pattern, f'/{repl}/', manifest_url)))
                else:
                    sep_manifest_urls = [(format_id, manifest_url)]
                for f_id, m_url in sep_manifest_urls:
                    if files_type == 'hls':
                        fmts, subs = self._extract_m3u8_formats_and_subtitles(
                            m_url, video_id, 'mp4', live=is_live, m3u8_id=f_id,
                            note=f'Downloading {cdn_name} m3u8 information',
                            fatal=False)
                        formats.extend(fmts)
                        self._merge_subtitles(subs, target=subtitles)
                    elif files_type == 'dash':
                        if 'json=1' in m_url:
                            real_m_url = (self._download_json(m_url, video_id, fatal=False) or {}).get('url')
                            if real_m_url:
                                m_url = real_m_url
                        fmts, subs = self._extract_mpd_formats_and_subtitles(
                            m_url.replace('/master.json', '/master.mpd'), video_id, f_id,
                            f'Downloading {cdn_name} MPD information',
                            fatal=False)
                        formats.extend(fmts)
                        self._merge_subtitles(subs, target=subtitles)

        live_archive = live_event.get('archive') or {}
        live_archive_source_url = live_archive.get('source_url')
        if live_archive_source_url and live_archive.get('status') == 'done':
            formats.append({
                'format_id': 'live-archive-source',
                'url': live_archive_source_url,
                'quality': 10,
            })

        for tt in (request.get('text_tracks') or []):
            subtitles.setdefault(tt['lang'], []).append({
                'ext': 'vtt',
                'url': urljoin('https://vimeo.com', tt['url']),
            })

        thumbnails = []
        if not is_live:
            for key, thumb in (video_data.get('thumbs') or {}).items():
                thumbnails.append({
                    'id': key,
                    'width': int_or_none(key),
                    'url': thumb,
                })
            thumbnail = video_data.get('thumbnail')
            if thumbnail:
                thumbnails.append({
                    'url': thumbnail,
                })

        owner = video_data.get('owner') or {}
        video_uploader_url = owner.get('url')

        duration = int_or_none(video_data.get('duration'))
        chapter_data = try_get(config, lambda x: x['embed']['chapters']) or []
        chapters = [{
            'title': current_chapter.get('title'),
            'start_time': current_chapter.get('timecode'),
            'end_time': next_chapter.get('timecode'),
        } for current_chapter, next_chapter in zip(chapter_data, chapter_data[1:] + [{'timecode': duration}])]
        if chapters and chapters[0]['start_time']:  # Chapters may not start from 0
            chapters[:0] = [{'title': '<Untitled>', 'start_time': 0, 'end_time': chapters[0]['start_time']}]

        return {
            'id': str_or_none(video_data.get('id')) or video_id,
            'title': video_title,
            'uploader': owner.get('name'),
            'uploader_id': video_uploader_url.split('/')[-1] if video_uploader_url else None,
            'uploader_url': video_uploader_url,
            'thumbnails': thumbnails,
            'duration': duration,
            'chapters': chapters or None,
            'formats': formats,
            'subtitles': subtitles,
            'live_status': live_status,
            'release_timestamp': traverse_obj(live_event, ('ingest', 'scheduled_start_time', {parse_iso8601})),
            # Note: Bitrates are completely broken. Single m3u8 may contain entries in kbps and bps
            # at the same time without actual units specified.
            '_format_sort_fields': ('quality', 'res', 'fps', 'hdr:12', 'source'),
        }

    def _extract_original_format(self, url, video_id, unlisted_hash=None):
        query = {'action': 'load_download_config'}
        if unlisted_hash:
            query['unlisted_hash'] = unlisted_hash
        download_data = self._download_json(
            url, video_id, fatal=False, query=query,
            headers={'X-Requested-With': 'XMLHttpRequest'},
            expected_status=(403, 404)) or {}
        source_file = download_data.get('source_file')
        download_url = try_get(source_file, lambda x: x['download_url'])
        if download_url and not source_file.get('is_cold') and not source_file.get('is_defrosting'):
            source_name = source_file.get('public_name', 'Original')
            if self._is_valid_url(download_url, video_id, f'{source_name} video'):
                ext = (try_get(
                    source_file, lambda x: x['extension'],
                    str) or determine_ext(
                    download_url, None) or 'mp4').lower()
                return {
                    'url': download_url,
                    'ext': ext,
                    'width': int_or_none(source_file.get('width')),
                    'height': int_or_none(source_file.get('height')),
                    'filesize': parse_filesize(source_file.get('size')),
                    'format_id': source_name,
                    'quality': 1,
                }

        jwt_response = self._download_json(
            'https://vimeo.com/_rv/viewer', video_id, note='Downloading jwt token', fatal=False) or {}
        if not jwt_response.get('jwt'):
            return
        headers = {'Authorization': 'jwt {}'.format(jwt_response['jwt']), 'Accept': 'application/json'}
        original_response = self._download_json(
            f'https://api.vimeo.com/videos/{video_id}', video_id,
            headers=headers, fatal=False, expected_status=(403, 404)) or {}
        for download_data in original_response.get('download') or []:
            download_url = download_data.get('link')
            if not download_url or download_data.get('quality') != 'source':
                continue
            ext = determine_ext(parse_qs(download_url).get('filename', [''])[0].lower(), default_ext=None)
            if not ext:
                urlh = self._request_webpage(
                    HEADRequest(download_url), video_id, fatal=False, note='Determining source extension')
                ext = urlh and urlhandle_detect_ext(urlh)
            return {
                'url': download_url,
                'ext': ext or 'unknown_video',
                'format_id': download_data.get('public_name', 'Original'),
                'width': int_or_none(download_data.get('width')),
                'height': int_or_none(download_data.get('height')),
                'fps': int_or_none(download_data.get('fps')),
                'filesize': int_or_none(download_data.get('size')),
                'quality': 1,
            }


class VimeoIE(VimeoBaseInfoExtractor):
    """Information extractor for vimeo.com."""

    # _VALID_URL matches Vimeo URLs
    _VALID_URL = r'''(?x)
                     https?://
                         (?:
                             (?:
                                 www|
                                 player
                             )
                             \.
                         )?
                         vimeo\.com/
                         (?:
                             (?P<u>user)|
                             (?!(?:channels|album|showcase)/[^/?#]+/?(?:$|[?#])|[^/]+/review/|ondemand/)
                             (?:.*?/)??
                             (?P<q>
                                 (?:
                                     play_redirect_hls|
                                     moogaloop\.swf)\?clip_id=
                             )?
                             (?:videos?/)?
                         )
                         (?P<id>[0-9]+)
                         (?(u)
                             /(?!videos|likes)[^/?#]+/?|
                             (?(q)|/(?P<unlisted_hash>[\da-f]{10}))?
                         )
                         (?:(?(q)[&]|(?(u)|/?)[?]).*?)?(?:[#].*)?$
                 '''
    IE_NAME = 'vimeo'
    _EMBED_REGEX = [
        # iframe
        r'<iframe[^>]+?src=(["\'])(?P<url>(?:https?:)?//player\.vimeo\.com/video/\d+.*?)\1',
        # Embedded (swf embed) Vimeo player
        r'<embed[^>]+?src=(["\'])(?P<url>(?:https?:)?//(?:www\.)?vimeo\.com/moogaloop\.swf.+?)\1',
        # Non-standard embedded Vimeo player
        r'<video[^>]+src=(["\'])(?P<url>(?:https?:)?//(?:www\.)?vimeo\.com/[0-9]+)\1',
    ]
    _TESTS = [
        {
            'url': 'http://vimeo.com/56015672#at=0',
            'md5': '8879b6cc097e987f02484baf890129e5',
            'info_dict': {
                'id': '56015672',
                'ext': 'mp4',
                'title': "youtube-dl test video '' ä↭𝕐-BaW jenozKc",
                'description': 'md5:2d3305bad981a06ff79f027f19865021',
                'timestamp': 1355990239,
                'upload_date': '20121220',
                'uploader_url': r're:https?://(?:www\.)?vimeo\.com/user7108434',
                'uploader_id': 'user7108434',
                'uploader': 'Filippo Valsorda',
                'duration': 10,
                'license': 'by-sa',
            },
            'params': {
                'format': 'best[protocol=https]',
            },
            'skip': 'No longer available',
        },
        {
            'url': 'http://player.vimeo.com/video/54469442',
            'md5': '619b811a4417aa4abe78dc653becf511',
            'note': 'Videos that embed the url in the player page',
            'info_dict': {
                'id': '54469442',
                'ext': 'mp4',
                'title': 'Kathy Sierra: Building the minimum Badass User, Business of Software 2012',
                'uploader': 'Business of Software',
                'uploader_url': r're:https?://(?:www\.)?vimeo\.com/businessofsoftware',
                'uploader_id': 'businessofsoftware',
                'duration': 3610,
                'thumbnail': 'https://i.vimeocdn.com/video/376682406-f34043e7b766af6bef2af81366eacd6724f3fc3173179a11a97a1e26587c9529-d_1280',
            },
            'params': {
                'format': 'best[protocol=https]',
            },
        },
        {
            'url': 'http://vimeo.com/68375962',
            'md5': 'aaf896bdb7ddd6476df50007a0ac0ae7',
            'note': 'Video protected with password',
            'info_dict': {
                'id': '68375962',
                'ext': 'mp4',
                'title': 'youtube-dl password protected test video',
                'timestamp': 1371200155,
                'upload_date': '20130614',
                'uploader_url': r're:https?://(?:www\.)?vimeo\.com/user18948128',
                'uploader_id': 'user18948128',
                'uploader': 'Jaime Marquínez Ferrándiz',
                'duration': 10,
                'description': 'md5:6173f270cd0c0119f22817204b3eb86c',
                'thumbnail': 'https://i.vimeocdn.com/video/440665496-b2c5aee2b61089442c794f64113a8e8f7d5763c3e6b3ebfaf696ae6413f8b1f4-d_1280',
                'view_count': int,
                'comment_count': int,
                'like_count': int,
            },
            'params': {
                'format': 'best[protocol=https]',
                'videopassword': 'youtube-dl',
            },
        },
        {
            'url': 'http://vimeo.com/channels/keypeele/75629013',
            'md5': '2f86a05afe9d7abc0b9126d229bbe15d',
            'info_dict': {
                'id': '75629013',
                'ext': 'mp4',
                'title': 'Key & Peele: Terrorist Interrogation',
                'description': 'md5:6173f270cd0c0119f22817204b3eb86c',
                'uploader_url': r're:https?://(?:www\.)?vimeo\.com/atencio',
                'uploader_id': 'atencio',
                'uploader': 'Peter Atencio',
                'channel_id': 'keypeele',
                'channel_url': r're:https?://(?:www\.)?vimeo\.com/channels/keypeele',
                'timestamp': 1380339469,
                'upload_date': '20130928',
                'duration': 187,
                'thumbnail': 'https://i.vimeocdn.com/video/450239872-a05512d9b1e55d707a7c04365c10980f327b06d966351bc403a5d5d65c95e572-d_1280',
                'view_count': int,
                'comment_count': int,
                'like_count': int,
            },
            'params': {'format': 'http-1080p'},
        },
        {
            'url': 'http://vimeo.com/76979871',
            'note': 'Video with subtitles',
            'info_dict': {
                'id': '76979871',
                'ext': 'mov',
                'title': 'The New Vimeo Player (You Know, For Videos)',
                'description': 'md5:2ec900bf97c3f389378a96aee11260ea',
                'timestamp': 1381846109,
                'upload_date': '20131015',
                'uploader_url': r're:https?://(?:www\.)?vimeo\.com/staff',
                'uploader_id': 'staff',
                'uploader': 'Vimeo Staff',
                'duration': 62,
                'subtitles': {
                    'de': [{'ext': 'vtt'}],
                    'en': [{'ext': 'vtt'}],
                    'es': [{'ext': 'vtt'}],
                    'fr': [{'ext': 'vtt'}],
                },
            },
            'expected_warnings': ['Ignoring subtitle tracks found in the HLS manifest'],
        },
        {
            # from https://www.ouya.tv/game/Pier-Solar-and-the-Great-Architects/
            'url': 'https://player.vimeo.com/video/98044508',
            'note': 'The js code contains assignments to the same variable as the config',
            'info_dict': {
                'id': '98044508',
                'ext': 'mp4',
                'title': 'Pier Solar OUYA Official Trailer',
                'uploader': 'Tulio Gonçalves',
                'uploader_url': r're:https?://(?:www\.)?vimeo\.com/user28849593',
                'uploader_id': 'user28849593',
                'duration': 118,
                'thumbnail': 'https://i.vimeocdn.com/video/478636036-c18440305ef3df9decfb6bf207a61fe39d2d17fa462a96f6f2d93d30492b037d-d_1280',
            },
        },
        {
            # contains original format
            'url': 'https://vimeo.com/33951933',
            'md5': '53c688fa95a55bf4b7293d37a89c5c53',
            'info_dict': {
                'id': '33951933',
                'ext': 'mp4',
                'title': 'FOX CLASSICS - Forever Classic ID - A Full Minute',
                'uploader': 'The DMCI',
                'uploader_url': r're:https?://(?:www\.)?vimeo\.com/dmci',
                'uploader_id': 'dmci',
                'timestamp': 1324343742,
                'upload_date': '20111220',
                'description': 'md5:ae23671e82d05415868f7ad1aec21147',
                'duration': 60,
                'comment_count': int,
                'view_count': int,
                'thumbnail': 'https://i.vimeocdn.com/video/231174622-dd07f015e9221ff529d451e1cc31c982b5d87bfafa48c4189b1da72824ee289a-d_1280',
                'like_count': int,
            },
        },
        {
            'note': 'Contains original format not accessible in webpage',
            'url': 'https://vimeo.com/393756517',
            'md5': 'c464af248b592190a5ffbb5d33f382b0',
            'info_dict': {
                'id': '393756517',
                'ext': 'mov',
                'timestamp': 1582642091,
                'uploader_id': 'frameworkla',
                'title': 'Straight To Hell - Sabrina: Netflix',
                'uploader': 'Framework Studio',
                'description': 'md5:f2edc61af3ea7a5592681ddbb683db73',
                'upload_date': '20200225',
                'duration': 176,
                'thumbnail': 'https://i.vimeocdn.com/video/859377297-836494a4ef775e9d4edbace83937d9ad34dc846c688c0c419c0e87f7ab06c4b3-d_1280',
                'uploader_url': 'https://vimeo.com/frameworkla',
            },
        },
        {
            # only available via https://vimeo.com/channels/tributes/6213729 and
            # not via https://vimeo.com/6213729
            'url': 'https://vimeo.com/channels/tributes/6213729',
            'info_dict': {
                'id': '6213729',
                'ext': 'mp4',
                'title': 'Vimeo Tribute: The Shining',
                'uploader': 'Casey Donahue',
                'uploader_url': r're:https?://(?:www\.)?vimeo\.com/caseydonahue',
                'uploader_id': 'caseydonahue',
                'channel_url': r're:https?://(?:www\.)?vimeo\.com/channels/tributes',
                'channel_id': 'tributes',
                'timestamp': 1250886430,
                'upload_date': '20090821',
                'description': 'md5:bdbf314014e58713e6e5b66eb252f4a6',
                'duration': 321,
                'comment_count': int,
                'view_count': int,
                'thumbnail': 'https://i.vimeocdn.com/video/22728298-bfc22146f930de7cf497821c7b0b9f168099201ecca39b00b6bd31fcedfca7a6-d_1280',
                'like_count': int,
            },
            'params': {
                'skip_download': True,
            },
        },
        {
            # redirects to ondemand extractor and should be passed through it
            # for successful extraction
            'url': 'https://vimeo.com/73445910',
            'info_dict': {
                'id': '73445910',
                'ext': 'mp4',
                'title': 'The Reluctant Revolutionary',
                'uploader': '10Ft Films',
                'uploader_url': r're:https?://(?:www\.)?vimeo\.com/tenfootfilms',
                'uploader_id': 'tenfootfilms',
                'description': 'md5:0fa704e05b04f91f40b7f3ca2e801384',
                'upload_date': '20130830',
                'timestamp': 1377853339,
            },
            'params': {
                'skip_download': True,
            },
            'skip': 'this page is no longer available.',
        },
        {
            'url': 'http://player.vimeo.com/video/68375962',
            'md5': 'aaf896bdb7ddd6476df50007a0ac0ae7',
            'info_dict': {
                'id': '68375962',
                'ext': 'mp4',
                'title': 'youtube-dl password protected test video',
                'timestamp': 1371200155,
                'upload_date': '20130614',
                'uploader_url': r're:https?://(?:www\.)?vimeo\.com/user18948128',
                'uploader_id': 'user18948128',
                'uploader': 'Jaime Marquínez Ferrándiz',
                'duration': 10,
                'description': 'md5:6173f270cd0c0119f22817204b3eb86c',
                'thumbnail': 'https://i.vimeocdn.com/video/440665496-b2c5aee2b61089442c794f64113a8e8f7d5763c3e6b3ebfaf696ae6413f8b1f4-d_1280',
                'view_count': int,
                'comment_count': int,
                'like_count': int,
            },
            'params': {
                'format': 'best[protocol=https]',
                'videopassword': 'youtube-dl',
            },
        },
        {
            'url': 'http://vimeo.com/moogaloop.swf?clip_id=2539741',
            'only_matching': True,
        },
        {
            'url': 'https://vimeo.com/109815029',
            'note': 'Video not completely processed, "failed" seed status',
            'only_matching': True,
        },
        {
            'url': 'https://vimeo.com/groups/travelhd/videos/22439234',
            'only_matching': True,
        },
        {
            'url': 'https://vimeo.com/album/2632481/video/79010983',
            'only_matching': True,
        },
        {
            'url': 'https://vimeo.com/showcase/3253534/video/119195465',
            'note': 'A video in a password protected album (showcase)',
            'info_dict': {
                'id': '119195465',
                'ext': 'mp4',
                'title': "youtube-dl test video '' ä↭𝕐-BaW jenozKc",
                'uploader': 'Philipp Hagemeister',
                'uploader_id': 'user20132939',
                'description': 'md5:fa7b6c6d8db0bdc353893df2f111855b',
                'upload_date': '20150209',
                'timestamp': 1423518307,
                'thumbnail': 'https://i.vimeocdn.com/video/default_1280',
                'duration': 10,
                'like_count': int,
                'uploader_url': 'https://vimeo.com/user20132939',
                'view_count': int,
                'comment_count': int,
            },
            'params': {
                'format': 'best[protocol=https]',
                'videopassword': 'youtube-dl',
            },
        },
        {
            # source file returns 403: Forbidden
            'url': 'https://vimeo.com/7809605',
            'only_matching': True,
        },
        {
            'note': 'Direct URL with hash',
            'url': 'https://vimeo.com/160743502/abd0e13fb4',
            'info_dict': {
                'id': '160743502',
                'ext': 'mp4',
                'uploader': 'Julian Tryba',
                'uploader_id': 'aliniamedia',
                'title': 'Harrisville New Hampshire',
                'timestamp': 1459259666,
                'upload_date': '20160329',
                'release_timestamp': 1459259666,
                'license': 'by-nc',
                'duration': 159,
                'comment_count': int,
                'thumbnail': 'https://i.vimeocdn.com/video/562802436-585eeb13b5020c6ac0f171a2234067938098f84737787df05ff0d767f6d54ee9-d_1280',
                'like_count': int,
                'uploader_url': 'https://vimeo.com/aliniamedia',
                'release_date': '20160329',
            },
            'params': {'skip_download': True},
        },
        {
            'url': 'https://vimeo.com/138909882',
            'info_dict': {
                'id': '138909882',
                'ext': 'mp4',
                'title': 'Eastnor Castle 2015 Firework Champions - The Promo!',
                'description': 'md5:5967e090768a831488f6e74b7821b3c1',
                'uploader_id': 'fireworkchampions',
                'uploader': 'Firework Champions',
                'upload_date': '20150910',
                'timestamp': 1441901895,
            },
            'params': {
                'skip_download': True,
                'format': 'Original',
            },
        },
        {
            'url': 'https://vimeo.com/channels/staffpicks/143603739',
            'info_dict': {
                'id': '143603739',
                'ext': 'mp4',
                'uploader': 'Karim Huu Do',
                'timestamp': 1445846953,
                'upload_date': '20151026',
                'title': 'The Shoes - Submarine Feat. Blaine Harrison',
                'uploader_id': 'karimhd',
                'description': 'md5:8e2eea76de4504c2e8020a9bcfa1e843',
                'channel_id': 'staffpicks',
                'duration': 336,
                'comment_count': int,
                'view_count': int,
                'thumbnail': 'https://i.vimeocdn.com/video/541243181-b593db36a16db2f0096f655da3f5a4dc46b8766d77b0f440df937ecb0c418347-d_1280',
                'like_count': int,
                'uploader_url': 'https://vimeo.com/karimhd',
                'channel_url': 'https://vimeo.com/channels/staffpicks',
            },
            'params': {'skip_download': 'm3u8'},
        },
        {
            # requires passing unlisted_hash(a52724358e) to load_download_config request
            'url': 'https://vimeo.com/392479337/a52724358e',
            'only_matching': True,
        },
        {
            # similar, but all numeric: ID must be 581039021, not 9603038895
            # issue #29690
            'url': 'https://vimeo.com/581039021/9603038895',
            'info_dict': {
                'id': '581039021',
                'ext': 'mp4',
                'timestamp': 1627621014,
                'release_timestamp': 1627621014,
                'duration': 976,
                'comment_count': int,
                'thumbnail': 'https://i.vimeocdn.com/video/1202249320-4ddb2c30398c0dc0ee059172d1bd5ea481ad12f0e0e3ad01d2266f56c744b015-d_1280',
                'like_count': int,
                'uploader_url': 'https://vimeo.com/txwestcapital',
                'release_date': '20210730',
                'uploader': 'Christopher Inks',
                'title': 'Thursday, July 29, 2021 BMA Evening Video Update',
                'uploader_id': 'txwestcapital',
                'upload_date': '20210730',
            },
            'params': {
                'skip_download': True,
            },
        },
        {
            # user playlist alias -> https://vimeo.com/258705797
            'url': 'https://vimeo.com/user26785108/newspiritualguide',
            'only_matching': True,
        },
        # https://gettingthingsdone.com/workflowmap/
        # vimeo embed with check-password page protected by Referer header
    ]

    @classmethod
    def _extract_embed_urls(cls, url, webpage):
        for embed_url in super()._extract_embed_urls(url, webpage):
            yield cls._smuggle_referrer(embed_url, url)

    @classmethod
    def _extract_url(cls, url, webpage):
        return next(cls._extract_embed_urls(url, webpage), None)

    def _verify_player_video_password(self, url, video_id, headers):
        password = self._get_video_password()
        data = urlencode_postdata({
            'password': base64.b64encode(password.encode()),
        })
        headers = merge_dicts(headers, {
            'Content-Type': 'application/x-www-form-urlencoded',
        })
        checked = self._download_json(
            f'{urllib.parse.urlsplit(url)._replace(query=None).geturl()}/check-password',
            video_id, 'Verifying the password', data=data, headers=headers)
        if checked is False:
            raise ExtractorError('Wrong video password', expected=True)
        return checked

    def _call_videos_api(self, video_id, jwt_token, unlisted_hash=None):
        return self._download_json(
            join_nonempty(f'https://api.vimeo.com/videos/{video_id}', unlisted_hash, delim=':'),
            video_id, 'Downloading API JSON', headers={
                'Authorization': f'jwt {jwt_token}',
                'Accept': 'application/json',
            }, query={
                'fields': 'config_url,created_time,description,license,metadata.connections.comments.total,metadata.connections.likes.total,release_time,stats.plays',
            })

    def _extract_from_api(self, video_id, unlisted_hash=None):
        viewer = self._download_json(
            'https://vimeo.com/_next/viewer', video_id, 'Downloading viewer info')

        for retry in (False, True):
            try:
                video = self._call_videos_api(video_id, viewer['jwt'], unlisted_hash)
            except ExtractorError as e:
                if (not retry and isinstance(e.cause, HTTPError) and e.cause.status == 400
                    and 'password' in traverse_obj(
                        e.cause.response.read(),
                        ({bytes.decode}, {json.loads}, 'invalid_parameters', ..., 'field'),
                )):
                    self._verify_video_password(
                        video_id, self._get_video_password(), viewer['xsrft'])
                    continue
                raise

        info = self._parse_config(self._download_json(
            video['config_url'], video_id), video_id)
        get_timestamp = lambda x: parse_iso8601(video.get(x + '_time'))
        info.update({
            'description': video.get('description'),
            'license': video.get('license'),
            'release_timestamp': get_timestamp('release'),
            'timestamp': get_timestamp('created'),
            'view_count': int_or_none(try_get(video, lambda x: x['stats']['plays'])),
        })
        connections = try_get(
            video, lambda x: x['metadata']['connections'], dict) or {}
        for k in ('comment', 'like'):
            info[k + '_count'] = int_or_none(try_get(connections, lambda x: x[k + 's']['total']))
        return info

    def _try_album_password(self, url):
        album_id = self._search_regex(
            r'vimeo\.com/(?:album|showcase)/([^/]+)', url, 'album id', default=None)
        if not album_id:
            return
        viewer = self._download_json(
            'https://vimeo.com/_rv/viewer', album_id, fatal=False)
        if not viewer:
            webpage = self._download_webpage(url, album_id)
            viewer = self._parse_json(self._search_regex(
                r'bootstrap_data\s*=\s*({.+?})</script>',
                webpage, 'bootstrap data'), album_id)['viewer']
        jwt = viewer['jwt']
        album = self._download_json(
            'https://api.vimeo.com/albums/' + album_id,
            album_id, headers={'Authorization': 'jwt ' + jwt, 'Accept': 'application/json'},
            query={'fields': 'description,name,privacy'})
        if try_get(album, lambda x: x['privacy']['view']) == 'password':
            password = self.get_param('videopassword')
            if not password:
                raise ExtractorError(
                    'This album is protected by a password, use the --video-password option',
                    expected=True)
            self._set_vimeo_cookie('vuid', viewer['vuid'])
            try:
                self._download_json(
                    f'https://vimeo.com/showcase/{album_id}/auth',
                    album_id, 'Verifying the password', data=urlencode_postdata({
                        'password': password,
                        'token': viewer['xsrft'],
                    }), headers={
                        'X-Requested-With': 'XMLHttpRequest',
                    })
            except ExtractorError as e:
                if isinstance(e.cause, HTTPError) and e.cause.status == 401:
                    raise ExtractorError('Wrong password', expected=True)
                raise

    def _real_extract(self, url):
        url, data, headers = self._unsmuggle_headers(url)
        if 'Referer' not in headers:
            headers['Referer'] = url

        # Extract ID from URL
        mobj = self._match_valid_url(url).groupdict()
        video_id, unlisted_hash = mobj['id'], mobj.get('unlisted_hash')
        if unlisted_hash:
            return self._extract_from_api(video_id, unlisted_hash)

        if any(p in url for p in ('play_redirect_hls', 'moogaloop.swf')):
            url = 'https://vimeo.com/' + video_id

        self._try_album_password(url)
        is_secure = urllib.parse.urlparse(url).scheme == 'https'
        try:
            # Retrieve video webpage to extract further information
            webpage, urlh = self._download_webpage_handle(
                url, video_id, headers=headers, impersonate=is_secure)
            redirect_url = urlh.url
        except ExtractorError as error:
            if not isinstance(error.cause, HTTPError) or error.cause.status not in (403, 429):
                raise
            errmsg = error.cause.response.read()
            if b'Because of its privacy settings, this video cannot be played here' in errmsg:
                raise ExtractorError(
                    'Cannot download embed-only video without embedding URL. Please call yt-dlp '
                    'with the URL of the page that embeds this video.', expected=True)
            # 403 == vimeo.com TLS fingerprint or DC IP block; 429 == player.vimeo.com TLS FP block
            status = error.cause.status
            dcip_msg = 'If you are using a data center IP or VPN/proxy, your IP may be blocked'
            if target := error.cause.response.extensions.get('impersonate'):
                raise ExtractorError(
                    f'Got HTTP Error {status} when using impersonate target "{target}". {dcip_msg}')
            elif not is_secure:
                raise ExtractorError(f'Got HTTP Error {status}. {dcip_msg}', expected=True)
            raise ExtractorError(
                'This request has been blocked due to its TLS fingerprint. Install a '
                'required impersonation dependency if possible, or else if you are okay with '
                f'{self._downloader._format_err("compromising your security/cookies", "light red")}, '
                f'try replacing "https:" with "http:" in the input URL. {dcip_msg}.', expected=True)

        if '://player.vimeo.com/video/' in url:
            config = self._search_json(
                r'\b(?:playerC|c)onfig\s*=', webpage, 'info section', video_id)
            if config.get('view') == 4:
                config = self._verify_player_video_password(
                    redirect_url, video_id, headers)
            return self._parse_config(config, video_id)

        vimeo_config = self._extract_vimeo_config(webpage, video_id, default=None)
        if vimeo_config:
            seed_status = vimeo_config.get('seed_status') or {}
            if seed_status.get('state') == 'failed':
                raise ExtractorError(
                    '{} said: {}'.format(self.IE_NAME, seed_status['title']),
                    expected=True)

        cc_license = None
        timestamp = None
        video_description = None
        info_dict = {}
        config_url = None

        channel_id = self._search_regex(
            r'vimeo\.com/channels/([^/]+)', url, 'channel id', default=None)
        if channel_id:
            config_url = self._html_search_regex(
                r'\bdata-config-url="([^"]+)"', webpage, 'config URL', default=None)
            video_description = clean_html(get_element_by_class('description', webpage))
            info_dict.update({
                'channel_id': channel_id,
                'channel_url': 'https://vimeo.com/channels/' + channel_id,
            })
        if not config_url:
            page_config = self._parse_json(self._search_regex(
                r'vimeo\.(?:clip|vod_title)_page_config\s*=\s*({.+?});',
                webpage, 'page config', default='{}'), video_id, fatal=False)
            if not page_config:
                return self._extract_from_api(video_id)
            config_url = page_config['player']['config_url']
            cc_license = page_config.get('cc_license')
            clip = page_config.get('clip') or {}
            timestamp = clip.get('uploaded_on')
            video_description = clean_html(
                clip.get('description') or page_config.get('description_html_escaped'))
        config = self._download_json(config_url, video_id)
        video = config.get('video') or {}
        vod = video.get('vod') or {}

        def is_rented():
            if '>You rented this title.<' in webpage:
                return True
            if try_get(config, lambda x: x['user']['purchased']):
                return True
            for purchase_option in (vod.get('purchase_options') or []):
                if purchase_option.get('purchased'):
                    return True
                label = purchase_option.get('label_string')
                if label and (label.startswith('You rented this') or label.endswith(' remaining')):
                    return True
            return False

        if is_rented() and vod.get('is_trailer'):
            feature_id = vod.get('feature_id')
            if feature_id and not data.get('force_feature_id', False):
                return self.url_result(smuggle_url(
                    f'https://player.vimeo.com/player/{feature_id}',
                    {'force_feature_id': True}), 'Vimeo')

        if not video_description:
            video_description = self._html_search_regex(
                r'(?s)<div\s+class="[^"]*description[^"]*"[^>]*>(.*?)</div>',
                webpage, 'description', default=None)
        if not video_description:
            video_description = self._html_search_meta(
                ['description', 'og:description', 'twitter:description'],
                webpage, default=None)
        if not video_description:
            self.report_warning('Cannot find video description')

        if not timestamp:
            timestamp = self._search_regex(
                r'<time[^>]+datetime="([^"]+)"', webpage,
                'timestamp', default=None)

        view_count = int_or_none(self._search_regex(r'UserPlays:(\d+)', webpage, 'view count', default=None))
        like_count = int_or_none(self._search_regex(r'UserLikes:(\d+)', webpage, 'like count', default=None))
        comment_count = int_or_none(self._search_regex(r'UserComments:(\d+)', webpage, 'comment count', default=None))

        formats = []

        source_format = self._extract_original_format(
            'https://vimeo.com/' + video_id, video_id, video.get('unlisted_hash'))
        if source_format:
            formats.append(source_format)

        info_dict_config = self._parse_config(config, video_id)
        formats.extend(info_dict_config['formats'])
        info_dict['_format_sort_fields'] = info_dict_config['_format_sort_fields']

        json_ld = self._search_json_ld(webpage, video_id, default={})

        if not cc_license:
            cc_license = self._search_regex(
                r'<link[^>]+rel=["\']license["\'][^>]+href=(["\'])(?P<license>(?:(?!\1).)+)\1',
                webpage, 'license', default=None, group='license')

        info_dict.update({
            'formats': formats,
            'timestamp': unified_timestamp(timestamp),
            'description': video_description,
            'webpage_url': url,
            'view_count': view_count,
            'like_count': like_count,
            'comment_count': comment_count,
            'license': cc_license,
        })

        return merge_dicts(info_dict, info_dict_config, json_ld)


class VimeoOndemandIE(VimeoIE):  # XXX: Do not subclass from concrete IE
    IE_NAME = 'vimeo:ondemand'
    _VALID_URL = r'https?://(?:www\.)?vimeo\.com/ondemand/(?:[^/]+/)?(?P<id>[^/?#&]+)'
    _TESTS = [{
        # ondemand video not available via https://vimeo.com/id
        'url': 'https://vimeo.com/ondemand/20704',
        'md5': 'c424deda8c7f73c1dfb3edd7630e2f35',
        'info_dict': {
            'id': '105442900',
            'ext': 'mp4',
            'title': 'המעבדה - במאי יותם פלדמן',
            'uploader': 'גם סרטים',
            'uploader_url': r're:https?://(?:www\.)?vimeo\.com/gumfilms',
            'uploader_id': 'gumfilms',
            'description': 'md5:aeeba3dbd4d04b0fa98a4fdc9c639998',
            'upload_date': '20140906',
            'timestamp': 1410032453,
            'thumbnail': 'https://i.vimeocdn.com/video/488238335-d7bf151c364cff8d467f1b73784668fe60aae28a54573a35d53a1210ae283bd8-d_1280',
            'comment_count': int,
            'license': 'https://creativecommons.org/licenses/by-nc-nd/3.0/',
            'duration': 53,
            'view_count': int,
            'like_count': int,
        },
        'params': {
            'format': 'best[protocol=https]',
        },
        'expected_warnings': ['Unable to download JSON metadata'],
    }, {
        # requires Referer to be passed along with og:video:url
        'url': 'https://vimeo.com/ondemand/36938/126682985',
        'info_dict': {
            'id': '126584684',
            'ext': 'mp4',
            'title': 'Rävlock, rätt läte på rätt plats',
            'uploader': 'Lindroth & Norin',
            'uploader_url': r're:https?://(?:www\.)?vimeo\.com/lindrothnorin',
            'uploader_id': 'lindrothnorin',
            'description': 'md5:c3c46a90529612c8279fb6af803fc0df',
            'upload_date': '20150502',
            'timestamp': 1430586422,
            'duration': 121,
            'comment_count': int,
            'view_count': int,
            'thumbnail': 'https://i.vimeocdn.com/video/517077723-7066ae1d9a79d3eb361334fb5d58ec13c8f04b52f8dd5eadfbd6fb0bcf11f613-d_1280',
            'like_count': int,
        },
        'params': {
            'skip_download': True,
        },
        'expected_warnings': ['Unable to download JSON metadata'],
    }, {
        'url': 'https://vimeo.com/ondemand/nazmaalik',
        'only_matching': True,
    }, {
        'url': 'https://vimeo.com/ondemand/141692381',
        'only_matching': True,
    }, {
        'url': 'https://vimeo.com/ondemand/thelastcolony/150274832',
        'only_matching': True,
    }]


class VimeoChannelIE(VimeoBaseInfoExtractor):
    IE_NAME = 'vimeo:channel'
    _VALID_URL = r'https://vimeo\.com/channels/(?P<id>[^/?#]+)/?(?:$|[?#])'
    _MORE_PAGES_INDICATOR = r'<a.+?rel="next"'
    _TITLE = None
    _TITLE_RE = r'<link rel="alternate"[^>]+?title="(.*?)"'
    _TESTS = [{
        'url': 'https://vimeo.com/channels/tributes',
        'info_dict': {
            'id': 'tributes',
            'title': 'Vimeo Tributes',
        },
        'playlist_mincount': 22,
    }]
    _BASE_URL_TEMPL = 'https://vimeo.com/channels/%s'

    def _page_url(self, base_url, pagenum):
        return f'{base_url}/videos/page:{pagenum}/'

    def _extract_list_title(self, webpage):
        return self._TITLE or self._html_search_regex(
            self._TITLE_RE, webpage, 'list title', fatal=False)

    def _title_and_entries(self, list_id, base_url):
        for pagenum in itertools.count(1):
            page_url = self._page_url(base_url, pagenum)
            webpage = self._download_webpage(
                page_url, list_id,
                f'Downloading page {pagenum}')

            if pagenum == 1:
                yield self._extract_list_title(webpage)

            # Try extracting href first since not all videos are available via
            # short https://vimeo.com/id URL (e.g. https://vimeo.com/channels/tributes/6213729)
            clips = re.findall(
                r'id="clip_(\d+)"[^>]*>\s*<a[^>]+href="(/(?:[^/]+/)*\1)(?:[^>]+\btitle="([^"]+)")?', webpage)
            if clips:
                for video_id, video_url, video_title in clips:
                    yield self.url_result(
                        urllib.parse.urljoin(base_url, video_url),
                        VimeoIE.ie_key(), video_id=video_id, video_title=video_title)
            # More relaxed fallback
            else:
                for video_id in re.findall(r'id=["\']clip_(\d+)', webpage):
                    yield self.url_result(
                        f'https://vimeo.com/{video_id}',
                        VimeoIE.ie_key(), video_id=video_id)

            if re.search(self._MORE_PAGES_INDICATOR, webpage, re.DOTALL) is None:
                break

    def _extract_videos(self, list_id, base_url):
        title_and_entries = self._title_and_entries(list_id, base_url)
        list_title = next(title_and_entries)
        return self.playlist_result(title_and_entries, list_id, list_title)

    def _real_extract(self, url):
        channel_id = self._match_id(url)
        return self._extract_videos(channel_id, self._BASE_URL_TEMPL % channel_id)


class VimeoUserIE(VimeoChannelIE):  # XXX: Do not subclass from concrete IE
    IE_NAME = 'vimeo:user'
    _VALID_URL = r'https://vimeo\.com/(?!(?:[0-9]+|watchlater)(?:$|[?#/]))(?P<id>[^/]+)(?:/videos)?/?(?:$|[?#])'
    _TITLE_RE = r'<a[^>]+?class="user">([^<>]+?)</a>'
    _TESTS = [{
        'url': 'https://vimeo.com/nkistudio/videos',
        'info_dict': {
            'title': 'Nki',
            'id': 'nkistudio',
        },
        'playlist_mincount': 66,
    }, {
        'url': 'https://vimeo.com/nkistudio/',
        'only_matching': True,
    }]
    _BASE_URL_TEMPL = 'https://vimeo.com/%s'


class VimeoAlbumIE(VimeoBaseInfoExtractor):
    IE_NAME = 'vimeo:album'
    _VALID_URL = r'https://vimeo\.com/(?:album|showcase)/(?P<id>\d+)(?:$|[?#]|/(?!video))'
    _TITLE_RE = r'<header id="page_header">\n\s*<h1>(.*?)</h1>'
    _TESTS = [{
        'url': 'https://vimeo.com/album/2632481',
        'info_dict': {
            'id': '2632481',
            'title': 'Staff Favorites: November 2013',
        },
        'playlist_mincount': 13,
    }, {
        'note': 'Password-protected album',
        'url': 'https://vimeo.com/album/3253534',
        'info_dict': {
            'title': 'test',
            'id': '3253534',
        },
        'playlist_count': 1,
        'params': {
            'videopassword': 'youtube-dl',
        },
    }]
    _PAGE_SIZE = 100

    def _fetch_page(self, album_id, authorization, hashed_pass, page):
        api_page = page + 1
        query = {
            'fields': 'link,uri',
            'page': api_page,
            'per_page': self._PAGE_SIZE,
        }
        if hashed_pass:
            query['_hashed_pass'] = hashed_pass
        try:
            videos = self._download_json(
                f'https://api.vimeo.com/albums/{album_id}/videos',
                album_id, f'Downloading page {api_page}', query=query, headers={
                    'Authorization': 'jwt ' + authorization,
                    'Accept': 'application/json',
                })['data']
        except ExtractorError as e:
            if isinstance(e.cause, HTTPError) and e.cause.status == 400:
                return
            raise
        for video in videos:
            link = video.get('link')
            if not link:
                continue
            uri = video.get('uri')
            video_id = self._search_regex(r'/videos/(\d+)', uri, 'video_id', default=None) if uri else None
            yield self.url_result(link, VimeoIE.ie_key(), video_id)

    def _real_extract(self, url):
        album_id = self._match_id(url)
        viewer = self._download_json(
            'https://vimeo.com/_rv/viewer', album_id, fatal=False)
        if not viewer:
            webpage = self._download_webpage(url, album_id)
            viewer = self._parse_json(self._search_regex(
                r'bootstrap_data\s*=\s*({.+?})</script>',
                webpage, 'bootstrap data'), album_id)['viewer']
        jwt = viewer['jwt']
        album = self._download_json(
            'https://api.vimeo.com/albums/' + album_id,
            album_id, headers={'Authorization': 'jwt ' + jwt, 'Accept': 'application/json'},
            query={'fields': 'description,name,privacy'})
        hashed_pass = None
        if try_get(album, lambda x: x['privacy']['view']) == 'password':
            password = self.get_param('videopassword')
            if not password:
                raise ExtractorError(
                    'This album is protected by a password, use the --video-password option',
                    expected=True)
            self._set_vimeo_cookie('vuid', viewer['vuid'])
            try:
                hashed_pass = self._download_json(
                    f'https://vimeo.com/showcase/{album_id}/auth',
                    album_id, 'Verifying the password', data=urlencode_postdata({
                        'password': password,
                        'token': viewer['xsrft'],
                    }), headers={
                        'X-Requested-With': 'XMLHttpRequest',
                    })['hashed_pass']
            except ExtractorError as e:
                if isinstance(e.cause, HTTPError) and e.cause.status == 401:
                    raise ExtractorError('Wrong password', expected=True)
                raise
        entries = OnDemandPagedList(functools.partial(
            self._fetch_page, album_id, jwt, hashed_pass), self._PAGE_SIZE)
        return self.playlist_result(
            entries, album_id, album.get('name'), album.get('description'))


class VimeoGroupsIE(VimeoChannelIE):  # XXX: Do not subclass from concrete IE
    IE_NAME = 'vimeo:group'
    _VALID_URL = r'https://vimeo\.com/groups/(?P<id>[^/]+)(?:/(?!videos?/\d+)|$)'
    _TESTS = [{
        'url': 'https://vimeo.com/groups/meetup',
        'info_dict': {
            'id': 'meetup',
            'title': 'Vimeo Meetup!',
        },
        'playlist_mincount': 27,
    }]
    _BASE_URL_TEMPL = 'https://vimeo.com/groups/%s'


class VimeoReviewIE(VimeoBaseInfoExtractor):
    IE_NAME = 'vimeo:review'
    IE_DESC = 'Review pages on vimeo'
    _VALID_URL = r'(?P<url>https://vimeo\.com/[^/]+/review/(?P<id>[^/]+)/[0-9a-f]{10})'
    _TESTS = [{
        'url': 'https://vimeo.com/user21297594/review/75524534/3c257a1b5d',
        'md5': 'c507a72f780cacc12b2248bb4006d253',
        'info_dict': {
            'id': '75524534',
            'ext': 'mp4',
            'title': "DICK HARDWICK 'Comedian'",
            'uploader': 'Richard Hardwick',
            'uploader_id': 'user21297594',
            'description': "Comedian Dick Hardwick's five minute demo filmed in front of a live theater audience.\nEdit by Doug Mattocks",
            'duration': 304,
            'thumbnail': 'https://i.vimeocdn.com/video/450115033-43303819d9ebe24c2630352e18b7056d25197d09b3ae901abdac4c4f1d68de71-d_1280',
            'uploader_url': 'https://vimeo.com/user21297594',
        },
    }, {
        'note': 'video player needs Referer',
        'url': 'https://vimeo.com/user22258446/review/91613211/13f927e053',
        'md5': '6295fdab8f4bf6a002d058b2c6dce276',
        'info_dict': {
            'id': '91613211',
            'ext': 'mp4',
            'title': 're:(?i)^Death by dogma versus assembling agile . Sander Hoogendoorn',
            'uploader': 'DevWeek Events',
            'duration': 2773,
            'thumbnail': r're:^https?://.*\.jpg$',
            'uploader_id': 'user22258446',
        },
        'skip': 'video gone',
    }, {
        'note': 'Password protected',
        'url': 'https://vimeo.com/user37284429/review/138823582/c4d865efde',
        'info_dict': {
            'id': '138823582',
            'ext': 'mp4',
            'title': 'EFFICIENT PICKUP MASTERCLASS MODULE 1',
            'uploader': 'TMB',
            'uploader_id': 'user37284429',
        },
        'params': {
            'videopassword': 'holygrail',
        },
        'skip': 'video gone',
    }]

    def _real_extract(self, url):
        page_url, video_id = self._match_valid_url(url).groups()
        data = self._download_json(
            page_url.replace('/review/', '/review/data/'), video_id)
        if data.get('isLocked') is True:
            video_password = self._get_video_password()
            viewer = self._download_json(
                'https://vimeo.com/_rv/viewer', video_id)
            webpage = self._verify_video_password(video_id, video_password, viewer['xsrft'])
            clip_page_config = self._parse_json(self._search_regex(
                r'window\.vimeo\.clip_page_config\s*=\s*({.+?});',
                webpage, 'clip page config'), video_id)
            config_url = clip_page_config['player']['config_url']
            clip_data = clip_page_config.get('clip') or {}
        else:
            clip_data = data['clipData']
            config_url = clip_data['configUrl']
        config = self._download_json(config_url, video_id)
        info_dict = self._parse_config(config, video_id)
        source_format = self._extract_original_format(
            page_url + '/action', video_id)
        if source_format:
            info_dict['formats'].append(source_format)
        info_dict['description'] = clean_html(clip_data.get('description'))
        return info_dict


class VimeoWatchLaterIE(VimeoChannelIE):  # XXX: Do not subclass from concrete IE
    IE_NAME = 'vimeo:watchlater'
    IE_DESC = 'Vimeo watch later list, ":vimeowatchlater" keyword (requires authentication)'
    _VALID_URL = r'https://vimeo\.com/(?:home/)?watchlater|:vimeowatchlater'
    _TITLE = 'Watch Later'
    _LOGIN_REQUIRED = True
    _TESTS = [{
        'url': 'https://vimeo.com/watchlater',
        'only_matching': True,
    }]

    def _page_url(self, base_url, pagenum):
        url = f'{base_url}/page:{pagenum}/'
        request = Request(url)
        # Set the header to get a partial html page with the ids,
        # the normal page doesn't contain them.
        request.headers['X-Requested-With'] = 'XMLHttpRequest'
        return request

    def _real_extract(self, url):
        return self._extract_videos('watchlater', 'https://vimeo.com/watchlater')


class VimeoLikesIE(VimeoChannelIE):  # XXX: Do not subclass from concrete IE
    _VALID_URL = r'https://(?:www\.)?vimeo\.com/(?P<id>[^/]+)/likes/?(?:$|[?#]|sort:)'
    IE_NAME = 'vimeo:likes'
    IE_DESC = 'Vimeo user likes'
    _TESTS = [{
        'url': 'https://vimeo.com/user755559/likes/',
        'playlist_mincount': 293,
        'info_dict': {
            'id': 'user755559',
            'title': 'urza’s Likes',
        },
    }, {
        'url': 'https://vimeo.com/stormlapse/likes',
        'only_matching': True,
    }]

    def _page_url(self, base_url, pagenum):
        return f'{base_url}/page:{pagenum}/'

    def _real_extract(self, url):
        user_id = self._match_id(url)
        return self._extract_videos(user_id, f'https://vimeo.com/{user_id}/likes')


class VHXEmbedIE(VimeoBaseInfoExtractor):
    IE_NAME = 'vhx:embed'
    _VALID_URL = r'https?://embed\.vhx\.tv/videos/(?P<id>\d+)'
    _EMBED_REGEX = [r'<iframe[^>]+src="(?P<url>https?://embed\.vhx\.tv/videos/\d+[^"]*)"']

    @classmethod
    def _extract_embed_urls(cls, url, webpage):
        for embed_url in super()._extract_embed_urls(url, webpage):
            yield cls._smuggle_referrer(embed_url, url)

    def _real_extract(self, url):
        video_id = self._match_id(url)
        url, _, headers = self._unsmuggle_headers(url)
        webpage = self._download_webpage(url, video_id, headers=headers)
        config_url = self._parse_json(self._search_regex(
            r'window\.OTTData\s*=\s*({.+})', webpage,
            'ott data'), video_id, js_to_json)['config_url']
        config = self._download_json(config_url, video_id)
        info = self._parse_config(config, video_id)
        info['id'] = video_id
        return info


class VimeoProIE(VimeoBaseInfoExtractor):
    IE_NAME = 'vimeo:pro'
    _VALID_URL = r'https?://(?:www\.)?vimeopro\.com/[^/?#]+/(?P<slug>[^/?#]+)(?:(?:/videos?/(?P<id>[0-9]+)))?'
    _TESTS = [{
        # Vimeo URL derived from video_id
        'url': 'http://vimeopro.com/openstreetmapus/state-of-the-map-us-2013/video/68093876',
        'md5': '3b5ca6aa22b60dfeeadf50b72e44ed82',
        'note': 'Vimeo Pro video (#1197)',
        'info_dict': {
            'id': '68093876',
            'ext': 'mp4',
            'uploader_url': r're:https?://(?:www\.)?vimeo\.com/openstreetmapus',
            'uploader_id': 'openstreetmapus',
            'uploader': 'OpenStreetMap US',
            'title': 'Andy Allan - Putting the Carto into OpenStreetMap Cartography',
            'description': 'md5:2c362968038d4499f4d79f88458590c1',
            'duration': 1595,
            'upload_date': '20130610',
            'timestamp': 1370893156,
            'license': 'by',
            'thumbnail': 'https://i.vimeocdn.com/video/440260469-19b0d92fca3bd84066623b53f1eb8aaa3980c6c809e2d67b6b39ab7b4a77a344-d_960',
            'view_count': int,
            'comment_count': int,
            'like_count': int,
            'tags': 'count:1',
        },
        'params': {
            'format': 'best[protocol=https]',
        },
    }, {
        # password-protected VimeoPro page with Vimeo player embed
        'url': 'https://vimeopro.com/cadfem/simulation-conference-mechanische-systeme-in-perfektion',
        'info_dict': {
            'id': '764543723',
            'ext': 'mp4',
            'title': 'Mechanische Systeme in Perfektion: Realität erfassen, Innovation treiben',
            'thumbnail': 'https://i.vimeocdn.com/video/1543784598-a1a750494a485e601110136b9fe11e28c2131942452b3a5d30391cb3800ca8fd-d_1280',
            'description': 'md5:2a9d195cd1b0f6f79827107dc88c2420',
            'uploader': 'CADFEM',
            'uploader_id': 'cadfem',
            'uploader_url': 'https://vimeo.com/cadfem',
            'duration': 12505,
            'chapters': 'count:10',
        },
        'params': {
            'videopassword': 'Conference2022',
            'skip_download': True,
        },
    }]

    def _real_extract(self, url):
        display_id, video_id = self._match_valid_url(url).group('slug', 'id')
        if video_id:
            display_id = video_id
        webpage = self._download_webpage(url, display_id)

        password_form = self._search_regex(
            r'(?is)<form[^>]+?method=["\']post["\'][^>]*>(.+?password.+?)</form>',
            webpage, 'password form', default=None)
        if password_form:
            try:
                webpage = self._download_webpage(url, display_id, data=urlencode_postdata({
                    'password': self._get_video_password(),
                    **self._hidden_inputs(password_form),
                }), note='Logging in with video password')
            except ExtractorError as e:
                if isinstance(e.cause, HTTPError) and e.cause.status == 418:
                    raise ExtractorError('Wrong video password', expected=True)
                raise

        description = None
        # even if we have video_id, some videos require player URL with portfolio_id query param
        # https://github.com/ytdl-org/youtube-dl/issues/20070
        vimeo_url = VimeoIE._extract_url(url, webpage)
        if vimeo_url:
            description = self._html_search_meta('description', webpage, default=None)
        elif video_id:
            vimeo_url = f'https://vimeo.com/{video_id}'
        else:
            raise ExtractorError(
                'No Vimeo embed or video ID could be found in VimeoPro page', expected=True)

        return self.url_result(vimeo_url, VimeoIE, video_id, url_transparent=True,
                               description=description)
