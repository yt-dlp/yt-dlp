from .common import InfoExtractor
from ..utils import (
    clean_html,
    compat_str,
    format_field,
    int_or_none,
    parse_iso8601,
    unified_strdate,
)


class LnkGoIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?lnk(?:go)?\.(?:alfa\.)?lt/(?:visi-video/[^/]+|video)/(?P<id>[A-Za-z0-9-]+)(?:/(?P<episode_id>\d+))?'
    _TESTS = [{
        'url': 'http://www.lnkgo.lt/visi-video/aktualai-pratesimas/ziurek-putka-trys-klausimai',
        'info_dict': {
            'id': '10809',
            'ext': 'mp4',
            'title': "Put'ka: Trys Klausimai",
            'upload_date': '20161216',
            'description': 'Seniai matytas Put’ka užduoda tris klausimėlius. Pabandykime surasti atsakymus.',
            'age_limit': 18,
            'duration': 117,
            'thumbnail': r're:^https?://.*\.jpg$',
            'timestamp': 1481904000,
        },
        'params': {
            'skip_download': True,  # HLS download
        },
    }, {
        'url': 'http://lnkgo.alfa.lt/visi-video/aktualai-pratesimas/ziurek-nerdas-taiso-kompiuteri-2',
        'info_dict': {
            'id': '10467',
            'ext': 'mp4',
            'title': 'Nėrdas: Kompiuterio Valymas',
            'upload_date': '20150113',
            'description': 'md5:7352d113a242a808676ff17e69db6a69',
            'age_limit': 18,
            'duration': 346,
            'thumbnail': r're:^https?://.*\.jpg$',
            'timestamp': 1421164800,
        },
        'params': {
            'skip_download': True,  # HLS download
        },
    }, {
        'url': 'https://lnk.lt/video/neigalieji-tv-bokste/37413',
        'only_matching': True,
    }]
    _AGE_LIMITS = {
        'N-7': 7,
        'N-14': 14,
        'S': 18,
    }
    _M3U8_TEMPL = 'https://vod.lnk.lt/lnk_vod/lnk/lnk/%s:%s/playlist.m3u8%s'

    def _real_extract(self, url):
        display_id, video_id = self._match_valid_url(url).groups()

        video_info = self._download_json(
            'https://lnk.lt/api/main/video-page/%s/%s/false' % (display_id, video_id or '0'),
            display_id)['videoConfig']['videoInfo']

        video_id = compat_str(video_info['id'])
        title = video_info['title']
        prefix = 'smil' if video_info.get('isQualityChangeAvailable') else 'mp4'
        formats = self._extract_m3u8_formats(
            self._M3U8_TEMPL % (prefix, video_info['videoUrl'], video_info.get('secureTokenParams') or ''),
            video_id, 'mp4', 'm3u8_native')
        self._sort_formats(formats)

        return {
            'id': video_id,
            'display_id': display_id,
            'title': title,
            'formats': formats,
            'thumbnail': format_field(video_info, 'posterImage', 'https://lnk.lt/all-images/%s'),
            'duration': int_or_none(video_info.get('duration')),
            'description': clean_html(video_info.get('htmlDescription')),
            'age_limit': self._AGE_LIMITS.get(video_info.get('pgRating'), 0),
            'timestamp': parse_iso8601(video_info.get('airDate')),
            'view_count': int_or_none(video_info.get('viewsCount')),
        }


class LnkIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?lnk\.lt/[^/]+/(?P<id>\d+)'

    _TESTS = [{
        'url': 'https://lnk.lt/zinios/79791',
        'info_dict': {
            'id': '79791',
            'ext': 'mp4',
            'title': 'LNK.lt: Viešintų gyventojai sukilo prieš radijo bangų siųstuvą',
            'description': 'Svarbiausios naujienos trumpai, LNK žinios ir Info dienos pokalbiai.',
            'view_count': int,
            'duration': 233,
            'upload_date': '20191123',
            'thumbnail': r're:^https?://.*\.jpg$',
            'episode_number': 13431,
            'series': 'Naujausi žinių reportažai',
            'episode': 'Episode 13431'
        },
        'params': {'skip_download': True}
    }, {
        'url': 'https://lnk.lt/istorijos-trumpai/152546',
        'info_dict': {
            'id': '152546',
            'ext': 'mp4',
            'title': 'Radžio koncertas gaisre ',
            'description': 'md5:0666b5b85cb9fc7c1238dec96f71faba',
            'view_count': int,
            'duration': 54,
            'upload_date': '20220105',
            'thumbnail': r're:^https?://.*\.jpg$',
            'episode_number': 1036,
            'series': 'Istorijos trumpai',
            'episode': 'Episode 1036'
        },
        'params': {'skip_download': True}
    }, {
        'url': 'https://lnk.lt/gyvunu-pasaulis/151549',
        'info_dict': {
            'id': '151549',
            'ext': 'mp4',
            'title': 'Gyvūnų pasaulis',
            'description': '',
            'view_count': int,
            'duration': 1264,
            'upload_date': '20220108',
            'thumbnail': r're:^https?://.*\.jpg$',
            'episode_number': 16,
            'series': 'Gyvūnų pasaulis',
            'episode': 'Episode 16'
        },
        'params': {'skip_download': True}
    }]

    def _real_extract(self, url):
        id = self._match_id(url)
        video_json = self._download_json(f'https://lnk.lt/api/video/video-config/{id}', id)['videoInfo']
        formats, subtitles = [], {}
        if video_json.get('videoUrl'):
            fmts, subs = self._extract_m3u8_formats_and_subtitles(video_json['videoUrl'], id)
            formats.extend(fmts)
            subtitles = self._merge_subtitles(subtitles, subs)
        if video_json.get('videoFairplayUrl') and not video_json.get('drm'):
            fmts, subs = self._extract_m3u8_formats_and_subtitles(video_json['videoFairplayUrl'], id)
            formats.extend(fmts)
            subtitles = self._merge_subtitles(subtitles, subs)

        self._sort_formats(formats)
        return {
            'id': id,
            'title': video_json.get('title'),
            'description': video_json.get('description'),
            'view_count': video_json.get('viewsCount'),
            'duration': video_json.get('duration'),
            'upload_date': unified_strdate(video_json.get('airDate')),
            'thumbnail': format_field(video_json, 'posterImage', 'https://lnk.lt/all-images/%s'),
            'episode_number': int_or_none(video_json.get('episodeNumber')),
            'series': video_json.get('programTitle'),
            'formats': formats,
            'subtitles': subtitles,
        }
