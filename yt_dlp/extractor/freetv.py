from .common import InfoExtractor
from ..utils import (
    urlencode_postdata,
    determine_ext,
)


class FreeTvIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?freetv\.com/(?:peliculas|series)/(?:[^/]+/)*(?P<id>[^/]+)'
    _TESTS = [{
        'url': 'https://www.freetv.com/peliculas/atrapame-si-puedes/',
        'md5': 'dc62d5abf0514726640077cd1591aa92',
        'info_dict': {
            'id': '428021',
            'title': 'Atrápame Si Puedes',
            'full_title': 'Atrápame Si Puedes',
            'description': 'md5:ca63bc00898aeb2f64ec87c6d3a5b982',
            'ext': 'mp4',
        }
    }, {
        'url': 'https://www.freetv.com/peliculas/monstruoso/',
        'md5': '509c15c68de41cb708d1f92d071f20aa',
        'info_dict': {
            'id': '377652',
            'title': 'Monstruoso',
            'full_title': 'Monstruoso',
            'description': 'md5:333fc19ee327b457b980e54a911ea4a3',
            'ext': 'mp4',
        }
    }]

    def _extract_video(self, contentId, action="olyott_video_play"):
        request_body = {
            'action': action,
            'contentID': contentId,
        }

        response = self._download_json(
            'https://www.freetv.com/wordpress/wp-admin/admin-ajax.php',
            contentId,
            'Downloading %s video JSON' % contentId,
            data=urlencode_postdata(request_body),
            fatal=False
        )

        if response is False:
            return False

        if response.get('success') is False:
            return False

        response_data = response.get('data')

        if response_data is False:
            return False

        video_metadata = response_data.get('displayMeta')

        video_id = video_metadata.get('contentID')
        title = video_metadata.get('title')
        full_title = video_metadata.get('fullTitle')
        description = video_metadata.get('desc')
        video_url = video_metadata.get('streamURLVideo')

        formats = []
        subtitles = []

        ext = determine_ext(video_url)

        if ext == "m3u8":
            fmts, subs = self._extract_m3u8_formats_and_subtitles(
                video_url, video_id, 'mp4',
                entry_protocol='m3u8_native',
                fatal=False)
            formats.extend(fmts)
            self._merge_subtitles(subs, target=subtitles)
        else:
            if self._is_valid_url(video_url, video_id):
                formats.append({
                    'url': video_url,
                })

        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': title,
            'full_title': full_title,
            'description': description,
            'formats': formats,
            'subtitles': subtitles,
            'ext': 'mp4',
        }

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)

        content_id = self._search_regex(
            (r'class=.*?postid-(\d+)',
             r'<link.*?freetv.com\/\?p=(\d+)'),
            webpage, 'video id', default=None, group=None)

        # If it's a series page, we should extract all episodes
        # matching <div data-contentid="*" class="episodeListEpisode">

        return self._extract_video(content_id)
