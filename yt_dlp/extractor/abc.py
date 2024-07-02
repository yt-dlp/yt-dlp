import functools
import hashlib
import hmac
import re
import time

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    dict_get,
    int_or_none,
    js_to_json,
    parse_iso8601,
    str_or_none,
    traverse_obj,
    try_get,
    unescapeHTML,
    update_url_query,
    url_or_none,
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
        },
    }, {
        'url': 'https://www.abc.net.au/news/programs/the-world/2020-06-10/black-lives-matter-protests-spawn-support-for/12342074',
        'info_dict': {
            'id': '12342074',
            'ext': 'mp4',
            'title': 'Black Lives Matter protests spawn support for Papuans in Indonesia',
            'description': 'md5:2961a17dc53abc558589ccd0fb8edd6f',
        },
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
        },
    }, {
        'url': 'https://www.abc.net.au/news/2023-06-25/wagner-boss-orders-troops-back-to-bases-to-avoid-bloodshed/102520540',
        'info_dict': {
            'id': '102520540',
            'title': 'Wagner Group retreating from Russia, leader Prigozhin to move to Belarus',
            'ext': 'mp4',
            'description': 'Wagner troops leave Rostov-on-Don and\xa0Yevgeny Prigozhin will move to Belarus under a deal brokered by Belarusian President Alexander Lukashenko to end the mutiny.',
            'thumbnail': 'https://live-production.wcms.abc-cdn.net.au/0c170f5b57f0105c432f366c0e8e267b?impolicy=wcms_crop_resize&cropH=2813&cropW=5000&xPos=0&yPos=249&width=862&height=485',
        },
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
            mobj = re.search(r'(?P<type>)"(?:sources|files|renditions)":\s*(?P<json_data>\[[^\]]+\])', webpage)
            if mobj is None:
                mobj = re.search(
                    r'inline(?P<type>Video|Audio|YouTube)Data\.push\((?P<json_data>[^)]+)\);',
                    webpage)
                if mobj is None:
                    expired = self._html_search_regex(r'(?s)class="expired-(?:video|audio)".+?<span>(.+?)</span>', webpage, 'expired', None)
                    if expired:
                        raise ExtractorError(f'{self.IE_NAME} said: {expired}', expected=True)
                    raise ExtractorError('Unable to extract video urls')

            urls_info = self._parse_json(
                mobj.group('json_data'), video_id, transform_source=js_to_json)
            youtube = mobj.group('type') == 'YouTube'
            video = mobj.group('type') == 'Video' or traverse_obj(
                urls_info, (0, ('contentType', 'MIMEType')), get_all=False) == 'video/mp4'

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
                'format_id': format_id,
            })

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

    _TESTS = [{
        'url': 'https://iview.abc.net.au/show/utopia/series/1/video/CO1211V001S00',
        'md5': '52a942bfd7a0b79a6bfe9b4ce6c9d0ed',
        'info_dict': {
            'id': 'CO1211V001S00',
            'ext': 'mp4',
            'title': 'Series 1 Episode 1 Wood For The Trees',
            'series': 'Utopia',
            'description': 'md5:0cfb2c183c1b952d1548fd65c8a95c00',
            'upload_date': '20230726',
            'uploader_id': 'abc1',
            'series_id': 'CO1211V',
            'episode_id': 'CO1211V001S00',
            'season_number': 1,
            'season': 'Season 1',
            'episode_number': 1,
            'episode': 'Wood For The Trees',
            'duration': 1584,
            'chapters': [
                {
                    'start_time': 0,
                    'end_time': 1,
                    'title': '<Untitled Chapter 1>',
                },
                {
                    'start_time': 1,
                    'end_time': 24,
                    'title': 'opening-credits',
                },
                {
                    'start_time': 1564,
                    'end_time': 1584,
                    'title': 'end-credits',
                },
            ],
            'thumbnail': 'https://cdn.iview.abc.net.au/thumbs/i/co/CO1211V001S00_5ad8353f4df09_1280.jpg',
            'timestamp': 1690403700,
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'note': 'No episode name',
        'url': 'https://iview.abc.net.au/show/gruen/series/15/video/LE2327H001S00',
        'md5': '67715ce3c78426b11ba167d875ac6abf',
        'info_dict': {
            'id': 'LE2327H001S00',
            'ext': 'mp4',
            'title': 'Series 15 Episode 1',
            'series': 'Gruen',
            'description': 'md5:ac3bf529d467d8436954db1e90d2f06d',
            'upload_date': '20230621',
            'uploader_id': 'abc1',
            'series_id': 'LE2327H',
            'episode_id': 'LE2327H001S00',
            'season_number': 15,
            'season': 'Season 15',
            'episode_number': 1,
            'episode': 'Episode 1',
            'thumbnail': 'https://cdn.iview.abc.net.au/thumbs/i/le/LE2327H001S00_649279152faea_3600.jpg',
            'timestamp': 1687379421,
            'duration': 2117,
            'chapters': 'count:2',
        },
        'expected_warnings': ['Ignoring subtitle tracks found in the HLS manifest'],
        'params': {
            'skip_download': True,
        },
    }, {
        'note': 'No episode number',
        'url': 'https://iview.abc.net.au/show/four-corners/series/2022/video/NC2203H039S00',
        'md5': '77cb7d8434440e3b28fbebe331c2456a',
        'info_dict': {
            'id': 'NC2203H039S00',
            'ext': 'mp4',
            'title': 'Series 2022 Locking Up Kids',
            'series': 'Four Corners',
            'description': 'md5:54829ca108846d1a70e1fcce2853e720',
            'upload_date': '20221114',
            'uploader_id': 'abc1',
            'series_id': 'NC2203H',
            'episode_id': 'NC2203H039S00',
            'season_number': 2022,
            'season': 'Season 2022',
            'episode': 'Locking Up Kids',
            'thumbnail': 'https://cdn.iview.abc.net.au/thumbs/i/nc/NC2203H039S00_636d8a0944a22_1920.jpg',
            'timestamp': 1668460497,
            'duration': 2802,
            'chapters': 'count:2',
        },
        'expected_warnings': ['Ignoring subtitle tracks found in the HLS manifest'],
        'params': {
            'skip_download': True,
        },
    }, {
        'note': 'No episode name or number',
        'url': 'https://iview.abc.net.au/show/landline/series/2021/video/RF2004Q043S00',
        'md5': '2e17dec06b13cc81dc119d2565289396',
        'info_dict': {
            'id': 'RF2004Q043S00',
            'ext': 'mp4',
            'title': 'Series 2021',
            'series': 'Landline',
            'description': 'md5:c9f30d9c0c914a7fd23842f6240be014',
            'upload_date': '20211205',
            'uploader_id': 'abc1',
            'series_id': 'RF2004Q',
            'episode_id': 'RF2004Q043S00',
            'season_number': 2021,
            'season': 'Season 2021',
            'thumbnail': 'https://cdn.iview.abc.net.au/thumbs/i/rf/RF2004Q043S00_61a950639dbc0_1920.jpg',
            'timestamp': 1638710705,
            'duration': 3381,
            'chapters': 'count:2',
        },
        'expected_warnings': ['Ignoring subtitle tracks found in the HLS manifest'],
        'params': {
            'skip_download': True,
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        video_params = self._download_json(
            f'https://api.iview.abc.net.au/v3/video/{video_id}', video_id,
            errnote='Failed to download API V3 JSON', fatal=False)
        # fallback to legacy API, which will return some useful info even if the video is unavailable
        if not video_params:
            video_params = self._download_json(
                f'https://iview.abc.net.au/api/programs/{video_id}', video_id,
                note='Falling back to legacy API JSON')
        stream = traverse_obj(video_params, (
            ('_embedded', None), 'playlist', lambda _, v: v['type'] in ('program', 'livestream'), any)) or {}

        house_number = traverse_obj(video_params, 'houseNumber', 'episodeHouseNumber') or video_id
        path = f'/auth/hls/sign?ts={int(time.time())}&hn={house_number}&d=android-tablet'
        sig = hmac.new(
            b'android.content.res.Resources',
            path.encode(), hashlib.sha256).hexdigest()
        token = self._download_webpage(
            f'http://iview.abc.net.au{path}&sig={sig}', video_id)

        def tokenize_url(url, token):
            return update_url_query(url, {
                'hdnea': token,
            })

        formats = []
        # hls: pre-merged formats
        # hls-latest: same as hls, but sometimes has separate audio tracks
        # Note: pre-merged formats in hls-latest are treated as video-only if audio-only tracks
        # are present, so we extract both types
        for label in ('hls', 'hls-latest'):
            for sd_url in traverse_obj(stream, ('streams', label, ('1080', '720', 'sd', 'sd-low'), {url_or_none})):
                fmts = self._extract_m3u8_formats(
                    tokenize_url(sd_url, token), video_id, 'mp4', m3u8_id=label, fatal=False)
                if fmts:
                    formats.extend(fmts)
                    break

        # deprioritize audio description tracks
        for f in formats:
            if 'description' in (f.get('format_note') or '').lower():
                f['language_preference'] = -10

        subtitles = {}
        if src_vtt := traverse_obj(stream, ('captions', 'src-vtt', {url_or_none})):
            subtitles['en'] = [{
                'url': src_vtt,
                'ext': 'vtt',
            }]

        title = traverse_obj(video_params, 'title', 'seriesTitle', 'showTitle', expected_type=unescapeHTML)

        return {
            'id': video_id,
            'title': title,
            'series_id': traverse_obj(
                video_params, ('analytics', 'oztam', 'seriesId'), 'seriesHouseNumber') or video_id[:7],
            'season_number': int_or_none(self._search_regex(
                r'\bSeries\s+(\d+)\b', title, 'season number', default=None)),
            'episode_number': int_or_none(self._search_regex(
                r'\bEp(?:isode)?\s+(\d+)\b', title, 'episode number', default=None)),
            'episode_id': house_number,
            'episode': self._search_regex(
                r'^(?:Series\s+\d+)?\s*(?:Ep(?:isode)?\s+\d+)?\s*(.*)$', title, 'episode', default='') or None,
            'is_live': video_params.get('livestream') == '1' or stream.get('type') == 'livestream',
            'formats': formats,
            'subtitles': subtitles,
            **traverse_obj(video_params, {
                'description': ('description', {str}),
                'thumbnail': ((
                    ('images', lambda _, v: v['name'] == 'episodeThumbnail', 'url'), 'thumbnail'), {url_or_none}, any),
                'chapters': ('cuePoints', lambda _, v: int(v['start']) is not None, {
                    'start_time': ('start', {int_or_none}),
                    'end_time': ('end', {int_or_none}),
                    'title': ('type', {str}),
                }),
                'duration': (('duration', 'eventDuration'), {int_or_none}, any),
                'timestamp': ('pubDate', {functools.partial(parse_iso8601, delimiter=' ')}),
                'series': (('seriesTitle', 'showTitle'), {unescapeHTML}, any),
                'uploader_id': ('channel', {str}),
            }),
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
            'thumbnail': r're:^https?://cdn\.iview\.abc\.net\.au/thumbs/.*\.jpg$',
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
    }, {
        # 'videoEpisodes' is a dict with `items` key
        'url': 'https://iview.abc.net.au/show/7-30-mark-humphries-satire',
        'info_dict': {
            'id': '178458-0',
            'title': 'Episodes',
            'description': 'Satirist Mark Humphries brings his unique perspective on current political events for 7.30.',
            'series': '7.30 Mark Humphries Satire',
            'season': 'Episodes',
            'thumbnail': r're:^https?://cdn\.iview\.abc\.net\.au/thumbs/.*\.jpg$',
        },
        'playlist_count': 15,
    }]

    def _real_extract(self, url):
        show_id = self._match_id(url)
        webpage = self._download_webpage(url, show_id)
        webpage_data = self._search_regex(
            r'window\.__INITIAL_STATE__\s*=\s*[\'"](.+?)[\'"]\s*;',
            webpage, 'initial state')
        video_data = self._parse_json(
            unescapeHTML(webpage_data).encode().decode('unicode_escape'), show_id)
        video_data = video_data['route']['pageData']['_embedded']

        highlight = try_get(video_data, lambda x: x['highlightVideo']['shareUrl'])
        if not self._yes_playlist(show_id, bool(highlight), video_label='highlight video'):
            return self.url_result(highlight, ie=ABCIViewIE.ie_key())

        series = video_data['selectedSeries']
        return {
            '_type': 'playlist',
            'entries': [self.url_result(episode_url, ABCIViewIE)
                        for episode_url in traverse_obj(series, (
                            '_embedded', 'videoEpisodes', (None, 'items'), ..., 'shareUrl', {url_or_none}))],
            'id': series.get('id'),
            'title': dict_get(series, ('title', 'displaySubtitle')),
            'description': series.get('description'),
            'series': dict_get(series, ('showTitle', 'displayTitle')),
            'season': dict_get(series, ('title', 'displaySubtitle')),
            'thumbnail': traverse_obj(
                series, 'thumbnail', ('images', lambda _, v: v['name'] == 'seriesThumbnail', 'url'), get_all=False),
        }
