# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..compat import compat_str
from ..utils import (
    int_or_none,
    parse_age_limit,
    parse_iso8601,
    update_url_query,
)


class IndavideoEmbedIE(InfoExtractor):
    _VALID_URL = r'https?://(?:(?:embed\.)?indavideo\.hu/player/video/|assets\.indavideo\.hu/swf/player\.swf\?.*\b(?:v(?:ID|id))=)(?P<id>[\da-f]+)'
    _TESTS = [{
        'url': 'http://indavideo.hu/player/video/1bdc3c6d80/',
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
        'url': 'http://embed.indavideo.hu/player/video/1bdc3c6d80?autostart=1&hide=1',
        'only_matching': True,
    }, {
        'url': 'http://assets.indavideo.hu/swf/player.swf?v=fe25e500&vID=1bdc3c6d80&autostart=1&hide=1&i=1',
        'only_matching': True,
    }]

    # Some example URLs covered by generic extractor:
    #   http://indavideo.hu/video/Vicces_cica_1
    #   http://index.indavideo.hu/video/2015_0728_beregszasz
    #   http://auto.indavideo.hu/video/Sajat_utanfutoban_a_kis_tacsko
    #   http://erotika.indavideo.hu/video/Amator_tini_punci
    #   http://film.indavideo.hu/video/f_hrom_nagymamm_volt
    #   http://palyazat.indavideo.hu/video/Embertelen_dal_Dodgem_egyuttes

    @staticmethod
    def _extract_urls(webpage):
        return re.findall(
            r'<iframe[^>]+\bsrc=["\'](?P<url>(?:https?:)?//embed\.indavideo\.hu/player/video/[\da-f]+)',
            webpage)

    def _real_extract(self, url):
        video_id = self._match_id(url)

        video = self._download_json(
            'https://amfphp.indavideo.hu/SYm0json.php/player.playerHandler.getVideoData/%s' % video_id,
            video_id)['data']

        title = video['title']

        video_urls = []

        video_files = video.get('video_files')
        if isinstance(video_files, list):
            video_urls.extend(video_files)
        elif isinstance(video_files, dict):
            video_urls.extend(video_files.values())

        video_file = video.get('video_file')
        if video:
            video_urls.append(video_file)
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
            if filesh:
                if not height:
                    continue
                token = filesh.get(compat_str(height))
                if token is None:
                    continue
                video_url = update_url_query(video_url, {'token': token})
            formats.append({
                'url': video_url,
                'height': height,
            })
        self._sort_formats(formats)

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
            'title': title,
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
