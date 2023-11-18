import json
import urllib.parse

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    make_archive_id,
    unified_timestamp,
    urljoin,
)
from ..utils.traversal import traverse_obj


class NintendoIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?nintendo\.com/(?:(?P<locale>\w{2}(?:-\w{2})?)/)?nintendo-direct/(?P<slug>[^/?#]+)'
    _TESTS = [{
        'url': 'https://www.nintendo.com/nintendo-direct/09-04-2019/',
        'info_dict': {
            'ext': 'mp4',
            'id': '2oPmiviVePUA1IqAZzjuVh',
            'display_id': '09-04-2019',
            'title': 'Nintendo Direct 9.4.2019',
            'timestamp': 1567580400,
            'description': 'md5:8aac2780361d8cb772b6d1de66d7d6f4',
            'upload_date': '20190904',
            'age_limit': 17,
            '_old_archive_ids': ['nintendo J2bXdmaTE6fe3dWJTPcc7m23FNbc_A1V'],
        },
    }, {
        'url': 'https://www.nintendo.com/en-ca/nintendo-direct/08-31-2023/',
        'info_dict': {
            'ext': 'mp4',
            'id': '2TB2w2rJhNYF84qQ9E57hU',
            'display_id': '08-31-2023',
            'title': 'Super Mario Bros. Wonder Direct 8.31.2023',
            'timestamp': 1693465200,
            'description': 'md5:3067c5b824bcfdae9090a7f38ab2d200',
            'tags': ['Mild Fantasy Violence', 'In-Game Purchases'],
            'upload_date': '20230831',
            'age_limit': 6,
        },
    }, {
        'url': 'https://www.nintendo.com/en/nintendo-direct/09-04-2019/',
        'only_matching': True,
    }]

    def _create_asset_url(self, path):
        return urljoin('https://assets.nintendo.com/', urllib.parse.quote(path))

    def _real_extract(self, url):
        locale, slug = self._match_valid_url(url).group('locale', 'slug')

        language, _, country = (locale or 'en').partition('-')
        parsed_locale = f'{language.lower()}_{country.upper() or "US"}'
        self.write_debug(f'Using locale {parsed_locale} (from {locale})', only_once=True)

        response = self._download_json('https://graph.nintendo.com/', slug, query={
            'operationName': 'NintendoDirect',
            'variables': json.dumps({
                'locale': parsed_locale,
                'slug': slug,
            }, separators=(',', ':')),
            'extensions': json.dumps({
                'persistedQuery': {
                    'version': 1,
                    'sha256Hash': '969b16fe9f08b686fa37bc44d1fd913b6188e65794bb5e341c54fa683a8004cb'
                },
            }, separators=(',', ':')),
        })
        # API returns `{"data": {"direct": null}}` if no matching id
        direct_info = traverse_obj(response, ('data', 'direct', {dict}))
        if not direct_info:
            raise ExtractorError(f'No Nintendo Direct with id {slug} exists', expected=True)

        errors = ', '.join(traverse_obj(response, ('errors', ..., 'message')))
        if errors:
            raise ExtractorError(f'GraphQL API error: {errors or "Unknown error"}')

        asset_id = traverse_obj(direct_info, ('video', 'publicId', {str}))
        if not asset_id:
            self.raise_no_formats('Could not find any video formats', video_id=slug)

        result = {
            'display_id': slug,
            'formats': self._extract_m3u8_formats(
                self._create_asset_url(f'/video/upload/sp_full_hd/v1/{asset_id}.m3u8'), slug),
        }
        result.update(traverse_obj(direct_info, {
            'id': ('id', {str}),
            'title': ('name', {str}),
            'timestamp': ('startDate', {unified_timestamp}),
            'description': ('description', 'text', {str}),
            'age_limit': ('contentRating', 'order', {int}),
            'tags': ('contentDescriptors', ..., 'label', {str}),
            'thumbnail': ('thumbnail', {self._create_asset_url}),
        }))
        if asset_id.startswith('Legacy Videos/'):
            result['_old_archive_ids'] = [make_archive_id(self, asset_id[14:])]

        return result
