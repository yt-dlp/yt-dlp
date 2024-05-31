from .brightcove import BrightcoveNewIE
from .common import InfoExtractor
from ..utils import ExtractorError
from ..utils.traversal import traverse_obj


class NineNewsIE(InfoExtractor):
    IE_NAME = '9News'
    _VALID_URL = r'https?://(?:www\.)?9news\.com\.au/(?:[\w-]+/){2,3}(?P<id>[\w-]+)/?(?:$|[?#])'
    _TESTS = [{
        'url': 'https://www.9news.com.au/videos/national/fair-trading-pulls-dozens-of-toys-from-shelves/clqgc7dvj000y0jnvfism0w5m',
        'md5': 'd1a65b2e9d126e5feb9bc5cb96e62c80',
        'info_dict': {
            'id': '6343717246112',
            'ext': 'mp4',
            'title': 'Fair Trading pulls dozens of toys from shelves',
            'description': 'Fair Trading Australia have been forced to pull dozens of toys from shelves over hazard fears.',
            'thumbnail': 'md5:bdbe44294e2323b762d97acf8843f66c',
            'duration': 93.44,
            'timestamp': 1703231748,
            'upload_date': '20231222',
            'uploader_id': '664969388001',
            'tags': ['networkclip', 'aunews_aunationalninenews', 'christmas presents', 'toys', 'fair trading', 'au_news'],
        }
    }, {
        'url': 'https://www.9news.com.au/world/tape-reveals-donald-trump-pressured-michigan-officials-not-to-certify-2020-vote-a-new-report-says/0b8b880e-7d3c-41b9-b2bd-55bc7e492259',
        'md5': 'a885c44d20898c3e70e9a53e8188cea1',
        'info_dict': {
            'id': '6343587450112',
            'ext': 'mp4',
            'title': 'Trump found ineligible to run for president by state court',
            'description': 'md5:40e6e7db7a4ac6be0e960569a5af6066',
            'thumbnail': 'md5:3e132c48c186039fd06c10787de9bff2',
            'duration': 104.64,
            'timestamp': 1703058034,
            'upload_date': '20231220',
            'uploader_id': '664969388001',
            'tags': ['networkclip', 'aunews_aunationalninenews', 'ineligible', 'presidential candidate', 'donald trump', 'au_news'],
        }
    }, {
        'url': 'https://www.9news.com.au/national/outrage-as-parents-banned-from-giving-gifts-to-kindergarten-teachers/e19b49d4-a1a4-4533-9089-6e10e2d9386a',
        'info_dict': {
            'id': '6343716797112',
            'ext': 'mp4',
            'title': 'Outrage as parents banned from giving gifts to kindergarten teachers',
            'description': 'md5:7a8b0ed2f9e08875fd9a3e86e462bc46',
            'thumbnail': 'md5:5ee4d66717bdd0dee9fc9a705ef041b8',
            'duration': 91.307,
            'timestamp': 1703229584,
            'upload_date': '20231222',
            'uploader_id': '664969388001',
            'tags': ['networkclip', 'aunews_aunationalninenews', 'presents', 'teachers', 'kindergarten', 'au_news'],
        },
    }]

    def _real_extract(self, url):
        article_id = self._match_id(url)
        webpage = self._download_webpage(url, article_id)
        initial_state = self._search_json(
            r'var\s+__INITIAL_STATE__\s*=', webpage, 'initial state', article_id)
        video_id = traverse_obj(
            initial_state, ('videoIndex', 'currentVideo', 'brightcoveId', {str}),
            ('article', ..., 'media', lambda _, v: v['type'] == 'video', 'urn', {str}), get_all=False)
        account = traverse_obj(initial_state, (
            'videoIndex', 'config', (None, 'video'), 'account', {str}), get_all=False)

        if not video_id or not account:
            raise ExtractorError('Unable to get the required video data')

        return self.url_result(
            f'https://players.brightcove.net/{account}/default_default/index.html?videoId={video_id}',
            BrightcoveNewIE, video_id)
