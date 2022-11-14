import json
import re

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    unified_strdate,
    urlencode_postdata,
    xpath_element,
    xpath_text,
    update_url_query,
    js_to_json,
)


class Laola1TvEmbedIE(InfoExtractor):
    IE_NAME = 'laola1tv:embed'
    _VALID_URL = r'https?://(?:www\.)?laola1\.tv/titanplayer\.php\?.*?\bvideoid=(?P<id>\d+)'
    _TESTS = [{
        # flashvars.premium = "false";
        'url': 'https://www.laola1.tv/titanplayer.php?videoid=708065&type=V&lang=en&portal=int&customer=1024',
        'info_dict': {
            'id': '708065',
            'ext': 'mp4',
            'title': 'MA Long CHN - FAN Zhendong CHN',
            'uploader': 'ITTF - International Table Tennis Federation',
            'upload_date': '20161211',
        },
    }]

    def _extract_token_url(self, stream_access_url, video_id, data):
        return self._download_json(
            self._proto_relative_url(stream_access_url, 'https:'), video_id,
            headers={
                'Content-Type': 'application/json',
            }, data=json.dumps(data).encode())['data']['stream-access'][0]

    def _extract_formats(self, token_url, video_id):
        token_doc = self._download_xml(
            token_url, video_id, 'Downloading token',
            headers=self.geo_verification_headers())

        token_attrib = xpath_element(token_doc, './/token').attrib

        if token_attrib['status'] != '0':
            raise ExtractorError(
                'Token error: %s' % token_attrib['comment'], expected=True)

        formats = self._extract_akamai_formats(
            '%s?hdnea=%s' % (token_attrib['url'], token_attrib['auth']),
            video_id)
        self._sort_formats(formats)
        return formats

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        flash_vars = self._search_regex(
            r'(?s)flashvars\s*=\s*({.+?});', webpage, 'flash vars')

        def get_flashvar(x, *args, **kwargs):
            flash_var = self._search_regex(
                r'%s\s*:\s*"([^"]+)"' % x,
                flash_vars, x, default=None)
            if not flash_var:
                flash_var = self._search_regex([
                    r'flashvars\.%s\s*=\s*"([^"]+)"' % x,
                    r'%s\s*=\s*"([^"]+)"' % x],
                    webpage, x, *args, **kwargs)
            return flash_var

        hd_doc = self._download_xml(
            'http://www.laola1.tv/server/hd_video.php', video_id, query={
                'play': get_flashvar('streamid'),
                'partner': get_flashvar('partnerid'),
                'portal': get_flashvar('portalid'),
                'lang': get_flashvar('sprache'),
                'v5ident': '',
            })

        _v = lambda x, **k: xpath_text(hd_doc, './/video/' + x, **k)
        title = _v('title', fatal=True)

        token_url = None
        premium = get_flashvar('premium', default=None)
        if premium:
            token_url = update_url_query(
                _v('url', fatal=True), {
                    'timestamp': get_flashvar('timestamp'),
                    'auth': get_flashvar('auth'),
                })
        else:
            data_abo = urlencode_postdata(
                dict((i, v) for i, v in enumerate(_v('req_liga_abos').split(','))))
            stream_access_url = update_url_query(
                'https://club.laola1.tv/sp/laola1/api/v3/user/session/premium/player/stream-access', {
                    'videoId': _v('id'),
                    'target': self._search_regex(r'vs_target = (\d+);', webpage, 'vs target'),
                    'label': _v('label'),
                    'area': _v('area'),
                })
            token_url = self._extract_token_url(stream_access_url, video_id, data_abo)

        formats = self._extract_formats(token_url, video_id)

        categories_str = _v('meta_sports')
        categories = categories_str.split(',') if categories_str else []
        is_live = _v('islive') == 'true'

        return {
            'id': video_id,
            'title': title,
            'upload_date': unified_strdate(_v('time_date')),
            'uploader': _v('meta_organisation'),
            'categories': categories,
            'is_live': is_live,
            'formats': formats,
        }


class Laola1TvBaseIE(Laola1TvEmbedIE):
    def _extract_video(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)

        if 'Dieser Livestream ist bereits beendet.' in webpage:
            raise ExtractorError('This live stream has already finished.', expected=True)

        conf = self._parse_json(self._search_regex(
            r'(?s)conf\s*=\s*({.+?});', webpage, 'conf'),
            display_id,
            transform_source=lambda s: js_to_json(re.sub(r'shareurl:.+,', '', s)))
        video_id = conf['videoid']

        config = self._download_json(conf['configUrl'], video_id, query={
            'videoid': video_id,
            'partnerid': conf['partnerid'],
            'language': conf.get('language', ''),
            'portal': conf.get('portalid', ''),
        })
        error = config.get('error')
        if error:
            raise ExtractorError('%s said: %s' % (self.IE_NAME, error), expected=True)

        video_data = config['video']
        title = video_data['title']
        is_live = video_data.get('isLivestream') and video_data.get('isLive')
        meta = video_data.get('metaInformation')
        sports = meta.get('sports')
        categories = sports.split(',') if sports else []

        token_url = self._extract_token_url(
            video_data['streamAccess'], video_id,
            video_data['abo']['required'])

        formats = self._extract_formats(token_url, video_id)

        return {
            'id': video_id,
            'display_id': display_id,
            'title': title,
            'description': video_data.get('description'),
            'thumbnail': video_data.get('image'),
            'categories': categories,
            'formats': formats,
            'is_live': is_live,
        }


class Laola1TvIE(Laola1TvBaseIE):
    IE_NAME = 'laola1tv'
    _VALID_URL = r'https?://(?:www\.)?laola1\.tv/[a-z]+-[a-z]+/[^/]+/(?P<id>[^/?#&]+)'

    _TESTS = [{
        'url': 'http://www.laola1.tv/de-de/video/straubing-tigers-koelner-haie/227883.html',
        'info_dict': {
            'id': '227883',
            'display_id': 'straubing-tigers-koelner-haie',
            'ext': 'flv',
            'title': 'Straubing Tigers - Kölner Haie',
            'upload_date': '20140912',
            'is_live': False,
            'categories': ['Eishockey'],
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'http://www.laola1.tv/de-de/video/straubing-tigers-koelner-haie',
        'info_dict': {
            'id': '464602',
            'display_id': 'straubing-tigers-koelner-haie',
            'ext': 'flv',
            'title': 'Straubing Tigers - Kölner Haie',
            'upload_date': '20160129',
            'is_live': False,
            'categories': ['Eishockey'],
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'http://www.laola1.tv/de-de/livestream/2016-03-22-belogorie-belgorod-trentino-diatec-lde',
        'info_dict': {
            'id': '487850',
            'display_id': '2016-03-22-belogorie-belgorod-trentino-diatec-lde',
            'ext': 'flv',
            'title': 'Belogorie BELGOROD - TRENTINO Diatec',
            'upload_date': '20160322',
            'uploader': 'CEV - Europäischer Volleyball Verband',
            'is_live': True,
            'categories': ['Volleyball'],
        },
        'params': {
            'skip_download': True,
        },
        'skip': 'This live stream has already finished.',
    }]

    def _real_extract(self, url):
        return self._extract_video(url)


class EHFTVIE(Laola1TvBaseIE):
    IE_NAME = 'ehftv'
    _VALID_URL = r'https?://(?:www\.)?ehftv\.com/[a-z]+(?:-[a-z]+)?/[^/]+/(?P<id>[^/?#&]+)'

    _TESTS = [{
        'url': 'https://www.ehftv.com/int/video/paris-saint-germain-handball-pge-vive-kielce/1166761',
        'info_dict': {
            'id': '1166761',
            'display_id': 'paris-saint-germain-handball-pge-vive-kielce',
            'ext': 'mp4',
            'title': 'Paris Saint-Germain Handball - PGE Vive Kielce',
            'is_live': False,
            'categories': ['Handball'],
        },
        'params': {
            'skip_download': True,
        },
    }]

    def _real_extract(self, url):
        return self._extract_video(url)


class ITTFIE(InfoExtractor):
    _VALID_URL = r'https?://tv\.ittf\.com/video/[^/]+/(?P<id>\d+)'
    _TEST = {
        'url': 'https://tv.ittf.com/video/peng-wang-wei-matsudaira-kenta/951802',
        'only_matching': True,
    }

    def _real_extract(self, url):
        return self.url_result(
            update_url_query('https://www.laola1.tv/titanplayer.php', {
                'videoid': self._match_id(url),
                'type': 'V',
                'lang': 'en',
                'portal': 'int',
                'customer': 1024,
            }), Laola1TvEmbedIE.ie_key())
