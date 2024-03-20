from .common import InfoExtractor
from ..utils import (
    parse_duration,
    parse_iso8601,
    js_to_json,
)
from ..compat import compat_str


class RDSIE(InfoExtractor):
    _WORKING = False
    IE_DESC = 'RDS.ca'
    _VALID_URL = r'https?://(?:www\.)?rds\.ca/vid(?:[eé]|%C3%A9)os/(?:[^/]+/)*(?P<id>[^/]+)-\d+\.\d+'

    _TESTS = [{
        # has two 9c9media ContentPackages, the web player selects the first ContentPackage
        'url': 'https://www.rds.ca/videos/Hockey/NationalHockeyLeague/teams/9/forum-du-5-a-7-jesperi-kotkaniemi-de-retour-de-finlande-3.1377606',
        'info_dict': {
            'id': '2083309',
            'display_id': 'forum-du-5-a-7-jesperi-kotkaniemi-de-retour-de-finlande',
            'ext': 'flv',
            'title': 'Forum du 5 à 7 : Kotkaniemi de retour de Finlande',
            'description': 'md5:83fa38ecc4a79b19e433433254077f25',
            'timestamp': 1606129030,
            'upload_date': '20201123',
            'duration': 773.039,
        }
    }, {
        'url': 'http://www.rds.ca/vid%C3%A9os/un-voyage-positif-3.877934',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)

        webpage = self._download_webpage(url, display_id)

        item = self._parse_json(self._search_regex(r'(?s)itemToPush\s*=\s*({.+?});', webpage, 'item'), display_id, js_to_json)
        video_id = compat_str(item['id'])
        title = item.get('title') or self._og_search_title(webpage) or self._html_search_meta(
            'title', webpage, 'title', fatal=True)
        description = self._og_search_description(webpage) or self._html_search_meta(
            'description', webpage, 'description')
        thumbnail = item.get('urlImageBig') or self._og_search_thumbnail(webpage) or self._search_regex(
            [r'<link[^>]+itemprop="thumbnailUrl"[^>]+href="([^"]+)"',
             r'<span[^>]+itemprop="thumbnailUrl"[^>]+content="([^"]+)"'],
            webpage, 'thumbnail', fatal=False)
        timestamp = parse_iso8601(self._search_regex(
            r'<span[^>]+itemprop="uploadDate"[^>]+content="([^"]+)"',
            webpage, 'upload date', fatal=False))
        duration = parse_duration(self._search_regex(
            r'<span[^>]+itemprop="duration"[^>]+content="([^"]+)"',
            webpage, 'duration', fatal=False))
        age_limit = self._family_friendly_search(webpage)

        return {
            '_type': 'url_transparent',
            'id': video_id,
            'display_id': display_id,
            'url': '9c9media:rds_web:%s' % video_id,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'timestamp': timestamp,
            'duration': duration,
            'age_limit': age_limit,
            'ie_key': 'NineCNineMedia',
        }
