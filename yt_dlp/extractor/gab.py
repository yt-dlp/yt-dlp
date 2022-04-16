import re

from .common import InfoExtractor
import urllib.parse
from ..utils import (
    clean_html,
    int_or_none,
    js_to_json,
    parse_codecs,
    parse_duration,
    unified_timestamp,
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
            'thumbnail': 'https://tv.gab.com/image/61217eca90b0355f10c99383',
        }
    }, {
        'url': 'https://tv.gab.com/channel/americanflavored/view/downhill-go-kart-race-no-engines-6254b9eaf1b75c149c703b7f',
        'info_dict': {
            'id': '6254b9eaf1b75c149c703b7f',
            'ext': 'mp4',
            'title': 'Downhill Go Kart Race- No Engines',
            'description': None,
            'uploader': 'AmericanFlavored',
            'uploader_id': '62454a53299da61b33305901',
            'thumbnail': 'https://tv.gab.com/image/6254b9f31e03ac67731b035a',
        }
    }]
    _DOMAIN = 'https://tv.gab.com/'

    def _real_extract(self, url):
        id = self._match_id(url).split('-')[-1]
        webpage = self._download_webpage(url, id)
        channel_id = self._search_regex(r'data-channel-id=\"(?P<channel_id>[^\"]+)', webpage, 'channel_id')
        video_info = self._parse_json(self._search_regex(r'(?s)mediaMetadata\:\s+(\{.+?\})', webpage, 'video_info'),
                                      video_id=id, transform_source=js_to_json)
        title = video_info.get('title')
        description = clean_html(
            self._html_search_regex(self._meta_regex('description'), webpage, 'description', group='content')) or None
        formats = [{
            'format_id': q,
            'quality': q,
            'ext': 'mp4',
            'url': urllib.parse.urljoin(self._DOMAIN, src),
        } for src, q in re.findall(r'<source[^>]+src="(?P<src>[^"]+)"[^>]*\ssize="(?P<quality>\d+)"', webpage)]
        self._sort_formats(formats)

        return {
            'id': id,
            'title': title,
            'formats': formats,
            'description': description,
            'uploader': video_info.get('artist'),
            'uploader_id': channel_id,
            'thumbnail': urllib.parse.urljoin(self._DOMAIN, self._search_regex(r'data-poster=\"(?P<data_poster>[^\"]+)', webpage, 'data_poster', fatal=False)),
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
