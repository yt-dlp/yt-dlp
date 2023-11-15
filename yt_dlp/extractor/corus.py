from .theplatform import ThePlatformFeedIE
from ..utils import (
    dict_get,
    ExtractorError,
    float_or_none,
    int_or_none,
)


class CorusIE(ThePlatformFeedIE):  # XXX: Do not subclass from concrete IE
    _VALID_URL = r'''(?x)
                    https?://
                        (?:www\.)?
                        (?P<domain>
                            (?:
                                globaltv|
                                etcanada|
                                seriesplus|
                                wnetwork|
                                ytv
                            )\.com|
                            (?:
                                hgtv|
                                foodnetwork|
                                slice|
                                history|
                                showcase|
                                bigbrothercanada|
                                abcspark|
                                disney(?:channel|lachaine)
                            )\.ca
                        )
                        /(?:[^/]+/)*
                        (?:
                            video\.html\?.*?\bv=|
                            videos?/(?:[^/]+/)*(?:[a-z0-9-]+-)?
                        )
                        (?P<id>
                            [\da-f]{8}-[\da-f]{4}-[\da-f]{4}-[\da-f]{4}-[\da-f]{12}|
                            (?:[A-Z]{4})?\d{12,20}
                        )
                    '''
    _TESTS = [{
        'url': 'https://www.hgtv.ca/video/bryan-inc/movie-night-popcorn-with-bryan/870923331648/',
        'info_dict': {
            'id': '870923331648',
            'ext': 'mp4',
            'title': 'Movie Night Popcorn with Bryan',
            'description': 'Bryan whips up homemade popcorn, the old fashion way for Jojo and Lincoln.',
            'upload_date': '20170206',
            'timestamp': 1486392197,
        },
        'params': {
            'skip_download': True,
        },
        'expected_warnings': ['Failed to parse JSON'],
        # FIXME: yt-dlp wrongly raises for geo restriction
    }, {
        'url': 'http://www.foodnetwork.ca/shows/chopped/video/episode/chocolate-obsession/video.html?v=872683587753',
        'only_matching': True,
    }, {
        'url': 'http://etcanada.com/video/873675331955/meet-the-survivor-game-changers-castaways-part-2/',
        'only_matching': True,
    }, {
        'url': 'http://www.history.ca/the-world-without-canada/video/full-episodes/natural-resources/video.html?v=955054659646#video',
        'only_matching': True,
    }, {
        'url': 'http://www.showcase.ca/eyewitness/video/eyewitness++106/video.html?v=955070531919&p=1&s=da#video',
        'only_matching': True,
    }, {
        'url': 'http://www.bigbrothercanada.ca/video/1457812035894/',
        'only_matching': True
    }, {
        'url': 'https://www.bigbrothercanada.ca/video/big-brother-canada-704/1457812035894/',
        'only_matching': True
    }, {
        'url': 'https://www.seriesplus.com/emissions/dre-mary-mort-sur-ordonnance/videos/deux-coeurs-battant/SERP0055626330000200/',
        'only_matching': True
    }, {
        'url': 'https://www.disneychannel.ca/shows/gabby-duran-the-unsittables/video/crybaby-duran-clip/2f557eec-0588-11ea-ae2b-e2c6776b770e/',
        'only_matching': True
    }]
    _GEO_BYPASS = False
    _SITE_MAP = {
        'globaltv': 'series',
        'etcanada': 'series',
        'foodnetwork': 'food',
        'bigbrothercanada': 'series',
        'disneychannel': 'disneyen',
        'disneylachaine': 'disneyfr',
    }

    def _real_extract(self, url):
        domain, video_id = self._match_valid_url(url).groups()
        site = domain.split('.')[0]
        path = self._SITE_MAP.get(site, site)
        if path != 'series':
            path = 'migration/' + path
        video = self._download_json(
            'https://globalcontent.corusappservices.com/templates/%s/playlist/' % path,
            video_id, query={'byId': video_id},
            headers={'Accept': 'application/json'})[0]
        title = video['title']

        formats = []
        for source in video.get('sources', []):
            smil_url = source.get('file')
            if not smil_url:
                continue
            source_type = source.get('type')
            note = 'Downloading%s smil file' % (' ' + source_type if source_type else '')
            resp = self._download_webpage(
                smil_url, video_id, note, fatal=False,
                headers=self.geo_verification_headers())
            if not resp:
                continue
            error = self._parse_json(resp, video_id, fatal=False)
            if error:
                if error.get('exception') == 'GeoLocationBlocked':
                    self.raise_geo_restricted(countries=['CA'])
                raise ExtractorError(error['description'])
            smil = self._parse_xml(resp, video_id, fatal=False)
            if smil is None:
                continue
            namespace = self._parse_smil_namespace(smil)
            formats.extend(self._parse_smil_formats(
                smil, smil_url, video_id, namespace))
        if not formats and video.get('drm'):
            self.report_drm(video_id)

        subtitles = {}
        for track in video.get('tracks', []):
            track_url = track.get('file')
            if not track_url:
                continue
            lang = 'fr' if site in ('disneylachaine', 'seriesplus') else 'en'
            subtitles.setdefault(lang, []).append({'url': track_url})

        metadata = video.get('metadata') or {}
        get_number = lambda x: int_or_none(video.get('pl1$' + x) or metadata.get(x + 'Number'))

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
            'thumbnail': dict_get(video, ('defaultThumbnailUrl', 'thumbnail', 'image')),
            'description': video.get('description'),
            'timestamp': int_or_none(video.get('availableDate'), 1000),
            'subtitles': subtitles,
            'duration': float_or_none(metadata.get('duration')),
            'series': dict_get(video, ('show', 'pl1$show')),
            'season_number': get_number('season'),
            'episode_number': get_number('episode'),
        }
