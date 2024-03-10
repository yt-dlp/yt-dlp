from .common import InfoExtractor
from ..utils import (
    int_or_none,
    parse_iso8601,
    try_get,
)


class VTMIE(InfoExtractor):
    _WORKING = False
    _VALID_URL = r'https?://(?:www\.)?vtm\.be/([^/?&#]+)~v(?P<id>[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12})'
    _TEST = {
        'url': 'https://vtm.be/gast-vernielt-genkse-hotelkamer~ve7534523-279f-4b4d-a5c9-a33ffdbe23e1',
        'md5': '37dca85fbc3a33f2de28ceb834b071f8',
        'info_dict': {
            'id': '192445',
            'ext': 'mp4',
            'title': 'Gast vernielt Genkse hotelkamer',
            'timestamp': 1611060180,
            'upload_date': '20210119',
            'duration': 74,
            # TODO: fix url _type result processing
            # 'series': 'Op Interventie',
        }
    }

    def _real_extract(self, url):
        uuid = self._match_id(url)
        video = self._download_json(
            'https://omc4vm23offuhaxx6hekxtzspi.appsync-api.eu-west-1.amazonaws.com/graphql',
            uuid, query={
                'query': '''{
  getComponent(type: Video, uuid: "%s") {
    ... on Video {
      description
      duration
      myChannelsVideo
      program {
        title
      }
      publishedAt
      title
    }
  }
}''' % uuid,
            }, headers={
                'x-api-key': 'da2-lz2cab4tfnah3mve6wiye4n77e',
            })['data']['getComponent']

        return {
            '_type': 'url',
            'id': uuid,
            'title': video.get('title'),
            'url': 'http://mychannels.video/embed/%d' % video['myChannelsVideo'],
            'description': video.get('description'),
            'timestamp': parse_iso8601(video.get('publishedAt')),
            'duration': int_or_none(video.get('duration')),
            'series': try_get(video, lambda x: x['program']['title']),
            'ie_key': 'Medialaan',
        }
