from .common import InfoExtractor


class DefenseGouvFrIE(InfoExtractor):
    IE_NAME = 'defense.gouv.fr'
    _VALID_URL = r'https?://.*?\.defense\.gouv\.fr/layout/set/ligthboxvideo/base-de-medias/webtv/(?P<id>[^/?#]*)'

    _TEST = {
        'url': 'http://www.defense.gouv.fr/layout/set/ligthboxvideo/base-de-medias/webtv/attaque-chimique-syrienne-du-21-aout-2013-1',
        'md5': '75bba6124da7e63d2d60b5244ec9430c',
        'info_dict': {
            'id': '11213',
            'ext': 'mp4',
            'title': 'attaque-chimique-syrienne-du-21-aout-2013-1'
        }
    }

    def _real_extract(self, url):
        title = self._match_id(url)
        webpage = self._download_webpage(url, title)

        video_id = self._search_regex(
            r"flashvars.pvg_id=\"(\d+)\";",
            webpage, 'ID')

        json_url = (
            'http://static.videos.gouv.fr/brightcovehub/export/json/%s' %
            video_id)
        info = self._download_json(json_url, title, 'Downloading JSON config')
        video_url = info['renditions'][0]['url']

        return {
            'id': video_id,
            'ext': 'mp4',
            'url': video_url,
            'title': title,
        }
