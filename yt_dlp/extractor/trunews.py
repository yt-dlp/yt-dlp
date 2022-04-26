from .common import InfoExtractor


class TruNewsIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?trunews\.com/stream/(?P<id>[^/?#&]+)'
    _TEST = {
        'url': 'https://www.trunews.com/stream/will-democrats-stage-a-circus-during-president-trump-s-state-of-the-union-speech',
        'info_dict': {
            'id': '5c5a21e65d3c196e1c0020cc',
            'display_id': 'will-democrats-stage-a-circus-during-president-trump-s-state-of-the-union-speech',
            'ext': 'mp4',
            'title': "Will Democrats Stage a Circus During President Trump's State of the Union Speech?",
            'description': 'md5:c583b72147cc92cf21f56a31aff7a670',
            'duration': 3685,
            'timestamp': 1549411440,
            'upload_date': '20190206',
        },
        'add_ie': ['Zype'],
    }
    _ZYPE_TEMPL = 'https://player.zype.com/embed/%s.js?api_key=X5XnahkjCwJrT_l5zUqypnaLEObotyvtUKJWWlONxDoHVjP8vqxlArLV8llxMbyt'

    def _real_extract(self, url):
        display_id = self._match_id(url)

        zype_id = self._download_json(
            'https://api.zype.com/videos', display_id, query={
                'app_key': 'PUVKp9WgGUb3-JUw6EqafLx8tFVP6VKZTWbUOR-HOm__g4fNDt1bCsm_LgYf_k9H',
                'per_page': 1,
                'active': 'true',
                'friendly_title': display_id,
            })['response'][0]['_id']
        return self.url_result(self._ZYPE_TEMPL % zype_id, 'Zype', zype_id)
