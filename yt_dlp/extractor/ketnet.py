from .canvas import CanvasIE
from .common import InfoExtractor
from ..compat import compat_urllib_parse_unquote
from ..utils import (
    int_or_none,
    parse_iso8601,
)


class KetnetIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?ketnet\.be/(?P<id>(?:[^/]+/)*[^/?#&]+)'
    _TESTS = [{
        'url': 'https://www.ketnet.be/kijken/n/nachtwacht/3/nachtwacht-s3a1-de-greystook',
        'md5': '37b2b7bb9b3dcaa05b67058dc3a714a9',
        'info_dict': {
            'id': 'pbs-pub-aef8b526-115e-4006-aa24-e59ff6c6ef6f$vid-ddb815bf-c8e7-467b-8879-6bad7a32cebd',
            'ext': 'mp4',
            'title': 'Nachtwacht - Reeks 3: Aflevering 1',
            'description': 'De Nachtwacht krijgt te maken met een parasiet',
            'thumbnail': r're:^https?://.*\.jpg$',
            'duration': 1468.02,
            'timestamp': 1609225200,
            'upload_date': '20201229',
            'series': 'Nachtwacht',
            'season': 'Reeks 3',
            'episode': 'De Greystook',
            'episode_number': 1,
        },
        'expected_warnings': ['is not a supported codec', 'Unknown MIME type'],
    }, {
        'url': 'https://www.ketnet.be/themas/karrewiet/jaaroverzicht-20200/karrewiet-het-jaar-van-black-mamba',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)

        video = self._download_json(
            'https://senior-bff.ketnet.be/graphql', display_id, query={
                'query': '''{
  video(id: "content/ketnet/nl/%s.model.json") {
    description
    episodeNr
    imageUrl
    mediaReference
    programTitle
    publicationDate
    seasonTitle
    subtitleVideodetail
    titleVideodetail
  }
}''' % display_id,
            })['data']['video']

        mz_id = compat_urllib_parse_unquote(video['mediaReference'])

        return {
            '_type': 'url_transparent',
            'id': mz_id,
            'title': video['titleVideodetail'],
            'url': 'https://mediazone.vrt.be/api/v1/ketnet/assets/' + mz_id,
            'thumbnail': video.get('imageUrl'),
            'description': video.get('description'),
            'timestamp': parse_iso8601(video.get('publicationDate')),
            'series': video.get('programTitle'),
            'season': video.get('seasonTitle'),
            'episode': video.get('subtitleVideodetail'),
            'episode_number': int_or_none(video.get('episodeNr')),
            'ie_key': CanvasIE.ie_key(),
        }
