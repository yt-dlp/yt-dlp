from __future__ import unicode_literals

import random
import re

from .common import InfoExtractor
from ..compat import (
    compat_str,
    compat_urlparse,
)
from ..utils import (
    encode_data_uri,
    ExtractorError,
    int_or_none,
    float_or_none,
    join_nonempty,
    mimetype2ext,
    str_or_none,
)


class UstreamIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?(?:ustream\.tv|video\.ibm\.com)/(?P<type>recorded|embed|embed/recorded)/(?P<id>\d+)'
    IE_NAME = 'ustream'
    _TESTS = [{
        'url': 'http://www.ustream.tv/recorded/20274954',
        'md5': '088f151799e8f572f84eb62f17d73e5c',
        'info_dict': {
            'id': '20274954',
            'ext': 'flv',
            'title': 'Young Americans for Liberty February 7, 2012 2:28 AM',
            'description': 'Young Americans for Liberty February 7, 2012 2:28 AM',
            'timestamp': 1328577035,
            'upload_date': '20120207',
            'uploader': 'yaliberty',
            'uploader_id': '6780869',
        },
    }, {
        # From http://sportscanada.tv/canadagames/index.php/week2/figure-skating/444
        # Title and uploader available only from params JSON
        'url': 'http://www.ustream.tv/embed/recorded/59307601?ub=ff0000&lc=ff0000&oc=ffffff&uc=ffffff&v=3&wmode=direct',
        'md5': '5a2abf40babeac9812ed20ae12d34e10',
        'info_dict': {
            'id': '59307601',
            'ext': 'flv',
            'title': '-CG11- Canada Games Figure Skating',
            'uploader': 'sportscanadatv',
        },
        'skip': 'This Pro Broadcaster has chosen to remove this video from the ustream.tv site.',
    }, {
        'url': 'http://www.ustream.tv/embed/10299409',
        'info_dict': {
            'id': '10299409',
        },
        'playlist_count': 3,
    }, {
        'url': 'http://www.ustream.tv/recorded/91343263',
        'info_dict': {
            'id': '91343263',
            'ext': 'mp4',
            'title': 'GitHub Universe - General Session - Day 1',
            'upload_date': '20160914',
            'description': 'GitHub Universe - General Session - Day 1',
            'timestamp': 1473872730,
            'uploader': 'wa0dnskeqkr',
            'uploader_id': '38977840',
        },
        'params': {
            'skip_download': True,  # m3u8 download
        },
    }, {
        'url': 'https://video.ibm.com/embed/recorded/128240221?&autoplay=true&controls=true&volume=100',
        'only_matching': True,
    }]

    @staticmethod
    def _extract_url(webpage):
        mobj = re.search(
            r'<iframe[^>]+?src=(["\'])(?P<url>https?://(?:www\.)?(?:ustream\.tv|video\.ibm\.com)/embed/.+?)\1', webpage)
        if mobj is not None:
            return mobj.group('url')

    def _get_stream_info(self, url, video_id, app_id_ver, extra_note=None):
        def num_to_hex(n):
            return hex(n)[2:]

        rnd = random.randrange

        if not extra_note:
            extra_note = ''

        conn_info = self._download_json(
            'http://r%d-1-%s-recorded-lp-live.ums.ustream.tv/1/ustream' % (rnd(1e8), video_id),
            video_id, note='Downloading connection info' + extra_note,
            query={
                'type': 'viewer',
                'appId': app_id_ver[0],
                'appVersion': app_id_ver[1],
                'rsid': '%s:%s' % (num_to_hex(rnd(1e8)), num_to_hex(rnd(1e8))),
                'rpin': '_rpin.%d' % rnd(1e15),
                'referrer': url,
                'media': video_id,
                'application': 'recorded',
            })
        host = conn_info[0]['args'][0]['host']
        connection_id = conn_info[0]['args'][0]['connectionId']

        return self._download_json(
            'http://%s/1/ustream?connectionId=%s' % (host, connection_id),
            video_id, note='Downloading stream info' + extra_note)

    def _get_streams(self, url, video_id, app_id_ver):
        # Sometimes the return dict does not have 'stream'
        for trial_count in range(3):
            stream_info = self._get_stream_info(
                url, video_id, app_id_ver,
                extra_note=' (try %d)' % (trial_count + 1) if trial_count > 0 else '')
            if 'stream' in stream_info[0]['args'][0]:
                return stream_info[0]['args'][0]['stream']
        return []

    def _parse_segmented_mp4(self, dash_stream_info):
        def resolve_dash_template(template, idx, chunk_hash):
            return template.replace('%', compat_str(idx), 1).replace('%', chunk_hash)

        formats = []
        for stream in dash_stream_info['streams']:
            # Use only one provider to avoid too many formats
            provider = dash_stream_info['providers'][0]
            fragments = [{
                'url': resolve_dash_template(
                    provider['url'] + stream['initUrl'], 0, dash_stream_info['hashes']['0'])
            }]
            for idx in range(dash_stream_info['videoLength'] // dash_stream_info['chunkTime']):
                fragments.append({
                    'url': resolve_dash_template(
                        provider['url'] + stream['segmentUrl'], idx,
                        dash_stream_info['hashes'][compat_str(idx // 10 * 10)])
                })
            content_type = stream['contentType']
            kind = content_type.split('/')[0]
            f = {
                'format_id': join_nonempty(
                    'dash', kind, str_or_none(stream.get('bitrate'))),
                'protocol': 'http_dash_segments',
                # TODO: generate a MPD doc for external players?
                'url': encode_data_uri(b'<MPD/>', 'text/xml'),
                'ext': mimetype2ext(content_type),
                'height': stream.get('height'),
                'width': stream.get('width'),
                'fragments': fragments,
            }
            if kind == 'video':
                f.update({
                    'vcodec': stream.get('codec'),
                    'acodec': 'none',
                    'vbr': stream.get('bitrate'),
                })
            else:
                f.update({
                    'vcodec': 'none',
                    'acodec': stream.get('codec'),
                    'abr': stream.get('bitrate'),
                })
            formats.append(f)
        return formats

    def _real_extract(self, url):
        m = self._match_valid_url(url)
        video_id = m.group('id')

        # some sites use this embed format (see: https://github.com/ytdl-org/youtube-dl/issues/2990)
        if m.group('type') == 'embed/recorded':
            video_id = m.group('id')
            desktop_url = 'http://www.ustream.tv/recorded/' + video_id
            return self.url_result(desktop_url, 'Ustream')
        if m.group('type') == 'embed':
            video_id = m.group('id')
            webpage = self._download_webpage(url, video_id)
            content_video_ids = self._parse_json(self._search_regex(
                r'ustream\.vars\.offAirContentVideoIds=([^;]+);', webpage,
                'content video IDs'), video_id)
            return self.playlist_result(
                map(lambda u: self.url_result('http://www.ustream.tv/recorded/' + u, 'Ustream'), content_video_ids),
                video_id)

        params = self._download_json(
            'https://api.ustream.tv/videos/%s.json' % video_id, video_id)

        error = params.get('error')
        if error:
            raise ExtractorError(
                '%s returned error: %s' % (self.IE_NAME, error), expected=True)

        video = params['video']

        title = video['title']
        filesize = float_or_none(video.get('file_size'))

        formats = [{
            'id': video_id,
            'url': video_url,
            'ext': format_id,
            'filesize': filesize,
        } for format_id, video_url in video['media_urls'].items() if video_url]

        if not formats:
            hls_streams = self._get_streams(url, video_id, app_id_ver=(11, 2))
            if hls_streams:
                # m3u8_native leads to intermittent ContentTooShortError
                formats.extend(self._extract_m3u8_formats(
                    hls_streams[0]['url'], video_id, ext='mp4', m3u8_id='hls'))

            '''
            # DASH streams handling is incomplete as 'url' is missing
            dash_streams = self._get_streams(url, video_id, app_id_ver=(3, 1))
            if dash_streams:
                formats.extend(self._parse_segmented_mp4(dash_streams))
            '''

        self._sort_formats(formats)

        description = video.get('description')
        timestamp = int_or_none(video.get('created_at'))
        duration = float_or_none(video.get('length'))
        view_count = int_or_none(video.get('views'))

        uploader = video.get('owner', {}).get('username')
        uploader_id = video.get('owner', {}).get('id')

        thumbnails = [{
            'id': thumbnail_id,
            'url': thumbnail_url,
        } for thumbnail_id, thumbnail_url in video.get('thumbnail', {}).items()]

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'thumbnails': thumbnails,
            'timestamp': timestamp,
            'duration': duration,
            'view_count': view_count,
            'uploader': uploader,
            'uploader_id': uploader_id,
            'formats': formats,
        }


class UstreamChannelIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?ustream\.tv/channel/(?P<slug>.+)'
    IE_NAME = 'ustream:channel'
    _TEST = {
        'url': 'http://www.ustream.tv/channel/channeljapan',
        'info_dict': {
            'id': '10874166',
        },
        'playlist_mincount': 17,
    }

    def _real_extract(self, url):
        m = self._match_valid_url(url)
        display_id = m.group('slug')
        webpage = self._download_webpage(url, display_id)
        channel_id = self._html_search_meta('ustream:channel_id', webpage)

        BASE = 'http://www.ustream.tv'
        next_url = '/ajax/socialstream/videos/%s/1.json' % channel_id
        video_ids = []
        while next_url:
            reply = self._download_json(
                compat_urlparse.urljoin(BASE, next_url), display_id,
                note='Downloading video information (next: %d)' % (len(video_ids) + 1))
            video_ids.extend(re.findall(r'data-content-id="(\d.*)"', reply['data']))
            next_url = reply['nextUrl']

        entries = [
            self.url_result('http://www.ustream.tv/recorded/' + vid, 'Ustream')
            for vid in video_ids]
        return {
            '_type': 'playlist',
            'id': channel_id,
            'display_id': display_id,
            'entries': entries,
        }
