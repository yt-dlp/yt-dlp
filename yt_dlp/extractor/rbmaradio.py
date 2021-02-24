from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..compat import compat_str
from ..utils import (
    clean_html,
    int_or_none,
    unified_timestamp,
    update_url_query,
)


class RBMARadioIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?(?:rbmaradio|redbullradio)\.com/shows/(?P<show_id>[^/]+)/episodes/(?P<id>[^/?#&]+)'
    _TEST = {
        'url': 'https://www.rbmaradio.com/shows/main-stage/episodes/ford-lopatin-live-at-primavera-sound-2011',
        'md5': '6bc6f9bcb18994b4c983bc3bf4384d95',
        'info_dict': {
            'id': 'ford-lopatin-live-at-primavera-sound-2011',
            'ext': 'mp3',
            'title': 'Main Stage - Ford & Lopatin at Primavera Sound',
            'description': 'md5:d41d8cd98f00b204e9800998ecf8427e',
            'thumbnail': r're:^https?://.*\.jpg',
            'duration': 2452,
            'timestamp': 1307103164,
            'upload_date': '20110603',
        },
    }

    def _real_extract(self, url):
        mobj = re.match(self._VALID_URL, url)
        show_id = mobj.group('show_id')
        episode_id = mobj.group('id')

        webpage = self._download_webpage(url, episode_id)

        episode = self._parse_json(
            self._search_regex(
                r'__INITIAL_STATE__\s*=\s*({.+?})\s*</script>',
                webpage, 'json data'),
            episode_id)['episodes'][show_id][episode_id]

        title = episode['title']

        show_title = episode.get('showTitle')
        if show_title:
            title = '%s - %s' % (show_title, title)

        formats = [{
            'url': update_url_query(episode['audioURL'], query={'cbr': abr}),
            'format_id': compat_str(abr),
            'abr': abr,
            'vcodec': 'none',
        } for abr in (96, 128, 192, 256)]
        self._check_formats(formats, episode_id)

        description = clean_html(episode.get('longTeaser'))
        thumbnail = self._proto_relative_url(episode.get('imageURL', {}).get('landscape'))
        duration = int_or_none(episode.get('duration'))
        timestamp = unified_timestamp(episode.get('publishedAt'))

        return {
            'id': episode_id,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'duration': duration,
            'timestamp': timestamp,
            'formats': formats,
        }
