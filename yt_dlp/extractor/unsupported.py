from .common import InfoExtractor
from ..utils import ExtractorError, classproperty, remove_start


class UnsupportedInfoExtractor(InfoExtractor):
    IE_DESC = False
    URLS = ()  # Redefine in subclasses

    @classproperty
    def IE_NAME(cls):
        return remove_start(super().IE_NAME, 'Known')

    @classproperty
    def _VALID_URL(cls):
        return rf'https?://(?:www\.)?(?:{"|".join(cls.URLS)})'


LF = '\n       '


class KnownDRMIE(UnsupportedInfoExtractor):
    """Sites that are known to use DRM for all their videos

    Add to this list only if:
    * You are reasonably certain that the site uses DRM for ALL their videos
    * Multiple users have asked about this site on github/discord
    """

    URLS = (
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
        r'vootkids\.com',
        r'nowtv\.it/watch',
        r'tv\.apple\.com',
        r'primevideo\.com',
        r'hulu\.com',
        r'resource\.inkryptvideos\.com',
        r'joyn\.de',
        r'amazon\.(?:\w{2}\.)?\w+/gp/video',
        r'music\.amazon\.(?:\w{2}\.)?\w+',
        r'(?:watch|front)\.njpwworld\.com',
        r'qub\.ca/vrai',
        r'(?:beta\.)?crunchyroll\.com',
        r'viki\.com',
        r'deezer\.com',
    )

    _TESTS = [{
        # https://github.com/yt-dlp/yt-dlp/issues/4309
        'url': 'https://peacocktv.com/watch/playback/vod/GMO_00000000073159_01/f9d03003-eb04-3c7f-a7b6-a83ab7eb55bc',
        'only_matching': True,
    }, {
        # https://github.com/yt-dlp/yt-dlp/issues/1719,
        'url': 'https://www.channel4.com/programmes/gurren-lagann/on-demand/69960-001',
        'only_matching': True,
    }, {
        # https://github.com/yt-dlp/yt-dlp/issues/1548
        'url': 'https://www.channel5.com/show/uk-s-strongest-man-2021/season-2021/episode-1',
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
        # https://github.com/yt-dlp/yt-dlp/issues/4122
        'url': 'https://www.tvnz.co.nz/shows/ice-airport-alaska/episodes/s1-e1',
        'only_matching': True,
    }, {
        # https://github.com/yt-dlp/yt-dlp/issues/1922
        'url': 'https://www.oneplus.ch/play/1008188',
        'only_matching': True,
    }, {
        # https://github.com/yt-dlp/yt-dlp/issues/1140
        'url': 'https://www.artstation.com/learning/courses/dqQ/character-design-masterclass-with-serge-birault/chapters/Rxn3/introduction',
        'only_matching': True,
    }, {
        # https://github.com/yt-dlp/yt-dlp/issues/3544
        'url': 'https://www.philo.com/player/player/vod/Vk9EOjYwODU0ODg5OTY0ODY0OTQ5NA',
        'only_matching': True,
    }, {
        # https://github.com/yt-dlp/yt-dlp/issues/3533
        'url': 'https://www.mech-plus.com/player/24892/stream?assetType=episodes&playlist_id=6',
        'only_matching': True,
    }, {
        'url': 'https://watch.mech-plus.com/details/25240?playlist_id=6',
        'only_matching': True,
    }, {
        # https://github.com/yt-dlp/yt-dlp/issues/2934
        'url': 'https://www.aha.video/player/movie/lucky-man',
        'only_matching': True,
    }, {
        # https://github.com/yt-dlp/yt-dlp/issues/2743
        'url': 'https://mubi.com/films/the-night-doctor',
        'only_matching': True,
    }, {
        # https://github.com/yt-dlp/yt-dlp/issues/3287
        'url': 'https://www.vootkids.com/movies/chhota-bheem-the-rise-of-kirmada/764459',
        'only_matching': True,
    }, {
        # https://github.com/yt-dlp/yt-dlp/issues/2744
        'url': 'https://www.nowtv.it/watch/home/asset/and-just-like-that/skyserie_f8fe979772e8437d8a61ab83b6d293e9/seasons/1/episodes/8/R_126182_HD',
        'only_matching': True,
    }, {
        # https://github.com/yt-dlp/yt-dlp/issues/5557
        'url': 'https://tv.apple.com/it/show/loot---una-fortuna/umc.cmc.5erbujil1mpazuerhr1udnk45?ctx_brand=tvs.sbd.4000',
        'only_matching': True,
    }, {
        # https://github.com/yt-dlp/yt-dlp/issues/3072
        'url': 'https://www.joyn.de/play/serien/clannad/1-1-wo-die-kirschblueten-fallen',
        'only_matching': True,
    }, {
        # https://github.com/yt-dlp/yt-dlp/issues/7323
        'url': 'https://music.amazon.co.jp/albums/B088Y368TK',
        'only_matching': True,
    }, {
        # https://github.com/yt-dlp/yt-dlp/issues/7323
        'url': 'https://www.amazon.co.jp/gp/video/detail/B09X5HBYRS/',
        'only_matching': True,
    }, {
        # https://github.com/yt-dlp/yt-dlp/issues/6125
        'url': 'https://www.primevideo.com/region/eu/detail/0H3DDB4KBJFNDCKKLHNRLRLVKQ/ref=atv_br_def_r_br_c_unkc_1_10',
        'only_matching': True,
    }, {
        # https://github.com/yt-dlp/yt-dlp/issues/5740
        'url': 'https://resource.inkryptvideos.com/v2-a83ns52/iframe/index.html#video_id=7999ea0f6e03439eb40d056258c2d736&otp=xxx',
        'only_matching': True,
    }, {
        # https://github.com/yt-dlp/yt-dlp/issues/5767
        'url': 'https://www.hulu.com/movie/anthem-6b25fac9-da2b-45a3-8e09-e4156b0471cc',
        'only_matching': True,
    }, {
        # https://github.com/yt-dlp/yt-dlp/pull/8570
        'url': 'https://watch.njpwworld.com/player/36447/series?assetType=series',
        'only_matching': True,
    }, {
        'url': 'https://front.njpwworld.com/p/s_series_00563_16_bs',
        'only_matching': True,
    }, {
        'url': 'https://www.qub.ca/vrai/l-effet-bocuse-d-or/saison-1/l-effet-bocuse-d-or-saison-1-bande-annonce-1098225063',
        'only_matching': True,
    }, {
        'url': 'https://www.crunchyroll.com/watch/GY2P1Q98Y/to-the-future',
        'only_matching': True,
    }, {
        'url': 'https://beta.crunchyroll.com/pt-br/watch/G8WUN8VKP/the-ruler-of-conspiracy',
        'only_matching': True,
    }, {
        'url': 'https://www.viki.com/videos/1175236v-choosing-spouse-by-lottery-episode-1',
        'only_matching': True,
    }, {
        'url': 'http://www.deezer.com/playlist/176747451',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        raise ExtractorError(
            f'The requested site is known to use DRM protection. '
            f'It will {self._downloader._format_err("NOT", self._downloader.Styles.EMPHASIS)} be supported.{LF}'
            f'Please {self._downloader._format_err("DO NOT", self._downloader.Styles.ERROR)} open an issue, '
            'unless you have evidence that the video is not DRM protected', expected=True)


class KnownPiracyIE(UnsupportedInfoExtractor):
    """Sites that have been deemed to be piracy

    In order for this to not end up being a catalog of piracy sites,
    only sites that were once supported should be added to this list
    """

    URLS = (
        r'dood\.(?:to|watch|so|pm|wf|re)',
        # Sites youtube-dl supports, but we won't
        r'viewsb\.com',
        r'filemoon\.sx',
        r'hentai\.animestigma\.com',
        r'thisav\.com',
        r'gounlimited\.to',
        r'highstream\.tv',
        r'uqload\.com',
        r'vedbam\.xyz',
        r'vadbam\.net'
        r'vidlo\.us',
        r'wolfstream\.tv',
        r'xvideosharing\.com',
        r'(?:\w+\.)?viidshar\.com',
        r'sxyprn\.com',
        r'jable\.tv',
        r'91porn\.com',
        r'einthusan\.(?:tv|com|ca)',
        r'yourupload\.com',
    )

    _TESTS = [{
        'url': 'http://dood.to/e/5s1wmbdacezb',
        'only_matching': True,
    }, {
        'url': 'https://thisav.com/en/terms',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        raise ExtractorError(
            f'This website is no longer supported since it has been determined to be primarily used for piracy.{LF}'
            f'{self._downloader._format_err("DO NOT", self._downloader.Styles.ERROR)} open issues for it', expected=True)
