import re

from .common import InfoExtractor
from ..compat import compat_HTTPError
from ..utils import (
    determine_ext,
    ExtractorError,
    int_or_none,
    float_or_none,
    js_to_json,
    parse_iso8601,
    remove_end,
    strip_or_none,
    try_get,
)


class TV2IE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?tv2\.no/v\d*/(?P<id>\d+)'
    _TESTS = [{
        'url': 'http://www.tv2.no/v/916509/',
        'info_dict': {
            'id': '916509',
            'ext': 'mp4',
            'title': 'Se Frode Gryttens hyllest av Steven Gerrard',
            'description': 'TV 2 Sportens huspoet tar avskjed med Liverpools kaptein Steven Gerrard.',
            'timestamp': 1431715610,
            'upload_date': '20150515',
            'duration': 157,
            'view_count': int,
            'categories': list,
        },
    }, {
        'url': 'http://www.tv2.no/v2/916509',
        'only_matching': True,
    }]
    _PROTOCOLS = ('HLS', 'DASH')
    _GEO_COUNTRIES = ['NO']

    def _real_extract(self, url):
        video_id = self._match_id(url)
        asset = self._download_json('https://sumo.tv2.no/rest/assets/' + video_id, video_id,
                                    'Downloading metadata JSON')
        title = asset['title']
        is_live = asset.get('live') is True

        formats = []
        format_urls = []
        for protocol in self._PROTOCOLS:
            try:
                data = self._download_json('https://api.sumo.tv2.no/play/%s?stream=%s' % (video_id, protocol),
                                           video_id, 'Downloading playabck JSON',
                                           headers={'content-type': 'application/json'},
                                           data='{"device":{"id":"1-1-1","name":"Nettleser (HTML)"}}'.encode())['playback']
            except ExtractorError as e:
                if isinstance(e.cause, compat_HTTPError) and e.cause.code == 401:
                    error = self._parse_json(e.cause.read().decode(), video_id)['error']
                    error_code = error.get('code')
                    if error_code == 'ASSET_PLAYBACK_INVALID_GEO_LOCATION':
                        self.raise_geo_restricted(countries=self._GEO_COUNTRIES)
                    elif error_code == 'SESSION_NOT_AUTHENTICATED':
                        self.raise_login_required()
                    raise ExtractorError(error['description'])
                raise
            items = data.get('streams', [])
            for item in items:
                video_url = item.get('url')
                if not video_url or video_url in format_urls:
                    continue
                format_id = '%s-%s' % (protocol.lower(), item.get('type'))
                if not self._is_valid_url(video_url, video_id, format_id):
                    continue
                format_urls.append(video_url)
                ext = determine_ext(video_url)
                if ext == 'f4m':
                    formats.extend(self._extract_f4m_formats(
                        video_url, video_id, f4m_id=format_id, fatal=False))
                elif ext == 'm3u8':
                    if not data.get('drmProtected'):
                        formats.extend(self._extract_m3u8_formats(
                            video_url, video_id, 'mp4', live=is_live, m3u8_id=format_id, fatal=False))
                elif ext == 'mpd':
                    formats.extend(self._extract_mpd_formats(
                        video_url, video_id, format_id, fatal=False))
                elif ext == 'ism' or video_url.endswith('.ism/Manifest'):
                    pass
                else:
                    formats.append({
                        'url': video_url,
                        'format_id': format_id,
                    })
        if not formats and data.get('drmProtected'):
            self.report_drm(video_id)
        self._sort_formats(formats)

        thumbnails = [{
            'id': type,
            'url': thumb_url,
        } for type, thumb_url in (asset.get('images') or {}).items()]

        return {
            'id': video_id,
            'url': video_url,
            'title': title,
            'description': strip_or_none(asset.get('description')),
            'thumbnails': thumbnails,
            'timestamp': parse_iso8601(asset.get('live_broadcast_time') or asset.get('update_time')),
            'duration': float_or_none(asset.get('accurateDuration') or asset.get('duration')),
            'view_count': int_or_none(asset.get('views')),
            'categories': asset.get('tags', '').split(','),
            'formats': formats,
            'is_live': is_live,
        }


class TV2ArticleIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?tv2\.no/(?:a|\d{4}/\d{2}/\d{2}(/[^/]+)+)/(?P<id>\d+)'
    _TESTS = [{
        'url': 'http://www.tv2.no/2015/05/16/nyheter/alesund/krim/pingvin/6930542',
        'info_dict': {
            'id': '6930542',
            'title': 'Russen hetses etter pingvintyveri - innrømmer å ha åpnet luken på buret',
            'description': 'De fire siktede nekter fortsatt for å ha stjålet pingvinbabyene, men innrømmer å ha åpnet luken til de små kyllingene.',
        },
        'playlist_count': 2,
    }, {
        'url': 'http://www.tv2.no/a/6930542',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        playlist_id = self._match_id(url)

        webpage = self._download_webpage(url, playlist_id)

        # Old embed pattern (looks unused nowadays)
        assets = re.findall(r'data-assetid=["\'](\d+)', webpage)

        if not assets:
            # New embed pattern
            for v in re.findall(r'(?s)TV2ContentboxVideo\(({.+?})\)', webpage):
                video = self._parse_json(
                    v, playlist_id, transform_source=js_to_json, fatal=False)
                if not video:
                    continue
                asset = video.get('assetId')
                if asset:
                    assets.append(asset)

        entries = [
            self.url_result('http://www.tv2.no/v/%s' % asset_id, 'TV2')
            for asset_id in assets]

        title = remove_end(self._og_search_title(webpage), ' - TV2.no')
        description = remove_end(self._og_search_description(webpage), ' - TV2.no')

        return self.playlist_result(entries, playlist_id, title, description)


class KatsomoIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?(?:katsomo|mtv(uutiset)?)\.fi/(?:sarja/[0-9a-z-]+-\d+/[0-9a-z-]+-|(?:#!/)?jakso/(?:\d+/[^/]+/)?|video/prog)(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://www.mtv.fi/sarja/mtv-uutiset-live-33001002003/lahden-pelicans-teki-kovan-ratkaisun-ville-nieminen-pihalle-1181321',
        'info_dict': {
            'id': '1181321',
            'ext': 'mp4',
            'title': 'Lahden Pelicans teki kovan ratkaisun – Ville Nieminen pihalle',
            'description': 'Päätöksen teki Pelicansin hallitus.',
            'timestamp': 1575116484,
            'upload_date': '20191130',
            'duration': 37.12,
            'view_count': int,
            'categories': list,
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
    }, {
        'url': 'http://www.katsomo.fi/#!/jakso/33001005/studio55-fi/658521/jukka-kuoppamaki-tekee-yha-lauluja-vaikka-lentokoneessa',
        'only_matching': True,
    }, {
        'url': 'https://www.mtvuutiset.fi/video/prog1311159',
        'only_matching': True,
    }, {
        'url': 'https://www.katsomo.fi/#!/jakso/1311159',
        'only_matching': True,
    }]
    _API_DOMAIN = 'api.katsomo.fi'
    _PROTOCOLS = ('HLS', 'MPD')
    _GEO_COUNTRIES = ['FI']

    def _real_extract(self, url):
        video_id = self._match_id(url)
        api_base = 'http://%s/api/web/asset/%s' % (self._API_DOMAIN, video_id)

        asset = self._download_json(
            api_base + '.json', video_id,
            'Downloading metadata JSON')['asset']
        title = asset.get('subtitle') or asset['title']
        is_live = asset.get('live') is True

        formats = []
        format_urls = []
        for protocol in self._PROTOCOLS:
            try:
                data = self._download_json(
                    api_base + '/play.json?protocol=%s&videoFormat=SMIL+ISMUSP' % protocol,
                    video_id, 'Downloading play JSON')['playback']
            except ExtractorError as e:
                if isinstance(e.cause, compat_HTTPError) and e.cause.code == 401:
                    error = self._parse_json(e.cause.read().decode(), video_id)['error']
                    error_code = error.get('code')
                    if error_code == 'ASSET_PLAYBACK_INVALID_GEO_LOCATION':
                        self.raise_geo_restricted(countries=self._GEO_COUNTRIES)
                    elif error_code == 'SESSION_NOT_AUTHENTICATED':
                        self.raise_login_required()
                    raise ExtractorError(error['description'])
                raise
            items = try_get(data, lambda x: x['items']['item'])
            if not items:
                continue
            if not isinstance(items, list):
                items = [items]
            for item in items:
                if not isinstance(item, dict):
                    continue
                video_url = item.get('url')
                if not video_url or video_url in format_urls:
                    continue
                format_id = '%s-%s' % (protocol.lower(), item.get('mediaFormat'))
                if not self._is_valid_url(video_url, video_id, format_id):
                    continue
                format_urls.append(video_url)
                ext = determine_ext(video_url)
                if ext == 'f4m':
                    formats.extend(self._extract_f4m_formats(
                        video_url, video_id, f4m_id=format_id, fatal=False))
                elif ext == 'm3u8':
                    if not data.get('drmProtected'):
                        formats.extend(self._extract_m3u8_formats(
                            video_url, video_id, 'mp4', live=is_live, m3u8_id=format_id, fatal=False))
                elif ext == 'mpd':
                    formats.extend(self._extract_mpd_formats(
                        video_url, video_id, format_id, fatal=False))
                elif ext == 'ism' or video_url.endswith('.ism/Manifest'):
                    pass
                else:
                    formats.append({
                        'url': video_url,
                        'format_id': format_id,
                        'tbr': int_or_none(item.get('bitrate')),
                        'filesize': int_or_none(item.get('fileSize')),
                    })
        if not formats and data.get('drmProtected'):
            self.report_drm(video_id)
        self._sort_formats(formats)

        thumbnails = [{
            'id': thumbnail.get('@type'),
            'url': thumbnail.get('url'),
        } for _, thumbnail in (asset.get('imageVersions') or {}).items()]

        return {
            'id': video_id,
            'url': video_url,
            'title': title,
            'description': strip_or_none(asset.get('description')),
            'thumbnails': thumbnails,
            'timestamp': parse_iso8601(asset.get('createTime')),
            'duration': float_or_none(asset.get('accurateDuration') or asset.get('duration')),
            'view_count': int_or_none(asset.get('views')),
            'categories': asset.get('keywords', '').split(','),
            'formats': formats,
            'is_live': is_live,
        }


class MTVUutisetArticleIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)mtvuutiset\.fi/artikkeli/[^/]+/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://www.mtvuutiset.fi/artikkeli/tallaisia-vaurioita-viking-amorellassa-on-useamman-osaston-alla-vetta/7931384',
        'info_dict': {
            'id': '1311159',
            'ext': 'mp4',
            'title': 'Viking Amorellan matkustajien evakuointi on alkanut – tältä operaatio näyttää laivalla',
            'description': 'Viking Amorellan matkustajien evakuointi on alkanut – tältä operaatio näyttää laivalla',
            'timestamp': 1600608966,
            'upload_date': '20200920',
            'duration': 153.7886666,
            'view_count': int,
            'categories': list,
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
    }, {
        # multiple Youtube embeds
        'url': 'https://www.mtvuutiset.fi/artikkeli/50-vuotta-subarun-vastaiskua/6070962',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        article_id = self._match_id(url)
        article = self._download_json(
            'http://api.mtvuutiset.fi/mtvuutiset/api/json/' + article_id,
            article_id)

        def entries():
            for video in (article.get('videos') or []):
                video_type = video.get('videotype')
                video_url = video.get('url')
                if not (video_url and video_type in ('katsomo', 'youtube')):
                    continue
                yield self.url_result(
                    video_url, video_type.capitalize(), video.get('video_id'))

        return self.playlist_result(
            entries(), article_id, article.get('title'), article.get('description'))
