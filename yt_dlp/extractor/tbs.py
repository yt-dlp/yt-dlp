import re
import urllib.parse

from .turner import TurnerBaseIE
from ..utils import (
    float_or_none,
    int_or_none,
    strip_or_none,
)


class TBSIE(TurnerBaseIE):
    _VALID_URL = r'https?://(?:www\.)?(?P<site>tbs|tntdrama)\.com(?P<path>/(?:movies|watchtnt|watchtbs|shows/[^/]+/(?:clips|season-\d+/episode-\d+))/(?P<id>[^/?#]+))'
    _TESTS = [{
        'url': 'http://www.tntdrama.com/shows/the-alienist/clips/monster',
        'info_dict': {
            'id': '8d384cde33b89f3a43ce5329de42903ed5099887',
            'ext': 'mp4',
            'title': 'Monster',
            'description': 'Get a first look at the theatrical trailer for TNT’s highly anticipated new psychological thriller The Alienist, which premieres January 22 on TNT.',
            'timestamp': 1508175329,
            'upload_date': '20171016',
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
    }, {
        'url': 'http://www.tbs.com/shows/search-party/season-1/episode-1/explicit-the-mysterious-disappearance-of-the-girl-no-one-knew',
        'only_matching': True,
    }, {
        'url': 'http://www.tntdrama.com/movies/star-wars-a-new-hope',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        site, path, display_id = self._match_valid_url(url).groups()
        webpage = self._download_webpage(url, display_id)
        drupal_settings = self._parse_json(self._search_regex(
            r'<script[^>]+?data-drupal-selector="drupal-settings-json"[^>]*?>({.+?})</script>',
            webpage, 'drupal setting'), display_id)
        is_live = 'watchtnt' in path or 'watchtbs' in path
        video_data = next(v for v in drupal_settings['turner_playlist'] if is_live or v.get('url') == path)

        media_id = video_data['mediaID']
        title = video_data['title']
        tokenizer_query = urllib.parse.parse_qs(urllib.parse.urlparse(
            drupal_settings['ngtv_token_url']).query)

        info = self._extract_ngtv_info(
            media_id, tokenizer_query, {
                'url': url,
                'site_name': site[:3].upper(),
                'auth_required': video_data.get('authRequired') == '1' or is_live,
                'is_live': is_live,
            })

        thumbnails = []
        for image_id, image in video_data.get('images', {}).items():
            image_url = image.get('url')
            if not image_url or image.get('type') != 'video':
                continue
            i = {
                'id': image_id,
                'url': image_url,
            }
            mobj = re.search(r'(\d+)x(\d+)', image_url)
            if mobj:
                i.update({
                    'width': int(mobj.group(1)),
                    'height': int(mobj.group(2)),
                })
            thumbnails.append(i)

        info.update({
            'id': media_id,
            'title': title,
            'description': strip_or_none(video_data.get('descriptionNoTags') or video_data.get('shortDescriptionNoTags')),
            'duration': float_or_none(video_data.get('duration')) or info.get('duration'),
            'timestamp': int_or_none(video_data.get('created')),
            'season_number': int_or_none(video_data.get('season')),
            'episode_number': int_or_none(video_data.get('episode')),
            'thumbnails': thumbnails,
            'is_live': is_live,
        })
        return info
