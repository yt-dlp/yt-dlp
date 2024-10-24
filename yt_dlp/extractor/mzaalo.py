from .common import InfoExtractor
from ..utils import (
    parse_age_limit,
    parse_duration,
    traverse_obj,
    url_or_none,
)


class MzaaloIE(InfoExtractor):
    _VALID_URL = r'(?i)https?://(?:www\.)?mzaalo\.com/(?:play|watch)/(?P<type>movie|original|clip)/(?P<id>[a-f0-9-]+)/[\w-]+'
    _TESTS = [{
        # Movies
        'url': 'https://www.mzaalo.com/play/movie/c0958d9f-f90e-4503-a755-44358758921d/Jamun',
        'info_dict': {
            'id': 'c0958d9f-f90e-4503-a755-44358758921d',
            'title': 'Jamun',
            'ext': 'mp4',
            'description': 'md5:24fe9ebb9bbe5b36f7b54b90ab1e2f31',
            'thumbnails': 'count:15',
            'thumbnail': r're:^https?://.*\.jpg$',
            'duration': 5527.0,
            'language': 'hin',
            'categories': ['Drama'],
            'age_limit': 13,
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        # Shows
        'url': 'https://www.mzaalo.com/play/original/93d42b2b-f373-4c2d-bca4-997412cb069d/Modi-Season-2-CM-TO-PM/Episode-1:Decision,-Not-Promises',
        'info_dict': {
            'id': '93d42b2b-f373-4c2d-bca4-997412cb069d',
            'title': 'Episode 1:Decision, Not Promises',
            'ext': 'mp4',
            'description': 'md5:16f76058432a54774fbb2561a1955652',
            'thumbnails': 'count:22',
            'thumbnail': r're:^https?://.*\.jpg$',
            'duration': 2040.0,
            'language': 'hin',
            'categories': ['Drama'],
            'age_limit': 13,
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        # Streams/Clips
        'url': 'https://www.mzaalo.com/play/clip/83cdbcb5-400a-42f1-a1d2-459053cfbda5/Manto-Ki-Kahaaniya',
        'info_dict': {
            'id': '83cdbcb5-400a-42f1-a1d2-459053cfbda5',
            'title': 'Manto Ki Kahaaniya',
            'ext': 'mp4',
            'description': 'md5:c3c5f1d05f0fd1bfcb05b673d1cc9f2f',
            'thumbnails': 'count:3',
            'thumbnail': r're:^https?://.*\.jpg$',
            'duration': 1937.0,
            'language': 'hin',
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://mzaalo.com/watch/MOVIE/389c892d-0b65-4019-bf73-d4edcb1c014f/Chalo-Dilli',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id, type_ = self._match_valid_url(url).group('id', 'type')
        path = (f'partner/streamurl?&assetId={video_id}&getClipDetails=YES' if type_ == 'clip'
                else f'api/v2/player/details?assetType={type_.upper()}&assetId={video_id}')
        data = self._download_json(
            f'https://production.mzaalo.com/platform/{path}', video_id, headers={
                'Ocp-Apim-Subscription-Key': '1d0caac2702049b89a305929fdf4cbae',
            })['data']

        formats = self._extract_m3u8_formats(data['streamURL'], video_id)

        subtitles = {}
        for subs_lang, subs_url in traverse_obj(data, ('subtitles', {dict.items}, ...)):
            if url_or_none(subs_url):
                subtitles[subs_lang] = [{'url': subs_url, 'ext': 'vtt'}]

        lang = traverse_obj(data, ('language', {str.lower}))
        for f in formats:
            f['language'] = lang

        return {
            'id': video_id,
            'formats': formats,
            'subtitles': subtitles,
            **traverse_obj(data, {
                'title': ('title', {str}),
                'description': ('description', {str}),
                'duration': ('duration', {parse_duration}),
                'age_limit': ('maturity_rating', {parse_age_limit}),
                'thumbnails': ('images', ..., {'url': {url_or_none}}),
                'categories': ('genre', ..., {str}),
            }),
        }
