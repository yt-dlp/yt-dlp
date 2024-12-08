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

            'thumbnail': r're:^https?://.*\.(jpe?g|webp)$',
            'uploader': 'wombatpmv',
            'title': 'NEW RULES',
            'description': 'Experience the mesmerizing PMV - NEW RULES created by wombatpmv',
            'ext': 'mp4',
        },
    }, {
        'url': 'https://pmvhaven.com/video/The-Succubus-Sidenpose_66910e34de14153c0fbab5c9',
        'md5': 'd86e7ad579163d9d8d4e0e434d8addce',
        'info_dict': {
            'id': '66910e34de14153c0fbab5c9',

            'thumbnail': r're:^https?://.*\.(jpe?g|webp)$',
            'uploader': 'sidenpose',
            'title': 'The Succubus Sidenpose',
            'description': 'Experience the mesmerizing PMV - The Succubus Sidenpose created by sidenpose',
            'ext': 'mp4',
        },
    }, {
        'url': 'https://pmvhaven.com/video/NASTY-TEENS-01_652e6ade99f1e372b0180107',
        'md5': '4b612116f90a80ead2481a834b615827',
        'info_dict': {
            'id': '652e6ade99f1e372b0180107',

            'thumbnail': r're:^https?://.*\.(jpe?g|webp)$',
            'uploader': 'PMVArchive',
            'title': 'NASTY TEENS 01',
            'description': 'Experience the mesmerizing PMV - NASTY TEENS 01 created by brktnz',
            'ext': 'mp4',
        },
    }, {
        'url': 'https://pmvhaven.com/video/Indian-Girls-Do-It-Well-Brown-Girls-PMV_6679d486c73601563c51fc50',
        'md5': 'cee8a8bcdad69fb0d3a7da92fdf7c615',
        'info_dict': {
            'id': '6679d486c73601563c51fc50',

            'thumbnail': r're:^https?://.*\.(jpe?g|webp)$',
            'uploader': 'shananne',
            'title': 'Indian Girls Do It Well - Brown Girls PMV',
            'description': 'Experience the mesmerizing PMV - Indian Girls Do It Well - Brown Girls PMV',
            'ext': 'mp4',
        },
    }]

    def _real_extract(self, url):
        episode_id = self._match_id(url)
        webpage = self._download_webpage(url, episode_id)
        data = self._search_json(
            r'<script[^>]+id=["\']__NUXT_DATA__["\'][^>]*>',
            webpage, 'nuxt data', None, end_pattern=r'</script>', contains_pattern=r'\[(?s:.+)\]')

        # Data contains "pointers", so we gotta follow them
        jdat = traverse_obj(data, (1, 'data'))
        jdat = traverse_obj(data, (jdat, lambda key, _: 'videoInput' in key))
        jdat = traverse_obj(data, (jdat, 'video'))
        jdat = traverse_obj(data, (jdat, 0))
        jdat = traverse_obj(data, (jdat))

        thumbnails = [{'url': data[idx]} for idx in traverse_obj(data, (jdat, 'thumbnails')) if data[idx] not in ['placeholder', 'null', None]]

        return {
            'id': episode_id,
            'title': traverse_obj(data, (jdat, 'title')),
            'description': self._og_search_description(webpage),
            'uploader': traverse_obj(data, (jdat, 'uploader')),
            'url': traverse_obj(data, (jdat, 'url')),
            'thumbnails': thumbnails,
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
