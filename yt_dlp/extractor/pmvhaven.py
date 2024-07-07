import json

from .common import InfoExtractor
from ..utils import traverse_obj


class PMVHavenIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?pmvhaven\.com/video/[a-zA-Z0-9\-]+_(?P<id>[a-z0-9]+)'
    _TESTS = [{
        'url': 'https://pmvhaven.com/video/NEW-RULES_66799ca1ca817a3e12107c75',
        'md5': '2a4483b529ad5f350009e5b98fc37d29',
        'info_dict': {
            # For videos, only the 'id' and 'ext' fields are required to RUN the test:
            'id': '66799ca1ca817a3e12107c75',

            'thumbnail': r're:^https?://.*\.jpeg$',
            'uploader': 'wombatpmv',
            'title': 'NEW RULES',
            'description': 'Experience the mesmerizing PMV - NEW RULES created by wombatpmv',
            'ext': 'mp4',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        data = self._search_regex(r'<script.*id="__NUXT_DATA__".*>(.+?)</script>', webpage, 'json data search')
        data = json.loads(data)

        # Data contains "pointers", so we gotta follow them
        jdat = data[data[data[0][1]]['data']]
        _idx = next(i for i in list(jdat.keys()) if 'videoInput' in i)
        jdat = data[data[jdat[_idx]]['video']]
        jdat = data[jdat[0]]

        return {
            'id': video_id,
            'title': data[jdat['title']],
            'description': self._og_search_description(webpage),
            'uploader': data[jdat['uploader']],
            'url': data[jdat['url']],
            'thumbnails': [{'url': data[i]} for i in data[jdat['thumbnails']] if data[i] != 'placeholder'],
        }


class PMVHavenProfileIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?pmvhaven\.com/profile/(?P<id>[a-zA-Z0-9-_]+)'
    _USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0'
    _HEADERS = {
        'Content-Type': 'text/plain;charset=UTF-8',
        'User-Agent': _USER_AGENT,
    }

    def _real_extract(self, url):
        profile_id = self._match_id(url)

        data = self._download_json(
            'https://pmvhaven.com/api/v2/profileInput',
            profile_id, headers=self._HEADERS,
            data=json.dumps({
                'mode': 'getProfileVideos',
                'user': profile_id,
            }).encode(),
            encoding='UTF-8',
        )
        entries = []
        need = data['count']
        entries.extend(data['videos'])
        if 'processingVideos' in data:
            entries.extend(data['processingVideos'])

        idx = 1
        while (len(entries) < need):
            idx += 1
            pdata = self._download_json(
                'https://pmvhaven.com/api/v2/profileInput',
                profile_id, headers=self._HEADERS,
                data=json.dumps({
                    'index': idx,
                    'mode': 'GetMoreProfileVideos',
                    'user': profile_id,
                }).encode(),
                encoding='UTF-8',
            )

            if len(pdata['data']) == 0:
                break

            entries.extend(pdata['data'])

        def transform(data):
            return {
                'id': traverse_obj(data, ('_id')),
                'title': traverse_obj(data, ('title')),
                'uploader': traverse_obj(data, ('uploader')),
                'url': traverse_obj(data, ('url')),
                'thumbnails': [{'url': i} for i in data['thumbnails'] if i != 'placeholder'],
            }
        entries = map(transform, entries)

        return self.playlist_result(
            entries, playlist_id=profile_id, playlist_title=f"{profile_id}'s profile")
