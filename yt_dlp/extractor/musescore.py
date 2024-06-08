from .common import InfoExtractor


class MuseScoreIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?musescore\.com/(?:user/\d+|[^/]+)(?:/scores)?/(?P<id>[^#&?]+)'
    _TESTS = [{
        'url': 'https://musescore.com/user/73797/scores/142975',
        'info_dict': {
            'id': '142975',
            'ext': 'mp3',
            'title': 'WA Mozart Marche Turque (Turkish March fingered)',
            'description': 'md5:7ede08230e4eaabd67a4a98bb54d07be',
            'thumbnail': r're:https?://(?:www\.)?musescore\.com/.*\.png[^$]+',
            'uploader': 'PapyPiano',
            'creator': 'Wolfgang Amadeus Mozart',
        },
    }, {
        'url': 'https://musescore.com/user/36164500/scores/6837638',
        'info_dict': {
            'id': '6837638',
            'ext': 'mp3',
            'title': 'Sweet Child O\' Mine  – Guns N\' Roses sweet child',
            'description': 'md5:4dca71191c14abc312a0a4192492eace',
            'thumbnail': r're:https?://(?:www\.)?musescore\.com/.*\.png[^$]+',
            'uploader': 'roxbelviolin',
            'creator': 'Guns N´Roses Arr. Roxbel Violin',
        },
    }, {
        'url': 'https://musescore.com/classicman/fur-elise',
        'info_dict': {
            'id': '33816',
            'ext': 'mp3',
            'title': 'Für Elise – Beethoven',
            'description': 'md5:49515a3556d5ecaf9fa4b2514064ac34',
            'thumbnail': r're:https?://(?:www\.)?musescore\.com/.*\.png[^$]+',
            'uploader': 'ClassicMan',
            'creator': 'Ludwig van Beethoven (1770–1827)',
        },
    }, {
        'url': 'https://musescore.com/minh_cuteee/scores/6555384',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        webpage = self._download_webpage(url, None)
        url = self._og_search_url(webpage) or url
        video_id = self._match_id(url)
        mp3_url = self._download_json(f'https://musescore.com/api/jmuse?id={video_id}&index=0&type=mp3&v2=1', video_id,
                                      headers={'authorization': '63794e5461e4cfa046edfbdddfccc1ac16daffd2'})['info']['url']
        formats = [{
            'url': mp3_url,
            'ext': 'mp3',
            'vcodec': 'none',
        }]

        return {
            'id': video_id,
            'formats': formats,
            'title': self._og_search_title(webpage),
            'description': self._og_search_description(webpage),
            'thumbnail': self._og_search_thumbnail(webpage),
            'uploader': self._html_search_meta('musescore:author', webpage, 'uploader'),
            'creator': self._html_search_meta('musescore:composer', webpage, 'composer'),
        }
