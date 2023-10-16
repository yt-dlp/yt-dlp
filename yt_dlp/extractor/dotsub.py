from .common import InfoExtractor
from ..utils import (
    float_or_none,
    int_or_none,
)


class DotsubIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?dotsub\.com/view/(?P<id>[^/]+)'
    _TESTS = [{
        'url': 'https://dotsub.com/view/9c63db2a-fa95-4838-8e6e-13deafe47f09',
        'md5': '21c7ff600f545358134fea762a6d42b6',
        'info_dict': {
            'id': '9c63db2a-fa95-4838-8e6e-13deafe47f09',
            'ext': 'flv',
            'title': 'MOTIVATION - "It\'s Possible" Best Inspirational Video Ever',
            'description': 'md5:41af1e273edbbdfe4e216a78b9d34ac6',
            'thumbnail': 're:^https?://dotsub.com/media/9c63db2a-fa95-4838-8e6e-13deafe47f09/p',
            'duration': 198,
            'uploader': 'liuxt',
            'timestamp': 1385778501.104,
            'upload_date': '20131130',
            'view_count': int,
        }
    }, {
        'url': 'https://dotsub.com/view/747bcf58-bd59-45b7-8c8c-ac312d084ee6',
        'md5': '2bb4a83896434d5c26be868c609429a3',
        'info_dict': {
            'id': '168006778',
            'ext': 'mp4',
            'title': 'Apartments and flats in Raipur the white symphony',
            'description': 'md5:784d0639e6b7d1bc29530878508e38fe',
            'thumbnail': 're:^https?://dotsub.com/media/747bcf58-bd59-45b7-8c8c-ac312d084ee6/p',
            'duration': 290,
            'timestamp': 1476767794.2809999,
            'upload_date': '20161018',
            'uploader': 'parthivi001',
            'uploader_id': 'user52596202',
            'view_count': int,
        },
        'add_ie': ['Vimeo'],
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        info = self._download_json(
            'https://dotsub.com/api/media/%s/metadata' % video_id, video_id)
        video_url = info.get('mediaURI')

        if not video_url:
            webpage = self._download_webpage(url, video_id)
            video_url = self._search_regex(
                [r'<source[^>]+src="([^"]+)"', r'"file"\s*:\s*\'([^\']+)'],
                webpage, 'video url', default=None)
            info_dict = {
                'id': video_id,
                'url': video_url,
                'ext': 'flv',
            }

        if not video_url:
            setup_data = self._parse_json(self._html_search_regex(
                r'(?s)data-setup=([\'"])(?P<content>(?!\1).+?)\1',
                webpage, 'setup data', group='content'), video_id)
            info_dict = {
                '_type': 'url_transparent',
                'url': setup_data['src'],
            }

        info_dict.update({
            'title': info['title'],
            'description': info.get('description'),
            'thumbnail': info.get('screenshotURI'),
            'duration': int_or_none(info.get('duration'), 1000),
            'uploader': info.get('user'),
            'timestamp': float_or_none(info.get('dateCreated'), 1000),
            'view_count': int_or_none(info.get('numberOfViews')),
        })

        return info_dict
