from .youtube import YoutubeIE
from .zdf import ZDFBaseIE
from ..utils import (
    int_or_none,
    merge_dicts,
    try_get,
    unified_timestamp,
)


class PhoenixIE(ZDFBaseIE):
    IE_NAME = 'phoenix.de'
    _VALID_URL = r'https?://(?:www\.)?phoenix\.de/(?:[^/?#]+/)*[^/?#&]*-a-(?P<id>\d+)\.html'
    _TESTS = [{
        'url': 'https://www.phoenix.de/sendungen/dokumentationen/spitzbergen-a-893349.html',
        'md5': 'a79e86d9774d0b3f2102aff988a0bd32',
        'info_dict': {
            'id': '221215_phx_spitzbergen',
            'ext': 'mp4',
            'title': 'Spitzbergen',
            'description': 'Film von Tilmann Bünz',
            'duration': 728.0,
            'timestamp': 1555600500,
            'upload_date': '20190418',
            'uploader': 'Phoenix',
            'thumbnail': 'https://www.phoenix.de/sixcms/media.php/21/Bergspitzen1.png',
            'series': 'Dokumentationen',
            'episode': 'Spitzbergen',
        },
    }, {
        'url': 'https://www.phoenix.de/entwicklungen-in-russland-a-2044720.html',
        'only_matching': True,
    }, {
        # no media
        'url': 'https://www.phoenix.de/sendungen/dokumentationen/mit-dem-jumbo-durch-die-nacht-a-89625.html',
        'only_matching': True,
    }, {
        # Same as https://www.zdf.de/politik/phoenix-sendungen/die-gesten-der-maechtigen-100.html
        'url': 'https://www.phoenix.de/sendungen/dokumentationen/gesten-der-maechtigen-i-a-89468.html?ref=suche',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        article_id = self._match_id(url)

        article = self._download_json(
            f'https://www.phoenix.de/response/id/{article_id}', article_id,
            'Downloading article JSON')

        video = article['absaetze'][0]
        title = video.get('titel') or article.get('subtitel')

        if video.get('typ') == 'video-youtube':
            video_id = video['id']
            return self.url_result(
                video_id, ie=YoutubeIE.ie_key(), video_id=video_id,
                video_title=title)

        video_id = str(video.get('basename') or video.get('content'))

        details = self._download_json(
            'https://www.phoenix.de/php/mediaplayer/data/beitrags_details.php',
            video_id, 'Downloading details JSON', query={
                'ak': 'web',
                'ptmd': 'true',
                'id': video_id,
                'profile': 'player2',
            })

        title = title or details['title']
        content_id = details['tracking']['nielsen']['content']['assetid']

        info = self._extract_ptmd(
            f'https://tmd.phoenix.de/tmd/2/android_native_6/vod/ptmd/phoenix/{content_id}',
            content_id)

        duration = int_or_none(try_get(
            details, lambda x: x['tracking']['nielsen']['content']['length']))
        timestamp = unified_timestamp(details.get('editorialDate'))
        series = try_get(
            details, lambda x: x['tracking']['nielsen']['content']['program'],
            str)
        episode = title if details.get('contentType') == 'episode' else None

        teaser_images = try_get(details, lambda x: x['teaserImageRef']['layouts'], dict) or {}
        thumbnails = self._extract_thumbnails(teaser_images)

        return merge_dicts(info, {
            'id': content_id,
            'title': title,
            'description': details.get('leadParagraph'),
            'duration': duration,
            'thumbnails': thumbnails,
            'timestamp': timestamp,
            'uploader': details.get('tvService'),
            'series': series,
            'episode': episode,
        })
