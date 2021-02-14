from __future__ import unicode_literals

from .common import InfoExtractor


class GrouponIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?groupon\.com/deals/(?P<id>[^/?#&]+)'

    _TEST = {
        'url': 'https://www.groupon.com/deals/bikram-yoga-huntington-beach-2#ooid=tubGNycTo_9Uxg82uESj4i61EYX8nyuf',
        'info_dict': {
            'id': 'bikram-yoga-huntington-beach-2',
            'title': '$49 for 10 Yoga Classes or One Month of Unlimited Classes at Bikram Yoga Huntington Beach ($180 Value)',
            'description': 'Studio kept at 105 degrees and 40% humidity with anti-microbial and anti-slip Flotex flooring; certified instructors',
        },
        'playlist': [{
            'md5': '42428ce8a00585f9bc36e49226eae7a1',
            'info_dict': {
                'id': 'fk6OhWpXgIQ',
                'ext': 'mp4',
                'title': 'Bikram Yoga Huntington Beach | Orange County !tubGNycTo@9Uxg82uESj4i61EYX8nyuf',
                'description': 'md5:d41d8cd98f00b204e9800998ecf8427e',
                'duration': 45,
                'upload_date': '20160405',
                'uploader_id': 'groupon',
                'uploader': 'Groupon',
            },
            'add_ie': ['Youtube'],
        }],
        'params': {
            'skip_download': True,
        },
    }

    _PROVIDERS = {
        'ooyala': ('ooyala:%s', 'Ooyala'),
        'youtube': ('%s', 'Youtube'),
    }

    def _real_extract(self, url):
        playlist_id = self._match_id(url)
        webpage = self._download_webpage(url, playlist_id)

        payload = self._parse_json(self._search_regex(
            r'(?:var\s+|window\.)payload\s*=\s*(.*?);\n', webpage, 'payload'), playlist_id)
        videos = payload['carousel'].get('dealVideos', [])
        entries = []
        for v in videos:
            provider = v.get('provider')
            video_id = v.get('media') or v.get('id') or v.get('baseURL')
            if not provider or not video_id:
                continue
            url_pattern, ie_key = self._PROVIDERS.get(provider.lower())
            if not url_pattern:
                self.report_warning(
                    '%s: Unsupported video provider %s, skipping video' %
                    (playlist_id, provider))
                continue
            entries.append(self.url_result(url_pattern % video_id, ie_key))

        return {
            '_type': 'playlist',
            'id': playlist_id,
            'entries': entries,
            'title': self._og_search_title(webpage),
            'description': self._og_search_description(webpage),
        }
