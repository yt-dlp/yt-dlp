from __future__ import unicode_literals

from .common import InfoExtractor


class RTRFMIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?rtrfm\.com\.au/(?:shows|show-episode)/(?P<id>[^/?\#&]+)'
    _PLAY_SHOW = r"\.playShow\('(?P<show>[^']+)', *'(?P<date>[0-9]{4}-[0-9]{2}-[0-9]{2})', *'(?P<title>[^']+)'\)"
    _PLAY_SHOW_FROM = r"\.playShowFrom\('(?P<show>[^']+)', *'(?P<date>[0-9]{4}-[0-9]{2}-[0-9]{2})', *'?P<title>([^']+)', \d+\)"
    _RESTREAMS_URL = 'https://restreams.rtrfm.com.au/rzz'
    _TESTS = [
        {
            'url': 'https://rtrfm.com.au/shows/breakfast/',
            # the downloaded file changes daily so the md5 is not checkable
            'info_dict': {
                'id': r're:^breakfast-\d{4}-\d{2}-\d{2}$',
                'ext': 'mp3',
                'series': 'Breakfast with Taylah',
                'title': r're:^Breakfast with Taylah \d{4}-\d{2}-\d{2}$',
                'description': 'md5:0979c3ab1febfbec3f1ccb743633c611',
            },
            'skip': 'tests with re in the id expect the re in the filename '
                    'instead of the id, but the id depends on the date.',
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
            'params': {
                # This audio has expired
                'skip_download': True,
            },
        },
    ]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        show, date, title = self._search_regex(
            [self._PLAY_SHOW, self._PLAY_SHOW_FROM],
            webpage, 'details', group=('show', 'date', 'title'))
        url = self._download_json(
            self._RESTREAMS_URL, show, 'Downloading MP3 URL', query={'n': show, 'd': date})['u']
        return {
            'id': '%s-%s' % (show, date),
            'title': '%s %s' % (title, date),
            'series': title,
            'url': url,
            'release_date': date,
            'description': self._og_search_description(webpage),
        }
