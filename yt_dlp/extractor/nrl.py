from .common import InfoExtractor


class NRLTVIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?nrl\.com/tv(/[^/]+)*/(?P<id>[^/?&#]+)'
    _TEST = {
        'url': 'https://www.nrl.com/tv/news/match-highlights-titans-v-knights-862805/',
        'info_dict': {
            'id': 'YyNnFuaDE6kPJqlDhG4CGQ_w89mKTau4',
            'ext': 'mp4',
            'title': 'Match Highlights: Titans v Knights',
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
    }

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        q_data = self._parse_json(self._html_search_regex(
            r'(?s)q-data="({.+?})"', webpage, 'player data'), display_id)
        ooyala_id = q_data['videoId']
        return self.url_result(
            'ooyala:' + ooyala_id, 'Ooyala', ooyala_id, q_data.get('title'))
