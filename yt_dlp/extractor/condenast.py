import re
import urllib.parse

from .common import InfoExtractor
from ..utils import (
    determine_ext,
    extract_attributes,
    int_or_none,
    js_to_json,
    mimetype2ext,
    orderedSet,
    parse_iso8601,
    strip_or_none,
    try_get,
)


class CondeNastIE(InfoExtractor):
    """
    Condé Nast is a media group, some of its sites use a custom HTML5 player
    that works the same in all of them.
    """

    # The keys are the supported sites and the values are the name to be shown
    # to the user and in the extractor description.
    _SITES = {
        'allure': 'Allure',
        'architecturaldigest': 'Architectural Digest',
        'arstechnica': 'Ars Technica',
        'bonappetit': 'Bon Appétit',
        'brides': 'Brides',
        'cnevids': 'Condé Nast',
        'cntraveler': 'Condé Nast Traveler',
        'details': 'Details',
        'epicurious': 'Epicurious',
        'glamour': 'Glamour',
        'golfdigest': 'Golf Digest',
        'gq': 'GQ',
        'newyorker': 'The New Yorker',
        'self': 'SELF',
        'teenvogue': 'Teen Vogue',
        'vanityfair': 'Vanity Fair',
        'vogue': 'Vogue',
        'wired': 'WIRED',
        'wmagazine': 'W Magazine',
    }

    _VALID_URL = r'''(?x)https?://(?:video|www|player(?:-backend)?)\.(?:{})\.com/
        (?:
            (?:
                embed(?:js)?|
                (?:script|inline)/video
            )/(?P<id>[0-9a-f]{{24}})(?:/(?P<player_id>[0-9a-f]{{24}}))?(?:.+?\btarget=(?P<target>[^&]+))?|
            (?P<type>watch|series|video)/(?P<display_id>[^/?#]+)
        )'''.format('|'.join(_SITES.keys()))
    IE_DESC = 'Condé Nast media group: {}'.format(', '.join(sorted(_SITES.values())))

    _EMBED_REGEX = [r'''(?x)
        <(?:iframe|script)[^>]+?src=(["\'])(?P<url>
            (?:https?:)?//player(?:-backend)?\.(?:{})\.com/(?:embed(?:js)?|(?:script|inline)/video)/.+?
        )\1'''.format('|'.join(_SITES.keys()))]

    _TESTS = [{
        'url': 'http://video.wired.com/watch/3d-printed-speakers-lit-with-led',
        'md5': '1921f713ed48aabd715691f774c451f7',
        'info_dict': {
            'id': '5171b343c2b4c00dd0c1ccb3',
            'ext': 'mp4',
            'title': '3D Printed Speakers Lit With LED',
            'description': 'Check out these beautiful 3D printed LED speakers.  You can\'t actually buy them, but LumiGeek is working on a board that will let you make you\'re own.',
            'uploader': 'wired',
            'upload_date': '20130314',
            'timestamp': 1363219200,
        },
    }, {
        'url': 'http://video.gq.com/watch/the-closer-with-keith-olbermann-the-only-true-surprise-trump-s-an-idiot?c=series',
        'info_dict': {
            'id': '58d1865bfd2e6126e2000015',
            'ext': 'mp4',
            'title': 'The Only True Surprise? Trump’s an Idiot',
            'uploader': 'gq',
            'upload_date': '20170321',
            'timestamp': 1490126427,
            'description': 'How much grimmer would things be if these people were competent?',
        },
    }, {
        # JS embed
        'url': 'http://player.cnevids.com/embedjs/55f9cf8b61646d1acf00000c/5511d76261646d5566020000.js',
        'md5': 'f1a6f9cafb7083bab74a710f65d08999',
        'info_dict': {
            'id': '55f9cf8b61646d1acf00000c',
            'ext': 'mp4',
            'title': '3D printed TSA Travel Sentry keys really do open TSA locks',
            'uploader': 'arstechnica',
            'upload_date': '20150916',
            'timestamp': 1442434920,
        },
    }, {
        'url': 'https://player.cnevids.com/inline/video/59138decb57ac36b83000005.js?target=js-cne-player',
        'only_matching': True,
    }, {
        'url': 'http://player-backend.cnevids.com/script/video/59138decb57ac36b83000005.js',
        'only_matching': True,
    }]

    def _extract_series(self, url, webpage):
        title = self._html_search_regex(
            r'(?s)<div class="cne-series-info">.*?<h1>(.+?)</h1>',
            webpage, 'series title')
        url_object = urllib.parse.urlparse(url)
        base_url = f'{url_object.scheme}://{url_object.netloc}'
        m_paths = re.finditer(
            r'(?s)<p class="cne-thumb-title">.*?<a href="(/watch/.+?)["\?]', webpage)
        paths = orderedSet(m.group(1) for m in m_paths)
        build_url = lambda path: urllib.parse.urljoin(base_url, path)
        entries = [self.url_result(build_url(path), 'CondeNast') for path in paths]
        return self.playlist_result(entries, playlist_title=title)

    def _extract_video_params(self, webpage, display_id):
        query = self._parse_json(
            self._search_regex(
                r'(?s)var\s+params\s*=\s*({.+?})[;,]', webpage, 'player params',
                default='{}'),
            display_id, transform_source=js_to_json, fatal=False)
        if query:
            query['videoId'] = self._search_regex(
                r'(?:data-video-id=|currentVideoId\s*=\s*)["\']([\da-f]+)',
                webpage, 'video id', default=None)
        else:
            params = extract_attributes(self._search_regex(
                r'(<[^>]+data-js="video-player"[^>]+>)',
                webpage, 'player params element'))
            query.update({
                'videoId': params['data-video'],
                'playerId': params['data-player'],
                'target': params['id'],
            })
        return query

    def _extract_video(self, params):
        video_id = params['videoId']

        video_info = None

        # New API path
        query = params.copy()
        query['embedType'] = 'inline'
        info_page = self._download_json(
            'http://player.cnevids.com/embed-api.json', video_id,
            'Downloading embed info', fatal=False, query=query)

        # Old fallbacks
        if not info_page:
            if params.get('playerId'):
                info_page = self._download_json(
                    'http://player.cnevids.com/player/video.js', video_id,
                    'Downloading video info', fatal=False, query=params)
        if info_page:
            video_info = info_page.get('video')
        if not video_info:
            info_page = self._download_webpage(
                'http://player.cnevids.com/player/loader.js',
                video_id, 'Downloading loader info', query=params)
        if not video_info:
            info_page = self._download_webpage(
                f'https://player.cnevids.com/inline/video/{video_id}.js',
                video_id, 'Downloading inline info', query={
                    'target': params.get('target', 'embedplayer'),
                })

        if not video_info:
            video_info = self._parse_json(
                self._search_regex(
                    r'(?s)var\s+config\s*=\s*({.+?});', info_page, 'config'),
                video_id, transform_source=js_to_json)['video']

        title = video_info['title']

        formats = []
        for fdata in video_info['sources']:
            src = fdata.get('src')
            if not src:
                continue
            ext = mimetype2ext(fdata.get('type')) or determine_ext(src)
            if ext == 'm3u8':
                formats.extend(self._extract_m3u8_formats(
                    src, video_id, 'mp4', entry_protocol='m3u8_native',
                    m3u8_id='hls', fatal=False))
                continue
            quality = fdata.get('quality')
            formats.append({
                'format_id': ext + (f'-{quality}' if quality else ''),
                'url': src,
                'ext': ext,
                'quality': 1 if quality == 'high' else 0,
            })

        subtitles = {}
        for t, caption in video_info.get('captions', {}).items():
            caption_url = caption.get('src')
            if not (t in ('vtt', 'srt', 'tml') and caption_url):
                continue
            subtitles.setdefault('en', []).append({'url': caption_url})

        return {
            'id': video_id,
            'formats': formats,
            'title': title,
            'thumbnail': video_info.get('poster_frame'),
            'uploader': video_info.get('brand'),
            'duration': int_or_none(video_info.get('duration')),
            'tags': video_info.get('tags'),
            'series': video_info.get('series_title'),
            'season': video_info.get('season_title'),
            'timestamp': parse_iso8601(video_info.get('premiere_date')),
            'categories': video_info.get('categories'),
            'subtitles': subtitles,
        }

    def _real_extract(self, url):
        video_id, player_id, target, url_type, display_id = self._match_valid_url(url).groups()

        if video_id:
            return self._extract_video({
                'videoId': video_id,
                'playerId': player_id,
                'target': target,
            })

        webpage = self._download_webpage(url, display_id)

        if url_type == 'series':
            return self._extract_series(url, webpage)
        else:
            video = try_get(self._parse_json(self._search_regex(
                r'__PRELOADED_STATE__\s*=\s*({.+?});', webpage,
                'preload state', '{}'), display_id),
                lambda x: x['transformed']['video'])
            if video:
                params = {'videoId': video['id']}
                info = {'description': strip_or_none(video.get('description'))}
            else:
                params = self._extract_video_params(webpage, display_id)
                info = self._search_json_ld(
                    webpage, display_id, fatal=False)
            info.update(self._extract_video(params))
            return info
