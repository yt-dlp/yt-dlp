from .seleniumpagerendering import SeleniumPageRenderingIE


class PandaVideoIE(SeleniumPageRenderingIE):
    # _VALID_URL = (
    #     r'https?://.*\.pandavideo\.com.*/embed/.*v=(?P<id>[a-f0-9\-]+)',
    # )
    _TESTS = [{
        'url': 'https://player-vz-ee438fcb-865.tv.pandavideo.com.br/embed/'
               '?color=f6c5c5&v=6035f7c1-83fe-4847-93c3-e2f4827e60f3',
        'info_dict': {},
    }]
