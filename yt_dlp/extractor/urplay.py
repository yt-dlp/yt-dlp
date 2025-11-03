from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    ISO639Utils,
    dict_get,
    int_or_none,
    parse_age_limit,
    try_get,
    unified_timestamp,
)
from ..utils.traversal import traverse_obj


class URPlayIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?ur(?:play|skola)\.se/(?:program|Produkter)/(?P<id>[0-9]+)'
    _TESTS = [{
        'url': 'https://urplay.se/program/203704-ur-samtiden-livet-universum-och-rymdens-markliga-musik-om-vetenskap-kritiskt-tankande-och-motstand',
        'md5': '5ba36643c77cc3d34ffeadad89937d1e',
        'info_dict': {
            'id': '203704',
            'ext': 'mp4',
            'title': 'UR Samtiden - Livet, universum och rymdens märkliga musik : Om vetenskap, kritiskt tänkande och motstånd',
            'description': 'md5:5344508a52aa78c1ced6c1b8b9e44e9a',
            'thumbnail': r're:^https?://.+\.jpg',
            'timestamp': 1513292400,
            'upload_date': '20171214',
            'series': 'UR Samtiden - Livet, universum och rymdens märkliga musik',
            'duration': 2269,
            'categories': ['Kultur & historia'],
            'tags': ['Kritiskt tänkande', 'Vetenskap', 'Vetenskaplig verksamhet'],
            'episode': 'Om vetenskap, kritiskt tänkande och motstånd',
            'age_limit': 15,
        },
    }, {
        'url': 'https://urplay.se/program/222967-en-foralders-dagbok-mitt-barn-skadar-sig-sjalv',
        'info_dict': {
            'id': '222967',
            'ext': 'mp4',
            'title': 'En förälders dagbok : Mitt barn skadar sig själv',
            'description': 'md5:9f771eef03a732a213b367b52fe826ca',
            'thumbnail': r're:^https?://.+\.jpg',
            'timestamp': 1629676800,
            'upload_date': '20210823',
            'series': 'En förälders dagbok',
            'duration': 1740,
            'age_limit': 15,
            'episode_number': 3,
            'categories': 'count:2',
            'tags': 'count:7',
            'episode': 'Mitt barn skadar sig själv',
        },
    }, {
        'url': 'https://urskola.se/Produkter/190031-Tripp-Trapp-Trad-Sovkudde',
        'info_dict': {
            'id': '190031',
            'ext': 'mp4',
            'title': 'Tripp, Trapp, Träd : Sovkudde',
            'description': 'md5:b86bffdae04a7e9379d1d7e5947df1d1',
            'thumbnail': r're:^https?://.+\.jpg',
            'timestamp': 1440086400,
            'upload_date': '20150820',
            'series': 'Tripp, Trapp, Träd',
            'duration': 865,
            'age_limit': 1,
            'episode_number': 1,
            'categories': [],
            'tags': ['Sova'],
            'episode': 'Sovkudde',
            'season': 'Säsong 1',
        },
    }, {
        'url': 'http://urskola.se/Produkter/155794-Smasagor-meankieli-Grodan-i-vida-varlden',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        url = url.replace('skola.se/Produkter', 'play.se/program')
        webpage = self._download_webpage(url, video_id)
        urplayer_data = self._search_nextjs_data(webpage, video_id, fatal=False) or {}
        if urplayer_data:
            urplayer_data = traverse_obj(urplayer_data, ('props', 'pageProps', 'productData', {dict}))
            if not urplayer_data:
                raise ExtractorError('Unable to parse __NEXT_DATA__')
        else:
            accessible_episodes = self._parse_json(self._html_search_regex(
                r'data-react-class="routes/Product/components/ProgramContainer/ProgramContainer"[^>]+data-react-props="({.+?})"',
                webpage, 'urplayer data'), video_id)['accessibleEpisodes']
            urplayer_data = next(e for e in accessible_episodes if e.get('id') == int_or_none(video_id))
        episode = urplayer_data['title']

        host = self._download_json('http://streaming-loadbalancer.ur.se/loadbalancer.json', video_id)['redirect']
        formats = []
        urplayer_streams = urplayer_data.get('streamingInfo', {})

        for k, v in urplayer_streams.get('raw', {}).items():
            if not (k in ('sd', 'hd', 'mp3', 'm4a') and isinstance(v, dict)):
                continue
            file_http = v.get('location')
            if file_http:
                formats.extend(self._extract_wowza_formats(
                    f'http://{host}/{file_http}playlist.m3u8',
                    video_id, skip_protocols=['f4m', 'rtmp', 'rtsp']))

        subtitles = {}

        def parse_lang_code(code):
            "3-character language code or None (utils candidate)"
            if code is None:
                return
            lang = code.lower()
            if not ISO639Utils.long2short(lang):
                lang = ISO639Utils.short2long(lang)
            return lang or None

        for stream in urplayer_data['streamingInfo'].values():
            for k, v in stream.items():
                if (k in ('sd', 'hd') or not isinstance(v, dict)):
                    continue
                lang, sttl_url = (v.get(kk) for kk in ('language', 'location'))
                if not sttl_url:
                    continue
                lang = parse_lang_code(lang)
                if not lang:
                    continue
                sttl = subtitles.get(lang) or []
                sttl.append({'ext': k, 'url': sttl_url})
                subtitles[lang] = sttl

        image = urplayer_data.get('image') or {}
        thumbnails = []
        for k, v in image.items():
            t = {
                'id': k,
                'url': v,
            }
            wh = k.split('x')
            if len(wh) == 2:
                t.update({
                    'width': int_or_none(wh[0]),
                    'height': int_or_none(wh[1]),
                })
            thumbnails.append(t)

        series = urplayer_data.get('series') or {}
        series_title = dict_get(series, ('seriesTitle', 'title')) or dict_get(urplayer_data, ('seriesTitle', 'mainTitle'))

        return {
            'id': video_id,
            'title': f'{series_title} : {episode}' if series_title else episode,
            'description': urplayer_data.get('description'),
            'thumbnails': thumbnails,
            'timestamp': unified_timestamp(urplayer_data.get('publishedAt')),
            'series': series_title,
            'formats': formats,
            'duration': int_or_none(urplayer_data.get('duration')),
            'categories': urplayer_data.get('categories'),
            'tags': urplayer_data.get('keywords'),
            'season': series.get('label'),
            'episode': episode,
            'episode_number': int_or_none(urplayer_data.get('episodeNumber')),
            'age_limit': parse_age_limit(min(try_get(a, lambda x: x['from'], int) or 0
                                             for a in urplayer_data.get('ageRanges', []))),
            'subtitles': subtitles,
        }
