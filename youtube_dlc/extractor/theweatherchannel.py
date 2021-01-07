# coding: utf-8
from __future__ import unicode_literals

import json
import re

from .theplatform import ThePlatformIE
from ..utils import (
    determine_ext,
    parse_duration,
    parse_iso8601,
)


class TheWeatherChannelIE(ThePlatformIE):
    _VALID_URL = r'https?://(?:www\.)?weather\.com(?P<asset_name>(?:/(?P<locale>[a-z]{2}-[A-Z]{2}))?/(?:[^/]+/)*video/(?P<id>[^/?#]+))'
    _TESTS = [{
        'url': 'https://weather.com/series/great-outdoors/video/ice-climber-is-in-for-a-shock',
        'md5': 'c4cbe74c9c17c5676b704b950b73dd92',
        'info_dict': {
            'id': 'cc82397e-cc3f-4d11-9390-a785add090e8',
            'ext': 'mp4',
            'title': 'Ice Climber Is In For A Shock',
            'description': 'md5:55606ce1378d4c72e6545e160c9d9695',
            'uploader': 'TWC - Digital (No Distro)',
            'uploader_id': '6ccd5455-16bb-46f2-9c57-ff858bb9f62c',
            'upload_date': '20160720',
            'timestamp': 1469018835,
        }
    }, {
        'url': 'https://weather.com/en-CA/international/videos/video/unidentified-object-falls-from-sky-in-india',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        asset_name, locale, display_id = re.match(self._VALID_URL, url).groups()
        if not locale:
            locale = 'en-US'
        video_data = list(self._download_json(
            'https://weather.com/api/v1/p/redux-dal', display_id, data=json.dumps([{
                'name': 'getCMSAssetsUrlConfig',
                'params': {
                    'language': locale.replace('-', '_'),
                    'query': {
                        'assetName': {
                            '$in': asset_name,
                        },
                    },
                }
            }]).encode(), headers={
                'Content-Type': 'application/json',
            })['dal']['getCMSAssetsUrlConfig'].values())[0]['data'][0]
        video_id = video_data['id']
        seo_meta = video_data.get('seometa', {})
        title = video_data.get('title') or seo_meta['title']

        urls = []
        thumbnails = []
        formats = []
        for variant_id, variant_url in video_data.get('variants', []).items():
            variant_url = variant_url.strip()
            if not variant_url or variant_url in urls:
                continue
            urls.append(variant_url)
            ext = determine_ext(variant_url)
            if ext == 'jpg':
                thumbnails.append({
                    'url': variant_url,
                    'id': variant_id,
                })
            elif ThePlatformIE.suitable(variant_url):
                tp_formats, _ = self._extract_theplatform_smil(variant_url, video_id)
                formats.extend(tp_formats)
            elif ext == 'm3u8':
                formats.extend(self._extract_m3u8_formats(
                    variant_url, video_id, 'mp4', 'm3u8_native',
                    m3u8_id=variant_id, fatal=False))
            elif ext == 'f4m':
                formats.extend(self._extract_f4m_formats(
                    variant_url, video_id, f4m_id=variant_id, fatal=False))
            else:
                formats.append({
                    'url': variant_url,
                    'format_id': variant_id,
                })
        self._sort_formats(formats)

        cc_url = video_data.get('cc_url')

        return {
            'id': video_id,
            'display_id': display_id,
            'title': title,
            'description': video_data.get('description') or seo_meta.get('description') or seo_meta.get('og:description'),
            'duration': parse_duration(video_data.get('duration')),
            'uploader': video_data.get('providername'),
            'uploader_id': video_data.get('providerid'),
            'timestamp': parse_iso8601(video_data.get('publishdate')),
            'subtitles': {locale[:2]: [{'url': cc_url}]} if cc_url else None,
            'thumbnails': thumbnails,
            'formats': formats,
        }
