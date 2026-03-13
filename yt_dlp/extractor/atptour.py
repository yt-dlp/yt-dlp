import re

from .brightcove import BrightcoveNewIE
from .common import InfoExtractor
from ..utils import base_url, extract_attributes, get_element_html_by_id, traverse_obj, urljoin


class ATPTourVideoIE(InfoExtractor):
    IE_NAME = 'atptour:video'
    _VALID_URL = r'https?://(?:www\.)?atptour\.com/(?:en|es)/video/(?P<id>[\w-]+)'
    _TESTS = [{
        'url': 'https://www.atptour.com/en/video/challenger-highlights-nishikori-wins-in-como-2024',
        'md5': '4721002227d98fe89afafa40eba3068d',
        'info_dict': {
            'id': '6361099221112',
            'ext': 'mp4',
            'description': 'md5:ef8afed21c52cbe4ad3409045d59f413',
            'upload_date': '20240827',
            'duration': 105.152,
            'tags': 'count:6',
            'thumbnail': r're:^https?://.*\.jpg$',
            'title': 'Challenger Highlights: Nishikori wins in Como 2024',
            'uploader_id': '6057277721001',
            'timestamp': 1724775281,
        },
    }, {
        'url': 'https://www.atptour.com/en/video/highlights-svajda-earns-highestranked-win-of-career-vs-cerundolo-winstonsalem-2024',
        'md5': 'a3829d10bdcb1829568fd88b9e6ecb15',
        'info_dict': {
            'id': '6360716257112',
            'ext': 'mp4',
            'description': 'md5:a334aeb73eac631ffab8249b1e68194c',
            'upload_date': '20240820',
            'duration': 139.691,
            'tags': 'count:5',
            'thumbnail': r're:^https?://.*\.jpg$',
            'title': 'Highlights: Svajda earns highest-ranked win of career vs. Cerundolo Winston-Salem 2024',
            'uploader_id': '6057277721001',
            'timestamp': 1724183755,
        },
    }, {
        'url': 'https://www.atptour.com/es/video/highlights-michelsen-defeats-fucsovics-in-winston-salem-2024',
        'md5': '7ba4c3aabef9eb20a1b9877f28e6f775',
        'info_dict': {
            'id': '6360727636112',
            'ext': 'mp4',
            'description': 'md5:2c5682fdfa514e508c6d947e9e9b6eeb',
            'upload_date': '20240821',
            'duration': 135.424,
            'tags': 'count:6',
            'thumbnail': r're:^https?://.*\.jpg$',
            'title': 'Highlights: Michelsen defeats Fucsovics in Winston-Salem 2024',
            'uploader_id': '6057277721001',
            'timestamp': 1724205624,
        },
    }, {
        'url': 'https://www.atptour.com/en/video/highlights-sonego-dominates-michelsen-for-winston-salem-open-title-2024',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id, fatal=False, impersonate=True)

        hidden_inputs = self._hidden_inputs(webpage, 'class')
        featured_videos_url = urljoin(base_url(url), hidden_inputs.get('atp_featured-videos-endpoint'))
        json_data = self._download_json(featured_videos_url, display_id, fatal=False, impersonate=True)
        video_data = traverse_obj(json_data, ('content', 0))
        account_id = traverse_obj(video_data, ('videoAccountId'))
        player_id = traverse_obj(video_data, ('videoPlayerId'))
        video_id = traverse_obj(video_data, ('videoId'))
        return self.url_result(
            f'https://players.brightcove.net/{account_id}/{player_id}/index.html?videoId={video_id}', BrightcoveNewIE)


class ATPTourNewsIE(InfoExtractor):
    IE_NAME = 'atptour:news'
    _VALID_URL = r'https?://(?:www\.)?atptour\.com/(?:en|es)/news/(?P<id>[\w-]+)'
    _TESTS = [{
        'url': 'https://www.atptour.com/en/news/sinner-zverev-cincinnati-2024-sf',
        'playlist_mincount': 2,
        'info_dict': {
            'id': 'sinner-zverev-cincinnati-2024-sf',
            'title': 'Jannik Sinner battles past Alexander Zverev to reach Cincinnati final | ATP Tour | Tennis',
            'description': 'md5:30cd3df666c8a5d45731d1e85d8d43ae',
        },
    }, {
        'url': 'https://www.atptour.com/en/news/borges-us-open-2024-this-is-tennis',
        'playlist_mincount': 1,
        'info_dict': {
            'id': 'borges-us-open-2024-this-is-tennis',
            'title': 'Nuno Borges: Building legos, facing Nadal, Cirque du Soleil & more | ATP Tour | Tennis',
            'description': 'md5:aaef866660c4e3ced69118c0f6ed237a',
        },
    }, {
        'url': 'https://www.atptour.com/es/news/popyrin-us-open-2024-feature',
        'playlist_mincount': 1,
        'info_dict': {
            'id': 'popyrin-us-open-2024-feature',
            'title': 'Alexei Popyrin: Hamilton, pollo frito y la revancha de Djokovic | ATP Tour | Tennis',
            'description': 'md5:b62a35720a278c9ab8410847915dc581',
        },
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id, fatal=False, impersonate=True)

        title = self._html_extract_title(webpage)
        description = self._og_search_description(webpage)

        entries = []

        first_video = get_element_html_by_id('articleVideoJSPlayer', webpage)
        if first_video is not None:
            attributes = extract_attributes(first_video)
            account_id = traverse_obj(attributes, ('data-account'))
            player_id = traverse_obj(attributes, ('data-player'))
            video_id = traverse_obj(attributes, ('data-video-id'))
            first_video_url = f'https://players.brightcove.net/{account_id}/{player_id}/index.html?videoId={video_id}'
            entries.append(self.url_result(first_video_url, BrightcoveNewIE))

        iframe_urls = re.findall(r'<iframe[^>]src="(https://players\.brightcove\.net/[^"]+)"', webpage)
        for video_url in iframe_urls:
            entries.append(self.url_result(video_url, BrightcoveNewIE))

        return self.playlist_result(entries, display_id, title, description)
