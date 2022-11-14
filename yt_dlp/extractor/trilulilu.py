from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    int_or_none,
    parse_iso8601,
)


class TriluliluIE(InfoExtractor):
    _VALID_URL = r'https?://(?:(?:www|m)\.)?trilulilu\.ro/(?:[^/]+/)?(?P<id>[^/#\?]+)'
    _TESTS = [{
        'url': 'http://www.trilulilu.ro/big-buck-bunny-1',
        'md5': '68da087b676a6196a413549212f60cc6',
        'info_dict': {
            'id': 'ae2899e124140b',
            'ext': 'mp4',
            'title': 'Big Buck Bunny',
            'description': ':) pentru copilul din noi',
            'uploader_id': 'chipy',
            'upload_date': '20120304',
            'timestamp': 1330830647,
            'uploader': 'chipy',
            'view_count': int,
            'like_count': int,
            'comment_count': int,
        },
    }, {
        'url': 'http://www.trilulilu.ro/adena-ft-morreti-inocenta',
        'md5': '929dfb8729dc71750463af88bbbbf4a4',
        'info_dict': {
            'id': 'f299710e3c91c5',
            'ext': 'mp4',
            'title': 'Adena ft. Morreti - Inocenta',
            'description': 'pop music',
            'uploader_id': 'VEVOmixt',
            'upload_date': '20151204',
            'uploader': 'VEVOmixt',
            'timestamp': 1449187937,
            'view_count': int,
            'like_count': int,
            'comment_count': int,
        },
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        media_info = self._download_json('http://m.trilulilu.ro/%s?format=json' % display_id, display_id)

        age_limit = 0
        errors = media_info.get('errors', {})
        if errors.get('friends'):
            raise ExtractorError('This video is private.', expected=True)
        elif errors.get('geoblock'):
            raise ExtractorError('This video is not available in your country.', expected=True)
        elif errors.get('xxx_unlogged'):
            age_limit = 18

        media_class = media_info.get('class')
        if media_class not in ('video', 'audio'):
            raise ExtractorError('not a video or an audio')

        user = media_info.get('user', {})

        thumbnail = media_info.get('cover_url')
        if thumbnail:
            thumbnail.format(width='1600', height='1200')

        # TODO: get correct ext for audio files
        stream_type = media_info.get('stream_type')
        formats = [{
            'url': media_info['href'],
            'ext': stream_type,
        }]
        if media_info.get('is_hd'):
            formats.append({
                'format_id': 'hd',
                'url': media_info['hrefhd'],
                'ext': stream_type,
            })
        if media_class == 'audio':
            formats[0]['vcodec'] = 'none'
        else:
            formats[0]['format_id'] = 'sd'

        return {
            'id': media_info['identifier'].split('|')[1],
            'display_id': display_id,
            'formats': formats,
            'title': media_info['title'],
            'description': media_info.get('description'),
            'thumbnail': thumbnail,
            'uploader_id': user.get('username'),
            'uploader': user.get('fullname'),
            'timestamp': parse_iso8601(media_info.get('published'), ' '),
            'duration': int_or_none(media_info.get('duration')),
            'view_count': int_or_none(media_info.get('count_views')),
            'like_count': int_or_none(media_info.get('count_likes')),
            'comment_count': int_or_none(media_info.get('count_comments')),
            'age_limit': age_limit,
        }
