# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    try_get,
)


class HoiChoiIE(InfoExtractor):
    _VALID_URL = r'(?:https?://)(?:www\.)?hoichoi\.tv(?P<path>(?:/[a-z]{2})?/(?:films|movies|webseries|videos|shows)/(?:title/)?(?P<id>[^/#$?&]+))'

    _TESTS = [{  # Free film with langauge code
        'url': 'https://www.hoichoi.tv/bn/films/title/shuyopoka',
        'info_dict': {
            'id': '7a7a9d33-1f4c-4771-9173-ee4fb6dbf196',
            'ext': 'mp4',
            'title': 'Shuyopoka',
            'description': 'md5:e28f2fb8680096a69c944d37c1fa5ffc',
            'thumbnail': r're:^https?://.*\.jpg$',
            'upload_date': '20211006',
            'series': None
        },
        'params': {'skip_download': True},
        'skip': 'Cookies (not necessarily logged in) are needed'
    }, {  # Free film
        'url': 'https://www.hoichoi.tv/films/title/dadu-no1',
        'info_dict': {
            'id': '0000015b-b009-d126-a1db-b81ff3780000',
            'ext': 'mp4',
            'title': 'Dadu No.1',
            'description': 'md5:605cba408e51a79dafcb824bdeded51e',
            'thumbnail': r're:^https?://.*\.jpg$',
            'upload_date': '20210827',
            'series': None
        },
        'params': {'skip_download': True},
        'skip': 'Cookies (not necessarily logged in) are needed'
    }, {  #Free episode
        'url': 'https://www.hoichoi.tv/webseries/case-jaundice-s01-e01',
        'info_dict': {
            'id': 'f779e07c-30c8-459c-8612-5a834ab5e5ba',
            'ext': 'mp4',
            'title': 'Humans Vs. Corona',
            'description': 'md5:ca30a682b4528d02a3eb6d0427dd0f87',
            'thumbnail': r're:^https?://.*\.jpg$',
            'upload_date': '20210830',
            'series': 'Case Jaundice'
        },
        'params': {'skip_download': True},
        'skip': 'Cookies (not necessarily logged in) are needed'
    }, {  # Free video
        'url': 'https://www.hoichoi.tv/videos/1549072415320-six-episode-02-hindi',
        'info_dict': {
            'id': 'b41fa1ce-aca6-47b6-b208-283ff0a2de30',
            'ext': 'mp4',
            'title': 'Woman in red - Hindi',
            'description': 'md5:9d21edc1827d32f8633eb67c2054fc31',
            'thumbnail': r're:^https?://.*\.jpg$',
            'upload_date': '20211006',
            'series': 'Six (Hindi)'
        },
        'params': {'skip_download': True},
        'skip': 'Cookies (not necessarily logged in) are needed'
    }, {  # Free episode
        'url': 'https://www.hoichoi.tv/shows/watch-asian-paints-moner-thikana-online-season-1-episode-1',
        'info_dict': {
            'id': '1f45d185-8500-455c-b88d-13252307c3eb',
            'ext': 'mp4',
            'title': 'Jisshu Sengupta',
            'description': 'md5:ef6ffae01a3d83438597367400f824ed',
            'thumbnail': r're:^https?://.*\.jpg$',
            'upload_date': '20211004',
            'series': 'Asian Paints Moner Thikana'
        },
        'params': {'skip_download': True},
        'skip': 'Cookies (not necessarily logged in) are needed'
    }, {  # Free series
        'url': 'https://www.hoichoi.tv/shows/watch-moner-thikana-bengali-web-series-online',
        'playlist_mincount': 5,
        'info_dict': {
            'id': 'watch-moner-thikana-bengali-web-series-online',
        },
    }, {  # Premium series
        'url': 'https://www.hoichoi.tv/shows/watch-byomkesh-bengali-web-series-online',
        'playlist_mincount': 14,
        'info_dict': {
            'id': 'watch-byomkesh-bengali-web-series-online',
        },
    }, {  # Premium movie
        'url': 'https://www.hoichoi.tv/movies/detective-2020',
        'only_matching': True
    }]

    def _real_extract(self, url):
        path, display_id = self._match_valid_url(url).groups()
        id, token = None, None
        content_json = self._download_json(f'https://prod-api-cached-2.viewlift.com/content/pages?path={path}&site=hoichoitv&includeContent=true', display_id)
        for module in content_json.get('modules', []):
            if module.get('moduleType') == 'VideoDetailModule':
                id = module['contentData'][0]['gist']['id']
            elif module.get('moduleType') == 'ShowDetailModule':
                entries = []
                for season in module['contentData'][0]['seasons']:
                    for episode in season.get('episodes') or []:
                        path = try_get(episode, lambda x: x['gist']['permalink'])
                        if path:
                            entries.append(self.url_result(f'https://www.hoichoi.tv{path}', ie=HoiChoiIE.ie_key()))
                return self.playlist_result(entries, display_id)

        cookies = self._get_cookies(url)
        if cookies and cookies.get('token'):
            token = self._search_regex(r'22authorizationToken\%22:\%22([^\%]+)\%22', cookies['token'].value, 'token')
        data_json = self._download_json(f'https://prod-api.viewlift.com/entitlement/video/status?id={id}', display_id,
                                        headers={'authorization': token})
        if not data_json['success']:
            raise ExtractorError(data_json['errorMessage'])
        data_json = data_json['video']
        m3u8_url = data_json['streamingInfo']['videoAssets']['hlsDetail']['url']
        formats, subtitles = self._extract_m3u8_formats_and_subtitles(m3u8_url, display_id)
        subs = {}
        for sub in try_get(data_json, lambda x: x['contentDetails']['closedCaptions']) or []:
            sub_url = sub.get('url')
            if not sub_url:
                continue
            subs.setdefault(sub.get('language', 'English'), []).append({
                'url': sub_url,
            })
        subs = self._merge_subtitles(subs, subtitles)
        self._sort_formats(formats)
        return {
            'id': id,
            'title': try_get(data_json, lambda x: x['gist']['title']),
            'description': try_get(data_json, lambda x: x['gist']['description']),
            'thumbnail': try_get(data_json, lambda x: x['gist']['videoImageUrl']),
            'timestamp': try_get(data_json, lambda x: x['gist']['updateDate']) // 1000,
            'series': try_get(data_json, lambda x: x['series'][0]['gist']['title']),
            'formats': formats,
            'subtitles': subs,
        }
