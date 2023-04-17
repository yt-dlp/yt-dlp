
import sys

from .common import InfoExtractor
from ..compat import (
    compat_HTTPError,
    compat_str,
)
from ..utils import (
    error_to_compat_str,
    ExtractorError,
    float_or_none,
    GeoRestrictedError,
    int_or_none,
    parse_duration,
    parse_iso8601,
    traverse_obj,
    update_url_query,
    url_or_none,
    variadic,
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
            'tags': [],
            'categories': [],
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

    def __handle_request_webpage_error(self, err, video_id=None, errnote=None, fatal=True):
        if errnote is False:
            return False
        if errnote is None:
            errnote = 'Unable to download webpage'

        errmsg = '%s: %s' % (errnote, error_to_compat_str(err))
        if fatal:
            raise ExtractorError(errmsg, sys.exc_info()[2], cause=err, video_id=video_id)
        else:
            self._downloader.report_warning(errmsg)
            return False

    def _download_webpage_handle(self, url, video_id, *args, **kwargs):
        # note, errnote, fatal, encoding, data, headers={}, query, expected_status
        # specialised to detect geo-block

        errnote = args[2] if len(args) > 2 else kwargs.get('errnote')
        fatal = args[3] if len(args) > 3 else kwargs.get('fatal')
        exp = args[7] if len(args) > 7 else kwargs.get('expected_status')

        exp = variadic(exp or [], allowed_types=(compat_str, ))
        if 403 not in exp and '403' not in exp:
            exp = list(exp)
            exp.append(403)
        else:
            exp = None

        if exp:
            if len(args) > 7:
                args = list(args)
                args[7] = exp
            else:
                kwargs['expected_status'] = exp

        ret = super(SBSIE, self)._download_webpage_handle(url, video_id, *args, **kwargs)
        if ret is False:
            return ret
        webpage, urlh = ret

        if urlh.getcode() == 403:
            if urlh.headers.get('x-error-reason') == 'geo-blocked':
                countries = ['AU']
                if fatal:
                    self.raise_geo_restricted(countries=countries)
                err = GeoRestrictedError(
                    'This Australian content is not available from your location due to geo restriction',
                    countries=countries)
            else:
                err = compat_HTTPError(urlh.geturl(), 403, 'HTTP Error 403: Forbidden', urlh.headers, urlh)
            ret = self.__handle_request_webpage_error(err, video_id, errnote, fatal)

        return ret

    def _extract_m3u8_formats(self, m3u8_url, video_id, *args, **kwargs):
        # ext, entry_protocol, preference, m3u8_id, note, errnote, fatal,
        # live, data, headers, query
        entry_protocol = args[1] if len(args) > 1 else kwargs.get('entry_protocol')
        if not entry_protocol:
            entry_protocol = 'm3u8_native'
            if len(args) > 1:
                args = list(args)
                args[1] = entry_protocol
            else:
                kwargs['entry_protocol'] = entry_protocol

        return super(SBSIE, self)._extract_m3u8_formats(m3u8_url, video_id, *args, **kwargs)

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
    _CATALOGUE_API = 'https://catalogue.pr.sbsod.com/'

    def _call_api(self, video_id, path, query=None, data=None, headers=None, fatal=True):
        return self._download_json(update_url_query(
            self._CATALOGUE_API + path, query),
            video_id, headers=headers, fatal=fatal) or {}

    def _get_smil_url(self, video_id):
        return update_url_query(
            self._PLAYER_API + 'video_smil', {'id': video_id})

    def _get_player_data(self, video_id, headers=None, fatal=False):
        return self._download_json(update_url_query(
            self._PLAYER_API + 'video_stream', {'id': video_id, 'context': 'tv'}),
            video_id, headers=headers, fatal=fatal) or {}

    def _real_extract(self, url):
        video_id = self._match_id(url)
        # get media links directly though later metadata may contain contentUrl
        smil_url = self._get_smil_url(video_id)
        formats, subtitles = self._extract_smil_formats_and_subtitles(smil_url, video_id, fatal=False) or ([], {})

        # try for metadata from the same source
        player_data = self._get_player_data(video_id, fatal=False)
        media = traverse_obj(player_data, 'video_object', expected_type=dict) or {}
        # get, or add, metadata from catalogue
        media.update(self._call_api(video_id, 'mpx-media/' + video_id, fatal=not media))

        # utils candidate for use with traverse_obj()
        def txt_or_none(s):
            return (s.strip() or None) if isinstance(s, compat_str) else None

        # expected_type fn for thumbs
        def xlate_thumb(t):
            u = url_or_none(t.get('contentUrl'))
            return u and {
                'id': t.get('name'),
                'url': u,
                'width': int_or_none(t.get('width')),
                'height': int_or_none(t.get('height')),
            }

        # may be numeric or timecoded
        def really_parse_duration(d):
            result = float_or_none(d)
            if result is None:
                result = parse_duration(d)
            return result

        def traverse_media(*args, **kwargs):
            if 'expected_type' not in kwargs:
                kwargs['expected_type'] = txt_or_none
            return traverse_obj(media, *args, **kwargs)

        return {
            'id': video_id,
            'title': media['name'],
            'formats': formats,
            'description': traverse_media('description'),
            'categories': traverse_media(
                ('genres', Ellipsis), ('taxonomy', ('genre', 'subgenre'), 'name')),
            'tags': traverse_media(
                (('consumerAdviceTexts', ('sbsSubCertification', 'consumerAdvice')), Ellipsis)),
            'age_limit': self._AUS_TV_PARENTAL_GUIDELINES.get(traverse_media(
                'classificationID', 'contentRating', default='').upper()),
            'thumbnails': traverse_media(('thumbnails', Ellipsis),
                                         expected_type=xlate_thumb),
            'duration': traverse_media('duration',
                                       expected_type=really_parse_duration),
            'series': traverse_media(('partOfSeries', 'name'), 'seriesTitle'),
            'series_id': traverse_media(('partOfSeries', 'uuid'), 'seriesID'),
            'season_number': traverse_media(
                (('partOfSeries', None), 'seasonNumber'),
                expected_type=int_or_none, get_all=False),
            'episode_number': traverse_media('episodeNumber',
                                             expected_type=int_or_none),
            'release_year': traverse_media('releaseYear',
                                           expected_type=int_or_none),
            'subtitles': subtitles,
            'timestamp': traverse_media(
                'datePublished', ('publication', 'startDate'),
                expected_type=parse_iso8601),
            'channel': traverse_media(('taxonomy', 'channel', 'name')),
            'uploader': 'SBSC',
        }
