import re

from .common import InfoExtractor
from ..utils import (
    clean_html,
    int_or_none,
    parse_codecs,
    parse_duration,
    str_to_int,
    unified_timestamp
)


class GabTVIE(InfoExtractor):
    _VALID_URL = r'https?://tv\.gab\.com/channel/[^/]+/view/(?P<id>[a-z0-9-]+)'
    _TESTS = [{
        'url': 'https://tv.gab.com/channel/wurzelroot/view/why-was-america-in-afghanistan-61217eacea5665de450d0488',
        'info_dict': {
            'id': '61217eacea5665de450d0488',
            'ext': 'mp4',
            'title': 'WHY WAS AMERICA IN AFGHANISTAN - AMERICA FIRST AGAINST AMERICAN OLIGARCHY',
            'description': None,
            'uploader': 'Wurzelroot',
            'uploader_id': '608fb0a85738fd1974984f7d',
            'thumbnail': 'https://tv.gab.com/image/61217eacea5665de450d0488',
        }
    }]

    def _real_extract(self, url):
        id = self._match_id(url).split('-')[-1]
        webpage = self._download_webpage(url, id)
        channel_id = self._search_regex(r'data-channel-id=\"(?P<channel_id>[^\"]+)', webpage, 'channel_id')
        channel_name = self._search_regex(r'data-channel-name=\"(?P<channel_id>[^\"]+)', webpage, 'channel_name')
        title = self._search_regex(r'data-episode-title=\"(?P<channel_id>[^\"]+)', webpage, 'title')
        view_key = self._search_regex(r'data-view-key=\"(?P<channel_id>[^\"]+)', webpage, 'view_key')
        description = clean_html(
            self._html_search_regex(self._meta_regex('description'), webpage, 'description', group='content')) or None
        available_resolutions = re.findall(r'<a\ data-episode-id=\"%s\"\ data-resolution=\"(?P<resolution>[^\"]+)' % id,
                                           webpage)

        formats = []
        for resolution in available_resolutions:
            frmt = {
                'url': f'https://tv.gab.com/media/{id}?viewKey={view_key}&r={resolution}',
                'format_id': resolution,
                'vcodec': 'h264',
                'acodec': 'aac',
                'ext': 'mp4'
            }
            if 'audio-' in resolution:
                frmt['abr'] = str_to_int(resolution.replace('audio-', ''))
                frmt['height'] = 144
                frmt['quality'] = -10
            else:
                frmt['height'] = str_to_int(resolution.replace('p', ''))
            formats.append(frmt)
        self._sort_formats(formats)

        return {
            'id': id,
            'title': title,
            'formats': formats,
            'description': description,
            'uploader': channel_name,
            'uploader_id': channel_id,
            'thumbnail': f'https://tv.gab.com/image/{id}',
        }


class GabIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?gab\.com/[^/]+/posts/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://gab.com/SomeBitchIKnow/posts/107163961867310434',
        'md5': '8ca34fb00f1e1033b5c5988d79ec531d',
        'info_dict': {
            'id': '107163961867310434-0',
            'ext': 'mp4',
            'title': 'L on Gab',
            'uploader_id': '946600',
            'uploader': 'SomeBitchIKnow',
            'description': 'md5:204055fafd5e1a519f5d6db953567ca3',
            'timestamp': 1635192289,
            'upload_date': '20211025',
        }
    }, {
        'url': 'https://gab.com/TheLonelyProud/posts/107045884469287653',
        'md5': 'f9cefcfdff6418e392611a828d47839d',
        'info_dict': {
            'id': '107045884469287653-0',
            'ext': 'mp4',
            'title': 'Jody Sadowski on Gab',
            'uploader_id': '1390705',
            'timestamp': 1633390571,
            'upload_date': '20211004',
            'uploader': 'TheLonelyProud',
        }
    }]

    def _real_extract(self, url):
        post_id = self._match_id(url)
        json_data = self._download_json(f'https://gab.com/api/v1/statuses/{post_id}', post_id)

        entries = []
        for idx, media in enumerate(json_data['media_attachments']):
            if media.get('type') not in ('video', 'gifv'):
                continue
            metadata = media['meta']
            format_metadata = {
                'acodec': parse_codecs(metadata.get('audio_encode')).get('acodec'),
                'asr': int_or_none((metadata.get('audio_bitrate') or '').split(' ')[0]),
                'fps': metadata.get('fps'),
            }

            formats = [{
                'url': url,
                'width': f.get('width'),
                'height': f.get('height'),
                'tbr': int_or_none(f.get('bitrate'), scale=1000),
                **format_metadata,
            } for url, f in ((media.get('url'), metadata.get('original') or {}),
                             (media.get('source_mp4'), metadata.get('playable') or {})) if url]

            self._sort_formats(formats)

            author = json_data.get('account') or {}
            entries.append({
                'id': f'{post_id}-{idx}',
                'title': f'{json_data["account"]["display_name"]} on Gab',
                'timestamp': unified_timestamp(json_data.get('created_at')),
                'formats': formats,
                'description': clean_html(json_data.get('content')),
                'duration': metadata.get('duration') or parse_duration(metadata.get('length')),
                'like_count': json_data.get('favourites_count'),
                'comment_count': json_data.get('replies_count'),
                'repost_count': json_data.get('reblogs_count'),
                'uploader': author.get('username'),
                'uploader_id': author.get('id'),
                'uploader_url': author.get('url'),
            })

        if len(entries) > 1:
            return self.playlist_result(entries, post_id)

        return entries[0]
