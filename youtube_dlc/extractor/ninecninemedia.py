# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
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
        destination_code, content_id = re.match(self._VALID_URL, url).groups()
        api_base_url = self._API_BASE_TEMPLATE % (destination_code, content_id)
        content = self._download_json(api_base_url, content_id, query={
            '$include': '[Media,Season,ContentPackages]',
        })
        title = content['Name']
        if len(content['ContentPackages']) > 1:
            raise ExtractorError('multiple content packages')
        content_package = content['ContentPackages'][0]
        package_id = content_package['Id']
        content_package_url = api_base_url + 'contentpackages/%s/' % package_id
        content_package = self._download_json(
            content_package_url, content_id, query={
                '$include': '[HasClosedCaptions]',
            })

        if try_get(content_package, lambda x: x['Constraints']['Security']['Type']):
            raise ExtractorError('This video is DRM protected.', expected=True)

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
