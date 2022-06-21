from .common import InfoExtractor
from ..compat import compat_str
from ..utils import (
    ExtractorError,
    determine_ext,
    int_or_none,
    urljoin,
)


class VoiceRepublicIE(InfoExtractor):
    _VALID_URL = r'https?://voicerepublic\.com/(?:talks|embed)/(?P<id>[0-9a-z-]+)'
    _TESTS = [{
        'url': 'http://voicerepublic.com/talks/watching-the-watchers-building-a-sousveillance-state',
        'md5': 'b9174d651323f17783000876347116e3',
        'info_dict': {
            'id': '2296',
            'display_id': 'watching-the-watchers-building-a-sousveillance-state',
            'ext': 'm4a',
            'title': 'Watching the Watchers: Building a Sousveillance State',
            'description': 'Secret surveillance programs have metadata too. The people and companies that operate secret surveillance programs can be surveilled.',
            'duration': 1556,
            'view_count': int,
        }
    }, {
        'url': 'http://voicerepublic.com/embed/watching-the-watchers-building-a-sousveillance-state',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)

        webpage = self._download_webpage(url, display_id)

        if '>Queued for processing, please stand by...<' in webpage:
            raise ExtractorError(
                'Audio is still queued for processing', expected=True)

        talk = self._parse_json(self._search_regex(
            r'initialSnapshot\s*=\s*({.+?});',
            webpage, 'talk'), display_id)['talk']
        title = talk['title']
        formats = [{
            'url': urljoin(url, talk_url),
            'format_id': format_id,
            'ext': determine_ext(talk_url) or format_id,
            'vcodec': 'none',
        } for format_id, talk_url in talk['media_links'].items()]
        self._sort_formats(formats)

        return {
            'id': compat_str(talk.get('id') or display_id),
            'display_id': display_id,
            'title': title,
            'description': talk.get('teaser'),
            'thumbnail': talk.get('image_url'),
            'duration': int_or_none(talk.get('archived_duration')),
            'view_count': int_or_none(talk.get('play_count')),
            'formats': formats,
        }
