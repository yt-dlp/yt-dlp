from .common import InfoExtractor
from ..utils import (
    clean_html,
    int_or_none,
    parse_codecs,
    parse_duration,
    unified_timestamp,
)


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
        },
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
        },
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
