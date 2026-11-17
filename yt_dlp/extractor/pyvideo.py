import re

from .common import InfoExtractor
from ..utils import int_or_none


class PyvideoIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?pyvideo\.org/(?P<category>[^/]+)/(?P<id>[^/?#&.]+)'

    _TESTS = [{
        'url': 'http://pyvideo.org/pycon-us-2013/become-a-logging-expert-in-30-minutes.html',
        'info_dict': {
            'id': 'become-a-logging-expert-in-30-minutes',
        },
        'playlist_count': 2,
    }, {
        'url': 'http://pyvideo.org/pygotham-2012/gloriajw-spotifywitherikbernhardsson182m4v.html',
        'md5': '5fe1c7e0a8aa5570330784c847ff6d12',
        'info_dict': {
            'id': '2542',
            'ext': 'm4v',
            'title': 'Gloriajw-SpotifyWithErikBernhardsson182.m4v',
        },
    }]

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        category = mobj.group('category')
        video_id = mobj.group('id')

        entries = []

        data = self._download_json(
            f'https://raw.githubusercontent.com/pyvideo/data/master/{category}/videos/{video_id}.json',
            video_id, fatal=False)

        if data:
            for video in data['videos']:
                video_url = video.get('url')
                if video_url:
                    if video.get('type') == 'youtube':
                        entries.append(self.url_result(video_url, 'Youtube'))
                    else:
                        entries.append({
                            'id': str(data.get('id') or video_id),
                            'url': video_url,
                            'title': data['title'],
                            'description': data.get('description') or data.get('summary'),
                            'thumbnail': data.get('thumbnail_url'),
                            'duration': int_or_none(data.get('duration')),
                        })
        else:
            webpage = self._download_webpage(url, video_id)
            title = self._og_search_title(webpage)
            media_urls = self._search_regex(
                r'(?s)Media URL:(.+?)</li>', webpage, 'media urls')
            for m in re.finditer(
                    r'<a[^>]+href=(["\'])(?P<url>http.+?)\1', media_urls):
                media_url = m.group('url')
                if re.match(r'https?://www\.youtube\.com/watch\?v=.*', media_url):
                    entries.append(self.url_result(media_url, 'Youtube'))
                else:
                    entries.append({
                        'id': video_id,
                        'url': media_url,
                        'title': title,
                    })

        return self.playlist_result(entries, video_id)
