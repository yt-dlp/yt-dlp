from .common import InfoExtractor
from .dailymotion import DailymotionIE


class KickerIE(InfoExtractor):
    _VALID_URL = r'https://www.kicker.de/(?P<video_slug>[\w-]+)/video'
    _TEST = {
        'url': 'https://www.kicker.de/pogba-dembel-co-die-top-11-der-abloesefreien-spieler-905049/video',
        'info_dict': {
            'id': 'km04mrK0DrRAVxy2GcA',
            'title': 'Pogba, Dembelé & Co.: Die Top 11 der ablösefreien Spieler | kicker.tv Hintergrund | Video - kicker',
            'ext': 'mp4',
            'duration': 350,
            'description': 'md5:a5a3dd77dbb6550dbfb997be100b9998',
            'uploader_id': 'x2dfupo',
            'timestamp': 1654677626,
            'like_count': int,
            'uploader': 'kicker.de',
            'view_count': int,
            'ie': 'Dailymotion',
            'age_limit': 0,
            'thumbnail': r're:https://s\d+.dmcdn.net/v/T-x741YeYAx8aSZ0Z/x1080',
            'tags': ['published', 'category.InternationalSoccer'],
            'upload_date': '20220608'
        }
    }

    def _real_extract(self, url):
        video_slug = self._match_valid_url(url).group('video_slug')

        webpage = self._download_webpage(url, video_slug)
        dailymotion_video_id = self._search_regex(
            r'data-dmprivateid=\"(?P<video_id>\w+)\"', webpage,
            'video_id', group='video_id')

        return {
            '_type': 'url_transparent',
            'ie': DailymotionIE.ie_key(),
            'url': f'https://www.dailymotion.com/video/{dailymotion_video_id}',
            'title': self._html_extract_title(webpage),
        }
