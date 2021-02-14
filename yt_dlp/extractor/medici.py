# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import (
    unified_strdate,
    update_url_query,
    urlencode_postdata,
)


class MediciIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?medici\.tv/#!/(?P<id>[^?#&]+)'
    _TEST = {
        'url': 'http://www.medici.tv/#!/daniel-harding-frans-helmerson-verbier-festival-music-camp',
        'md5': '004c21bb0a57248085b6ff3fec72719d',
        'info_dict': {
            'id': '3059',
            'ext': 'flv',
            'title': 'Daniel Harding conducts the Verbier Festival Music Camp \u2013 With Frans Helmerson',
            'description': 'md5:322a1e952bafb725174fd8c1a8212f58',
            'thumbnail': r're:^https?://.*\.jpg$',
            'upload_date': '20170408',
        },
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)

        # Sets csrftoken cookie
        self._download_webpage(url, video_id)

        MEDICI_URL = 'http://www.medici.tv/'

        data = self._download_json(
            MEDICI_URL, video_id,
            data=urlencode_postdata({
                'json': 'true',
                'page': '/%s' % video_id,
                'timezone_offset': -420,
            }), headers={
                'X-CSRFToken': self._get_cookies(url)['csrftoken'].value,
                'X-Requested-With': 'XMLHttpRequest',
                'Referer': MEDICI_URL,
                'Content-Type': 'application/x-www-form-urlencoded',
            })

        video = data['video']['videos']['video1']

        title = video.get('nom') or data['title']

        video_id = video.get('id') or video_id
        formats = self._extract_f4m_formats(
            update_url_query(video['url_akamai'], {
                'hdcore': '3.1.0',
                'plugin=aasp': '3.1.0.43.124',
            }), video_id, f4m_id='hds')

        description = data.get('meta_description')
        thumbnail = video.get('url_thumbnail') or data.get('main_image')
        upload_date = unified_strdate(data['video'].get('date'))

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'upload_date': upload_date,
            'formats': formats,
        }
