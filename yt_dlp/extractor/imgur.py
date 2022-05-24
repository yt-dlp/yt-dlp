import re

from .common import InfoExtractor
from ..utils import (
    int_or_none,
    js_to_json,
    mimetype2ext,
    ExtractorError,
)


class ImgurIE(InfoExtractor):
    _VALID_URL = r'https?://(?:i\.)?imgur\.com/(?!(?:a|gallery|(?:t(?:opic)?|r)/[^/]+)/)(?P<id>[a-zA-Z0-9]+)'

    _TESTS = [{
        'url': 'https://i.imgur.com/A61SaA1.gifv',
        'info_dict': {
            'id': 'A61SaA1',
            'ext': 'mp4',
            'title': 're:Imgur GIF$|MRW gifv is up and running without any bugs$',
        },
    }, {
        'url': 'https://imgur.com/A61SaA1',
        'only_matching': True,
    }, {
        'url': 'https://i.imgur.com/crGpqCV.mp4',
        'only_matching': True,
    }, {
        # no title
        'url': 'https://i.imgur.com/jxBXAMC.gifv',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(
            'https://i.imgur.com/{id}.gifv'.format(id=video_id), video_id)

        width = int_or_none(self._og_search_property(
            'video:width', webpage, default=None))
        height = int_or_none(self._og_search_property(
            'video:height', webpage, default=None))

        video_elements = self._search_regex(
            r'(?s)<div class="video-elements">(.*?)</div>',
            webpage, 'video elements', default=None)
        if not video_elements:
            raise ExtractorError(
                'No sources found for video %s. Maybe an image?' % video_id,
                expected=True)

        formats = []
        for m in re.finditer(r'<source\s+src="(?P<src>[^"]+)"\s+type="(?P<type>[^"]+)"', video_elements):
            formats.append({
                'format_id': m.group('type').partition('/')[2],
                'url': self._proto_relative_url(m.group('src')),
                'ext': mimetype2ext(m.group('type')),
                'width': width,
                'height': height,
                'http_headers': {
                    'User-Agent': 'yt-dlp (like wget)',
                },
            })

        gif_json = self._search_regex(
            r'(?s)var\s+videoItem\s*=\s*(\{.*?\})',
            webpage, 'GIF code', fatal=False)
        if gif_json:
            gifd = self._parse_json(
                gif_json, video_id, transform_source=js_to_json)
            formats.append({
                'format_id': 'gif',
                'preference': -10,  # gifs are worse than videos
                'width': width,
                'height': height,
                'ext': 'gif',
                'acodec': 'none',
                'vcodec': 'gif',
                'container': 'gif',
                'url': self._proto_relative_url(gifd['gifUrl']),
                'filesize': gifd.get('size'),
                'http_headers': {
                    'User-Agent': 'yt-dlp (like wget)',
                },
            })

        self._sort_formats(formats)

        return {
            'id': video_id,
            'formats': formats,
            'title': self._og_search_title(webpage, default=video_id),
        }


class ImgurGalleryIE(InfoExtractor):
    IE_NAME = 'imgur:gallery'
    _VALID_URL = r'https?://(?:i\.)?imgur\.com/(?:gallery|(?:t(?:opic)?|r)/[^/]+)/(?P<id>[a-zA-Z0-9]+)'

    _TESTS = [{
        'url': 'http://imgur.com/gallery/Q95ko',
        'info_dict': {
            'id': 'Q95ko',
            'title': 'Adding faces make every GIF better',
        },
        'playlist_count': 25,
    }, {
        'url': 'http://imgur.com/topic/Aww/ll5Vk',
        'only_matching': True,
    }, {
        'url': 'https://imgur.com/gallery/YcAQlkx',
        'info_dict': {
            'id': 'YcAQlkx',
            'ext': 'mp4',
            'title': 'Classic Steve Carell gif...cracks me up everytime....damn the repost downvotes....',
        }
    }, {
        'url': 'http://imgur.com/topic/Funny/N8rOudd',
        'only_matching': True,
    }, {
        'url': 'http://imgur.com/r/aww/VQcQPhM',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        gallery_id = self._match_id(url)

        data = self._download_json(
            'https://imgur.com/gallery/%s.json' % gallery_id,
            gallery_id)['data']['image']

        if data.get('is_album'):
            entries = [
                self.url_result('http://imgur.com/%s' % image['hash'], ImgurIE.ie_key(), image['hash'])
                for image in data['album_images']['images'] if image.get('hash')]
            return self.playlist_result(entries, gallery_id, data.get('title'), data.get('description'))

        return self.url_result('http://imgur.com/%s' % gallery_id, ImgurIE.ie_key(), gallery_id)


class ImgurAlbumIE(ImgurGalleryIE):
    IE_NAME = 'imgur:album'
    _VALID_URL = r'https?://(?:i\.)?imgur\.com/a/(?P<id>[a-zA-Z0-9]+)'

    _TESTS = [{
        'url': 'http://imgur.com/a/j6Orj',
        'info_dict': {
            'id': 'j6Orj',
            'title': 'A Literary Analysis of "Star Wars: The Force Awakens"',
        },
        'playlist_count': 12,
    }]
