import re

from .adobepass import AdobePassIE
from ..compat import compat_str
from ..utils import (
    fix_xml_ampersands,
    xpath_text,
    int_or_none,
    determine_ext,
    float_or_none,
    parse_duration,
    xpath_attr,
    update_url_query,
    ExtractorError,
    strip_or_none,
    url_or_none,
)


class TurnerBaseIE(AdobePassIE):
    _AKAMAI_SPE_TOKEN_CACHE = {}

    def _extract_timestamp(self, video_data):
        return int_or_none(xpath_attr(video_data, 'dateCreated', 'uts'))

    def _add_akamai_spe_token(self, tokenizer_src, video_url, content_id, ap_data, custom_tokenizer_query=None):
        secure_path = self._search_regex(r'https?://[^/]+(.+/)', video_url, 'secure path') + '*'
        token = self._AKAMAI_SPE_TOKEN_CACHE.get(secure_path)
        if not token:
            query = {
                'path': secure_path,
            }
            if custom_tokenizer_query:
                query.update(custom_tokenizer_query)
            else:
                query['videoId'] = content_id
            if ap_data.get('auth_required'):
                query['accessToken'] = self._extract_mvpd_auth(ap_data['url'], content_id, ap_data['site_name'], ap_data['site_name'])
            auth = self._download_xml(
                tokenizer_src, content_id, query=query)
            error_msg = xpath_text(auth, 'error/msg')
            if error_msg:
                raise ExtractorError(error_msg, expected=True)
            token = xpath_text(auth, 'token')
            if not token:
                return video_url
            self._AKAMAI_SPE_TOKEN_CACHE[secure_path] = token
        return video_url + '?hdnea=' + token

    def _extract_cvp_info(self, data_src, video_id, path_data={}, ap_data={}, fatal=False):
        video_data = self._download_xml(
            data_src, video_id,
            transform_source=lambda s: fix_xml_ampersands(s).strip(),
            fatal=fatal)
        if not video_data:
            return {}
        video_id = video_data.attrib['id']
        title = xpath_text(video_data, 'headline', fatal=True)
        content_id = xpath_text(video_data, 'contentId') or video_id
        # rtmp_src = xpath_text(video_data, 'akamai/src')
        # if rtmp_src:
        #     split_rtmp_src = rtmp_src.split(',')
        #     if len(split_rtmp_src) == 2:
        #         rtmp_src = split_rtmp_src[1]
        # aifp = xpath_text(video_data, 'akamai/aifp', default='')

        urls = []
        formats = []
        thumbnails = []
        subtitles = {}
        rex = re.compile(
            r'(?P<width>[0-9]+)x(?P<height>[0-9]+)(?:_(?P<bitrate>[0-9]+))?')
        # Possible formats locations: files/file, files/groupFiles/files
        # and maybe others
        for video_file in video_data.findall('.//file'):
            video_url = url_or_none(video_file.text.strip())
            if not video_url:
                continue
            ext = determine_ext(video_url)
            if video_url.startswith('/mp4:protected/'):
                continue
                # TODO Correct extraction for these files
                # protected_path_data = path_data.get('protected')
                # if not protected_path_data or not rtmp_src:
                #     continue
                # protected_path = self._search_regex(
                #     r'/mp4:(.+)\.[a-z0-9]', video_url, 'secure path')
                # auth = self._download_webpage(
                #     protected_path_data['tokenizer_src'], query={
                #         'path': protected_path,
                #         'videoId': content_id,
                #         'aifp': aifp,
                #     })
                # token = xpath_text(auth, 'token')
                # if not token:
                #     continue
                # video_url = rtmp_src + video_url + '?' + token
            elif video_url.startswith('/secure/'):
                secure_path_data = path_data.get('secure')
                if not secure_path_data:
                    continue
                video_url = self._add_akamai_spe_token(
                    secure_path_data['tokenizer_src'],
                    secure_path_data['media_src'] + video_url,
                    content_id, ap_data)
            elif not re.match('https?://', video_url):
                base_path_data = path_data.get(ext, path_data.get('default', {}))
                media_src = base_path_data.get('media_src')
                if not media_src:
                    continue
                video_url = media_src + video_url
            if video_url in urls:
                continue
            urls.append(video_url)
            format_id = video_file.get('bitrate')
            if ext in ('scc', 'srt', 'vtt'):
                subtitles.setdefault('en', []).append({
                    'ext': ext,
                    'url': video_url,
                })
            elif ext == 'png':
                thumbnails.append({
                    'id': format_id,
                    'url': video_url,
                })
            elif ext == 'smil':
                formats.extend(self._extract_smil_formats(
                    video_url, video_id, fatal=False))
            elif re.match(r'https?://[^/]+\.akamaihd\.net/[iz]/', video_url):
                formats.extend(self._extract_akamai_formats(
                    video_url, video_id, {
                        'hds': path_data.get('f4m', {}).get('host'),
                        # nba.cdn.turner.com, ht.cdn.turner.com, ht2.cdn.turner.com
                        # ht3.cdn.turner.com, i.cdn.turner.com, s.cdn.turner.com
                        # ssl.cdn.turner.com
                        'http': 'pmd.cdn.turner.com',
                    }))
            elif ext == 'm3u8':
                m3u8_formats = self._extract_m3u8_formats(
                    video_url, video_id, 'mp4',
                    m3u8_id=format_id or 'hls', fatal=False)
                if '/secure/' in video_url and '?hdnea=' in video_url:
                    for f in m3u8_formats:
                        f['downloader_options'] = {'ffmpeg_args': ['-seekable', '0']}
                formats.extend(m3u8_formats)
            elif ext == 'f4m':
                formats.extend(self._extract_f4m_formats(
                    update_url_query(video_url, {'hdcore': '3.7.0'}),
                    video_id, f4m_id=format_id or 'hds', fatal=False))
            else:
                f = {
                    'format_id': format_id,
                    'url': video_url,
                    'ext': ext,
                }
                mobj = rex.search(video_url)
                if mobj:
                    f.update({
                        'width': int(mobj.group('width')),
                        'height': int(mobj.group('height')),
                        'tbr': int_or_none(mobj.group('bitrate')),
                    })
                elif isinstance(format_id, compat_str):
                    if format_id.isdigit():
                        f['tbr'] = int(format_id)
                    else:
                        mobj = re.match(r'ios_(audio|[0-9]+)$', format_id)
                        if mobj:
                            if mobj.group(1) == 'audio':
                                f.update({
                                    'vcodec': 'none',
                                    'ext': 'm4a',
                                })
                            else:
                                f['tbr'] = int(mobj.group(1))
                formats.append(f)
        self._sort_formats(formats)

        for source in video_data.findall('closedCaptions/source'):
            for track in source.findall('track'):
                track_url = url_or_none(track.get('url'))
                if not track_url or track_url.endswith('/big'):
                    continue
                lang = track.get('lang') or track.get('label') or 'en'
                subtitles.setdefault(lang, []).append({
                    'url': track_url,
                    'ext': {
                        'scc': 'scc',
                        'webvtt': 'vtt',
                        'smptett': 'tt',
                    }.get(source.get('format'))
                })

        thumbnails.extend({
            'id': image.get('cut') or image.get('name'),
            'url': image.text,
            'width': int_or_none(image.get('width')),
            'height': int_or_none(image.get('height')),
        } for image in video_data.findall('images/image'))

        is_live = xpath_text(video_data, 'isLive') == 'true'

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
            'subtitles': subtitles,
            'thumbnails': thumbnails,
            'thumbnail': xpath_text(video_data, 'poster'),
            'description': strip_or_none(xpath_text(video_data, 'description')),
            'duration': parse_duration(xpath_text(video_data, 'length') or xpath_text(video_data, 'trt')),
            'timestamp': self._extract_timestamp(video_data),
            'upload_date': xpath_attr(video_data, 'metas', 'version'),
            'series': xpath_text(video_data, 'showTitle'),
            'season_number': int_or_none(xpath_text(video_data, 'seasonNumber')),
            'episode_number': int_or_none(xpath_text(video_data, 'episodeNumber')),
            'is_live': is_live,
        }

    def _extract_ngtv_info(self, media_id, tokenizer_query, ap_data=None):
        is_live = ap_data.get('is_live')
        streams_data = self._download_json(
            'http://medium.ngtv.io/media/%s/tv' % media_id,
            media_id)['media']['tv']
        duration = None
        chapters = []
        formats = []
        for supported_type in ('unprotected', 'bulkaes'):
            stream_data = streams_data.get(supported_type, {})
            m3u8_url = stream_data.get('secureUrl') or stream_data.get('url')
            if not m3u8_url:
                continue
            if stream_data.get('playlistProtection') == 'spe':
                m3u8_url = self._add_akamai_spe_token(
                    'http://token.ngtv.io/token/token_spe',
                    m3u8_url, media_id, ap_data or {}, tokenizer_query)
            formats.extend(self._extract_m3u8_formats(
                m3u8_url, media_id, 'mp4', m3u8_id='hls', live=is_live, fatal=False))

            duration = float_or_none(stream_data.get('totalRuntime'))

            if not chapters and not is_live:
                for chapter in stream_data.get('contentSegments', []):
                    start_time = float_or_none(chapter.get('start'))
                    chapter_duration = float_or_none(chapter.get('duration'))
                    if start_time is None or chapter_duration is None:
                        continue
                    chapters.append({
                        'start_time': start_time,
                        'end_time': start_time + chapter_duration,
                    })
        self._sort_formats(formats)

        return {
            'formats': formats,
            'chapters': chapters,
            'duration': duration,
        }
