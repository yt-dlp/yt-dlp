from .common import InfoExtractor
from ..utils import (
    int_or_none,
    unified_strdate,
    unescapeHTML,
)


class UstudioIE(InfoExtractor):
    IE_NAME = 'ustudio'
    _VALID_URL = r'https?://(?:(?:www|v1)\.)?ustudio\.com/video/(?P<id>[^/]+)/(?P<display_id>[^/?#&]+)'
    _TEST = {
        'url': 'http://ustudio.com/video/Uxu2my9bgSph/san_francisco_golden_gate_bridge',
        'md5': '58bbfca62125378742df01fc2abbdef6',
        'info_dict': {
            'id': 'Uxu2my9bgSph',
            'display_id': 'san_francisco_golden_gate_bridge',
            'ext': 'mp4',
            'title': 'San Francisco: Golden Gate Bridge',
            'description': 'md5:23925500697f2c6d4830e387ba51a9be',
            'thumbnail': r're:^https?://.*\.jpg$',
            'upload_date': '20111107',
            'uploader': 'Tony Farley',
        }
    }

    def _real_extract(self, url):
        video_id, display_id = self._match_valid_url(url).groups()

        config = self._download_xml(
            'http://v1.ustudio.com/embed/%s/ustudio/config.xml' % video_id,
            display_id)

        def extract(kind):
            return [{
                'url': unescapeHTML(item.attrib['url']),
                'width': int_or_none(item.get('width')),
                'height': int_or_none(item.get('height')),
            } for item in config.findall('./qualities/quality/%s' % kind) if item.get('url')]

        formats = extract('video')
        self._sort_formats(formats)

        webpage = self._download_webpage(url, display_id)

        title = self._og_search_title(webpage)
        upload_date = unified_strdate(self._search_regex(
            r'(?s)Uploaded by\s*.+?\s*on\s*<span>([^<]+)</span>',
            webpage, 'upload date', fatal=False))
        uploader = self._search_regex(
            r'Uploaded by\s*<a[^>]*>([^<]+)<',
            webpage, 'uploader', fatal=False)

        return {
            'id': video_id,
            'display_id': display_id,
            'title': title,
            'description': self._og_search_description(webpage),
            'thumbnails': extract('image'),
            'upload_date': upload_date,
            'uploader': uploader,
            'formats': formats,
        }


class UstudioEmbedIE(InfoExtractor):
    IE_NAME = 'ustudio:embed'
    _VALID_URL = r'https?://(?:(?:app|embed)\.)?ustudio\.com/embed/(?P<uid>[^/]+)/(?P<id>[^/]+)'
    _TEST = {
        'url': 'http://app.ustudio.com/embed/DeN7VdYRDKhP/Uw7G1kMCe65T',
        'md5': '47c0be52a09b23a7f40de9469cec58f4',
        'info_dict': {
            'id': 'Uw7G1kMCe65T',
            'ext': 'mp4',
            'title': '5 Things IT Should Know About Video',
            'description': 'md5:93d32650884b500115e158c5677d25ad',
            'uploader_id': 'DeN7VdYRDKhP',
        }
    }

    def _real_extract(self, url):
        uploader_id, video_id = self._match_valid_url(url).groups()
        video_data = self._download_json(
            'http://app.ustudio.com/embed/%s/%s/config.json' % (uploader_id, video_id),
            video_id)['videos'][0]
        title = video_data['name']

        formats = []
        for ext, qualities in video_data.get('transcodes', {}).items():
            for quality in qualities:
                quality_url = quality.get('url')
                if not quality_url:
                    continue
                height = int_or_none(quality.get('height'))
                formats.append({
                    'format_id': '%s-%dp' % (ext, height) if height else ext,
                    'url': quality_url,
                    'width': int_or_none(quality.get('width')),
                    'height': height,
                })
        self._sort_formats(formats)

        thumbnails = []
        for image in video_data.get('images', []):
            image_url = image.get('url')
            if not image_url:
                continue
            thumbnails.append({
                'url': image_url,
            })

        return {
            'id': video_id,
            'title': title,
            'description': video_data.get('description'),
            'duration': int_or_none(video_data.get('duration')),
            'uploader_id': uploader_id,
            'tags': video_data.get('keywords'),
            'thumbnails': thumbnails,
            'formats': formats,
        }
