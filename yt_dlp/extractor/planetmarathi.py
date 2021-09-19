# coding: utf-8
from __future__ import unicode_literals

import json

from .common import InfoExtractor
from ..utils import unified_strdate

class PlanetMarathiIE(InfoExtractor):
    _VALID_URL = r'(?:https?://)(?:www\.)?planetmarathi\.com/titles/(?P<id>[^/#&?$]+)'
    _TESTS = []

    def _real_extract(self, url):
        id = self._match_id(url)
        genres = self._download_json(f'https://www.planetmarathi.com/api/v1/titles/{id}/genres', id)['genres']
        types = ['trailer', 'behind-the-scene', 'character-profile']
        tags = []
        for genre in genres:
            tag = genre.get('genreSlug')
            if tag == 'movies':
                types.append('movie')
            else:
                types.append('episode')
            tags.append(tag)
        entries = []
        for type in types:
            json_data = self._download_json(f'https://www.planetmarathi.com/api/v1/titles/{id}/assets', id, data= json.dumps({"assetType": type}).encode())['assets']
            for asset in json_data:
                asset_title = asset['mediaAssetName']['en']
                alt_title = asset['mediaAssetType']
                asset_id = f'{alt_title}-{asset_title}'
                formats, subtitles = self._extract_m3u8_formats_and_subtitles(asset['mediaAssetURL'], asset_id)
                self._sort_formats(formats)
                entries.append({
                    'id': asset_id,
                    'title': asset_title,
                    'alt_title': alt_title,
                    'description': asset['mediaAssetDescription']['en'],
                    'tags': tags,
                    'season_number': asset.get('mediaAssetSeason'),
                    'episode_number': asset.get('mediaAssetIndexForAssetType'),
                    'duration': asset.get('mediaAssetDurationInSeconds'),
                    'upload_date': unified_strdate(asset.get('created')),
                    'formats': formats,
                    'subtitles': subtitles,
                })
        return self.playlist_result(entries, playlist_id=id)
