# coding: utf-8
from __future__ import unicode_literals

import base64
import functools
import json
import re
import itertools

from .common import InfoExtractor
from ..compat import (
    compat_kwargs,
    compat_HTTPError,
    compat_str,
    compat_urlparse,
)
from ..utils import (
    clean_html,
    determine_ext,
    dict_get,
    ExtractorError,
    js_to_json,
    int_or_none,
    merge_dicts,
    OnDemandPagedList,
    parse_filesize,
    parse_iso8601,
    RegexNotFoundError,
    sanitized_Request,
    smuggle_url,
    std_headers,
    str_or_none,
    try_get,
    unified_timestamp,
    unsmuggle_url,
    urlencode_postdata,
    urljoin,
    unescapeHTML,
)


class VimeoBaseInfoExtractor(InfoExtractor):
    _NETRC_MACHINE = 'vimeo'
    _LOGIN_REQUIRED = False
    _LOGIN_URL = 'https://vimeo.com/log_in'

    def _login(self):
        username, password = self._get_login_info()
        if username is None:
            if self._LOGIN_REQUIRED:
                raise ExtractorError('No login info available, needed for using %s.' % self.IE_NAME, expected=True)
            return
        webpage = self._download_webpage(
            self._LOGIN_URL, None, 'Downloading login page')
        token, vuid = self._extract_xsrft_and_vuid(webpage)
        data = {
            'action': 'login',
            'email': username,
            'password': password,
            'service': 'vimeo',
            'token': token,
        }
        self._set_vimeo_cookie('vuid', vuid)
        try:
            self._download_webpage(
                self._LOGIN_URL, None, 'Logging in',
                data=urlencode_postdata(data), headers={
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Referer': self._LOGIN_URL,
                })
        except ExtractorError as e:
            if isinstance(e.cause, compat_HTTPError) and e.cause.code == 418:
                raise ExtractorError(
                    'Unable to log in: bad username or password',
                    expected=True)
            raise ExtractorError('Unable to log in')

    def _get_video_password(self):
        password = self._downloader.params.get('videopassword')
        if password is None:
            raise ExtractorError(
                'This video is protected by a password, use the --video-password option',
                expected=True)
        return password

    def _verify_video_password(self, url, video_id, password, token, vuid):
        if url.startswith('http://'):
            # vimeo only supports https now, but the user can give an http url
            url = url.replace('http://', 'https://')
        self._set_vimeo_cookie('vuid', vuid)
        return self._download_webpage(
            url + '/password', video_id, 'Verifying the password',
            'Wrong password', data=urlencode_postdata({
                'password': password,
                'token': token,
            }), headers={
                'Content-Type': 'application/x-www-form-urlencoded',
                'Referer': url,
            })

    def _extract_xsrft_and_vuid(self, webpage):
        xsrft = self._search_regex(
            r'(?:(?P<q1>["\'])xsrft(?P=q1)\s*:|xsrft\s*[=:])\s*(?P<q>["\'])(?P<xsrft>.+?)(?P=q)',
            webpage, 'login token', group='xsrft')
        vuid = self._search_regex(
            r'["\']vuid["\']\s*:\s*(["\'])(?P<vuid>.+?)\1',
            webpage, 'vuid', group='vuid')
        return xsrft, vuid

    def _extract_vimeo_config(self, webpage, video_id, *args, **kwargs):
        vimeo_config = self._search_regex(
            r'vimeo\.config\s*=\s*(?:({.+?})|_extend\([^,]+,\s+({.+?})\));',
            webpage, 'vimeo config', *args, **compat_kwargs(kwargs))
        if vimeo_config:
            return self._parse_json(vimeo_config, video_id)

    def _set_vimeo_cookie(self, name, value):
        self._set_cookie('vimeo.com', name, value)

    def _vimeo_sort_formats(self, formats):
        # Bitrates are completely broken. Single m3u8 may contain entries in kbps and bps
        # at the same time without actual units specified. This lead to wrong sorting.
        # But since yt-dlp prefers 'res,fps' anyway, 'field_preference' is not needed
        self._sort_formats(formats)

    def _parse_config(self, config, video_id):
        video_data = config['video']
        video_title = video_data['title']
        live_event = video_data.get('live_event') or {}
        is_live = live_event.get('status') == 'started'

        formats = []
        config_files = video_data.get('files') or config['request'].get('files', {})
        for f in config_files.get('progressive', []):
            video_url = f.get('url')
            if not video_url:
                continue
            formats.append({
                'url': video_url,
                'format_id': 'http-%s' % f.get('quality'),
                'width': int_or_none(f.get('width')),
                'height': int_or_none(f.get('height')),
                'fps': int_or_none(f.get('fps')),
                'tbr': int_or_none(f.get('bitrate')),
            })

        # TODO: fix handling of 308 status code returned for live archive manifest requests
        sep_pattern = r'/sep/video/'
        for files_type in ('hls', 'dash'):
            for cdn_name, cdn_data in config_files.get(files_type, {}).get('cdns', {}).items():
                manifest_url = cdn_data.get('url')
                if not manifest_url:
                    continue
                format_id = '%s-%s' % (files_type, cdn_name)
                sep_manifest_urls = []
                if re.search(sep_pattern, manifest_url):
                    for suffix, repl in (('', 'video'), ('_sep', 'sep/video')):
                        sep_manifest_urls.append((format_id + suffix, re.sub(
                            sep_pattern, '/%s/' % repl, manifest_url)))
                else:
                    sep_manifest_urls = [(format_id, manifest_url)]
                for f_id, m_url in sep_manifest_urls:
                    if files_type == 'hls':
                        formats.extend(self._extract_m3u8_formats(
                            m_url, video_id, 'mp4',
                            'm3u8' if is_live else 'm3u8_native', m3u8_id=f_id,
                            note='Downloading %s m3u8 information' % cdn_name,
                            fatal=False))
                    elif files_type == 'dash':
                        if 'json=1' in m_url:
                            real_m_url = (self._download_json(m_url, video_id, fatal=False) or {}).get('url')
                            if real_m_url:
                                m_url = real_m_url
                        mpd_formats = self._extract_mpd_formats(
                            m_url.replace('/master.json', '/master.mpd'), video_id, f_id,
                            'Downloading %s MPD information' % cdn_name,
                            fatal=False)
                        formats.extend(mpd_formats)

        live_archive = live_event.get('archive') or {}
        live_archive_source_url = live_archive.get('source_url')
        if live_archive_source_url and live_archive.get('status') == 'done':
            formats.append({
                'format_id': 'live-archive-source',
                'url': live_archive_source_url,
                'quality': 10,
            })

        subtitles = {}
        text_tracks = config['request'].get('text_tracks')
        if text_tracks:
            for tt in text_tracks:
                subtitles[tt['lang']] = [{
                    'ext': 'vtt',
                    'url': urljoin('https://vimeo.com', tt['url']),
                }]

        thumbnails = []
        if not is_live:
            for key, thumb in video_data.get('thumbs', {}).items():
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

        return {
            'id': str_or_none(video_data.get('id')) or video_id,
            'title': self._live_title(video_title) if is_live else video_title,
            'uploader': owner.get('name'),
            'uploader_id': video_uploader_url.split('/')[-1] if video_uploader_url else None,
            'uploader_url': video_uploader_url,
            'thumbnails': thumbnails,
            'duration': int_or_none(video_data.get('duration')),
            'formats': formats,
            'subtitles': subtitles,
            'is_live': is_live,
        }

    def _extract_original_format(self, url, video_id, unlisted_hash=None):
        query = {'action': 'load_download_config'}
        if unlisted_hash:
            query['unlisted_hash'] = unlisted_hash
        download_data = self._download_json(
            url, video_id, fatal=False, query=query,
            headers={'X-Requested-With': 'XMLHttpRequest'})
        if download_data:
            source_file = download_data.get('source_file')
            if isinstance(source_file, dict):
                download_url = source_file.get('download_url')
                if download_url and not source_file.get('is_cold') and not source_file.get('is_defrosting'):
                    source_name = source_file.get('public_name', 'Original')
                    if self._is_valid_url(download_url, video_id, '%s video' % source_name):
                        ext = (try_get(
                            source_file, lambda x: x['extension'],
                            compat_str) or determine_ext(
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
                        vimeo(?:pro)?\.com/
                        (?!(?:channels|album|showcase)/[^/?#]+/?(?:$|[?#])|[^/]+/review/|ondemand/)
                        (?:.*?/)?
                        (?:
                            (?:
                                play_redirect_hls|
                                moogaloop\.swf)\?clip_id=
                            )?
                        (?:videos?/)?
                        (?P<id>[0-9]+)
                        (?:/(?P<unlisted_hash>[\da-f]{10}))?
                        /?(?:[?&].*)?(?:[#].*)?$
                    '''
    IE_NAME = 'vimeo'
    _TESTS = [
        {
            'url': 'http://vimeo.com/56015672#at=0',
            'md5': '8879b6cc097e987f02484baf890129e5',
            'info_dict': {
                'id': '56015672',
                'ext': 'mp4',
                'title': "youtube-dl test video - \u2605 \" ' \u5e78 / \\ \u00e4 \u21ad \U0001d550",
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
        },
        {
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
            },
            'params': {
                'format': 'best[protocol=https]',
            },
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
                'description': None,
            },
            'params': {
                'format': 'best[protocol=https]',
            },
            'expected_warnings': ['Unable to download JSON metadata'],
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
                'description': 'md5:dca3ea23adb29ee387127bc4ddfce63f',
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
                'description': 'md5:8678b246399b070816b12313e8b4eb5c',
                'uploader_url': r're:https?://(?:www\.)?vimeo\.com/atencio',
                'uploader_id': 'atencio',
                'uploader': 'Peter Atencio',
                'channel_id': 'keypeele',
                'channel_url': r're:https?://(?:www\.)?vimeo\.com/channels/keypeele',
                'timestamp': 1380339469,
                'upload_date': '20130928',
                'duration': 187,
            },
            'expected_warnings': ['Unable to download JSON metadata'],
        },
        {
            'url': 'http://vimeo.com/76979871',
            'note': 'Video with subtitles',
            'info_dict': {
                'id': '76979871',
                'ext': 'mp4',
                'title': 'The New Vimeo Player (You Know, For Videos)',
                'description': 'md5:2ec900bf97c3f389378a96aee11260ea',
                'timestamp': 1381846109,
                'upload_date': '20131015',
                'uploader_url': r're:https?://(?:www\.)?vimeo\.com/staff',
                'uploader_id': 'staff',
                'uploader': 'Vimeo Staff',
                'duration': 62,
            }
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
            },
            'params': {
                'skip_download': True,
            },
            'expected_warnings': ['Unable to download JSON metadata'],
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
            'expected_warnings': ['Unable to download JSON metadata'],
            'skip': 'this page is no longer available.',
        },
        {
            'url': 'http://player.vimeo.com/video/68375962',
            'md5': 'aaf896bdb7ddd6476df50007a0ac0ae7',
            'info_dict': {
                'id': '68375962',
                'ext': 'mp4',
                'title': 'youtube-dl password protected test video',
                'uploader_url': r're:https?://(?:www\.)?vimeo\.com/user18948128',
                'uploader_id': 'user18948128',
                'uploader': 'Jaime Marquínez Ferrándiz',
                'duration': 10,
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
                'title': 'youtube-dl test video \'ä"BaW_jenozKc',
                'uploader': 'Philipp Hagemeister',
                'uploader_id': 'user20132939',
                'description': 'md5:fa7b6c6d8db0bdc353893df2f111855b',
                'upload_date': '20150209',
                'timestamp': 1423518307,
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
            'url': 'https://vimeo.com/160743502/abd0e13fb4',
            'only_matching': True,
        },
        {
            # requires passing unlisted_hash(a52724358e) to load_download_config request
            'url': 'https://vimeo.com/392479337/a52724358e',
            'only_matching': True,
        }
        # https://gettingthingsdone.com/workflowmap/
        # vimeo embed with check-password page protected by Referer header
    ]

    @staticmethod
    def _smuggle_referrer(url, referrer_url):
        return smuggle_url(url, {'http_headers': {'Referer': referrer_url}})

    @staticmethod
    def _extract_urls(url, webpage):
        urls = []
        # Look for embedded (iframe) Vimeo player
        for mobj in re.finditer(
                r'<iframe[^>]+?src=(["\'])(?P<url>(?:https?:)?//player\.vimeo\.com/video/\d+.*?)\1',
                webpage):
            urls.append(VimeoIE._smuggle_referrer(unescapeHTML(mobj.group('url')), url))
        PLAIN_EMBED_RE = (
            # Look for embedded (swf embed) Vimeo player
            r'<embed[^>]+?src=(["\'])(?P<url>(?:https?:)?//(?:www\.)?vimeo\.com/moogaloop\.swf.+?)\1',
            # Look more for non-standard embedded Vimeo player
            r'<video[^>]+src=(["\'])(?P<url>(?:https?:)?//(?:www\.)?vimeo\.com/[0-9]+)\1',
        )
        for embed_re in PLAIN_EMBED_RE:
            for mobj in re.finditer(embed_re, webpage):
                urls.append(mobj.group('url'))
        return urls

    @staticmethod
    def _extract_url(url, webpage):
        urls = VimeoIE._extract_urls(url, webpage)
        return urls[0] if urls else None

    def _verify_player_video_password(self, url, video_id, headers):
        password = self._get_video_password()
        data = urlencode_postdata({
            'password': base64.b64encode(password.encode()),
        })
        headers = merge_dicts(headers, {
            'Content-Type': 'application/x-www-form-urlencoded',
        })
        checked = self._download_json(
            url + '/check-password', video_id,
            'Verifying the password', data=data, headers=headers)
        if checked is False:
            raise ExtractorError('Wrong video password', expected=True)
        return checked

    def _real_initialize(self):
        self._login()

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
            album_id, headers={'Authorization': 'jwt ' + jwt},
            query={'fields': 'description,name,privacy'})
        if try_get(album, lambda x: x['privacy']['view']) == 'password':
            password = self._downloader.params.get('videopassword')
            if not password:
                raise ExtractorError(
                    'This album is protected by a password, use the --video-password option',
                    expected=True)
            self._set_vimeo_cookie('vuid', viewer['vuid'])
            try:
                self._download_json(
                    'https://vimeo.com/showcase/%s/auth' % album_id,
                    album_id, 'Verifying the password', data=urlencode_postdata({
                        'password': password,
                        'token': viewer['xsrft'],
                    }), headers={
                        'X-Requested-With': 'XMLHttpRequest',
                    })
            except ExtractorError as e:
                if isinstance(e.cause, compat_HTTPError) and e.cause.code == 401:
                    raise ExtractorError('Wrong password', expected=True)
                raise

    def _real_extract(self, url):
        url, data = unsmuggle_url(url, {})
        headers = std_headers.copy()
        if 'http_headers' in data:
            headers.update(data['http_headers'])
        if 'Referer' not in headers:
            headers['Referer'] = url

        # Extract ID from URL
        video_id, unlisted_hash = re.match(self._VALID_URL, url).groups()
        if unlisted_hash:
            token = self._download_json(
                'https://vimeo.com/_rv/jwt', video_id, headers={
                    'X-Requested-With': 'XMLHttpRequest'
                })['token']
            video = self._download_json(
                'https://api.vimeo.com/videos/%s:%s' % (video_id, unlisted_hash),
                video_id, headers={
                    'Authorization': 'jwt ' + token,
                }, query={
                    'fields': 'config_url,created_time,description,license,metadata.connections.comments.total,metadata.connections.likes.total,release_time,stats.plays',
                })
            info = self._parse_config(self._download_json(
                video['config_url'], video_id), video_id)
            self._vimeo_sort_formats(info['formats'])
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

        orig_url = url
        is_pro = 'vimeopro.com/' in url
        is_player = '://player.vimeo.com/video/' in url
        if is_pro:
            # some videos require portfolio_id to be present in player url
            # https://github.com/ytdl-org/youtube-dl/issues/20070
            url = self._extract_url(url, self._download_webpage(url, video_id))
            if not url:
                url = 'https://vimeo.com/' + video_id
        elif is_player:
            url = 'https://player.vimeo.com/video/' + video_id
        elif any(p in url for p in ('play_redirect_hls', 'moogaloop.swf')):
            url = 'https://vimeo.com/' + video_id

        self._try_album_password(url)
        try:
            # Retrieve video webpage to extract further information
            webpage, urlh = self._download_webpage_handle(
                url, video_id, headers=headers)
            redirect_url = urlh.geturl()
        except ExtractorError as ee:
            if isinstance(ee.cause, compat_HTTPError) and ee.cause.code == 403:
                errmsg = ee.cause.read()
                if b'Because of its privacy settings, this video cannot be played here' in errmsg:
                    raise ExtractorError(
                        'Cannot download embed-only video without embedding '
                        'URL. Please call yt-dlp with the URL of the page '
                        'that embeds this video.',
                        expected=True)
            raise

        # Now we begin extracting as much information as we can from what we
        # retrieved. First we extract the information common to all extractors,
        # and latter we extract those that are Vimeo specific.
        self.report_extraction(video_id)

        vimeo_config = self._extract_vimeo_config(webpage, video_id, default=None)
        if vimeo_config:
            seed_status = vimeo_config.get('seed_status', {})
            if seed_status.get('state') == 'failed':
                raise ExtractorError(
                    '%s said: %s' % (self.IE_NAME, seed_status['title']),
                    expected=True)

        cc_license = None
        timestamp = None
        video_description = None

        # Extract the config JSON
        try:
            try:
                config_url = self._html_search_regex(
                    r' data-config-url="(.+?)"', webpage,
                    'config URL', default=None)
                if not config_url:
                    # Sometimes new react-based page is served instead of old one that require
                    # different config URL extraction approach (see
                    # https://github.com/ytdl-org/youtube-dl/pull/7209)
                    page_config = self._parse_json(self._search_regex(
                        r'vimeo\.(?:clip|vod_title)_page_config\s*=\s*({.+?});',
                        webpage, 'page config'), video_id)
                    config_url = page_config['player']['config_url']
                    cc_license = page_config.get('cc_license')
                    timestamp = try_get(
                        page_config, lambda x: x['clip']['uploaded_on'],
                        compat_str)
                    video_description = clean_html(dict_get(
                        page_config, ('description', 'description_html_escaped')))
                config = self._download_json(config_url, video_id)
            except RegexNotFoundError:
                # For pro videos or player.vimeo.com urls
                # We try to find out to which variable is assigned the config dic
                m_variable_name = re.search(r'(\w)\.video\.id', webpage)
                if m_variable_name is not None:
                    config_re = [r'%s=({[^}].+?});' % re.escape(m_variable_name.group(1))]
                else:
                    config_re = [r' = {config:({.+?}),assets:', r'(?:[abc])=({.+?});']
                config_re.append(r'\bvar\s+r\s*=\s*({.+?})\s*;')
                config_re.append(r'\bconfig\s*=\s*({.+?})\s*;')
                config = self._search_regex(config_re, webpage, 'info section',
                                            flags=re.DOTALL)
                config = json.loads(config)
        except Exception as e:
            if re.search('The creator of this video has not given you permission to embed it on this domain.', webpage):
                raise ExtractorError('The author has restricted the access to this video, try with the "--referer" option')

            if re.search(r'<form[^>]+?id="pw_form"', webpage) is not None:
                if '_video_password_verified' in data:
                    raise ExtractorError('video password verification failed!')
                video_password = self._get_video_password()
                token, vuid = self._extract_xsrft_and_vuid(webpage)
                self._verify_video_password(
                    redirect_url, video_id, video_password, token, vuid)
                return self._real_extract(
                    smuggle_url(redirect_url, {'_video_password_verified': 'verified'}))
            else:
                raise ExtractorError('Unable to extract info section',
                                     cause=e)
        else:
            if config.get('view') == 4:
                config = self._verify_player_video_password(redirect_url, video_id, headers)

        video = config.get('video') or {}
        vod = video.get('vod') or {}

        def is_rented():
            if '>You rented this title.<' in webpage:
                return True
            if config.get('user', {}).get('purchased'):
                return True
            for purchase_option in vod.get('purchase_options', []):
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
                    'https://player.vimeo.com/player/%s' % feature_id,
                    {'force_feature_id': True}), 'Vimeo')

        # Extract video description
        if not video_description:
            video_description = self._html_search_regex(
                r'(?s)<div\s+class="[^"]*description[^"]*"[^>]*>(.*?)</div>',
                webpage, 'description', default=None)
        if not video_description:
            video_description = self._html_search_meta(
                'description', webpage, default=None)
        if not video_description and is_pro:
            orig_webpage = self._download_webpage(
                orig_url, video_id,
                note='Downloading webpage for description',
                fatal=False)
            if orig_webpage:
                video_description = self._html_search_meta(
                    'description', orig_webpage, default=None)
        if not video_description and not is_player:
            self.report_warning('Cannot find video description')

        # Extract upload date
        if not timestamp:
            timestamp = self._search_regex(
                r'<time[^>]+datetime="([^"]+)"', webpage,
                'timestamp', default=None)

        try:
            view_count = int(self._search_regex(r'UserPlays:(\d+)', webpage, 'view count'))
            like_count = int(self._search_regex(r'UserLikes:(\d+)', webpage, 'like count'))
            comment_count = int(self._search_regex(r'UserComments:(\d+)', webpage, 'comment count'))
        except RegexNotFoundError:
            # This info is only available in vimeo.com/{id} urls
            view_count = None
            like_count = None
            comment_count = None

        formats = []

        source_format = self._extract_original_format(
            'https://vimeo.com/' + video_id, video_id, video.get('unlisted_hash'))
        if source_format:
            formats.append(source_format)

        info_dict_config = self._parse_config(config, video_id)
        formats.extend(info_dict_config['formats'])
        self._vimeo_sort_formats(formats)

        json_ld = self._search_json_ld(webpage, video_id, default={})

        if not cc_license:
            cc_license = self._search_regex(
                r'<link[^>]+rel=["\']license["\'][^>]+href=(["\'])(?P<license>(?:(?!\1).)+)\1',
                webpage, 'license', default=None, group='license')

        channel_id = self._search_regex(
            r'vimeo\.com/channels/([^/]+)', url, 'channel id', default=None)
        channel_url = 'https://vimeo.com/channels/%s' % channel_id if channel_id else None

        info_dict = {
            'formats': formats,
            'timestamp': unified_timestamp(timestamp),
            'description': video_description,
            'webpage_url': url,
            'view_count': view_count,
            'like_count': like_count,
            'comment_count': comment_count,
            'license': cc_license,
            'channel_id': channel_id,
            'channel_url': channel_url,
        }

        info_dict = merge_dicts(info_dict, info_dict_config, json_ld)

        return info_dict


class VimeoOndemandIE(VimeoIE):
    IE_NAME = 'vimeo:ondemand'
    _VALID_URL = r'https?://(?:www\.)?vimeo\.com/ondemand/([^/]+/)?(?P<id>[^/?#&]+)'
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
            'description': 'md5:4c027c965e439de4baab621e48b60791',
            'upload_date': '20140906',
            'timestamp': 1410032453,
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
        'playlist_mincount': 25,
    }]
    _BASE_URL_TEMPL = 'https://vimeo.com/channels/%s'

    def _page_url(self, base_url, pagenum):
        return '%s/videos/page:%d/' % (base_url, pagenum)

    def _extract_list_title(self, webpage):
        return self._TITLE or self._html_search_regex(
            self._TITLE_RE, webpage, 'list title', fatal=False)

    def _title_and_entries(self, list_id, base_url):
        for pagenum in itertools.count(1):
            page_url = self._page_url(base_url, pagenum)
            webpage = self._download_webpage(
                page_url, list_id,
                'Downloading page %s' % pagenum)

            if pagenum == 1:
                yield self._extract_list_title(webpage)

            # Try extracting href first since not all videos are available via
            # short https://vimeo.com/id URL (e.g. https://vimeo.com/channels/tributes/6213729)
            clips = re.findall(
                r'id="clip_(\d+)"[^>]*>\s*<a[^>]+href="(/(?:[^/]+/)*\1)(?:[^>]+\btitle="([^"]+)")?', webpage)
            if clips:
                for video_id, video_url, video_title in clips:
                    yield self.url_result(
                        compat_urlparse.urljoin(base_url, video_url),
                        VimeoIE.ie_key(), video_id=video_id, video_title=video_title)
            # More relaxed fallback
            else:
                for video_id in re.findall(r'id=["\']clip_(\d+)', webpage):
                    yield self.url_result(
                        'https://vimeo.com/%s' % video_id,
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


class VimeoUserIE(VimeoChannelIE):
    IE_NAME = 'vimeo:user'
    _VALID_URL = r'https://vimeo\.com/(?!(?:[0-9]+|watchlater)(?:$|[?#/]))(?P<id>[^/]+)(?:/videos|[#?]|$)'
    _TITLE_RE = r'<a[^>]+?class="user">([^<>]+?)</a>'
    _TESTS = [{
        'url': 'https://vimeo.com/nkistudio/videos',
        'info_dict': {
            'title': 'Nki',
            'id': 'nkistudio',
        },
        'playlist_mincount': 66,
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
        }
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
                'https://api.vimeo.com/albums/%s/videos' % album_id,
                album_id, 'Downloading page %d' % api_page, query=query, headers={
                    'Authorization': 'jwt ' + authorization,
                })['data']
        except ExtractorError as e:
            if isinstance(e.cause, compat_HTTPError) and e.cause.code == 400:
                return
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
            album_id, headers={'Authorization': 'jwt ' + jwt},
            query={'fields': 'description,name,privacy'})
        hashed_pass = None
        if try_get(album, lambda x: x['privacy']['view']) == 'password':
            password = self._downloader.params.get('videopassword')
            if not password:
                raise ExtractorError(
                    'This album is protected by a password, use the --video-password option',
                    expected=True)
            self._set_vimeo_cookie('vuid', viewer['vuid'])
            try:
                hashed_pass = self._download_json(
                    'https://vimeo.com/showcase/%s/auth' % album_id,
                    album_id, 'Verifying the password', data=urlencode_postdata({
                        'password': password,
                        'token': viewer['xsrft'],
                    }), headers={
                        'X-Requested-With': 'XMLHttpRequest',
                    })['hashed_pass']
            except ExtractorError as e:
                if isinstance(e.cause, compat_HTTPError) and e.cause.code == 401:
                    raise ExtractorError('Wrong password', expected=True)
                raise
        entries = OnDemandPagedList(functools.partial(
            self._fetch_page, album_id, jwt, hashed_pass), self._PAGE_SIZE)
        return self.playlist_result(
            entries, album_id, album.get('name'), album.get('description'))


class VimeoGroupsIE(VimeoChannelIE):
    IE_NAME = 'vimeo:group'
    _VALID_URL = r'https://vimeo\.com/groups/(?P<id>[^/]+)(?:/(?!videos?/\d+)|$)'
    _TESTS = [{
        'url': 'https://vimeo.com/groups/kattykay',
        'info_dict': {
            'id': 'kattykay',
            'title': 'Katty Kay',
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
        },
        'expected_warnings': ['Unable to download JSON metadata'],
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

    def _real_initialize(self):
        self._login()

    def _real_extract(self, url):
        page_url, video_id = re.match(self._VALID_URL, url).groups()
        data = self._download_json(
            page_url.replace('/review/', '/review/data/'), video_id)
        if data.get('isLocked') is True:
            video_password = self._get_video_password()
            viewer = self._download_json(
                'https://vimeo.com/_rv/viewer', video_id)
            webpage = self._verify_video_password(
                'https://vimeo.com/' + video_id, video_id,
                video_password, viewer['xsrft'], viewer['vuid'])
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
        self._vimeo_sort_formats(info_dict['formats'])
        info_dict['description'] = clean_html(clip_data.get('description'))
        return info_dict


class VimeoWatchLaterIE(VimeoChannelIE):
    IE_NAME = 'vimeo:watchlater'
    IE_DESC = 'Vimeo watch later list, "vimeowatchlater" keyword (requires authentication)'
    _VALID_URL = r'https://vimeo\.com/(?:home/)?watchlater|:vimeowatchlater'
    _TITLE = 'Watch Later'
    _LOGIN_REQUIRED = True
    _TESTS = [{
        'url': 'https://vimeo.com/watchlater',
        'only_matching': True,
    }]

    def _real_initialize(self):
        self._login()

    def _page_url(self, base_url, pagenum):
        url = '%s/page:%d/' % (base_url, pagenum)
        request = sanitized_Request(url)
        # Set the header to get a partial html page with the ids,
        # the normal page doesn't contain them.
        request.add_header('X-Requested-With', 'XMLHttpRequest')
        return request

    def _real_extract(self, url):
        return self._extract_videos('watchlater', 'https://vimeo.com/watchlater')


class VimeoLikesIE(VimeoChannelIE):
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
        return '%s/page:%d/' % (base_url, pagenum)

    def _real_extract(self, url):
        user_id = self._match_id(url)
        return self._extract_videos(user_id, 'https://vimeo.com/%s/likes' % user_id)


class VHXEmbedIE(VimeoBaseInfoExtractor):
    IE_NAME = 'vhx:embed'
    _VALID_URL = r'https?://embed\.vhx\.tv/videos/(?P<id>\d+)'

    @staticmethod
    def _extract_url(webpage):
        mobj = re.search(
            r'<iframe[^>]+src="(https?://embed\.vhx\.tv/videos/\d+[^"]*)"', webpage)
        return unescapeHTML(mobj.group(1)) if mobj else None

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        config_url = self._parse_json(self._search_regex(
            r'window\.OTTData\s*=\s*({.+})', webpage,
            'ott data'), video_id, js_to_json)['config_url']
        config = self._download_json(config_url, video_id)
        info = self._parse_config(config, video_id)
        info['id'] = video_id
        self._vimeo_sort_formats(info['formats'])
        return info
