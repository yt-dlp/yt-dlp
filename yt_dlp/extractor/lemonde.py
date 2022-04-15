from .common import InfoExtractor


class LemondeIE(InfoExtractor):
    _VALID_URL = r'https?://(?:.+?\.)?lemonde\.fr/(?:[^/]+/)*(?P<id>[^/]+)\.html'
    _TESTS = [{
        'url': 'http://www.lemonde.fr/police-justice/video/2016/01/19/comprendre-l-affaire-bygmalion-en-cinq-minutes_4849702_1653578.html',
        'md5': 'da120c8722d8632eec6ced937536cc98',
        'info_dict': {
            'id': 'lqm3kl',
            'ext': 'mp4',
            'title': "Comprendre l'affaire Bygmalion en 5 minutes",
            'thumbnail': r're:^https?://.*\.jpg',
            'duration': 309,
            'upload_date': '20160119',
            'timestamp': 1453194778,
            'uploader_id': '3pmkp',
        },
    }, {
        # standard iframe embed
        'url': 'http://www.lemonde.fr/les-decodeurs/article/2016/10/18/tout-comprendre-du-ceta-le-petit-cousin-du-traite-transatlantique_5015920_4355770.html',
        'info_dict': {
            'id': 'uzsxms',
            'ext': 'mp4',
            'title': "CETA : quelles suites pour l'accord commercial entre l'Europe et le Canada ?",
            'thumbnail': r're:^https?://.*\.jpg',
            'duration': 325,
            'upload_date': '20161021',
            'timestamp': 1477044540,
            'uploader_id': '3pmkp',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'http://redaction.actu.lemonde.fr/societe/video/2016/01/18/calais-debut-des-travaux-de-defrichement-dans-la-jungle_4849233_3224.html',
        'only_matching': True,
    }, {
        # YouTube embeds
        'url': 'http://www.lemonde.fr/pixels/article/2016/12/09/pourquoi-pewdiepie-superstar-de-youtube-a-menace-de-fermer-sa-chaine_5046649_4408996.html',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)

        webpage = self._download_webpage(url, display_id)

        digiteka_url = self._proto_relative_url(self._search_regex(
            r'url\s*:\s*(["\'])(?P<url>(?:https?://)?//(?:www\.)?(?:digiteka\.net|ultimedia\.com)/deliver/.+?)\1',
            webpage, 'digiteka url', group='url', default=None))

        if digiteka_url:
            return self.url_result(digiteka_url, 'Digiteka')

        return self.url_result(url, 'Generic')
