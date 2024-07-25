from .common import InfoExtractor


class CaltransIE(InfoExtractor):
    _VALID_URL = r'https?://(?:[^/]+\.)?ca\.gov/vm/loc/[^/]+/(?P<id>[a-z0-9_]+)\.htm'
    _TEST = {
        'url': 'https://cwwp2.dot.ca.gov/vm/loc/d3/hwy50at24th.htm',
        'info_dict': {
            'id': 'hwy50at24th',
            'ext': 'ts',
            'title': 'US-50 : Sacramento : Hwy 50 at 24th',
            'live_status': 'is_live',
            'thumbnail': 'https://cwwp2.dot.ca.gov/data/d3/cctv/image/hwy50at24th/hwy50at24th.jpg',
        },
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        global_vars = self._search_regex(
            r'<script[^<]+?([^<]+\.m3u8[^<]+)</script>',
            webpage, 'Global Vars')
        route_place = self._search_regex(r'routePlace\s*=\s*"([^"]+)"', global_vars, 'Route Place', fatal=False)
        location_name = self._search_regex(r'locationName\s*=\s*"([^"]+)"', global_vars, 'Location Name', fatal=False)
        poster_url = self._search_regex(r'posterURL\s*=\s*"([^"]+)"', global_vars, 'Poster Url', fatal=False)
        video_stream = self._search_regex(r'videoStreamURL\s*=\s*"([^"]+)"', global_vars, 'Video Stream URL', fatal=False)

        formats = self._extract_m3u8_formats(video_stream, video_id, 'ts', live=True)

        return {
            'id': video_id,
            'title': f'{route_place} : {location_name}',
            'is_live': True,
            'formats': formats,
            'thumbnail': poster_url,
        }
