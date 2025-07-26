from .common import InfoExtractor
from ..utils import (
    int_or_none,
    parse_age_limit,
    parse_iso8601,
    time_seconds,
    update_url_query,
)


class IndavideoEmbedIE(InfoExtractor):
    _VALID_URL = r'https?://(?:(?:embed\.)?indavideo\.hu/player/video/|assets\.indavideo\.hu/swf/player\.swf\?.*\b(?:v(?:ID|id))=)(?P<id>[\da-f]+)'
    # Some example URLs covered by generic extractor:
    #   https://index.indavideo.hu/video/Hod_Nemetorszagban
    #   https://auto.indavideo.hu/video/Sajat_utanfutoban_a_kis_tacsko
    #   https://film.indavideo.hu/video/f_farkaslesen
    #   https://palyazat.indavideo.hu/video/Embertelen_dal_Dodgem_egyuttes
    _EMBED_REGEX = [r'<iframe[^>]+\bsrc=["\'](?P<url>(?:https?:)//embed\.indavideo\.hu/player/video/[\da-f]+)']
    _TESTS = [{
        'url': 'https://indavideo.hu/player/video/1bdc3c6d80/',
        'md5': 'c8a507a1c7410685f83a06eaeeaafeab',
        'info_dict': {
            'id': '1837039',
            'ext': 'mp4',
            'title': 'Cicatánc',
            'description': '',
            'uploader': 'cukiajanlo',
            'uploader_id': '83729',
            'thumbnail': r're:https?://pics\.indavideo\.hu/videos/.+\.jpg',
            'timestamp': 1439193826,
            'upload_date': '20150810',
            'duration': 72,
            'age_limit': 0,
            'tags': 'count:5',
        },
    }, {
        'url': 'https://embed.indavideo.hu/player/video/1bdc3c6d80?autostart=1&hide=1',
        'only_matching': True,
    }]
    _WEBPAGE_TESTS = [{
        'url': 'https://indavideo.hu/video/Vicces_cica_1',
        'info_dict': {
            'id': '1335611',
            'ext': 'mp4',
            'title': 'Vicces cica',
            'description': 'Játszik a tablettel. :D',
            'thumbnail': r're:https?://pics\.indavideo\.hu/videos/.+\.jpg',
            'uploader': 'Jet_Pack',
            'uploader_id': '491217',
            'timestamp': 1390821212,
            'upload_date': '20140127',
            'duration': 7,
            'age_limit': 0,
            'tags': 'count:2',
        },
    }, {
        'url': 'https://palyazat.indavideo.hu/video/RUSH_1',
        'info_dict': {
            'id': '3808180',
            'ext': 'mp4',
            'title': 'RUSH',
            'age_limit': 0,
            'description': '',
            'duration': 650,
            'tags': 'count:2',
            'thumbnail': r're:https?://pics\.indavideo\.hu/videos/.+\.jpg',
            'timestamp': 1729136266,
            'upload_date': '20241017',
            'uploader': '7summerfilms',
            'uploader_id': '1628496',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        video = self._download_json(
            f'https://amfphp.indavideo.hu/SYm0json.php/player.playerHandler.getVideoData/{video_id}/',
            video_id, query={'_': time_seconds()})['data']

        video_urls = []

        video_files = video.get('video_files')
        if isinstance(video_files, list):
            video_urls.extend(video_files)
        elif isinstance(video_files, dict):
            video_urls.extend(video_files.values())

        video_urls = list(set(video_urls))

        filesh = video.get('filesh') or {}

        formats = []
        for video_url in video_urls:
            height = int_or_none(self._search_regex(
                r'\.(\d{3,4})\.mp4(?:\?|$)', video_url, 'height', default=None))
            if not height and len(filesh) == 1:
                height = int_or_none(next(iter(filesh.keys())))
            token = filesh.get(str(height))
            if token is None:
                continue
            formats.append({
                'url': update_url_query(video_url, {'token': token}),
                'height': height,
            })

        timestamp = video.get('date')
        if timestamp:
            # upload date is in CEST
            timestamp = parse_iso8601(timestamp + ' +0200', ' ')

        thumbnails = [{
            'url': self._proto_relative_url(thumbnail),
        } for thumbnail in video.get('thumbnails', [])]

        tags = [tag['title'] for tag in video.get('tags') or []]

        return {
            'id': video.get('id') or video_id,
            'title': video.get('title'),
            'description': video.get('description'),
            'thumbnails': thumbnails,
            'uploader': video.get('user_name'),
            'uploader_id': video.get('user_id'),
            'timestamp': timestamp,
            'duration': int_or_none(video.get('length')),
            'age_limit': parse_age_limit(video.get('age_limit')),
            'tags': tags,
            'formats': formats,
        }
