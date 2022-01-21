from __future__ import unicode_literals

from .common import InfoExtractor


class RTRFMIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?rtrfm\.com\.au/(?:shows|show-episode)/(?P<id>[^/?\#&]+)'
    _TESTS = [
        {
            'url': 'https://rtrfm.com.au/shows/breakfast/',
            'md5': '46168394d3a5ce237cf47e85d0745413',
            'info_dict': {
                'id': 'breakfast-2021-11-16',
                'ext': 'mp3',
                'series': 'Breakfast with Taylah',
                'title': r're:^Breakfast with Taylah \d{4}-\d{2}-\d{2}$',
                'description': 'md5:0979c3ab1febfbec3f1ccb743633c611',
            },
            'skip': 'ID and md5 changes daily',
        },
        {
            'url': 'https://rtrfm.com.au/show-episode/breakfast-2021-11-11/',
            'md5': '396bedf1e40f96c62b30d4999202a790',
            'info_dict': {
                'id': 'breakfast-2021-11-11',
                'ext': 'mp3',
                'series': 'Breakfast with Taylah',
                'title': 'Breakfast with Taylah 2021-11-11',
                'description': 'md5:0979c3ab1febfbec3f1ccb743633c611',
            },
        },
        {
            'url': 'https://rtrfm.com.au/show-episode/breakfast-2020-06-01/',
            'md5': '594027f513ec36a24b15d65007a24dff',
            'info_dict': {
                'id': 'breakfast-2020-06-01',
                'ext': 'mp3',
                'series': 'Breakfast with Taylah',
                'title': 'Breakfast with Taylah 2020-06-01',
                'description': r're:^Breakfast with Taylah ',
            },
            'skip': 'This audio has expired',
        },
    ]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        show, date, title = self._search_regex(
            r'''\.playShow(?:From)?\(['"](?P<show>[^'"]+)['"],\s*['"](?P<date>[0-9]{4}-[0-9]{2}-[0-9]{2})['"],\s*['"](?P<title>[^'"]+)['"]''',
            webpage, 'details', group=('show', 'date', 'title'))
        url = self._download_json(
            'https://restreams.rtrfm.com.au/rzz',
            show, 'Downloading MP3 URL', query={'n': show, 'd': date})['u']
        # This is the only indicator of an error until trying to download the URL and
        # downloads of mp4 URLs always fail (403 for current episodes, 404 for missing).
        if '.mp4' in url:
            url = None
            self.raise_no_formats('Expired or no episode on this date', expected=True)
        return {
            'id': '%s-%s' % (show, date),
            'title': '%s %s' % (title, date),
            'series': title,
            'url': url,
            'release_date': date,
            'description': self._og_search_description(webpage),
        }
