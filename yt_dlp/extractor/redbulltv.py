from .common import InfoExtractor
from ..networking.exceptions import HTTPError
from ..utils import (
    ExtractorError,
    float_or_none,
)


class RedBullTVIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?redbull(?:\.tv|\.com(?:/[^/]+)?(?:/tv)?)(?:/events/[^/]+)?/(?:videos?|live|(?:film|episode)s)/(?P<id>AP-\w+)'
    _TESTS = [{
        # film
        'url': 'https://www.redbull.tv/video/AP-1Q6XCDTAN1W11',
        'md5': 'fb0445b98aa4394e504b413d98031d1f',
        'info_dict': {
            'id': 'AP-1Q6XCDTAN1W11',
            'ext': 'mp4',
            'title': 'ABC of... WRC - ABC of... S1E6',
            'description': 'md5:5c7ed8f4015c8492ecf64b6ab31e7d31',
            'duration': 1582.04,
        },
    }, {
        # episode
        'url': 'https://www.redbull.tv/video/AP-1PMHKJFCW1W11',
        'info_dict': {
            'id': 'AP-1PMHKJFCW1W11',
            'ext': 'mp4',
            'title': 'Grime - Hashtags S2E4',
            'description': 'md5:5546aa612958c08a98faaad4abce484d',
            'duration': 904,
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'https://www.redbull.com/int-en/tv/video/AP-1UWHCAR9S1W11/rob-meets-sam-gaze?playlist=playlists::3f81040a-2f31-4832-8e2e-545b1d39d173',
        'only_matching': True,
    }, {
        'url': 'https://www.redbull.com/us-en/videos/AP-1YM9QCYE52111',
        'only_matching': True,
    }, {
        'url': 'https://www.redbull.com/us-en/events/AP-1XV2K61Q51W11/live/AP-1XUJ86FDH1W11',
        'only_matching': True,
    }, {
        'url': 'https://www.redbull.com/int-en/films/AP-1ZSMAW8FH2111',
        'only_matching': True,
    }, {
        'url': 'https://www.redbull.com/int-en/episodes/AP-1TQWK7XE11W11',
        'only_matching': True,
    }]

    def extract_info(self, video_id):
        session = self._download_json(
            'https://api.redbull.tv/v3/session', video_id,
            note='Downloading access token', query={
                'category': 'personal_computer',
                'os_family': 'http',
            })
        if session.get('code') == 'error':
            raise ExtractorError('%s said: %s' % (
                self.IE_NAME, session['message']))
        token = session['token']

        try:
            video = self._download_json(
                'https://api.redbull.tv/v3/products/' + video_id,
                video_id, note='Downloading video information',
                headers={'Authorization': token}
            )
        except ExtractorError as e:
            if isinstance(e.cause, HTTPError) and e.cause.status == 404:
                error_message = self._parse_json(
                    e.cause.response.read().decode(), video_id)['error']
                raise ExtractorError('%s said: %s' % (
                    self.IE_NAME, error_message), expected=True)
            raise

        title = video['title'].strip()

        formats, subtitles = self._extract_m3u8_formats_and_subtitles(
            'https://dms.redbull.tv/v3/%s/%s/playlist.m3u8' % (video_id, token),
            video_id, 'mp4', entry_protocol='m3u8_native', m3u8_id='hls')

        for resource in video.get('resources', []):
            if resource.startswith('closed_caption_'):
                splitted_resource = resource.split('_')
                if splitted_resource[2]:
                    subtitles.setdefault('en', []).append({
                        'url': 'https://resources.redbull.tv/%s/%s' % (video_id, resource),
                        'ext': splitted_resource[2],
                    })

        subheading = video.get('subheading')
        if subheading:
            title += ' - %s' % subheading

        return {
            'id': video_id,
            'title': title,
            'description': video.get('long_description') or video.get(
                'short_description'),
            'duration': float_or_none(video.get('duration'), scale=1000),
            'formats': formats,
            'subtitles': subtitles,
        }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        return self.extract_info(video_id)


class RedBullEmbedIE(RedBullTVIE):  # XXX: Do not subclass from concrete IE
    _VALID_URL = r'https?://(?:www\.)?redbull\.com/embed/(?P<id>rrn:content:[^:]+:[\da-f]{8}-[\da-f]{4}-[\da-f]{4}-[\da-f]{4}-[\da-f]{12}:[a-z]{2}-[A-Z]{2,3})'
    _TESTS = [{
        # HLS manifest accessible only using assetId
        'url': 'https://www.redbull.com/embed/rrn:content:episode-videos:f3021f4f-3ed4-51ac-915a-11987126e405:en-INT',
        'only_matching': True,
    }]
    _VIDEO_ESSENSE_TMPL = '''... on %s {
      videoEssence {
        attributes
      }
    }'''

    def _real_extract(self, url):
        rrn_id = self._match_id(url)
        asset_id = self._download_json(
            'https://edge-graphql.crepo-production.redbullaws.com/v1/graphql',
            rrn_id, headers={
                'Accept': 'application/json',
                'API-KEY': 'e90a1ff11335423998b100c929ecc866',
            }, query={
                'query': '''{
  resource(id: "%s", enforceGeoBlocking: false) {
    %s
    %s
  }
}''' % (rrn_id, self._VIDEO_ESSENSE_TMPL % 'LiveVideo', self._VIDEO_ESSENSE_TMPL % 'VideoResource'),
            })['data']['resource']['videoEssence']['attributes']['assetId']
        return self.extract_info(asset_id)


class RedBullTVRrnContentIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?redbull\.com/(?P<region>[a-z]{2,3})-(?P<lang>[a-z]{2})/tv/(?:video|live|film)/(?P<id>rrn:content:[^:]+:[\da-f]{8}-[\da-f]{4}-[\da-f]{4}-[\da-f]{4}-[\da-f]{12})'
    _TESTS = [{
        'url': 'https://www.redbull.com/int-en/tv/video/rrn:content:live-videos:e3e6feb4-e95f-50b7-962a-c70f8fd13c73/mens-dh-finals-fort-william',
        'only_matching': True,
    }, {
        'url': 'https://www.redbull.com/int-en/tv/video/rrn:content:videos:a36a0f36-ff1b-5db8-a69d-ee11a14bf48b/tn-ts-style?playlist=rrn:content:event-profiles:83f05926-5de8-5389-b5e4-9bb312d715e8:extras',
        'only_matching': True,
    }, {
        'url': 'https://www.redbull.com/int-en/tv/film/rrn:content:films:d1f4d00e-4c04-5d19-b510-a805ffa2ab83/follow-me',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        region, lang, rrn_id = self._match_valid_url(url).groups()
        rrn_id += ':%s-%s' % (lang, region.upper())
        return self.url_result(
            'https://www.redbull.com/embed/' + rrn_id,
            RedBullEmbedIE.ie_key(), rrn_id)


class RedBullIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?redbull\.com/(?P<region>[a-z]{2,3})-(?P<lang>[a-z]{2})/(?P<type>(?:episode|film|(?:(?:recap|trailer)-)?video)s|live)/(?!AP-|rrn:content:)(?P<id>[^/?#&]+)'
    _TESTS = [{
        'url': 'https://www.redbull.com/int-en/episodes/grime-hashtags-s02-e04',
        'md5': 'db8271a7200d40053a1809ed0dd574ff',
        'info_dict': {
            'id': 'AA-1MT8DQWA91W14',
            'ext': 'mp4',
            'title': 'Grime - Hashtags S2E4',
            'description': 'md5:5546aa612958c08a98faaad4abce484d',
        },
    }, {
        'url': 'https://www.redbull.com/int-en/films/kilimanjaro-mountain-of-greatness',
        'only_matching': True,
    }, {
        'url': 'https://www.redbull.com/int-en/recap-videos/uci-mountain-bike-world-cup-2017-mens-xco-finals-from-vallnord',
        'only_matching': True,
    }, {
        'url': 'https://www.redbull.com/int-en/trailer-videos/kings-of-content',
        'only_matching': True,
    }, {
        'url': 'https://www.redbull.com/int-en/videos/tnts-style-red-bull-dance-your-style-s1-e12',
        'only_matching': True,
    }, {
        'url': 'https://www.redbull.com/int-en/live/mens-dh-finals-fort-william',
        'only_matching': True,
    }, {
        # only available on the int-en website so a fallback is need for the API
        # https://www.redbull.com/v3/api/graphql/v1/v3/query/en-GB>en-INT?filter[uriSlug]=fia-wrc-saturday-recap-estonia&rb3Schema=v1:hero
        'url': 'https://www.redbull.com/gb-en/live/fia-wrc-saturday-recap-estonia',
        'only_matching': True,
    }]
    _INT_FALLBACK_LIST = ['de', 'en', 'es', 'fr']
    _LAT_FALLBACK_MAP = ['ar', 'bo', 'car', 'cl', 'co', 'mx', 'pe']

    def _real_extract(self, url):
        region, lang, filter_type, display_id = self._match_valid_url(url).groups()
        if filter_type == 'episodes':
            filter_type = 'episode-videos'
        elif filter_type == 'live':
            filter_type = 'live-videos'

        regions = [region.upper()]
        if region != 'int':
            if region in self._LAT_FALLBACK_MAP:
                regions.append('LAT')
            if lang in self._INT_FALLBACK_LIST:
                regions.append('INT')
        locale = '>'.join(['%s-%s' % (lang, reg) for reg in regions])

        rrn_id = self._download_json(
            'https://www.redbull.com/v3/api/graphql/v1/v3/query/' + locale,
            display_id, query={
                'filter[type]': filter_type,
                'filter[uriSlug]': display_id,
                'rb3Schema': 'v1:hero',
            })['data']['id']

        return self.url_result(
            'https://www.redbull.com/embed/' + rrn_id,
            RedBullEmbedIE.ie_key(), rrn_id)
