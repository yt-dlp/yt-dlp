from .common import InfoExtractor
from ..utils import (
    int_or_none,
    float_or_none,
    qualities,
    ExtractorError,
)


class GfycatIE(InfoExtractor):
    _VALID_URL = r'https?://(?:(?:www|giant|thumbs)\.)?gfycat\.com/(?i:ru/|ifr/|gifs/detail/)?(?P<id>[^-/?#\."\']+)'
    _EMBED_REGEX = [rf'<(?:iframe|source)[^>]+\bsrc=["\'](?P<url>{_VALID_URL})']
    _TESTS = [{
        'url': 'http://gfycat.com/DeadlyDecisiveGermanpinscher',
        'info_dict': {
            'id': 'DeadlyDecisiveGermanpinscher',
            'ext': 'mp4',
            'title': 'Ghost in the Shell',
            'timestamp': 1410656006,
            'upload_date': '20140914',
            'uploader': 'anonymous',
            'duration': 10.4,
            'view_count': int,
            'like_count': int,
            'categories': list,
            'age_limit': 0,
            'uploader_id': 'anonymous',
            'description': '',
        }
    }, {
        'url': 'http://gfycat.com/ifr/JauntyTimelyAmazontreeboa',
        'info_dict': {
            'id': 'JauntyTimelyAmazontreeboa',
            'ext': 'mp4',
            'title': 'JauntyTimelyAmazontreeboa',
            'timestamp': 1411720126,
            'upload_date': '20140926',
            'uploader': 'anonymous',
            'duration': 3.52,
            'view_count': int,
            'like_count': int,
            'categories': list,
            'age_limit': 0,
            'uploader_id': 'anonymous',
            'description': '',
        }
    }, {
        'url': 'https://gfycat.com/alienatedsolidgreathornedowl',
        'info_dict': {
            'id': 'alienatedsolidgreathornedowl',
            'ext': 'mp4',
            'upload_date': '20211226',
            'uploader_id': 'reactions',
            'timestamp': 1640536930,
            'like_count': int,
            'description': '',
            'title': 'Ingrid Michaelson, Zooey Deschanel - Merry Christmas Happy New Year',
            'categories': list,
            'age_limit': 0,
            'duration': 2.9583333333333335,
            'uploader': 'Reaction GIFs',
            'view_count': int,
        }
    }, {
        'url': 'https://gfycat.com/ru/RemarkableDrearyAmurstarfish',
        'only_matching': True
    }, {
        'url': 'https://gfycat.com/gifs/detail/UnconsciousLankyIvorygull',
        'only_matching': True
    }, {
        'url': 'https://gfycat.com/acceptablehappygoluckyharborporpoise-baseball',
        'only_matching': True
    }, {
        'url': 'https://thumbs.gfycat.com/acceptablehappygoluckyharborporpoise-size_restricted.gif',
        'only_matching': True
    }, {
        'url': 'https://giant.gfycat.com/acceptablehappygoluckyharborporpoise.mp4',
        'only_matching': True
    }, {
        'url': 'http://gfycat.com/IFR/JauntyTimelyAmazontreeboa',
        'only_matching': True
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        gfy = self._download_json(
            'https://api.gfycat.com/v1/gfycats/%s' % video_id,
            video_id, 'Downloading video info')
        if 'error' in gfy:
            raise ExtractorError('Gfycat said: ' + gfy['error'], expected=True)
        gfy = gfy['gfyItem']

        title = gfy.get('title') or gfy['gfyName']
        description = gfy.get('description')
        timestamp = int_or_none(gfy.get('createDate'))
        uploader = gfy.get('userName') or gfy.get('username')
        view_count = int_or_none(gfy.get('views'))
        like_count = int_or_none(gfy.get('likes'))
        dislike_count = int_or_none(gfy.get('dislikes'))
        age_limit = 18 if gfy.get('nsfw') == '1' else 0

        width = int_or_none(gfy.get('width'))
        height = int_or_none(gfy.get('height'))
        fps = int_or_none(gfy.get('frameRate'))
        num_frames = int_or_none(gfy.get('numFrames'))

        duration = float_or_none(num_frames, fps) if num_frames and fps else None

        categories = gfy.get('tags') or gfy.get('extraLemmas') or []

        FORMATS = ('gif', 'webm', 'mp4')
        quality = qualities(FORMATS)

        formats = []
        for format_id in FORMATS:
            video_url = gfy.get('%sUrl' % format_id)
            if not video_url:
                continue
            filesize = int_or_none(gfy.get('%sSize' % format_id))
            formats.append({
                'url': video_url,
                'format_id': format_id,
                'width': width,
                'height': height,
                'fps': fps,
                'filesize': filesize,
                'quality': quality(format_id),
            })

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'timestamp': timestamp,
            'uploader': gfy.get('userDisplayName') or uploader,
            'uploader_id': uploader,
            'duration': duration,
            'view_count': view_count,
            'like_count': like_count,
            'dislike_count': dislike_count,
            'categories': categories,
            'age_limit': age_limit,
            'formats': formats,
        }
