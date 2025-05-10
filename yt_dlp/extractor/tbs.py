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
    _SOFTWARE_STATEMENT_MAP = {
        'tbs': 'eyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiJkZTA0NTYxZS1iMTFhLTRlYTgtYTg5NC01NjI3MGM1NmM2MWIiLCJuYmYiOjE1MzcxODkzOTAsImlzcyI6ImF1dGguYWRvYmUuY29tIiwiaWF0IjoxNTM3MTg5MzkwfQ.Z7ny66kaqNDdCHf9Y9KsV12LrBxrLkGGxlYe2XGm6qsw2T-k1OCKC1TMzeqiZP735292MMRAQkcJDKrMIzNbAuf9nCdIcv4kE1E2nqUnjPMBduC1bHffZp8zlllyrN2ElDwM8Vhwv_5nElLRwWGEt0Kaq6KJAMZA__WDxKWC18T-wVtsOZWXQpDqO7nByhfj2t-Z8c3TUNVsA_wHgNXlkzJCZ16F2b7yGLT5ZhLPupOScd3MXC5iPh19HSVIok22h8_F_noTmGzmMnIRQi6bWYWK2zC7TQ_MsYHfv7V6EaG5m1RKZTV6JAwwoJQF_9ByzarLV1DGwZxD9-eQdqswvg',
        'tntdrama': 'eyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiIwOTMxYTU4OS1jZjEzLTRmNjMtYTJmYy03MzhjMjE1NWU5NjEiLCJuYmYiOjE1MzcxOTA4MjcsImlzcyI6ImF1dGguYWRvYmUuY29tIiwiaWF0IjoxNTM3MTkwODI3fQ.AucKvtws7oekTXi80_zX4-BlgJD9GLvlOI9FlBCjdlx7Pa3eJ0AqbogynKMiatMbnLOTMHGjd7tTiq422unmZjBz70dhePAe9BbW0dIo7oQ57vZ-VBYw_tWYRPmON61MwAbLVlqROD3n_zURs85S8TlkQx9aNx9x_riGGELjd8l05CVa_pOluNhYvuIFn6wmrASOKI1hNEblBDWh468UWP571-fe4zzi0rlYeeHd-cjvtWvOB3bQsWrUVbK4pRmqvzEH59j0vNF-ihJF9HncmUicYONe47Mib3elfMok23v4dB1_UAlQY_oawfNcynmEnJQCcqFmbHdEwTW6gMiYsA',
    }

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
            media_id, tokenizer_query, self._SOFTWARE_STATEMENT_MAP[site], {
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
