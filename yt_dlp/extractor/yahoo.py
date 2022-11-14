import hashlib
import itertools
import urllib.parse

from .brightcove import BrightcoveNewIE
from .common import InfoExtractor, SearchInfoExtractor
from .youtube import YoutubeIE
from ..utils import (
    ExtractorError,
    clean_html,
    int_or_none,
    mimetype2ext,
    parse_iso8601,
    smuggle_url,
    traverse_obj,
    try_get,
    url_or_none,
)


class YahooIE(InfoExtractor):
    IE_DESC = 'Yahoo screen and movies'
    _VALID_URL = r'(?P<url>https?://(?:(?P<country>[a-zA-Z]{2}(?:-[a-zA-Z]{2})?|malaysia)\.)?(?:[\da-zA-Z_-]+\.)?yahoo\.com/(?:[^/]+/)*(?P<id>[^?&#]*-[0-9]+(?:-[a-z]+)?)\.html)'
    _EMBED_REGEX = [r'<iframe[^>]+?src=(["\'])(?P<url>https?://(?:screen|movies)\.yahoo\.com/.+?\.html\?format=embed)\1']

    _TESTS = [{
        'url': 'http://screen.yahoo.com/julian-smith-travis-legg-watch-214727115.html',
        'info_dict': {
            'id': '2d25e626-2378-391f-ada0-ddaf1417e588',
            'ext': 'mp4',
            'title': 'Julian Smith & Travis Legg Watch Julian Smith',
            'description': 'Julian and Travis watch Julian Smith',
            'duration': 6863,
            'timestamp': 1369812016,
            'upload_date': '20130529',
        },
        'skip': 'No longer exists',
    }, {
        'url': 'https://screen.yahoo.com/community/community-sizzle-reel-203225340.html?format=embed',
        'md5': '7993e572fac98e044588d0b5260f4352',
        'info_dict': {
            'id': '4fe78544-8d48-39d8-97cd-13f205d9fcdb',
            'ext': 'mp4',
            'title': "Yahoo Saves 'Community'",
            'description': 'md5:4d4145af2fd3de00cbb6c1d664105053',
            'duration': 170,
            'timestamp': 1406838636,
            'upload_date': '20140731',
        },
        'skip': 'Unfortunately, this video is not available in your region',
    }, {
        'url': 'https://uk.screen.yahoo.com/editor-picks/cute-raccoon-freed-drain-using-091756545.html',
        'md5': '71298482f7c64cbb7fa064e4553ff1c1',
        'info_dict': {
            'id': 'b3affa53-2e14-3590-852b-0e0db6cd1a58',
            'ext': 'webm',
            'title': 'Cute Raccoon Freed From Drain\u00a0Using Angle Grinder',
            'description': 'md5:f66c890e1490f4910a9953c941dee944',
            'duration': 97,
            'timestamp': 1414489862,
            'upload_date': '20141028',
        },
        'skip': 'No longer exists',
    }, {
        'url': 'http://news.yahoo.com/video/china-moses-crazy-blues-104538833.html',
        'md5': '88e209b417f173d86186bef6e4d1f160',
        'info_dict': {
            'id': 'f885cf7f-43d4-3450-9fac-46ac30ece521',
            'ext': 'mp4',
            'title': 'China Moses Is Crazy About the Blues',
            'description': 'md5:9900ab8cd5808175c7b3fe55b979bed0',
            'duration': 128,
            'timestamp': 1385722202,
            'upload_date': '20131129',
        }
    }, {
        'url': 'https://www.yahoo.com/movies/v/true-story-trailer-173000497.html',
        'md5': '2a9752f74cb898af5d1083ea9f661b58',
        'info_dict': {
            'id': '071c4013-ce30-3a93-a5b2-e0413cd4a9d1',
            'ext': 'mp4',
            'title': '\'True Story\' Trailer',
            'description': 'True Story',
            'duration': 150,
            'timestamp': 1418919206,
            'upload_date': '20141218',
        },
    }, {
        'url': 'https://gma.yahoo.com/pizza-delivery-man-surprised-huge-tip-college-kids-195200785.html',
        'only_matching': True,
    }, {
        'note': 'NBC Sports embeds',
        'url': 'http://sports.yahoo.com/blogs/ncaab-the-dagger/tyler-kalinoski-s-buzzer-beater-caps-davidson-s-comeback-win-185609842.html?guid=nbc_cbk_davidsonbuzzerbeater_150313',
        'info_dict': {
            'id': '9CsDKds0kvHI',
            'ext': 'flv',
            'description': 'md5:df390f70a9ba7c95ff1daace988f0d8d',
            'title': 'Tyler Kalinoski hits buzzer-beater to lift Davidson',
            'upload_date': '20150313',
            'uploader': 'NBCU-SPORTS',
            'timestamp': 1426270238,
        },
    }, {
        'url': 'https://tw.news.yahoo.com/-100120367.html',
        'only_matching': True,
    }, {
        # Query result is embedded in webpage, but explicit request to video API fails with geo restriction
        'url': 'https://screen.yahoo.com/community/communitary-community-episode-1-ladders-154501237.html',
        'md5': '4fbafb9c9b6f07aa8f870629f6671b35',
        'info_dict': {
            'id': '1f32853c-a271-3eef-8cb6-f6d6872cb504',
            'ext': 'mp4',
            'title': 'Communitary - Community Episode 1: Ladders',
            'description': 'md5:8fc39608213295748e1e289807838c97',
            'duration': 1646,
            'timestamp': 1440436550,
            'upload_date': '20150824',
            'series': 'Communitary',
            'season_number': 6,
            'episode_number': 1,
        },
        'skip': 'No longer exists',
    }, {
        # ytwnews://cavideo/
        'url': 'https://tw.video.yahoo.com/movie-tw/單車天使-中文版預-092316541.html',
        'info_dict': {
            'id': 'ba133ff2-0793-3510-b636-59dfe9ff6cff',
            'ext': 'mp4',
            'title': '單車天使 - 中文版預',
            'description': '中文版預',
            'timestamp': 1476696196,
            'upload_date': '20161017',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        # Contains both a Yahoo hosted video and multiple Youtube embeds
        'url': 'https://www.yahoo.com/entertainment/gwen-stefani-reveals-the-pop-hit-she-passed-on-assigns-it-to-her-voice-contestant-instead-033045672.html',
        'info_dict': {
            'id': '46c5d95a-528f-3d03-b732-732fcadd51de',
            'title': 'Gwen Stefani reveals the pop hit she passed on, assigns it to her \'Voice\' contestant instead',
            'description': 'Gwen decided not to record this hit herself, but she decided it was the perfect fit for Kyndall Inskeep.',
        },
        'playlist': [{
            'info_dict': {
                'id': '966d4262-4fd1-3aaa-b45b-049ca6e38ba6',
                'ext': 'mp4',
                'title': 'Gwen Stefani reveals she turned down one of Sia\'s best songs',
                'description': 'On "The Voice" Tuesday, Gwen Stefani told Taylor Swift which Sia hit was almost hers.',
                'timestamp': 1572406500,
                'upload_date': '20191030',
            },
        }, {
            'info_dict': {
                'id': '352CFDOQrKg',
                'ext': 'mp4',
                'title': 'Kyndal Inskeep "Performs the Hell Out of" Sia\'s "Elastic Heart" - The Voice Knockouts 2019',
                'description': 'md5:7fe8e3d5806f96002e55f190d1d94479',
                'uploader': 'The Voice',
                'uploader_id': 'NBCTheVoice',
                'upload_date': '20191029',
            },
        }],
        'params': {
            'playlistend': 2,
        },
        'expected_warnings': ['HTTP Error 404', 'Ignoring subtitle tracks'],
    }, {
        'url': 'https://malaysia.news.yahoo.com/video/bystanders-help-ontario-policeman-bust-190932818.html',
        'only_matching': True,
    }, {
        'url': 'https://es-us.noticias.yahoo.com/es-la-puerta-irrompible-que-110539379.html',
        'only_matching': True,
    }, {
        'url': 'https://www.yahoo.com/entertainment/v/longtime-cbs-news-60-minutes-032036500-cbs.html',
        'only_matching': True,
    }]

    def _extract_yahoo_video(self, video_id, country):
        video = self._download_json(
            'https://%s.yahoo.com/_td/api/resource/VideoService.videos;view=full;video_ids=["%s"]' % (country, video_id),
            video_id, 'Downloading video JSON metadata')[0]
        title = video['title']

        if country == 'malaysia':
            country = 'my'

        is_live = video.get('live_state') == 'live'
        fmts = ('m3u8',) if is_live else ('webm', 'mp4')

        urls = []
        formats = []
        subtitles = {}
        for fmt in fmts:
            media_obj = self._download_json(
                'https://video-api.yql.yahoo.com/v1/video/sapi/streams/' + video_id,
                video_id, 'Downloading %s JSON metadata' % fmt,
                headers=self.geo_verification_headers(), query={
                    'format': fmt,
                    'region': country.upper(),
                })['query']['results']['mediaObj'][0]
            msg = media_obj.get('status', {}).get('msg')

            for s in media_obj.get('streams', []):
                host = s.get('host')
                path = s.get('path')
                if not host or not path:
                    continue
                s_url = host + path
                if s.get('format') == 'm3u8':
                    formats.extend(self._extract_m3u8_formats(
                        s_url, video_id, 'mp4', m3u8_id='hls', fatal=False))
                    continue
                tbr = int_or_none(s.get('bitrate'))
                formats.append({
                    'url': s_url,
                    'format_id': fmt + ('-%d' % tbr if tbr else ''),
                    'width': int_or_none(s.get('width')),
                    'height': int_or_none(s.get('height')),
                    'tbr': tbr,
                    'fps': int_or_none(s.get('framerate')),
                })

            for cc in media_obj.get('closedcaptions', []):
                cc_url = cc.get('url')
                if not cc_url or cc_url in urls:
                    continue
                urls.append(cc_url)
                subtitles.setdefault(cc.get('lang') or 'en-US', []).append({
                    'url': cc_url,
                    'ext': mimetype2ext(cc.get('content_type')),
                })

        streaming_url = video.get('streaming_url')
        if streaming_url and not is_live:
            formats.extend(self._extract_m3u8_formats(
                streaming_url, video_id, 'mp4',
                'm3u8_native', m3u8_id='hls', fatal=False))

        if not formats and msg == 'geo restricted':
            self.raise_geo_restricted(metadata_available=True)

        self._sort_formats(formats)

        thumbnails = []
        for thumb in video.get('thumbnails', []):
            thumb_url = thumb.get('url')
            if not thumb_url:
                continue
            thumbnails.append({
                'id': thumb.get('tag'),
                'url': thumb.get('url'),
                'width': int_or_none(thumb.get('width')),
                'height': int_or_none(thumb.get('height')),
            })

        series_info = video.get('series_info') or {}

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
            'thumbnails': thumbnails,
            'description': clean_html(video.get('description')),
            'timestamp': parse_iso8601(video.get('publish_time')),
            'subtitles': subtitles,
            'duration': int_or_none(video.get('duration')),
            'view_count': int_or_none(video.get('view_count')),
            'is_live': is_live,
            'series': video.get('show_name'),
            'season_number': int_or_none(series_info.get('season_number')),
            'episode_number': int_or_none(series_info.get('episode_number')),
        }

    def _real_extract(self, url):
        url, country, display_id = self._match_valid_url(url).groups()
        if not country:
            country = 'us'
        else:
            country = country.split('-')[0]

        items = self._download_json(
            'https://%s.yahoo.com/caas/content/article' % country, display_id,
            'Downloading content JSON metadata', query={
                'url': url
            })['items'][0]

        item = items['data']['partnerData']
        if item.get('type') != 'video':
            entries = []

            cover = item.get('cover') or {}
            if cover.get('type') == 'yvideo':
                cover_url = cover.get('url')
                if cover_url:
                    entries.append(self.url_result(
                        cover_url, 'Yahoo', cover.get('uuid')))

            for e in (item.get('body') or []):
                if e.get('type') == 'videoIframe':
                    iframe_url = e.get('url')
                    if iframe_url:
                        entries.append(self.url_result(iframe_url))

            if item.get('type') == 'storywithleadvideo':
                iframe_url = try_get(item, lambda x: x['meta']['player']['url'])
                if iframe_url:
                    entries.append(self.url_result(iframe_url))
                else:
                    self.report_warning("Yahoo didn't provide an iframe url for this storywithleadvideo")

            if items.get('markup'):
                entries.extend(
                    self.url_result(yt_url) for yt_url in YoutubeIE._extract_embed_urls(url, items['markup']))

            return self.playlist_result(
                entries, item.get('uuid'),
                item.get('title'), item.get('summary'))

        info = self._extract_yahoo_video(item['uuid'], country)
        info['display_id'] = display_id
        return info


class YahooSearchIE(SearchInfoExtractor):
    IE_DESC = 'Yahoo screen search'
    _MAX_RESULTS = 1000
    IE_NAME = 'screen.yahoo:search'
    _SEARCH_KEY = 'yvsearch'

    def _search_results(self, query):
        for pagenum in itertools.count(0):
            result_url = 'http://video.search.yahoo.com/search/?p=%s&fr=screen&o=js&gs=0&b=%d' % (urllib.parse.quote_plus(query), pagenum * 30)
            info = self._download_json(result_url, query,
                                       note='Downloading results page ' + str(pagenum + 1))
            yield from (self.url_result(result['rurl']) for result in info['results'])
            if info['m']['last'] >= info['m']['total'] - 1:
                break


class YahooGyaOPlayerIE(InfoExtractor):
    IE_NAME = 'yahoo:gyao:player'
    _VALID_URL = r'https?://(?:gyao\.yahoo\.co\.jp/(?:player|episode(?:/[^/]+)?)|streaming\.yahoo\.co\.jp/c/y)/(?P<id>\d+/v\d+/v\d+|[\da-f]{8}-[\da-f]{4}-[\da-f]{4}-[\da-f]{4}-[\da-f]{12})'
    _TESTS = [{
        'url': 'https://gyao.yahoo.co.jp/player/00998/v00818/v0000000000000008564/',
        'info_dict': {
            'id': '5993125228001',
            'ext': 'mp4',
            'title': 'フューリー　【字幕版】',
            'description': 'md5:21e691c798a15330eda4db17a8fe45a5',
            'uploader_id': '4235717419001',
            'upload_date': '20190124',
            'timestamp': 1548294365,
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
    }, {
        'url': 'https://streaming.yahoo.co.jp/c/y/01034/v00133/v0000000000000000706/',
        'only_matching': True,
    }, {
        'url': 'https://gyao.yahoo.co.jp/episode/%E3%81%8D%E3%81%AE%E3%81%86%E4%BD%95%E9%A3%9F%E3%81%B9%E3%81%9F%EF%BC%9F%20%E7%AC%AC2%E8%A9%B1%202019%2F4%2F12%E6%94%BE%E9%80%81%E5%88%86/5cb02352-b725-409e-9f8d-88f947a9f682',
        'only_matching': True,
    }, {
        'url': 'https://gyao.yahoo.co.jp/episode/5fa1226c-ef8d-4e93-af7a-fd92f4e30597',
        'only_matching': True,
    }]
    _GEO_BYPASS = False

    def _real_extract(self, url):
        video_id = self._match_id(url).replace('/', ':')
        headers = self.geo_verification_headers()
        headers['Accept'] = 'application/json'
        resp = self._download_json(
            'https://gyao.yahoo.co.jp/apis/playback/graphql', video_id, query={
                'appId': 'dj00aiZpPUNJeDh2cU1RazU3UCZzPWNvbnN1bWVyc2VjcmV0Jng9NTk-',
                'query': '''{
  content(parameter: {contentId: "%s", logicaAgent: PC_WEB}) {
    video {
      delivery {
        id
      }
      title
    }
  }
}''' % video_id,
            }, headers=headers)
        content = resp['data']['content']
        if not content:
            msg = resp['errors'][0]['message']
            if msg == 'not in japan':
                self.raise_geo_restricted(countries=['JP'])
            raise ExtractorError(msg)
        video = content['video']
        return {
            '_type': 'url_transparent',
            'id': video_id,
            'title': video['title'],
            'url': smuggle_url(
                'http://players.brightcove.net/4235717419001/SyG5P0gjb_default/index.html?videoId=' + video['delivery']['id'],
                {'geo_countries': ['JP']}),
            'ie_key': BrightcoveNewIE.ie_key(),
        }


class YahooGyaOIE(InfoExtractor):
    IE_NAME = 'yahoo:gyao'
    _VALID_URL = r'https?://(?:gyao\.yahoo\.co\.jp/(?:p|title(?:/[^/]+)?)|streaming\.yahoo\.co\.jp/p/y)/(?P<id>\d+/v\d+|[\da-f]{8}-[\da-f]{4}-[\da-f]{4}-[\da-f]{4}-[\da-f]{12})'
    _TESTS = [{
        'url': 'https://gyao.yahoo.co.jp/title/%E3%82%BF%E3%82%A4%E3%83%A0%E3%83%9C%E3%82%AB%E3%83%B3%E3%82%B7%E3%83%AA%E3%83%BC%E3%82%BA%20%E3%83%A4%E3%83%83%E3%82%BF%E3%83%BC%E3%83%9E%E3%83%B3/5f60ceb3-6e5e-40ef-ba40-d68b598d067f',
        'info_dict': {
            'id': '5f60ceb3-6e5e-40ef-ba40-d68b598d067f',
        },
        'playlist_mincount': 80,
    }, {
        'url': 'https://gyao.yahoo.co.jp/p/00449/v03102/',
        'only_matching': True,
    }, {
        'url': 'https://streaming.yahoo.co.jp/p/y/01034/v00133/',
        'only_matching': True,
    }, {
        'url': 'https://gyao.yahoo.co.jp/title/%E3%81%97%E3%82%83%E3%81%B9%E3%81%8F%E3%82%8A007/5b025a49-b2e5-4dc7-945c-09c6634afacf',
        'only_matching': True,
    }, {
        'url': 'https://gyao.yahoo.co.jp/title/5b025a49-b2e5-4dc7-945c-09c6634afacf',
        'only_matching': True,
    }]

    def _entries(self, program_id):
        page = 1
        while True:
            playlist = self._download_json(
                f'https://gyao.yahoo.co.jp/api/programs/{program_id}/videos?page={page}&serviceId=gy', program_id,
                note=f'Downloading JSON metadata page {page}')
            if not playlist:
                break
            for video in playlist['videos']:
                video_id = video.get('id')
                if not video_id:
                    continue
                if video.get('streamingAvailability') == 'notYet':
                    continue
                yield self.url_result(
                    'https://gyao.yahoo.co.jp/player/%s/' % video_id.replace(':', '/'),
                    YahooGyaOPlayerIE.ie_key(), video_id)
            if playlist.get('ended'):
                break
            page += 1

    def _real_extract(self, url):
        program_id = self._match_id(url).replace('/', ':')
        return self.playlist_result(self._entries(program_id), program_id)


class YahooJapanNewsIE(InfoExtractor):
    IE_NAME = 'yahoo:japannews'
    IE_DESC = 'Yahoo! Japan News'
    _VALID_URL = r'https?://news\.yahoo\.co\.jp/(?:articles|feature)/(?P<id>[a-zA-Z0-9]+)'
    _GEO_COUNTRIES = ['JP']
    _TESTS = [{
        'url': 'https://news.yahoo.co.jp/articles/a70fe3a064f1cfec937e2252c7fc6c1ba3201c0e',
        'info_dict': {
            'id': 'a70fe3a064f1cfec937e2252c7fc6c1ba3201c0e',
            'ext': 'mp4',
            'title': '【独自】安倍元総理「国葬」中止求め“脅迫メール”…「子ども誘拐」“送信者”を追跡',
            'description': 'md5:1c06974575f930f692d8696fbcfdc546',
            'thumbnail': r're:https://.+',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'https://news.yahoo.co.jp/feature/1356',
        'only_matching': True
    }]

    def _extract_formats(self, json_data, content_id):
        formats = []

        for vid in traverse_obj(json_data, ('ResultSet', 'Result', ..., 'VideoUrlSet', 'VideoUrl', ...)) or []:
            delivery = vid.get('delivery')
            url = url_or_none(vid.get('Url'))
            if not delivery or not url:
                continue
            elif delivery == 'hls':
                formats.extend(
                    self._extract_m3u8_formats(
                        url, content_id, 'mp4', 'm3u8_native',
                        m3u8_id='hls', fatal=False))
            else:
                formats.append({
                    'url': url,
                    'format_id': f'http-{vid.get("bitrate")}',
                    'height': int_or_none(vid.get('height')),
                    'width': int_or_none(vid.get('width')),
                    'tbr': int_or_none(vid.get('bitrate')),
                })
        self._remove_duplicate_formats(formats)
        self._sort_formats(formats)

        return formats

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        preloaded_state = self._search_json(r'__PRELOADED_STATE__\s*=', webpage, 'preloaded state', video_id)

        content_id = traverse_obj(
            preloaded_state, ('articleDetail', 'paragraphs', ..., 'objectItems', ..., 'video', 'vid'),
            get_all=False, expected_type=int)
        if content_id is None:
            raise ExtractorError('This article does not contain a video', expected=True)

        HOST = 'news.yahoo.co.jp'
        space_id = traverse_obj(preloaded_state, ('pageData', 'spaceId'), expected_type=str)
        json_data = self._download_json(
            f'https://feapi-yvpub.yahooapis.jp/v1/content/{content_id}',
            video_id, query={
                'appid': 'dj0zaiZpPVZMTVFJR0FwZWpiMyZzPWNvbnN1bWVyc2VjcmV0Jng9YjU-',
                'output': 'json',
                'domain': HOST,
                'ak': hashlib.md5('_'.join((space_id, HOST)).encode()).hexdigest() if space_id else '',
                'device_type': '1100',
            })

        title = (
            traverse_obj(preloaded_state,
                         ('articleDetail', 'headline'), ('pageData', 'pageParam', 'title'),
                         expected_type=str)
            or self._html_search_meta(('og:title', 'twitter:title'), webpage, 'title', default=None)
            or self._html_extract_title(webpage))
        description = (
            traverse_obj(preloaded_state, ('pageData', 'description'), expected_type=str)
            or self._html_search_meta(
                ('og:description', 'description', 'twitter:description'),
                webpage, 'description', default=None))
        thumbnail = (
            traverse_obj(preloaded_state, ('pageData', 'ogpImage'), expected_type=str)
            or self._og_search_thumbnail(webpage, default=None)
            or self._html_search_meta('twitter:image', webpage, 'thumbnail', default=None))

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'formats': self._extract_formats(json_data, video_id),
        }
