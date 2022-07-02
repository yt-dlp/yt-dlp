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
        _NEXT_DATA = self._html_search_regex(
            r'<script id="__NEXT_DATA__" type="application\/json">(?P<meta_dict>{.+})<\/script>', webpage,
            'audio URL', group='meta_dict')
        info = json.loads(_NEXT_DATA)
        audio_details = info["props"]["pageProps"]["episodeDetails"][0]["details"]
        audio_url = audio_details["enclosure"]
        description = audio_details.get("post_title")
        title = info["props"]["pageProps"]["episodeDetails"][0]["title"]["rendered"]
        _id = str(info["props"]["pageProps"]["episodeDetails"][0]["id"])

        return {
            'id': _id,
            'title': title,
            'description': description,
            'vcodec': 'none',
            'ext': 'mp3',
            'url': audio_url
        }
