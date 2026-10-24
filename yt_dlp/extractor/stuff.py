from .brightcove import BrightcoveNewIE
from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    parse_duration,
    parse_iso8601,
    smuggle_url,
    url_or_none,
)
from ..utils.traversal import traverse_obj


class StuffIE(InfoExtractor):
    IE_NAME = 'stuff'
    _VALID_URL = r'https?://(?:www\.)?stuff\.co\.nz/(?:[\w-]+/)+(?P<id>\d+)(?:/[\w-]+)?/?'
    _TESTS = [{
        'url': 'https://www.stuff.co.nz/nz-news/360880160/extraordinary-aerial-video-shows-scale-and-ferocity-tongariro-fire',
        'info_dict': {
            'id': '6384842477112',
            'ext': 'mp4',
            'display_id': '360880160',
            'title': 'Extraordinary aerial video shows scale and ferocity of Tongariro fire',
            'description': 'Vision taken from the air shows the fire on Saturday afternoon.',
            'duration': 36,
            'timestamp': 1762635537,
            'upload_date': '20251108',
            'modified_timestamp': 1762645228,
            'modified_date': '20251108',
            'thumbnail': r're:^https?://www\.stuff\.co\.nz/media/images/.+',
            'creators': ['Lakeview Helicopters'],
            'uploader_id': '3921507366001',
            'channel': 'Stuff',
            'categories': ['NZ news'],
            'tags': ['Fire', 'Video moments', 'Playlist Include', 'NEWS'],
        },
        'params': {'skip_download': True},
    }, {
        'url': 'https://www.stuff.co.nz/world-news/360978270/hegseth-gets-bipartisan-grilling-rising-costs-iran',
        'info_dict': {
            'id': '6395364048112',
            'ext': 'mp4',
            'display_id': '360978273',
            'title': "Hegseth gets bipartisan grilling on rising costs of the Iran war and Trump's end game",
            'description': r're:^Defense Secretary Pete Hegseth has faced tough questions.+',
            'duration': 109,
            'timestamp': 1778634811,
            'upload_date': '20260513',
            'modified_timestamp': 1778634811,
            'modified_date': '20260513',
            'thumbnail': r're:^https?://www\.stuff\.co\.nz/media/images/.+',
            'creators': ['AP'],
            'uploader_id': '3921507366001',
            'channel': 'Stuff',
            'categories': ['World news'],
            'tags': [
                'War', 'Military', 'Heads of state', 'Politics', 'International politics',
                'Pete Hegseth', 'Iran', 'Donald Trump', 'United States', 'Chris Coons',
                'Republican', 'Susan Collins', 'The Pentagon', 'NATO', 'NEWS',
            ],
        },
        'params': {'skip_download': True},
    }, {
        'url': 'https://www.stuff.co.nz/nz-news/360977692/mother-baby-who-died-suspected-homicide-give-evidence',
        'expected_exception': 'ExtractorError',
    }]

    BRIGHTCOVE_URL_TEMPLATE = 'https://players.brightcove.net/3921507366001/yPkF3onU8_default/index.html?videoId=%s'

    def _parse_video_asset(self, asset, article_json, url, article_id):
        item = asset.get('item') or {}
        video_id = traverse_obj(item, ('id', {str}))
        if not video_id:
            return None

        info = traverse_obj(article_json, {
            'timestamp': ('publishedDate', {parse_iso8601}),
            'modified_timestamp': ('updatedDate', {parse_iso8601}),
            'channel': ('mainPublicationName', {str}),
            'categories': ('metadata', 'section', {str}, filter, all, filter),
        })
        tags = traverse_obj(article_json, ('metadata', ('topic', 'entity', 'keyword'), ..., {str}))
        if tags:
            info['tags'] = list(dict.fromkeys(tags))

        info.update(traverse_obj(asset, {
            'title': ('title', {str}),
            'description': ('caption', {str}),
            'creators': (('creditline', 'source'), {str}, any, filter, all, filter),
        }))
        info.update(traverse_obj(item, {
            'thumbnail': ('poster', {url_or_none}),
            'duration': ('duration', {parse_duration}),
        }))

        info.setdefault('title', traverse_obj(article_json, ('content', 'title', {str})))
        info.setdefault('description', traverse_obj(article_json, ('content', 'intro', {str})))

        return {
            '_type': 'url_transparent',
            'url': smuggle_url(self.BRIGHTCOVE_URL_TEMPLATE % video_id, {'referrer': url}),
            'ie_key': BrightcoveNewIE.ie_key(),
            'id': video_id,
            'display_id': str(item.get('assetId') or article_id),
            **info,
        }

    def _real_extract(self, url):
        article_id = self._match_id(url)
        article_json = self._download_json(
            f'https://www.stuff.co.nz/api/v1.0/stuff/story/{article_id}', article_id)
        article_type = article_json.get('type')

        if article_type == 'VIDEO/BRIGHTCOVE':
            asset = traverse_obj(article_json, ('content', 'asset')) or {}
            return self._parse_video_asset(asset, article_json, url, article_id)

        if article_type == 'ARTICLE':
            video_assets = traverse_obj(
                article_json,
                ('content', 'contentBody', 'assets', lambda _, v: v.get('type') == 'VIDEO'))
            entries = list(filter(None, (
                self._parse_video_asset(a, article_json, url, article_id) for a in video_assets)))

            if not entries:
                raise ExtractorError('Article contains no embedded videos', expected=True)

            if len(entries) == 1:
                return entries[0]
            return self.playlist_result(
                entries, article_id,
                playlist_title=traverse_obj(article_json, ('content', 'title', {str})),
                playlist_description=traverse_obj(article_json, ('content', 'intro', {str})))

        raise ExtractorError(f'Cannot process Article type {article_type}', expected=True)
