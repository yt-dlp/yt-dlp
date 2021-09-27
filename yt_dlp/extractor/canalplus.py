# coding: utf-8
from __future__ import unicode_literals


from .common import InfoExtractor
from ..utils import (
    # ExtractorError,
    # HEADRequest,
    int_or_none,
    qualities,
    unified_strdate,
)


class CanalplusIE(InfoExtractor):
    IE_DESC = 'mycanal.fr and piwiplus.fr'
    _VALID_URL = r'https?://(?:www\.)?(?P<site>mycanal|piwiplus)\.fr/(?:[^/]+/)*(?P<display_id>[^?/]+)(?:\.html\?.*\bvid=|/p/)(?P<id>\d+)'
    _VIDEO_INFO_TEMPLATE = 'http://service.canal-plus.com/video/rest/getVideosLiees/%s/%s?format=json'
    _SITE_ID_MAP = {
        'mycanal': 'cplus',
        'piwiplus': 'teletoon',
    }

    # Only works for direct mp4 URLs
    _GEO_COUNTRIES = ['FR']

    _TESTS = [{
        'url': 'https://www.mycanal.fr/d17-emissions/lolywood/p/1397061',
        'info_dict': {
            'id': '1397061',
            'display_id': 'lolywood',
            'ext': 'mp4',
            'title': 'Euro 2016 : Je préfère te prévenir - Lolywood - Episode 34',
            'description': 'md5:7d97039d455cb29cdba0d652a0efaa5e',
            'upload_date': '20160602',
        },
    }, {
        # geo restricted, bypassed
        'url': 'http://www.piwiplus.fr/videos-piwi/pid1405-le-labyrinthe-boing-super-ranger.html?vid=1108190',
        'info_dict': {
            'id': '1108190',
            'display_id': 'pid1405-le-labyrinthe-boing-super-ranger',
            'ext': 'mp4',
            'title': 'BOING SUPER RANGER - Ep : Le labyrinthe',
            'description': 'md5:4cea7a37153be42c1ba2c1d3064376ff',
            'upload_date': '20140724',
        },
        'expected_warnings': ['HTTP Error 403: Forbidden'],
    }]

    def _real_extract(self, url):
        site, display_id, video_id = self._match_valid_url(url).groups()

        site_id = self._SITE_ID_MAP[site]

        info_url = self._VIDEO_INFO_TEMPLATE % (site_id, video_id)
        video_data = self._download_json(info_url, video_id, 'Downloading video JSON')

        if isinstance(video_data, list):
            video_data = [video for video in video_data if video.get('ID') == video_id][0]
        media = video_data['MEDIA']
        infos = video_data['INFOS']

        preference = qualities(['MOBILE', 'BAS_DEBIT', 'HAUT_DEBIT', 'HD'])

        # _, fmt_url = next(iter(media['VIDEOS'].items()))
        # if '/geo' in fmt_url.lower():
        #     response = self._request_webpage(
        #         HEADRequest(fmt_url), video_id,
        #         'Checking if the video is georestricted')
        #     if '/blocage' in response.geturl():
        #         raise ExtractorError(
        #             'The video is not available in your country',
        #             expected=True)

        formats = []
        for format_id, format_url in media['VIDEOS'].items():
            if not format_url:
                continue
            if format_id == 'HLS':
                formats.extend(self._extract_m3u8_formats(
                    format_url, video_id, 'mp4', 'm3u8_native', m3u8_id=format_id, fatal=False))
            elif format_id == 'HDS':
                formats.extend(self._extract_f4m_formats(
                    format_url + '?hdcore=2.11.3', video_id, f4m_id=format_id, fatal=False))
            else:
                formats.append({
                    # the secret extracted from ya function in http://player.canalplus.fr/common/js/canalPlayer.js
                    'url': format_url + '?secret=pqzerjlsmdkjfoiuerhsdlfknaes',
                    'format_id': format_id,
                    'quality': preference(format_id),
                })
        self._sort_formats(formats)

        thumbnails = [{
            'id': image_id,
            'url': image_url,
        } for image_id, image_url in media.get('images', {}).items()]

        titrage = infos['TITRAGE']

        return {
            'id': video_id,
            'display_id': display_id,
            'title': '%s - %s' % (titrage['TITRE'],
                                  titrage['SOUS_TITRE']),
            'upload_date': unified_strdate(infos.get('PUBLICATION', {}).get('DATE')),
            'thumbnails': thumbnails,
            'description': infos.get('DESCRIPTION'),
            'duration': int_or_none(infos.get('DURATION')),
            'view_count': int_or_none(infos.get('NB_VUES')),
            'like_count': int_or_none(infos.get('NB_LIKES')),
            'comment_count': int_or_none(infos.get('NB_COMMENTS')),
            'formats': formats,
        }
