from .common import InfoExtractor
from ..utils import parse_age_limit, parse_duration, url_or_none
from ..utils.traversal import traverse_obj


class MagellanTVIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?magellantv\.com/(?:watch|video)/(?P<id>[\w-]+)'
    _TESTS = [{
        'url': 'https://www.magellantv.com/watch/incas-the-new-story?type=v',
        'info_dict': {
            'id': 'incas-the-new-story',
            'ext': 'mp4',
            'title': 'Incas: The New Story',
            'description': 'md5:936c7f6d711c02dfb9db22a067b586fe',
            'age_limit': 14,
            'duration': 3060.0,
            'tags': ['Ancient History', 'Archaeology', 'Anthropology'],
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://www.magellantv.com/video/tortured-to-death-murdering-the-nanny',
        'info_dict': {
            'id': 'tortured-to-death-murdering-the-nanny',
            'ext': 'mp4',
            'title': 'Tortured to Death: Murdering the Nanny',
            'description': 'md5:d87033594fa218af2b1a8b49f52511e5',
            'age_limit': 14,
            'duration': 2640.0,
            'tags': ['True Crime', 'Murder'],
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://www.magellantv.com/watch/celebration-nation?type=s',
        'info_dict': {
            'id': 'celebration-nation',
            'ext': 'mp4',
            'tags': ['Art & Culture', 'Human Interest', 'Anthropology', 'China', 'History'],
            'duration': 2640.0,
            'title': 'Ancestors',
        },
        'params': {'skip_download': 'm3u8'},
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        context = self._search_nextjs_data(webpage, video_id)['props']['pageProps']['reactContext']
        data = traverse_obj(context, ((('video', 'detail'), ('series', 'currentEpisode')), {dict}, any))

        formats, subtitles = [], {}
        for m3u8_url in set(traverse_obj(data, ((('manifests', ..., 'hls'), 'jwp_video_url'), {url_or_none}))):
            fmts, subs = self._extract_m3u8_formats_and_subtitles(
                m3u8_url, video_id, 'mp4', m3u8_id='hls', fatal=False)
            formats.extend(fmts)
            self._merge_subtitles(subs, target=subtitles)
        if not formats and (error := traverse_obj(context, ('errorDetailPage', 'errorMessage', {str}))):
            if 'available in your country' in error:
                self.raise_geo_restricted(msg=error)
            self.raise_no_formats(f'{self.IE_NAME} said: {error}', expected=True)

        return {
            'id': video_id,
            'formats': formats,
            'subtitles': subtitles,
            **traverse_obj(data, {
                'title': ('title', {str}),
                'description': ('metadata', 'description', {str}),
                'duration': ('duration', {parse_duration}),
                'age_limit': ('ratingCategory', {parse_age_limit}),
                'tags': ('tags', ..., {str}),
            }),
        }
