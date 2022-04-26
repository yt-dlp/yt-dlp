from .common import InfoExtractor


class PeopleIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?people\.com/people/videos/0,,(?P<id>\d+),00\.html'

    _TEST = {
        'url': 'http://www.people.com/people/videos/0,,20995451,00.html',
        'info_dict': {
            'id': 'ref:20995451',
            'ext': 'mp4',
            'title': 'Astronaut Love Triangle Victim Speaks Out: “The Crime in 2007 Hasn’t Defined Us”',
            'description': 'Colleen Shipman speaks to PEOPLE for the first time about life after the attack',
            'thumbnail': r're:^https?://.*\.jpg',
            'duration': 246.318,
            'timestamp': 1458720585,
            'upload_date': '20160323',
            'uploader_id': '416418724',
        },
        'params': {
            'skip_download': True,
        },
        'add_ie': ['BrightcoveNew'],
    }

    def _real_extract(self, url):
        return self.url_result(
            'http://players.brightcove.net/416418724/default_default/index.html?videoId=ref:%s'
            % self._match_id(url), 'BrightcoveNew')
