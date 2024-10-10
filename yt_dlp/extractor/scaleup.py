from .seleniumpagerendering import SeleniumPageRenderingIE


class ScaleUpIE(SeleniumPageRenderingIE):
    # _VALID_URL = r'https?://.*\.scaleup\.com.*/embed/(?P<id>[a-f0-9\-]+)'
    _TESTS = [{
        'url': 'https://player.scaleup.com.br/embed/35ad6ab30cc5294a49bc1bad6a8a3d966ec39038',
        'info_dict': {},
    }]

    # @classmethod
    # def _match_valid_url(cls, url):
    #     if cls._VALID_URL is False:
    #         return None
    #     # This does not use has/getattr intentionally - we want to know whether
    #     # we have cached the regexp for *this* class, whereas getattr would also
    #     # match the superclass
    #     if '_VALID_URL_RE' not in cls.__dict__:
    #         cls._VALID_URL_RE = tuple(map(re.compile, variadic(cls._VALID_URL)))
    #     return next(filter(None, (regex.match(url) for regex in cls._VALID_URL_RE)), None)
