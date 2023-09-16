from .common import InfoExtractor
from ..compat import compat_str
from ..utils import (
    int_or_none,
    parse_age_limit,
    parse_iso8601,
    update_url_query,
    time_seconds,
)


class IndavideoEmbedIE(InfoExtractor):
    _VALID_URL = r'https?://(?:(?:embed\.)?indavideo\.hu/player/video/|assets\.indavideo\.hu/swf/player\.swf\?.*\b(?:v(?:ID|id))=)(?P<id>[\da-f]+)'
    # Some example URLs covered by generic extractor:
    #   https://indavideo.hu/video/Vicces_cica_1
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
            'thumbnail': r're:^https?://.*\.jpg$',
            'uploader': 'cukiajanlo',
            'uploader_id': '83729',
            'timestamp': 1439193826,
            'upload_date': '20150810',
            'duration': 72,
            'age_limit': 0,
            'tags': ['tánc', 'cica', 'cuki', 'cukiajanlo', 'newsroom'],
        },
    }, {
        'url': 'https://embed.indavideo.hu/player/video/1bdc3c6d80?autostart=1&hide=1',
        'only_matching': True,
    }, {
        'url': 'https://assets.indavideo.hu/swf/player.swf?v=fe25e500&vID=1bdc3c6d80&autostart=1&hide=1&i=1',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        video = self._download_json(
            'https://amfphp.indavideo.hu/SYm0json.php/player.playerHandler.getVideoData/%s/?_=%d' % (video_id, time_seconds()),
            video_id)['data']

        video_urls = []

        video_files = video.get('video_files')
        if isinstance(video_files, list):
            video_urls.extend(video_files)
        elif isinstance(video_files, dict):
            video_urls.extend(video_files.values())

        video_urls = list(set(video_urls))

        video_prefix = video_urls[0].rsplit('/', 1)[0]

        for flv_file in video.get('flv_files', []):
            flv_url = '%s/%s' % (video_prefix, flv_file)
            if flv_url not in video_urls:
                video_urls.append(flv_url)

        filesh = video.get('filesh')

        formats = []
        for video_url in video_urls:
            height = int_or_none(self._search_regex(
                r'\.(\d{3,4})\.mp4(?:\?|$)', video_url, 'height', default=None))
            if not height and len(filesh) == 1:
                height = int(list(filesh.keys())[0])
            token = filesh.get(compat_str(height))
            if token is None:
                continue
            video_url = update_url_query(video_url, {'token': token})
            formats.append({
                'url': video_url,
                'height': height,
            })

        timestamp = video.get('date')
        if timestamp:
            # upload date is in CEST
            timestamp = parse_iso8601(timestamp + ' +0200', ' ')

        thumbnails = [{
            'url': self._proto_relative_url(thumbnail)
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
