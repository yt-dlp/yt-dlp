import hashlib
import hmac
import re
import time

from .common import InfoExtractor
from ..compat import compat_str
from ..utils import (
    dict_get,
    ExtractorError,
    js_to_json,
    int_or_none,
    parse_iso8601,
    str_or_none,
    try_get,
    unescapeHTML,
    update_url_query,
)


class ABCIE(InfoExtractor):
    IE_NAME = 'abc.net.au'
    _VALID_URL = r'https?://(?:www\.)?abc\.net\.au/(?:news|btn)/(?:[^/]+/){1,4}(?P<id>\d{5,})'

    _TESTS = [{
        'url': 'http://www.abc.net.au/news/2014-11-05/australia-to-staff-ebola-treatment-centre-in-sierra-leone/5868334',
        'md5': 'cb3dd03b18455a661071ee1e28344d9f',
        'info_dict': {
            'id': '5868334',
            'ext': 'mp4',
            'title': 'Australia to help staff Ebola treatment centre in Sierra Leone',
            'description': 'md5:809ad29c67a05f54eb41f2a105693a67',
        },
        'skip': 'this video has expired',
    }, {
        'url': 'http://www.abc.net.au/news/2015-08-17/warren-entsch-introduces-same-sex-marriage-bill/6702326',
        'md5': '4ebd61bdc82d9a8b722f64f1f4b4d121',
        'info_dict': {
            'id': 'NvqvPeNZsHU',
            'ext': 'mp4',
            'upload_date': '20150816',
            'uploader': 'ABC News (Australia)',
            'description': 'Government backbencher Warren Entsch introduces a cross-party sponsored bill to legalise same-sex marriage, saying the bill is designed to promote "an inclusive Australia, not a divided one.". Read more here: http://ab.co/1Mwc6ef',
            'uploader_id': 'NewsOnABC',
            'title': 'Marriage Equality: Warren Entsch introduces same sex marriage bill',
        },
        'add_ie': ['Youtube'],
        'skip': 'Not accessible from Travis CI server',
    }, {
        'url': 'http://www.abc.net.au/news/2015-10-23/nab-lifts-interest-rates-following-westpac-and-cba/6880080',
        'md5': 'b96eee7c9edf4fc5a358a0252881cc1f',
        'info_dict': {
            'id': '6880080',
            'ext': 'mp3',
            'title': 'NAB lifts interest rates, following Westpac and CBA',
            'description': 'md5:f13d8edc81e462fce4a0437c7dc04728',
        },
    }, {
        'url': 'http://www.abc.net.au/news/2015-10-19/6866214',
        'only_matching': True,
    }, {
        'url': 'https://www.abc.net.au/btn/classroom/wwi-centenary/10527914',
        'info_dict': {
            'id': '10527914',
            'ext': 'mp4',
            'title': 'WWI Centenary',
            'description': 'md5:c2379ec0ca84072e86b446e536954546',
        }
    }, {
        'url': 'https://www.abc.net.au/news/programs/the-world/2020-06-10/black-lives-matter-protests-spawn-support-for/12342074',
        'info_dict': {
            'id': '12342074',
            'ext': 'mp4',
            'title': 'Black Lives Matter protests spawn support for Papuans in Indonesia',
            'description': 'md5:2961a17dc53abc558589ccd0fb8edd6f',
        }
    }, {
        'url': 'https://www.abc.net.au/btn/newsbreak/btn-newsbreak-20200814/12560476',
        'info_dict': {
            'id': 'tDL8Ld4dK_8',
            'ext': 'mp4',
            'title': 'Fortnite Banned From Apple and Google App Stores',
            'description': 'md5:a6df3f36ce8f816b74af4bd6462f5651',
            'upload_date': '20200813',
            'uploader': 'Behind the News',
            'uploader_id': 'behindthenews',
        }
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        mobj = re.search(r'<a\s+href="(?P<url>[^"]+)"\s+data-duration="\d+"\s+title="Download audio directly">', webpage)
        if mobj:
            urls_info = mobj.groupdict()
            youtube = False
            video = False
        else:
            mobj = re.search(r'<a href="(?P<url>http://www\.youtube\.com/watch\?v=[^"]+)"><span><strong>External Link:</strong>',
                             webpage)
            if mobj is None:
                mobj = re.search(r'<iframe width="100%" src="(?P<url>//www\.youtube-nocookie\.com/embed/[^?"]+)', webpage)
            if mobj:
                urls_info = mobj.groupdict()
                youtube = True
                video = True

        if mobj is None:
            mobj = re.search(r'(?P<type>)"sources": (?P<json_data>\[[^\]]+\]),', webpage)
            if mobj is None:
                mobj = re.search(
                    r'inline(?P<type>Video|Audio|YouTube)Data\.push\((?P<json_data>[^)]+)\);',
                    webpage)
                if mobj is None:
                    expired = self._html_search_regex(r'(?s)class="expired-(?:video|audio)".+?<span>(.+?)</span>', webpage, 'expired', None)
                    if expired:
                        raise ExtractorError('%s said: %s' % (self.IE_NAME, expired), expected=True)
                    raise ExtractorError('Unable to extract video urls')

            urls_info = self._parse_json(
                mobj.group('json_data'), video_id, transform_source=js_to_json)
            youtube = mobj.group('type') == 'YouTube'
            video = mobj.group('type') == 'Video' or urls_info[0]['contentType'] == 'video/mp4'

        if not isinstance(urls_info, list):
            urls_info = [urls_info]

        if youtube:
            return self.playlist_result([
                self.url_result(url_info['url']) for url_info in urls_info])

        formats = []
        for url_info in urls_info:
            height = int_or_none(url_info.get('height'))
            bitrate = int_or_none(url_info.get('bitrate'))
            width = int_or_none(url_info.get('width'))
            format_id = None
            mobj = re.search(r'_(?:(?P<height>\d+)|(?P<bitrate>\d+)k)\.mp4$', url_info['url'])
            if mobj:
                height_from_url = mobj.group('height')
                if height_from_url:
                    height = height or int_or_none(height_from_url)
                    width = width or int_or_none(url_info.get('label'))
                else:
                    bitrate = bitrate or int_or_none(mobj.group('bitrate'))
                    format_id = str_or_none(url_info.get('label'))
            formats.append({
                'url': url_info['url'],
                'vcodec': url_info.get('codec') if video else 'none',
                'width': width,
                'height': height,
                'tbr': bitrate,
                'filesize': int_or_none(url_info.get('filesize')),
                'format_id': format_id
            })

        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': self._og_search_title(webpage),
            'formats': formats,
            'description': self._og_search_description(webpage),
            'thumbnail': self._og_search_thumbnail(webpage),
        }


class ABCIViewIE(InfoExtractor):
    IE_NAME = 'abc.net.au:iview'
    _VALID_URL = r'https?://iview\.abc\.net\.au/(?:[^/]+/)*video/(?P<id>[^/?#]+)'
    _GEO_COUNTRIES = ['AU']

    # ABC iview programs are normally available for 14 days only.
    _TESTS = [{
        'url': 'https://iview.abc.net.au/show/gruen/series/11/video/LE1927H001S00',
        'md5': '67715ce3c78426b11ba167d875ac6abf',
        'info_dict': {
            'id': 'LE1927H001S00',
            'ext': 'mp4',
            'title': "Series 11 Ep 1",
            'series': "Gruen",
            'description': 'md5:52cc744ad35045baf6aded2ce7287f67',
            'upload_date': '20190925',
            'uploader_id': 'abc1',
            'timestamp': 1569445289,
        },
        'params': {
            'skip_download': True,
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        video_params = self._download_json(
            'https://iview.abc.net.au/api/programs/' + video_id, video_id)
        title = unescapeHTML(video_params.get('title') or video_params['seriesTitle'])
        stream = next(s for s in video_params['playlist'] if s.get('type') in ('program', 'livestream'))

        house_number = video_params.get('episodeHouseNumber') or video_id
        path = '/auth/hls/sign?ts={0}&hn={1}&d=android-tablet'.format(
            int(time.time()), house_number)
        sig = hmac.new(
            b'android.content.res.Resources',
            path.encode('utf-8'), hashlib.sha256).hexdigest()
        token = self._download_webpage(
            'http://iview.abc.net.au{0}&sig={1}'.format(path, sig), video_id)

        def tokenize_url(url, token):
            return update_url_query(url, {
                'hdnea': token,
            })

        for sd in ('1080', '720', 'sd', 'sd-low'):
            sd_url = try_get(
                stream, lambda x: x['streams']['hls'][sd], compat_str)
            if not sd_url:
                continue
            formats = self._extract_m3u8_formats(
                tokenize_url(sd_url, token), video_id, 'mp4',
                entry_protocol='m3u8_native', m3u8_id='hls', fatal=False)
            if formats:
                break
        self._sort_formats(formats)

        subtitles = {}
        src_vtt = stream.get('captions', {}).get('src-vtt')
        if src_vtt:
            subtitles['en'] = [{
                'url': src_vtt,
                'ext': 'vtt',
            }]

        is_live = video_params.get('livestream') == '1'

        return {
            'id': video_id,
            'title': title,
            'description': video_params.get('description'),
            'thumbnail': video_params.get('thumbnail'),
            'duration': int_or_none(video_params.get('eventDuration')),
            'timestamp': parse_iso8601(video_params.get('pubDate'), ' '),
            'series': unescapeHTML(video_params.get('seriesTitle')),
            'series_id': video_params.get('seriesHouseNumber') or video_id[:7],
            'season_number': int_or_none(self._search_regex(
                r'\bSeries\s+(\d+)\b', title, 'season number', default=None)),
            'episode_number': int_or_none(self._search_regex(
                r'\bEp\s+(\d+)\b', title, 'episode number', default=None)),
            'episode_id': house_number,
            'uploader_id': video_params.get('channel'),
            'formats': formats,
            'subtitles': subtitles,
            'is_live': is_live,
        }


class ABCIViewShowSeriesIE(InfoExtractor):
    IE_NAME = 'abc.net.au:iview:showseries'
    _VALID_URL = r'https?://iview\.abc\.net\.au/show/(?P<id>[^/]+)(?:/series/\d+)?$'
    _GEO_COUNTRIES = ['AU']

    _TESTS = [{
        'url': 'https://iview.abc.net.au/show/upper-middle-bogan',
        'info_dict': {
            'id': '124870-1',
            'title': 'Series 1',
            'description': 'md5:93119346c24a7c322d446d8eece430ff',
            'series': 'Upper Middle Bogan',
            'season': 'Series 1',
            'thumbnail': r're:^https?://cdn\.iview\.abc\.net\.au/thumbs/.*\.jpg$'
        },
        'playlist_count': 8,
    }, {
        'url': 'https://iview.abc.net.au/show/upper-middle-bogan',
        'info_dict': {
            'id': 'CO1108V001S00',
            'ext': 'mp4',
            'title': 'Series 1 Ep 1 I\'m A Swan',
            'description': 'md5:7b676758c1de11a30b79b4d301e8da93',
            'series': 'Upper Middle Bogan',
            'uploader_id': 'abc1',
            'upload_date': '20210630',
            'timestamp': 1625036400,
        },
        'params': {
            'noplaylist': True,
            'skip_download': 'm3u8',
        },
    }]

    def _real_extract(self, url):
        show_id = self._match_id(url)
        webpage = self._download_webpage(url, show_id)
        webpage_data = self._search_regex(
            r'window\.__INITIAL_STATE__\s*=\s*[\'"](.+?)[\'"]\s*;',
            webpage, 'initial state')
        video_data = self._parse_json(
            unescapeHTML(webpage_data).encode('utf-8').decode('unicode_escape'), show_id)
        video_data = video_data['route']['pageData']['_embedded']

        highlight = try_get(video_data, lambda x: x['highlightVideo']['shareUrl'])
        if not self._yes_playlist(show_id, bool(highlight), video_label='highlight video'):
            return self.url_result(highlight, ie=ABCIViewIE.ie_key())

        series = video_data['selectedSeries']
        return {
            '_type': 'playlist',
            'entries': [self.url_result(episode['shareUrl'])
                        for episode in series['_embedded']['videoEpisodes']],
            'id': series.get('id'),
            'title': dict_get(series, ('title', 'displaySubtitle')),
            'description': series.get('description'),
            'series': dict_get(series, ('showTitle', 'displayTitle')),
            'season': dict_get(series, ('title', 'displaySubtitle')),
            'thumbnail': series.get('thumbnail'),
        }
