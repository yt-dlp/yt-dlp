from .common import InfoExtractor
from ..utils import (
    determine_ext,
    float_or_none,
    int_or_none,
    parse_age_limit,
    qualities,
    random_birthday,
    unified_timestamp,
    urljoin,
)


class VideoPressIE(InfoExtractor):
    _ID_REGEX = r'[\da-zA-Z]{8}'
    _PATH_REGEX = r'video(?:\.word)?press\.com/embed/'
    _VALID_URL = r'https?://%s(?P<id>%s)' % (_PATH_REGEX, _ID_REGEX)
    _EMBED_REGEX = [rf'<iframe[^>]+src=["\'](?P<url>(?:https?://)?{_PATH_REGEX}{_ID_REGEX})']
    _TESTS = [{
        'url': 'https://videopress.com/embed/kUJmAcSf',
        'md5': '706956a6c875873d51010921310e4bc6',
        'info_dict': {
            'id': 'kUJmAcSf',
            'ext': 'mp4',
            'title': 'VideoPress Demo',
            'thumbnail': r're:^https?://.*\.jpg',
            'duration': 634.6,
            'timestamp': 1434983935,
            'upload_date': '20150622',
            'age_limit': 0,
        },
    }, {
        # 17+, requires birth_* params
        'url': 'https://videopress.com/embed/iH3gstfZ',
        'only_matching': True,
    }, {
        'url': 'https://video.wordpress.com/embed/kUJmAcSf',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        query = random_birthday('birth_year', 'birth_month', 'birth_day')
        query['fields'] = 'description,duration,file_url_base,files,height,original,poster,rating,title,upload_date,width'
        video = self._download_json(
            'https://public-api.wordpress.com/rest/v1.1/videos/%s' % video_id,
            video_id, query=query)

        title = video['title']

        file_url_base = video.get('file_url_base') or {}
        base_url = file_url_base.get('https') or file_url_base.get('http')

        QUALITIES = ('std', 'dvd', 'hd')
        quality = qualities(QUALITIES)

        formats = []
        for format_id, f in (video.get('files') or {}).items():
            if not isinstance(f, dict):
                continue
            for ext, path in f.items():
                if ext in ('mp4', 'ogg'):
                    formats.append({
                        'url': urljoin(base_url, path),
                        'format_id': '%s-%s' % (format_id, ext),
                        'ext': determine_ext(path, ext),
                        'quality': quality(format_id),
                    })
        original_url = video.get('original')
        if original_url:
            formats.append({
                'url': original_url,
                'format_id': 'original',
                'quality': len(QUALITIES),
                'width': int_or_none(video.get('width')),
                'height': int_or_none(video.get('height')),
            })
        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': title,
            'description': video.get('description'),
            'thumbnail': video.get('poster'),
            'duration': float_or_none(video.get('duration'), 1000),
            'timestamp': unified_timestamp(video.get('upload_date')),
            'age_limit': parse_age_limit(video.get('rating')),
            'formats': formats,
        }
