from .common import InfoExtractor
from ..utils import (
    format_field,
    int_or_none,
    unified_strdate,
)


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
            'episode': 'Episode 13431',
        },
        'params': {'skip_download': True},
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
            'episode': 'Episode 1036',
        },
        'params': {'skip_download': True},
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
            'episode': 'Episode 16',
        },
        'params': {'skip_download': True},
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        video_json = self._download_json(f'https://lnk.lt/api/video/video-config/{video_id}', video_id)['videoInfo']
        formats, subtitles = [], {}
        if video_json.get('videoUrl'):
            fmts, subs = self._extract_m3u8_formats_and_subtitles(video_json['videoUrl'], video_id)
            formats.extend(fmts)
            subtitles = self._merge_subtitles(subtitles, subs)
        if video_json.get('videoFairplayUrl') and not video_json.get('drm'):
            fmts, subs = self._extract_m3u8_formats_and_subtitles(video_json['videoFairplayUrl'], video_id)
            formats.extend(fmts)
            subtitles = self._merge_subtitles(subtitles, subs)

        return {
            'id': video_id,
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
