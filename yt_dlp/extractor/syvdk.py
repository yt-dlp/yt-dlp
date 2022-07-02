from .common import InfoExtractor
import json


class SYVDKIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?24syv\.dk/episode/(?P<id>[a-zA-Z0-9-]+)'

    _TESTS = [{
        'url': 'https://24syv.dk/episode/isabella-arendt-stiller-op-for-de-konservative-2',
        'md5': '429ce5a423dd4b1e1d0bf3a569558089',
        'info_dict': {
            'id': '12215',
            'ext': 'mp3',
            'title': 'Isabella Arendt stiller op for De Konservative',
            'description': 'Tidligere formand for Kristendemokraterne Isabella Arendt stiller op til folketingsvalget for Det Konservative Folkeparti. Men hvorfor netop de konservative? og hvordan harmonisere det med hendes ønske om en mere human udlændinge- og integrationspolitikken. Hun er med fra start og fortæller hvorfor. <br /><br />Vi har også LOKK - Landsorganisation af Kvindekrisecentre’s formand Karin Gaardsted i programmet. Vi får talt om handleplanen mod partnerdrab. Og om der behov for at ændre den generelle samtale om vold i nære relationer og kvindedrab.'
        }
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        info_data = self._search_nextjs_data(webpage, video_id)["props"]["pageProps"]["episodeDetails"][0]

        return {
            'id': str(info['id']),
            'display_id': video_id,
            'title': try_get(info, lambda x: x['title']['rendered']),
            'description': try_get(info, lambda x: x['details']['post_title']),
            'vcodec': 'none',
            'ext': 'mp3',
            'url': info['details']['enclosure']
        }
