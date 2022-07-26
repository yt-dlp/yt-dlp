import re

from ..extractor.redbee import RedBeeIE
from ..utils import (
    ExtractorError,
    float_or_none,
    int_or_none,
    strip_or_none,
)


class RTBFIE(RedBeeIE):
    _VALID_URL = r'''(?x)
        https?://(?:www\.)?rtbf\.be/
        (?:
            video/[^?]+\?.*\bid=|
            ouftivi/(?:[^/]+/)*[^?]+\?.*\bvideoId=|
            auvio/[^/]+\?.*\b(?P<live>l)?id=
        )(?P<id>\d+)'''
    _TESTS = [{
        'url': 'https://www.rtbf.be/video/detail_les-diables-au-coeur-episode-2?id=1921274',
        'md5': '8c876a1cceeb6cf31b476461ade72384',
        'info_dict': {
            'id': '1921274',
            'ext': 'mp4',
            'title': 'Les Diables au coeur (épisode 2)',
            'description': '(du 25/04/2014)',
            'duration': 3099.54,
            'upload_date': '20140425',
            'timestamp': 1398456300,
        },
        'skip': 'No longer available',
    }, {
        # geo restricted
        'url': 'http://www.rtbf.be/ouftivi/heros/detail_scooby-doo-mysteres-associes?id=1097&videoId=2057442',
        'only_matching': True,
    }, {
        'url': 'http://www.rtbf.be/ouftivi/niouzz?videoId=2055858',
        'only_matching': True,
    }, {
        'url': 'http://www.rtbf.be/auvio/detail_jeudi-en-prime-siegfried-bracke?id=2102996',
        'only_matching': True,
    }, {
        # Live
        'url': 'https://www.rtbf.be/auvio/direct_pure-fm?lid=134775',
        'only_matching': True,
    }, {
        # Audio
        'url': 'https://www.rtbf.be/auvio/detail_cinq-heures-cinema?id=2360811',
        'only_matching': True,
    }, {
        # With Subtitle
        'url': 'https://www.rtbf.be/auvio/detail_les-carnets-du-bourlingueur?id=2361588',
        'only_matching': True,
    }]
    _IMAGE_HOST = 'http://ds1.ds.static.rtbf.be'
    _PROVIDERS = {
        'YOUTUBE': 'Youtube',
        'DAILYMOTION': 'Dailymotion',
        'VIMEO': 'Vimeo',
    }
    _QUALITIES = [
        ('mobile', 'SD'),
        ('web', 'MD'),
        ('high', 'HD'),
    ]
    _REDBEE_CUSTOMER = 'RTBF'
    _REDBEE_BUSINESS_UNIT = 'Auvio'

    def _get_redbee_formats_and_subtitles(self, url, media_id):
        api_key = (self._search_regex(r'<div[^>]+gigya\.js\?apikey=(?P<api_key>[^"&]+)',
                                      self._download_webpage(url, media_id), 'api_key', fatal=False)
                   or '3_kWKuPgcdAybqnqxq_MvHVk0-6PN8Zk8pIIkJM_yXOu-qLPDDsGOtIDFfpGivtbeO')

        login_token = self._get_cookies(url).get(f'glt_{api_key}')
        if not login_token:
            self.raise_login_required()

        session_jwt = self._download_json(
            "https://login.rtbf.be/accounts.getJWT", media_id, query={
                'login_token': login_token.value,
                'APIKey': api_key,
                'sdk': 'js_latest',
                'authMode': 'cookie',
                'pageURL': url,
                'sdkBuild': '13273',
                'format': 'json',
            })['id_token']

        return self._get_entitlement_formats_and_subtitles(
            media_id, self._REDBEE_CUSTOMER, self._REDBEE_BUSINESS_UNIT,
            self._get_bearer_token(
                media_id, self._REDBEE_CUSTOMER, self._REDBEE_BUSINESS_UNIT, 'gigyaLogin', jwt=session_jwt))

    def _real_extract(self, url):
        live, media_id = self._match_valid_url(url).groups()
        embed_page = self._download_webpage(
            'https://www.rtbf.be/auvio/embed/' + ('direct' if live else 'media'),
            media_id, query={'id': media_id})
        data = self._parse_json(self._html_search_regex(
            r'data-media="([^"]+)"', embed_page, 'media data'), media_id)

        error = data.get('error')
        if error:
            raise ExtractorError('%s said: %s' % (self.IE_NAME, error), expected=True)

        provider = data.get('provider')
        if provider in self._PROVIDERS:
            return self.url_result(data['url'], self._PROVIDERS[provider])

        title = data['title']
        is_live = data.get('isLive')
        height_re = r'-(\d+)p\.'
        formats = []

        m3u8_url = data.get('urlHlsAes128') or data.get('urlHls')
        if m3u8_url:
            formats.extend(self._extract_m3u8_formats(
                m3u8_url, media_id, 'mp4', m3u8_id='hls', fatal=False))

        fix_url = lambda x: x.replace('//rtbf-vod.', '//rtbf.') if '/geo/drm/' in x else x
        http_url = data.get('url')
        if formats and http_url and re.search(height_re, http_url):
            http_url = fix_url(http_url)
            for m3u8_f in formats[:]:
                height = m3u8_f.get('height')
                if not height:
                    continue
                f = m3u8_f.copy()
                del f['protocol']
                f.update({
                    'format_id': m3u8_f['format_id'].replace('hls-', 'http-'),
                    'url': re.sub(height_re, '-%dp.' % height, http_url),
                })
                formats.append(f)
        else:
            sources = data.get('sources') or {}
            for key, format_id in self._QUALITIES:
                format_url = sources.get(key)
                if not format_url:
                    continue
                height = int_or_none(self._search_regex(
                    height_re, format_url, 'height', default=None))
                formats.append({
                    'format_id': format_id,
                    'url': fix_url(format_url),
                    'height': height,
                })

        mpd_url = data.get('urlDash')
        if mpd_url and (self.get_param('allow_unplayable_formats') or not data.get('drm')):
            formats.extend(self._extract_mpd_formats(
                mpd_url, media_id, mpd_id='dash', fatal=False))

        audio_url = data.get('urlAudio')
        if audio_url:
            formats.append({
                'format_id': 'audio',
                'url': audio_url,
                'vcodec': 'none',
            })
        self._sort_formats(formats)

        subtitles = {}
        for track in (data.get('tracks') or {}).values():
            sub_url = track.get('url')
            if not sub_url:
                continue
            subtitles.setdefault(track.get('lang') or 'fr', []).append({
                'url': sub_url,
            })

        if not formats:
            fmts, subs = self._get_redbee_formats_and_subtitles(url, media_id)
            formats.extend(fmts)
            self._merge_subtitles(subs, target=subtitles)

        return {
            'id': media_id,
            'formats': formats,
            'title': title,
            'description': strip_or_none(data.get('description')),
            'thumbnail': data.get('thumbnail'),
            'duration': float_or_none(data.get('realDuration')),
            'timestamp': int_or_none(data.get('liveFrom')),
            'series': data.get('programLabel'),
            'subtitles': subtitles,
            'is_live': is_live,
        }
