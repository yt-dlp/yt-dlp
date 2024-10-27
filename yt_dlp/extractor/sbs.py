from .common import InfoExtractor
from ..networking import HEADRequest
from ..utils import (
    float_or_none,
    int_or_none,
    parse_duration,
    parse_iso8601,
    traverse_obj,
    update_url_query,
    url_or_none,
)


class SBSIE(InfoExtractor):
    IE_DESC = 'sbs.com.au'
    _VALID_URL = r'''(?x)
        https?://(?:www\.)?sbs\.com\.au/(?:
            ondemand(?:
                /video/(?:single/)?|
                /(?:movie|tv-program)/[^/]+/|
                /(?:tv|news)-series/(?:[^/]+/){3}|
                .*?\bplay=|/watch/
            )|news/(?:embeds/)?video/
        )(?P<id>[0-9]+)'''
    _EMBED_REGEX = [r'''(?x)]
            (?:
                <meta\s+property="og:video"\s+content=|
                <iframe[^>]+?src=
            )
            (["\'])(?P<url>https?://(?:www\.)?sbs\.com\.au/ondemand/video/.+?)\1''']

    _TESTS = [{
        # Original URL is handled by the generic IE which finds the iframe:
        # http://www.sbs.com.au/thefeed/blog/2014/08/21/dingo-conservation
        'url': 'http://www.sbs.com.au/ondemand/video/single/320403011771/?source=drupal&vertical=thefeed',
        'md5': '31f84a7a19b53635db63c73f8ab0c4a7',
        'info_dict': {
            'id': '320403011771',  # '_rFBPRPO4pMR',
            'ext': 'mp4',
            'title': 'Dingo Conservation (The Feed)',
            'description': 'md5:f250a9856fca50d22dec0b5b8015f8a5',
            'thumbnail': r're:https?://.*\.jpg',
            'duration': 308,
            'timestamp': 1408613220,
            'upload_date': '20140821',
            'uploader': 'SBSC',
        },
        'expected_warnings': ['Unable to download JSON metadata'],
    }, {
        'url': 'http://www.sbs.com.au/ondemand/video/320403011771/Dingo-Conservation-The-Feed',
        'only_matching': True,
    }, {
        'url': 'http://www.sbs.com.au/news/video/471395907773/The-Feed-July-9',
        'only_matching': True,
    }, {
        'url': 'https://www.sbs.com.au/ondemand/?play=1836638787723',
        'only_matching': True,
    }, {
        'url': 'https://www.sbs.com.au/ondemand/program/inside-windsor-castle?play=1283505731842',
        'only_matching': True,
    }, {
        'url': 'https://www.sbs.com.au/news/embeds/video/1840778819866',
        'only_matching': True,
    }, {
        'url': 'https://www.sbs.com.au/ondemand/watch/1698704451971',
        'only_matching': True,
    }, {
        'url': 'https://www.sbs.com.au/ondemand/movie/coherence/1469404227931',
        'only_matching': True,
    }, {
        'note': 'Live stream',
        'url': 'https://www.sbs.com.au/ondemand/video/1726824003663/sbs-24x7-live-stream-nsw',
        'only_matching': True,
    }, {
        'url': 'https://www.sbs.com.au/ondemand/news-series/dateline/dateline-2022/dateline-s2022-ep26/2072245827515',
        'only_matching': True,
    }, {
        'url': 'https://www.sbs.com.au/ondemand/tv-series/the-handmaids-tale/season-5/the-handmaids-tale-s5-ep1/2065631811776',
        'only_matching': True,
    }, {
        'url': 'https://www.sbs.com.au/ondemand/tv-program/autun-romes-forgotten-sister/2116212803602',
        'only_matching': True,
    }]

    _GEO_COUNTRIES = ['AU']
    _AUS_TV_PARENTAL_GUIDELINES = {
        'P': 0,
        'C': 7,
        'G': 0,
        'PG': 0,
        'M': 14,
        'MA15+': 15,
        'MAV15+': 15,
        'R18+': 18,
    }
    _PLAYER_API = 'https://www.sbs.com.au/api/v3'

    def _real_extract(self, url):
        video_id = self._match_id(url)
        formats, subtitles = self._extract_smil_formats_and_subtitles(
            update_url_query(f'{self._PLAYER_API}/video_smil', {'id': video_id}), video_id)

        if not formats:
            urlh = self._request_webpage(
                HEADRequest('https://sbs-vod-prod-01.akamaized.net/'), video_id,
                note='Checking geo-restriction', fatal=False, expected_status=403)
            if urlh:
                error_reasons = urlh.headers.get_all('x-error-reason') or []
                if 'geo-blocked' in error_reasons:
                    self.raise_geo_restricted(countries=['AU'])
            self.raise_no_formats('No formats are available', video_id=video_id)

        media = traverse_obj(self._download_json(
            f'{self._PLAYER_API}/video_stream', video_id, fatal=False,
            query={'id': video_id, 'context': 'tv'}), ('video_object', {dict})) or {}

        media.update(self._download_json(
            f'https://catalogue.pr.sbsod.com/mpx-media/{video_id}',
            video_id, fatal=not media) or {})

        # For named episodes, use the catalogue's title to set episode, rather than generic 'Episode N'.
        if traverse_obj(media, ('partOfSeries', {dict})):
            media['epName'] = traverse_obj(media, ('title', {str}))

        return {
            'id': video_id,
            **traverse_obj(media, {
                'title': ('name', {str}),
                'description': ('description', {str}),
                'channel': ('taxonomy', 'channel', 'name', {str}),
                'series': ((('partOfSeries', 'name'), 'seriesTitle'), {str}),
                'series_id': ((('partOfSeries', 'uuid'), 'seriesID'), {str}),
                'season_number': ('seasonNumber', {int_or_none}),
                'episode': ('epName', {str}),
                'episode_number': ('episodeNumber', {int_or_none}),
                'timestamp': (('datePublished', ('publication', 'startDate')), {parse_iso8601}),
                'release_year': ('releaseYear', {int_or_none}),
                'duration': ('duration', ({float_or_none}, {parse_duration})),
                'is_live': ('liveStream', {bool}),
                'age_limit': (('classificationID', 'contentRating'), {str.upper}, {
                    lambda x: self._AUS_TV_PARENTAL_GUIDELINES.get(x)}),  # dict.get is unhashable in py3.7
            }, get_all=False),
            **traverse_obj(media, {
                'categories': (('genres', ...), ('taxonomy', ('genre', 'subgenre'), 'name'), {str}),
                'tags': (('consumerAdviceTexts', ('sbsSubCertification', 'consumerAdvice')), ..., {str}),
                'thumbnails': ('thumbnails', lambda _, v: url_or_none(v['contentUrl']), {
                    'id': ('name', {str}),
                    'url': 'contentUrl',
                    'width': ('width', {int_or_none}),
                    'height': ('height', {int_or_none}),
                }),
            }),
            'formats': formats,
            'subtitles': subtitles,
            'uploader': 'SBSC',
        }
