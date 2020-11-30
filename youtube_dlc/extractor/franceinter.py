# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import month_by_name


class FranceInterIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?franceinter\.fr/emissions/(?P<id>[^?#]+)'

    _TEST = {
        'url': 'https://www.franceinter.fr/emissions/affaires-sensibles/affaires-sensibles-07-septembre-2016',
        'md5': '9e54d7bdb6fdc02a841007f8a975c094',
        'info_dict': {
            'id': 'affaires-sensibles/affaires-sensibles-07-septembre-2016',
            'ext': 'mp3',
            'title': 'Affaire Cahuzac : le contentieux du compte en Suisse',
            'description': 'md5:401969c5d318c061f86bda1fa359292b',
            'thumbnail': r're:^https?://.*\.jpg',
            'upload_date': '20160907',
        },
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(url, video_id)

        video_url = self._search_regex(
            r'(?s)<div[^>]+class=["\']page-diffusion["\'][^>]*>.*?<button[^>]+data-url=(["\'])(?P<url>(?:(?!\1).)+)\1',
            webpage, 'video url', group='url')

        title = self._og_search_title(webpage)
        description = self._og_search_description(webpage)
        thumbnail = self._html_search_meta(['og:image', 'twitter:image'], webpage)

        upload_date_str = self._search_regex(
            r'class=["\']\s*cover-emission-period\s*["\'][^>]*>[^<]+\s+(\d{1,2}\s+[^\s]+\s+\d{4})<',
            webpage, 'upload date', fatal=False)
        if upload_date_str:
            upload_date_list = upload_date_str.split()
            upload_date_list.reverse()
            upload_date_list[1] = '%02d' % (month_by_name(upload_date_list[1], lang='fr') or 0)
            upload_date_list[2] = '%02d' % int(upload_date_list[2])
            upload_date = ''.join(upload_date_list)
        else:
            upload_date = None

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'upload_date': upload_date,
            'formats': [{
                'url': video_url,
                'vcodec': 'none',
            }],
        }
