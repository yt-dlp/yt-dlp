# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import (
    float_or_none,
    int_or_none,
    parse_iso8601,
    try_get,
)


class NineCNineMediaIE(InfoExtractor):
    IE_NAME = '9c9media'
    _GEO_COUNTRIES = ['CA']
    _VALID_URL = r'9c9media:(?P<destination_code>[^:]+):(?P<id>\d+)'
    _API_BASE_TEMPLATE = 'http://capi.9c9media.com/destinations/%s/platforms/desktop/contents/%s/'

    def _real_extract(self, url):
        destination_code, content_id = self._match_valid_url(url).groups()
        api_base_url = self._API_BASE_TEMPLATE % (destination_code, content_id)
        content = self._download_json(api_base_url, content_id, query={
            '$include': '[Media.Name,Season,ContentPackages.Duration,ContentPackages.Id]',
        })
        title = content['Name']
        content_package = content['ContentPackages'][0]
        package_id = content_package['Id']
        content_package_url = api_base_url + 'contentpackages/%s/' % package_id
        content_package = self._download_json(
            content_package_url, content_id, query={
                '$include': '[HasClosedCaptions]',
            })

        if (not self.get_param('allow_unplayable_formats')
                and try_get(content_package, lambda x: x['Constraints']['Security']['Type'])):
            self.report_drm(content_id)

        manifest_base_url = content_package_url + 'manifest.'
        formats = []
        formats.extend(self._extract_m3u8_formats(
            manifest_base_url + 'm3u8', content_id, 'mp4',
            'm3u8_native', m3u8_id='hls', fatal=False))
        formats.extend(self._extract_f4m_formats(
            manifest_base_url + 'f4m', content_id,
            f4m_id='hds', fatal=False))
        formats.extend(self._extract_mpd_formats(
            manifest_base_url + 'mpd', content_id,
            mpd_id='dash', fatal=False))
        self._sort_formats(formats)

        thumbnails = []
        for image in (content.get('Images') or []):
            image_url = image.get('Url')
            if not image_url:
                continue
            thumbnails.append({
                'url': image_url,
                'width': int_or_none(image.get('Width')),
                'height': int_or_none(image.get('Height')),
            })

        tags, categories = [], []
        for source_name, container in (('Tags', tags), ('Genres', categories)):
            for e in content.get(source_name, []):
                e_name = e.get('Name')
                if not e_name:
                    continue
                container.append(e_name)

        season = content.get('Season') or {}

        info = {
            'id': content_id,
            'title': title,
            'description': content.get('Desc') or content.get('ShortDesc'),
            'timestamp': parse_iso8601(content.get('BroadcastDateTime')),
            'episode_number': int_or_none(content.get('Episode')),
            'season': season.get('Name'),
            'season_number': int_or_none(season.get('Number')),
            'season_id': season.get('Id'),
            'series': try_get(content, lambda x: x['Media']['Name']),
            'tags': tags,
            'categories': categories,
            'duration': float_or_none(content_package.get('Duration')),
            'formats': formats,
            'thumbnails': thumbnails,
        }

        if content_package.get('HasClosedCaptions'):
            info['subtitles'] = {
                'en': [{
                    'url': manifest_base_url + 'vtt',
                    'ext': 'vtt',
                }, {
                    'url': manifest_base_url + 'srt',
                    'ext': 'srt',
                }]
            }

        return info


class CPTwentyFourIE(InfoExtractor):
    IE_NAME = 'cp24'
    _GEO_COUNTRIES = ['CA']
    _VALID_URL = r'https?://(?:www\.)?cp24\.com/news/(?P<id>[^?#]+)'

    _TESTS = [{
        'url': 'https://www.cp24.com/news/video-shows-atm-being-ripped-out-of-business-by-pickup-truck-driver-in-mississauga-1.5676877',
        'info_dict': {
            'id': '2328005',
            'ext': 'mp4',
            'title': 'WATCH: Truck rips ATM from Mississauga business',
            'description': 'md5:cf7498480885f080a754389a2b2f7073',
            'timestamp': 1637618377,
            'episode_number': None,
            'season': 'Season 0',
            'season_number': 0,
            'season_id': 57974,
            'series': 'CTV News Toronto',
            'duration': 26.86,
            'thumbnail': 'http://images2.9c9media.com/image_asset/2014_11_5_2eb609a0-475b-0132-fbd6-34b52f6f1279_jpg_2000x1125.jpg',
            'upload_date': '20211122',
        },
        'params': {'skip_download': True, 'format': 'bv'}
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        id, destination = self._search_regex(
            r'getAuthStates\("(?P<id>[^"]+)",\s?"(?P<destination>[^"]+)"\);',
            webpage, 'video id and destination', group=('id', 'destination'))
        return self.url_result(f'9c9media:{destination}:{id}', ie=NineCNineMediaIE.ie_key(), video_id=id)
