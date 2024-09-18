
from .brightcove import BrightcoveNewIE
from .common import InfoExtractor
from .omnyfm import OmnyFMShowIE
from ..utils import (
    extract_attributes,
    get_element_by_class,
    smuggle_url,
    str_or_none,
    traverse_obj,
    url_or_none,
)


class AFLVideoIE(InfoExtractor):
    IE_NAME = 'afl:video'
    _VALID_URL = r'https?://(?:www\.)?afl\.com.au/(?:aflw/)?video/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://www.afl.com.au/aflw/video/1217670/the-w-show-aflws-line-in-the-sand-moment-bonnies-bold-bid',
        'md5': '7000431c2bd3f96eddb5f63273aea83e',
        'info_dict': {
            'id': '6361825702112',
            'ext': 'mp4',
            'description': 'md5:d1fee2ae8e3ecf486c1f0f7aa19e724b',
            'upload_date': '20240911',
            'duration': 1523.28,
            'tags': 'count:0',
            'thumbnail': r're:^https?://.*\.jpg$',
            'title': "The W Show: AFLW's 'line in the sand' moment, Bonnie's bold bid",
            'uploader_id': '6057984922001',
            'timestamp': 1726038522,
        },
    }, {
        'url': 'https://www.afl.com.au/video/1217264/bulldogs-season-review-gold-plated-list-going-to-waste-duos-frightening-future?videoId=1217264&modal=true&type=video&publishFrom=1725998400001',
        'only_matching': True,
    }, {
        'url': 'https://www.afl.com.au/video/1210885/wafl-showreel-ef-hamish-davis-highlights?videoId=1210885&modal=true&type=video&publishFrom=1725171238001',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        element = get_element_by_class('inline-player__player-container', webpage)
        attrs = traverse_obj(extract_attributes(element), {
            'account_id': ('data-account', {str_or_none}),
            'player_id': ('data-player', {lambda x: f'{x}_default'}, {str_or_none}),
            'video_id': ('data-video-id', {str_or_none}),
        })
        account_id = attrs.get('account_id')
        player_id = attrs.get('player_id')
        video_id = attrs.get('video_id')

        video_url = f'https://players.brightcove.net/{account_id}/{player_id}/index.html?videoId={video_id}'
        video_url = smuggle_url(video_url, {'referrer': url})
        return self.url_result(video_url, BrightcoveNewIE)


class AFLPodcastIE(InfoExtractor):
    IE_NAME = 'afl:podcast'
    _VALID_URL = r'https?://(?:www\.)?afl\.com.au/(?:aflw/)?podcasts/(?P<id>[\w-]+)'
    _TESTS = [{
        'url': 'https://www.afl.com.au/podcasts/between-us',
        'md5': '7000431c2bd3f96eddb5f63273aea83e',
        'info_dict': {
            'id': 'e0ab8454-f818-483f-bed1-b156002c021f',
            'title': 'Between Us',
        },
        'playlist_mincount': 7,
    }, {
        'url': 'https://www.afl.com.au/podcasts/afl-daily',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        element = get_element_by_class('omny-embed', webpage)
        podcast_url = traverse_obj(extract_attributes(element), ('src', {url_or_none}))
        return self.url_result(podcast_url, OmnyFMShowIE)


class AFCVideoIE(InfoExtractor):
    IE_NAME = 'afc:video'
    _VALID_URL = r'https?://(?:www\.)?afc\.com.au/video/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://www.afc.com.au/video/1657583/girls-academies-be-a-pro?videoId=1657583&modal=true&type=video&publishFrom=1726548621001',
        'md5': '6b52c149ae6566abe4cfc2d24978983d',
        'info_dict': {
            'id': '6362050135112',
            'ext': 'mp4',
            'description': 'md5:35897062f9a02043ece73a410bda595c',
            'upload_date': '20240917',
            'duration': 103.92,
            'tags': 'count:0',
            'thumbnail': r're:^https?://.*\.jpg$',
            'title': 'AFLW Jones Radiology Injury Update: R4',
            'uploader_id': '6057984922001',
            'timestamp': 1726558062,
        },
    }, {
        'url': 'https://www.afc.com.au/video/1586280/se10ep16-the-crows-show?videoId=1586280&modal=true&type=video&publishFrom=1719639000001&tagNames=crowsshowepisode',
        'only_matching': True,
    }, {
        'url': 'https://www.afc.com.au/video/1647468/matthew-clarke-presser-september-6?videoId=1647468&modal=true&type=video&publishFrom=1725591002001',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        video_id = self._search_regex(r'"mediaId"\s*:\s*"(\d+)"', webpage, 'video-id')
        player_id = self._search_regex(r'data-player-id\s*=\s*"(\w+)"', webpage, 'player-id') + '_default'
        account_id = self._search_regex(r'data-account-id\s*=\s*"(\d+)"', webpage, 'account-id')

        video_url = f'https://players.brightcove.net/{account_id}/{player_id}/index.html?videoId={video_id}'
        video_url = smuggle_url(video_url, {'referrer': url})
        return self.url_result(video_url, BrightcoveNewIE)
