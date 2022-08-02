import re

from .common import InfoExtractor
from ..utils import (
    clean_html,
    determine_ext,
    get_element_by_class,
)


class NFLBaseIE(InfoExtractor):
    _VALID_URL_BASE = r'''(?x)
                    https?://
                        (?P<host>
                            (?:www\.)?
                            (?:
                                (?:
                                    nfl|
                                    buffalobills|
                                    miamidolphins|
                                    patriots|
                                    newyorkjets|
                                    baltimoreravens|
                                    bengals|
                                    clevelandbrowns|
                                    steelers|
                                    houstontexans|
                                    colts|
                                    jaguars|
                                    (?:titansonline|tennesseetitans)|
                                    denverbroncos|
                                    (?:kc)?chiefs|
                                    raiders|
                                    chargers|
                                    dallascowboys|
                                    giants|
                                    philadelphiaeagles|
                                    (?:redskins|washingtonfootball)|
                                    chicagobears|
                                    detroitlions|
                                    packers|
                                    vikings|
                                    atlantafalcons|
                                    panthers|
                                    neworleanssaints|
                                    buccaneers|
                                    azcardinals|
                                    (?:stlouis|the)rams|
                                    49ers|
                                    seahawks
                                )\.com|
                                .+?\.clubs\.nfl\.com
                            )
                        )/
                    '''
    _VIDEO_CONFIG_REGEX = r'<script[^>]+id="[^"]*video-config-[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}[^"]*"[^>]*>\s*({.+})'
    _WORKING = False

    def _parse_video_config(self, video_config, display_id):
        video_config = self._parse_json(video_config, display_id)
        item = video_config['playlist'][0]
        mcp_id = item.get('mcpID')
        if mcp_id:
            info = self.url_result(
                'anvato:GXvEgwyJeWem8KCYXfeoHWknwP48Mboj:' + mcp_id,
                'Anvato', mcp_id)
        else:
            media_id = item.get('id') or item['entityId']
            title = item['title']
            item_url = item['url']
            info = {'id': media_id}
            ext = determine_ext(item_url)
            if ext == 'm3u8':
                info['formats'] = self._extract_m3u8_formats(item_url, media_id, 'mp4')
                self._sort_formats(info['formats'])
            else:
                info['url'] = item_url
                if item.get('audio') is True:
                    info['vcodec'] = 'none'
            is_live = video_config.get('live') is True
            thumbnails = None
            image_url = item.get(item.get('imageSrc')) or item.get(item.get('posterImage'))
            if image_url:
                thumbnails = [{
                    'url': image_url,
                    'ext': determine_ext(image_url, 'jpg'),
                }]
            info.update({
                'title': title,
                'is_live': is_live,
                'description': clean_html(item.get('description')),
                'thumbnails': thumbnails,
            })
        return info


class NFLIE(NFLBaseIE):
    IE_NAME = 'nfl.com'
    _VALID_URL = NFLBaseIE._VALID_URL_BASE + r'(?:videos?|listen|audio)/(?P<id>[^/#?&]+)'
    _TESTS = [{
        'url': 'https://www.nfl.com/videos/baker-mayfield-s-game-changing-plays-from-3-td-game-week-14',
        'info_dict': {
            'id': '899441',
            'ext': 'mp4',
            'title': "Baker Mayfield's game-changing plays from 3-TD game Week 14",
            'description': 'md5:85e05a3cc163f8c344340f220521136d',
            'upload_date': '20201215',
            'timestamp': 1608009755,
            'thumbnail': r're:^https?://.*\.jpg$',
            'uploader': 'NFL',
        }
    }, {
        'url': 'https://www.chiefs.com/listen/patrick-mahomes-travis-kelce-react-to-win-over-dolphins-the-breakdown',
        'md5': '6886b32c24b463038c760ceb55a34566',
        'info_dict': {
            'id': 'd87e8790-3e14-11eb-8ceb-ff05c2867f99',
            'ext': 'mp3',
            'title': 'Patrick Mahomes, Travis Kelce React to Win Over Dolphins | The Breakdown',
            'description': 'md5:12ada8ee70e6762658c30e223e095075',
        }
    }, {
        'url': 'https://www.buffalobills.com/video/buffalo-bills-military-recognition-week-14',
        'only_matching': True,
    }, {
        'url': 'https://www.raiders.com/audio/instant-reactions-raiders-week-14-loss-to-indianapolis-colts-espn-jason-fitz',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        return self._parse_video_config(self._search_regex(
            self._VIDEO_CONFIG_REGEX, webpage, 'video config'), display_id)


class NFLArticleIE(NFLBaseIE):
    IE_NAME = 'nfl.com:article'
    _VALID_URL = NFLBaseIE._VALID_URL_BASE + r'news/(?P<id>[^/#?&]+)'
    _TEST = {
        'url': 'https://www.buffalobills.com/news/the-only-thing-we-ve-earned-is-the-noise-bills-coaches-discuss-handling-rising-e',
        'info_dict': {
            'id': 'the-only-thing-we-ve-earned-is-the-noise-bills-coaches-discuss-handling-rising-e',
            'title': "'The only thing we've earned is the noise' | Bills coaches discuss handling rising expectations",
        },
        'playlist_count': 4,
    }

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        entries = []
        for video_config in re.findall(self._VIDEO_CONFIG_REGEX, webpage):
            entries.append(self._parse_video_config(video_config, display_id))
        title = clean_html(get_element_by_class(
            'nfl-c-article__title', webpage)) or self._html_search_meta(
            ['og:title', 'twitter:title'], webpage)
        return self.playlist_result(entries, display_id, title)
