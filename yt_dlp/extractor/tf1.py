# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..compat import compat_str


class TF1IE(InfoExtractor):
    """TF1 uses the wat.tv player."""
    _VALID_URL = r'https?://(?:(?:videos|www|lci)\.tf1|(?:www\.)?(?:tfou|ushuaiatv|histoire|tvbreizh))\.fr/(?:[^/]+/)*(?P<id>[^/?#.]+)'
    _TESTS = [{
        'url': 'http://videos.tf1.fr/auto-moto/citroen-grand-c4-picasso-2013-presentation-officielle-8062060.html',
        'info_dict': {
            'id': '10635995',
            'ext': 'mp4',
            'title': 'Citroën Grand C4 Picasso 2013 : présentation officielle',
            'description': 'Vidéo officielle du nouveau Citroën Grand C4 Picasso, lancé à l\'automne 2013.',
        },
        'params': {
            # Sometimes wat serves the whole file with the --test option
            'skip_download': True,
        },
        'expected_warnings': ['HTTP Error 404'],
    }, {
        'url': 'http://www.tfou.fr/chuggington/videos/le-grand-mysterioso-chuggington-7085291-739.html',
        'info_dict': {
            'id': 'le-grand-mysterioso-chuggington-7085291-739',
            'ext': 'mp4',
            'title': 'Le grand Mystérioso - Chuggington',
            'description': 'Le grand Mystérioso - Emery rêve qu\'un article lui soit consacré dans le journal.',
            'upload_date': '20150103',
        },
        'params': {
            # Sometimes wat serves the whole file with the --test option
            'skip_download': True,
        },
        'skip': 'HTTP Error 410: Gone',
    }, {
        'url': 'http://www.tf1.fr/tf1/koh-lanta/videos/replay-koh-lanta-22-mai-2015.html',
        'only_matching': True,
    }, {
        'url': 'http://lci.tf1.fr/sept-a-huit/videos/sept-a-huit-du-24-mai-2015-8611550.html',
        'only_matching': True,
    }, {
        'url': 'http://www.tf1.fr/hd1/documentaire/videos/mylene-farmer-d-une-icone.html',
        'only_matching': True,
    }, {
        'url': 'https://www.tf1.fr/tmc/quotidien-avec-yann-barthes/videos/quotidien-premiere-partie-11-juin-2019.html',
        'info_dict': {
            'id': '13641379',
            'ext': 'mp4',
            'title': 'md5:f392bc52245dc5ad43771650c96fb620',
            'description': 'md5:44bc54f0a21322f5b91d68e76a544eae',
            'upload_date': '20190611',
        },
        'params': {
            # Sometimes wat serves the whole file with the --test option
            'skip_download': True,
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(url, video_id)

        wat_id = None

        data = self._parse_json(
            self._search_regex(
                r'__APOLLO_STATE__\s*=\s*({.+?})\s*(?:;|</script>)', webpage,
                'data', default='{}'), video_id, fatal=False)

        if data:
            try:
                wat_id = next(
                    video.get('streamId')
                    for key, video in data.items()
                    if isinstance(video, dict)
                    and video.get('slug') == video_id)
                if not isinstance(wat_id, compat_str) or not wat_id.isdigit():
                    wat_id = None
            except StopIteration:
                pass

        if not wat_id:
            wat_id = self._html_search_regex(
                (r'(["\'])(?:https?:)?//www\.wat\.tv/embedframe/.*?(?P<id>\d{8})\1',
                 r'(["\']?)streamId\1\s*:\s*(["\']?)(?P<id>\d+)\2'),
                webpage, 'wat id', group='id')

        return self.url_result('wat:%s' % wat_id, 'Wat')
