from .common import InfoExtractor
from ..utils import (
    try_get,
    unified_strdate,
)


class PlanetMarathiIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?planetmarathi\.com/titles/(?P<id>[^/#&?$]+)'
    _TESTS = [{
        'url': 'https://www.planetmarathi.com/titles/ek-unad-divas',
        'playlist_mincount': 2,
        'info_dict': {
            'id': 'ek-unad-divas',
        },
        'playlist': [{
            'info_dict': {
                'id': 'ASSETS-MOVIE-ASSET-01_ek-unad-divas',
                'ext': 'mp4',
                'title': 'ek unad divas',
                'alt_title': 'चित्रपट',
                'description': 'md5:41c7ed6b041c2fea9820a3f3125bd881',
                'season_number': None,
                'episode_number': 1,
                'duration': 5539,
                'upload_date': '20210829',
            },
        }]  # Trailer skipped
    }, {
        'url': 'https://www.planetmarathi.com/titles/baap-beep-baap-season-1',
        'playlist_mincount': 10,
        'info_dict': {
            'id': 'baap-beep-baap-season-1',
        },
        'playlist': [{
            'info_dict': {
                'id': 'ASSETS-CHARACTER-PROFILE-SEASON-01-ASSET-01_baap-beep-baap-season-1',
                'ext': 'mp4',
                'title': 'Manohar Kanhere',
                'alt_title': 'मनोहर कान्हेरे',
                'description': 'md5:285ed45d5c0ab5522cac9a043354ebc6',
                'season_number': 1,
                'episode_number': 1,
                'duration': 29,
                'upload_date': '20210829',
            },
        }]  # Trailers, Episodes, other Character profiles skipped
    }]

    def _real_extract(self, url):
        id = self._match_id(url)
        entries = []
        json_data = self._download_json(f'https://www.planetmarathi.com/api/v1/titles/{id}/assets', id)['assets']
        for asset in json_data:
            asset_title = asset['mediaAssetName']['en']
            if asset_title == 'Movie':
                asset_title = id.replace('-', ' ')
            asset_id = f'{asset["sk"]}_{id}'.replace('#', '-')
            formats, subtitles = self._extract_m3u8_formats_and_subtitles(asset['mediaAssetURL'], asset_id)
            self._sort_formats(formats)
            entries.append({
                'id': asset_id,
                'title': asset_title,
                'alt_title': try_get(asset, lambda x: x['mediaAssetName']['mr']),
                'description': try_get(asset, lambda x: x['mediaAssetDescription']['en']),
                'season_number': asset.get('mediaAssetSeason'),
                'episode_number': asset.get('mediaAssetIndexForAssetType'),
                'duration': asset.get('mediaAssetDurationInSeconds'),
                'upload_date': unified_strdate(asset.get('created')),
                'formats': formats,
                'subtitles': subtitles,
            })
        return self.playlist_result(entries, playlist_id=id)
