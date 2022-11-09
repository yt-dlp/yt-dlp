from .common import InfoExtractor
from ..utils import classproperty, ExtractorError


class KnownDRMIE(InfoExtractor):
    IE_DESC = False
    IE_NAME = 'unsupported:drm'
    UNSUPPORTED_URLS = (
        r'play\.hbomax\.com',
        r'channel(?:4|5)\.com',
        r'peacocktv\.com',
        r'(?:[\w\.]+\.)?disneyplus\.com',
        r'open\.spotify\.com/(?:track|playlist|album|artist)',
        r'tvnz\.co\.nz',
        r'oneplus\.ch',
        r'artstation\.com/learning/courses',
        r'philo\.com',
        r'(?:[\w\.]+\.)?mech-plus\.com',
        r'aha\.video',
        r'mubi\.com',
        r'vootkids\.com'
    )

    _TESTS = [{
        # https://github.com/yt-dlp/yt-dlp/issues/4309
        'url': 'https://www.peacocktv.com',
        'only_matching': True,
    }, {
        # https://github.com/yt-dlp/yt-dlp/issues/1719,
        'url': 'https://www.channel4.com',
        'only_matching': True,
    }, {
        # https://github.com/yt-dlp/yt-dlp/issues/1548
        'url': 'https://www.channel5.com',
        'only_matching': True,
    }, {
        'url': r'https://hsesn.apps.disneyplus.com',
        'only_matching': True,
    }, {
        'url': r'https://www.disneyplus.com',
        'only_matching': True,
    }, {
        'url': 'https://open.spotify.com/artist/',
        'only_matching': True,
    }, {
        'url': 'https://open.spotify.com/track/',
        'only_matching': True,
    }, {
        # TVNZ: https://github.com/yt-dlp/yt-dlp/issues/4122
        'url': 'https://tvnz.co.nz',
        'only_matching': True,
    }, {
        # https://github.com/yt-dlp/yt-dlp/issues/1922
        'url': 'https://www.oneplus.ch',
        'only_matching': True,
    }, {
        # https://github.com/yt-dlp/yt-dlp/issues/1140
        'url': 'https://www.artstation.com/learning/courses/',
        'only_matching': True,
    }, {
        # https://github.com/yt-dlp/yt-dlp/issues/3544
        'url': 'https://www.philo.com',
        'only_matching': True,
    }, {
        # https://github.com/yt-dlp/yt-dlp/issues/3533
        'url': 'https://www.mech-plus.com/',
        'only_matching': True,
    }, {
        'url': 'https://watch.mech-plus.com/',
        'only_matching': True,
    }, {
        # https://github.com/yt-dlp/yt-dlp/issues/2934
        'url': 'https://www.aha.video',
        'only_matching': True,
    }, {
        # https://github.com/yt-dlp/yt-dlp/issues/2743
        'url': 'https://mubi.com',
        'only_matching': True,
    }, {
        # https://github.com/yt-dlp/yt-dlp/issues/3287
        'url': 'https://www.vootkids.com',
        'only_matching': True,
    }]

    @classproperty
    def _VALID_URL(cls):
        return rf'https?://(?:www\.)?(?:{"|".join(cls.UNSUPPORTED_URLS)})'

    def _real_extract(self, url):
        raise ExtractorError(
            f'The requested site is known to use DRM protection. It will {self._downloader._format_err("NOT", self._downloader.Styles.EMPHASIS)} be supported by yt-dlp. '
            f'Please {self._downloader._format_err("DO NOT", self._downloader.Styles.ERROR)} open an issue, unless you have evidence that it is not DRM protected.',
            expected=True)
