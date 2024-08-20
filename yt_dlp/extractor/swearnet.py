from .common import InfoExtractor
from ..utils import ExtractorError, int_or_none, traverse_obj


class SwearnetEpisodeIE(InfoExtractor):
    _VALID_URL = r'https?://www\.swearnet\.com/shows/(?P<id>[\w-]+)/seasons/(?P<season_num>\d+)/episodes/(?P<episode_num>\d+)'
    _TESTS = [{
        'url': 'https://www.swearnet.com/shows/gettin-learnt-with-ricky/seasons/1/episodes/1',
        'info_dict': {
            'id': '232819',
            'ext': 'mp4',
            'episode_number': 1,
            'episode': 'Episode 1',
            'duration': 719,
            'description': 'md5:c48ef71440ce466284c07085cd7bd761',
            'season': 'Season 1',
            'title': 'Episode 1 - Grilled Cheese Sammich',
            'season_number': 1,
            'thumbnail': 'https://cdn.vidyard.com/thumbnails/232819/_RX04IKIq60a2V6rIRqq_Q_small.jpg',
        },
    }]

    def _get_formats_and_subtitle(self, video_source, video_id):
        video_source = video_source or {}
        formats, subtitles = [], {}
        for key, value in video_source.items():
            if key == 'hls':
                for video_hls in value:
                    fmts, subs = self._extract_m3u8_formats_and_subtitles(video_hls.get('url'), video_id)
                    formats.extend(fmts)
                    self._merge_subtitles(subs, target=subtitles)
            else:
                formats.extend({
                    'url': video_mp4.get('url'),
                    'ext': 'mp4',
                } for video_mp4 in value)

        return formats, subtitles

    def _get_direct_subtitle(self, caption_json):
        subs = {}
        for caption in caption_json:
            subs.setdefault(caption.get('language') or 'und', []).append({
                'url': caption.get('vttUrl'),
                'name': caption.get('name'),
            })

        return subs

    def _real_extract(self, url):
        display_id, season_number, episode_number = self._match_valid_url(url).group('id', 'season_num', 'episode_num')
        webpage = self._download_webpage(url, display_id)

        try:
            external_id = self._search_regex(r'externalid\s*=\s*"([^"]+)', webpage, 'externalid')
        except ExtractorError:
            if 'Upgrade Now' in webpage:
                self.raise_login_required()
            raise

        json_data = self._download_json(
            f'https://play.vidyard.com/player/{external_id}.json', display_id)['payload']['chapters'][0]

        formats, subtitles = self._get_formats_and_subtitle(json_data['sources'], display_id)
        self._merge_subtitles(self._get_direct_subtitle(json_data.get('captions')), target=subtitles)

        return {
            'id': str(json_data['videoId']),
            'title': json_data.get('name') or self._html_search_meta(['og:title', 'twitter:title'], webpage),
            'description': (json_data.get('description')
                            or self._html_search_meta(['og:description', 'twitter:description'], webpage)),
            'duration': int_or_none(json_data.get('seconds')),
            'formats': formats,
            'subtitles': subtitles,
            'season_number': int_or_none(season_number),
            'episode_number': int_or_none(episode_number),
            'thumbnails': [{'url': thumbnail_url}
                           for thumbnail_url in traverse_obj(json_data, ('thumbnailUrls', ...))],
        }
