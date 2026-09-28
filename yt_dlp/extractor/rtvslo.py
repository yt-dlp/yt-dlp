import functools
import re

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    OnDemandPagedList,
    base_url,
    int_or_none,
    parse_duration,
    traverse_obj,
    unified_timestamp,
    url_or_none,
    urljoin,
)


class RTVSLOIE(InfoExtractor):
    IE_NAME = 'rtvslo.si'
    _VALID_URL = r'''(?x)
        https?://(?:
            (?:365|4d)\.rtvslo.si/(?:arhiv|podkast)/[^/?#&;]+|
            (?:www\.)?rtvslo\.si/rtv365/arhiv|
            (?:val202)\.rtvslo\.si/podkast/[^/?#&;]+/[^/?#&;]+
        )/(?P<id>\d+)'''
    _GEO_COUNTRIES = ['SI']

    _API_BASE = 'https://api.rtvslo.si/ava/{}/{}?client_id=82013fb3a531d5414f478747c1aca622'
    SUB_LANGS_MAP = {'Slovenski': 'sl'}

    _TESTS = [{
        'url': 'https://www.rtvslo.si/rtv365/arhiv/174842550?s=tv',
        'info_dict': {
            'id': '174842550',
            'ext': 'mp4',
            'release_timestamp': 1643140032,
            'upload_date': '20220125',
            'series': 'Dnevnik',
            'thumbnail': 'https://img.rtvcdn.si/_up/ava/ava_misc/show_logos/92/dnevnik_3_wide2.jpg',
            'description': 'md5:76a18692757aeb8f0f51221106277dd2',
            'timestamp': 1643137046,
            'title': 'Dnevnik',
            'series_id': '92',
            'release_date': '20220125',
            'duration': 1789,
        },
    }, {
        'url': 'https://365.rtvslo.si/arhiv/utrip/174843754',
        'info_dict': {
            'id': '174843754',
            'ext': 'mp4',
            'series_id': '94',
            'release_date': '20220129',
            'timestamp': 1643484455,
            'title': 'Utrip',
            'duration': 813,
            'thumbnail': 'https://img.rtvcdn.si/_up/ava/ava_misc/show_logos/94/utrip_1_wide2.jpg',
            'description': 'md5:77f2892630c7b17bb7a5bb84319020c9',
            'release_timestamp': 1643485825,
            'upload_date': '20220129',
            'series': 'Utrip',
        },
    }, {
        'url': 'https://365.rtvslo.si/arhiv/il-giornale-della-sera/174844609',
        'info_dict': {
            'id': '174844609',
            'ext': 'mp3',
            'series_id': '106615841',
            'title': 'Il giornale della sera',
            'duration': 1328,
            'series': 'Il giornale della sera',
            'timestamp': 1643743800,
            'release_timestamp': 1643745424,
            'thumbnail': 'https://img.rtvcdn.si/_up/ava/ava_misc/channel_logos/CAPO_wide2.jpg',
            'upload_date': '20220201',
            'tbr': 128000,
            'release_date': '20220201',
        },
    }, {
        'url': 'https://365.rtvslo.si/arhiv/razred-zase/148350750',
        'info_dict': {
            'id': '148350750',
            'ext': 'mp4',
            'title': 'Prvi šolski dan, mozaična oddaja za mlade',
            'series': 'Razred zase',
            'series_id': '148185730',
            'duration': 1481,
            'upload_date': '20121019',
            'timestamp': 1350672122,
            'release_date': '20121019',
            'release_timestamp': 1350672122,
            'thumbnail': 'https://img.rtvcdn.si/_up/ava/ava_misc/show_logos/148185730/razred_zase_2014_logo_4d_wide2.jpg',
        },
    }, {
        'url': 'https://4d.rtvslo.si/arhiv/dnevnik/174842550',
        'only_matching': True,
    }, {
        'url': 'https://val202.rtvslo.si/podkast/izstekani/52137502/175205734',
        'info_dict': {
            'id': '175205734',
            'ext': 'mp3',
            'title': 'Izštekani Koala Voice v Cankarjevem domu',
            'series': 'Izštekani',
            'series_id': '52137502',
            'duration': 7798,
            'upload_date': '20260312',
            'timestamp': 1773355398,
            'release_date': '20260312',
            'release_timestamp': 1773356585,
            'thumbnail': 'https://img.rtvcdn.si/_up/ava/ava_misc/show_logos/52137502/logo_1_wide2.jpg',
            'description': 'md5:f5fc2dcf75d1864b6d7a1ecace192053',
        },
    }, {
        'url': 'https://365.rtvslo.si/podkast/toplovod/175054103',
        'info_dict': {
            'id': '175054103',
            'ext': 'mp3',
            'title': 'Zadnji Toplovod',
            'series': 'Toplovod',
            'series_id': '185',
            'duration': 3508,
            'upload_date': '20240618',
            'timestamp': 1718743800,
            'release_date': '20240618',
            'release_timestamp': 1718750166,
            'thumbnail': 'https://img.rtvcdn.si/_up/ava/ava_misc/show_logos/185/toplovod_1280x720_wide2.jpg',
            'description': 'md5:915075e267ecbac1343e002e524966bf',
        },
    }]

    def _real_extract(self, url):
        v_id = self._match_id(url)
        meta = self._download_json(self._API_BASE.format('getRecordingDrm', v_id), v_id)['response']

        thumbs = [{'id': k, 'url': v, 'http_headers': {'Accept': 'image/jpeg'}}
                  for k, v in (meta.get('images') or {}).items()]

        subs = {}
        for s in traverse_obj(meta, 'subs', 'subtitles', default=[]):
            lang = self.SUB_LANGS_MAP.get(s.get('language'), s.get('language') or 'und')
            subs.setdefault(lang, []).append({
                'url': s.get('file'),
                'ext': traverse_obj(s, 'format', expected_type=str.lower),
            })

        jwt = meta.get('jwt')
        if not jwt:
            raise ExtractorError('Site did not provide an authentication token, cannot proceed.')

        media = self._download_json(self._API_BASE.format('getMedia', v_id), v_id, query={'jwt': jwt})['response']

        formats = []
        skip_protocols = ['smil', 'f4m', 'dash']
        adaptive_url = traverse_obj(media, ('addaptiveMedia', 'hls_sec'), expected_type=url_or_none)
        if adaptive_url:
            formats = self._extract_wowza_formats(adaptive_url, v_id, skip_protocols=skip_protocols)

        adaptive_url = traverse_obj(media, ('addaptiveMedia_sl', 'hls_sec'), expected_type=url_or_none)
        if adaptive_url:
            for f in self._extract_wowza_formats(adaptive_url, v_id, skip_protocols=skip_protocols):
                formats.append({
                    **f,
                    'format_id': 'sign-' + f['format_id'],
                    'format_note': 'Sign language interpretation', 'preference': -10,
                    'language': (
                        'slv' if f.get('language') == 'eng' and f.get('acodec') != 'none'
                        else f.get('language')),
                })

        for mediafile in traverse_obj(media, ('mediaFiles', lambda _, v: url_or_none(v['streams']['https']))):
            formats.append(traverse_obj(mediafile, {
                'url': ('streams', 'https'),
                'ext': ('mediaType', {str.lower}),
                'width': ('width', {int_or_none}),
                'height': ('height', {int_or_none}),
                'tbr': ('bitrate', {int_or_none}),
                'filesize': ('filesize', {int_or_none}),
            }))

        for mediafile in traverse_obj(media, ('mediaFiles', lambda _, v: url_or_none(v['streams']['hls_sec']))):
            formats.extend(self._extract_wowza_formats(
                mediafile['streams']['hls_sec'], v_id, skip_protocols=skip_protocols))

        if any('intermission.mp4' in x['url'] for x in formats):
            self.raise_geo_restricted(countries=self._GEO_COUNTRIES, metadata_available=True)
        if any('dummy_720p.mp4' in x.get('manifest_url', '') for x in formats) and meta.get('stub') == 'error':
            raise ExtractorError(f'{self.IE_NAME} said: Clip not available', expected=True)

        return {
            'id': v_id,
            'webpage_url': ''.join(traverse_obj(meta, ('canonical', ('domain', 'path')))),
            'title': meta.get('title'),
            'formats': formats,
            'subtitles': subs,
            'thumbnails': thumbs,
            'description': meta.get('description'),
            'timestamp': unified_timestamp(traverse_obj(meta, 'broadcastDate', ('broadcastDates', 0))),
            'release_timestamp': unified_timestamp(meta.get('recordingDate')),
            'duration': meta.get('duration') or parse_duration(meta.get('length')),
            'tags': meta.get('genre'),
            'series': meta.get('showName'),
            'series_id': meta.get('showId'),
        }


class RTVSLOShowIE(InfoExtractor):
    IE_NAME = 'rtvslo.si:show'

    _PAGE_SIZES = {
        'podkasti': 10,
        'oddaja': 50,
    }
    #    _VALID_URL = r'https?://(?P<service>(365|4d|val202))\.rtvslo.si/(?P<type>(oddaja|podkasti|podkast))/(?P<title>[^/]+)/(?P<id>\d+)/?$'
    _VALID_URL = r'''(?x)
            https?://
            (?P<service>365|4d|val202)\.rtvslo\.si/
            (?P<type>
                (?:(?<=365\.rtvslo\.si/)|(?<=4d\.rtvslo\.si/))(?:oddaja|podkasti)
                |
                (?:(?<=val202\.rtvslo\.si/))podkast
            )/
            (?P<title>[^/]+)/
            (?P<id>\d+)
            /?$
        '''

    _TESTS = [{
        'url': 'https://365.rtvslo.si/oddaja/ekipa-bled/173250997',
        'info_dict': {
            'id': '173250997',
            'title': 'Ekipa Bled',
            'description': 'md5:c88471e27a1268c448747a5325319ab7',
        },
        'playlist_count': 18,
    }, {
        'url': 'https://365.rtvslo.si/oddaja/tarca/397',
        'info_dict': {
            'id': '397',
            'title': 'Tarča',
            'description': 'md5:a1861ba86c18ac3f7096cd79002e0922',
        },
        'playlist_mincount': 687,
    }, {
        'url': 'https://365.rtvslo.si/podkasti/toplovod/185',
        'info_dict': {
            'id': '185',
            'title': 'Toplovod',
            'description': 'md5:4367c366228f1d500ad66d0fa65add3a',
        },
        'playlist_count': 261,
    }, {
        'url': 'https://val202.rtvslo.si/podkast/izstekani/52137502',
        'info_dict': {
            'id': '52137502',
            'title': 'Izštekani',
            'description': 'md5:bd2232a56925d2bf565a68d5f2e443bf',
        },
        'expected_warnings': ['Val202 is not supported redirecting to RTV365'],
        'playlist_count': 192,
    }]

    def _fetch_page(self, url, playlist_id, title, page):
        page += 1

        url_without_query = url.split('?')[0]
        url_p = f'{url_without_query}?p={page}'
        base = base_url(url)

        webpage = self._download_webpage(url_p, playlist_id, note=f'Fetching {title}, page: {page}')

        episodes = set(re.findall(r'<a [^>]*\bhref="(/(?:arhiv|podkast)/[^"]+)"', webpage))

        yield from (self.url_result(urljoin(base, episode)) for episode in episodes)

    def _real_extract(self, url):
        playlist_id = self._match_id(url)
        url_type = self._match_valid_url(url).group('type')
        url_title = self._match_valid_url(url).group('title')
        url_service = self._match_valid_url(url).group('service')

        if url_service == 'val202':
            new_url = f'https://365.rtvslo.si/podkasti/{url_title}/{playlist_id}'
            self.report_warning(f'Val202 is not supported redirecting to RTV365. ({new_url})')
            # Url is rewritten because whatever is hosted on val202 is also hosted on 365 which has explicit pagination.
            return self._real_extract(new_url)

        webpage = self._download_webpage(url, playlist_id)

        description = self._og_search_description(webpage)
        title = self._og_search_title(webpage)

        return self.playlist_result(
            OnDemandPagedList(
                functools.partial(
                    self._fetch_page, url, playlist_id, title,
                ),
                self._PAGE_SIZES[url_type]),
            playlist_id=playlist_id,
            playlist_title=title,
            playlist_description=description,
        )
