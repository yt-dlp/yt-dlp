from .common import InfoExtractor
from ..utils import ExtractorError, int_or_none, join_nonempty, url_or_none
from ..utils.traversal import traverse_obj


class MagentaMusikIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?magentamusik\.de/(?P<id>[^/?#]+)'

    _TESTS = [{
        'url': 'https://www.magentamusik.de/marty-friedman-woa-2023-9208205928595409235',
        'md5': 'd82dd4748f55fc91957094546aaf8584',
        'info_dict': {
            'id': '9208205928595409235',
            'display_id': 'marty-friedman-woa-2023-9208205928595409235',
            'ext': 'mp4',
            'title': 'Marty Friedman: W:O:A 2023',
            'alt_title': 'Konzert vom: 05.08.2023 13:00',
            'duration': 2760,
            'categories': ['Musikkonzert'],
            'release_year': 2023,
            'location': 'Deutschland',
        },
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        player_config = self._search_json(
            r'data-js-element="o-video-player__config">', webpage, 'player config', display_id, fatal=False)
        if not player_config:
            raise ExtractorError('No video found', expected=True)

        asset_id = player_config['assetId']
        asset_details = self._download_json(
            f'https://wcps.t-online.de/cvss/magentamusic/vodclient/v2/assetdetails/58938/{asset_id}',
            display_id, note='Downloading asset details')

        video_id = traverse_obj(
            asset_details, ('content', 'partnerInformation', ..., 'reference', {str}), get_all=False)
        if not video_id:
            raise ExtractorError('Unable to extract video id')

        vod_data = self._download_json(
            f'https://wcps.t-online.de/cvss/magentamusic/vodclient/v2/player/58935/{video_id}/Main%20Movie', video_id)
        smil_url = traverse_obj(
            vod_data, ('content', 'feature', 'representations', ...,
                       'contentPackages', ..., 'media', 'href', {url_or_none}), get_all=False)

        return {
            'id': video_id,
            'display_id': display_id,
            'formats': self._extract_smil_formats(smil_url, video_id),
            **traverse_obj(vod_data, ('content', 'feature', 'metadata', {
                'title': 'title',
                'alt_title': 'originalTitle',
                'description': 'longDescription',
                'duration': ('runtimeInSeconds', {int_or_none}),
                'location': ('countriesOfProduction', {list}, {lambda x: join_nonempty(*x, delim=', ')}),
                'release_year': ('yearOfProduction', {int_or_none}),
                'categories': ('mainGenre', {str}, all, filter),
            })),
        }
