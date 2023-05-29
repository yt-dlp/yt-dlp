import base64
import re
import urllib.error
import urllib.parse
import zlib

from .anvato import AnvatoIE
from .common import InfoExtractor
from .paramountplus import ParamountPlusIE
from ..utils import (
    ExtractorError,
    HEADRequest,
    UserNotLive,
    determine_ext,
    float_or_none,
    format_field,
    int_or_none,
    make_archive_id,
    mimetype2ext,
    parse_duration,
    smuggle_url,
    traverse_obj,
    url_or_none,
)


class CBSNewsBaseIE(InfoExtractor):
    _LOCALES = {
        'atlanta': None,
        'baltimore': 'BAL',
        'boston': 'BOS',
        'chicago': 'CHI',
        'colorado': 'DEN',
        'detroit': 'DET',
        'losangeles': 'LA',
        'miami': 'MIA',
        'minnesota': 'MIN',
        'newyork': 'NY',
        'philadelphia': 'PHI',
        'pittsburgh': 'PIT',
        'sacramento': 'SAC',
        'sanfrancisco': 'SF',
        'texas': 'DAL',
    }
    _LOCALE_RE = '|'.join(map(re.escape, _LOCALES))
    _ANVACK = '5VD6Eyd6djewbCmNwBFnsJj17YAvGRwl'

    def _get_item(self, webpage, display_id):
        return traverse_obj(self._search_json(
            r'CBSNEWS\.defaultPayload\s*=', webpage, 'payload', display_id,
            default={}), ('items', 0, {dict})) or {}

    def _get_video_url(self, item):
        return traverse_obj(item, 'video', 'video2', expected_type=url_or_none)

    def _extract_playlist(self, webpage, playlist_id):
        entries = [self.url_result(embed_url, CBSNewsEmbedIE) for embed_url in re.findall(
            r'<iframe[^>]+data-src="(https?://(?:www\.)?cbsnews\.com/embed/video/[^#]*#[^"]+)"', webpage)]
        if entries:
            return self.playlist_result(
                entries, playlist_id, self._html_search_meta(['og:title', 'twitter:title'], webpage),
                self._html_search_meta(['og:description', 'twitter:description', 'description'], webpage))

    def _extract_video(self, item, video_url, video_id):
        if mimetype2ext(item.get('format'), default=determine_ext(video_url)) == 'mp4':
            formats = [{'url': video_url, 'ext': 'mp4'}]

        else:
            manifest = self._download_webpage(video_url, video_id, note='Downloading m3u8 information')

            anvato_id = self._search_regex(r'anvato-(\d+)', manifest, 'Anvato ID', default=None)
            # Prefer Anvato if available; cbsnews.com m3u8 formats are re-encoded from Anvato source
            if anvato_id:
                return self.url_result(
                    smuggle_url(f'anvato:{self._ANVACK}:{anvato_id}', {'token': 'default'}),
                    AnvatoIE, url_transparent=True, _old_archive_ids=[make_archive_id(self, anvato_id)])

            formats, _ = self._parse_m3u8_formats_and_subtitles(
                manifest, video_url, 'mp4', m3u8_id='hls', video_id=video_id)

        def get_subtitles(subs_url):
            return {
                'en': [{
                    'url': subs_url,
                    'ext': 'dfxp',  # TTAF1
                }],
            } if url_or_none(subs_url) else None

        episode_meta = traverse_obj(item, {
            'season_number': ('season', {int_or_none}),
            'episode_number': ('episode', {int_or_none}),
        }) if item.get('isFullEpisode') else {}

        return {
            'id': video_id,
            'formats': formats,
            **traverse_obj(item, {
                'title': (None, ('fulltitle', 'title')),
                'description': 'dek',
                'timestamp': ('timestamp', {lambda x: float_or_none(x, 1000)}),
                'duration': ('duration', {float_or_none}),
                'subtitles': ('captions', {get_subtitles}),
                'thumbnail': ('images', ('hd', 'sd'), {url_or_none}),
                'is_live': ('type', {lambda x: x == 'live'}),
            }, get_all=False),
            **episode_meta,
        }


class CBSNewsEmbedIE(CBSNewsBaseIE):
    IE_NAME = 'cbsnews:embed'
    _VALID_URL = r'https?://(?:www\.)?cbsnews\.com/embed/video[^#]*#(?P<id>.+)'
    _TESTS = [{
        'url': 'https://www.cbsnews.com/embed/video/?v=1.c9b5b61492913d6660db0b2f03579ef25e86307a#1Vb7b9s2EP5XBAHbT6Gt98PAMKTJ0se6LVjWYWtdGBR1stlIpEBSTtwi%2F%2FvuJNkNhmHdGxgM2NL57vjd6zt%2B8PngdN%2Fyg79qeGvhzN%2FLGrS%2F%2BuBLB531V28%2B%2BO7Qg7%2Fy97r2z3xZ42NW8yLhDbA0S0KWlHnIijwKWJBHZZnHBa8Cgbpdf%2F89NM9Hi9fXifhpr8sr%2FlP848tn%2BTdXycX25zh4cdX%2FvHl6PmmPqnWQv9w8Ed%2B9GjYRim07bFEqdG%2BZVHuwTm65A7bVRrYtR5lAyMox7pigF6W4k%2By91mjspGsJ%2BwVae4%2BsvdnaO1p73HkXs%2FVisUDTGm7R8IcdnOROeq%2B19qT1amhA1VJtPenoTUgrtfKc9m7Rq8dP7nnjwOB7wg7ADdNt7VX64DWAWlKhPtmDEq22g4GF99x6Dk9E8OSsankHXqPNKDxC%2FdK7MLKTircTDgsI3mmj4OBdSq64dy7fd1x577RU1rt4cvMtOaulFYOd%2FLewRWvDO9lIgXFpZSnkZmjbv5SxKTPoQXClFbpsf%2Fhbbpzs0IB3vb8KkyzJQ%2BywOAgCrMpgRrz%2BKk4fvb7kFbR4XJCu0gAdtNO7woCwZTu%2BBUs9bam%2Fds71drVerpeisgrubLjAB4nnOSkWQnfr5W6o1ku5Xpr1MgrCbL0M0vUyDtfLLK15WiYp47xKWSLyjFVpwVmVJSLIoCjSOFkv3W7oKsVliwZJcB9nwXpZ5GEQQwY8jNKqKCBrgjTLeFxgdCIpazojDgnRtn43J6kG7nZ6cAbxh0EeFFk4%2B1u867cY5u4344n%2FxXjCqAjucdTHgLKojNKmSfO8KRsOFY%2FzKEYCKEJBzv90QA9nfm9gL%2BHulaFqUkz9ULUYxl62B3U%2FRVNLA8IhggaPycOoBuwOCESciDQVSSUgiOMsROB%2FhKfwCKOzEk%2B4k6rWd4uuT%2FwTDz7K7t3d3WLO8ISD95jSPQbayBacthbz86XVgxHwhex5zawzgDOmtp%2F3GPcXn0VXHdSS029%2Fj99UC%2FwJUvyKQ%2FzKyixIEVlYJOn4RxxuaH43Ty9fbJ5OObykHH435XAzJTHeOF4hhEUXD8URe%2FQ%2FBT%2BMpf8d5GN02Ox%2FfiGsl7TA7POu1xZ5%2BbTzcAVKMe48mqcC21hkacVEVScM26liVVBnrKkC4CLKyzAvHu0lhEaTKMFwI3a4SN9MsrfYzdBLq2vkwRD1gVviLT8kY9h2CHH6Y%2Bix6609weFtey4ESp60WtyeWMy%2BsmBuhsoKIyuoT%2Bq2R%2FrW5qi3g%2FvzS2j40DoixDP8%2BKP0yUdpXJ4l6Vla%2Bg9vce%2BC4yM5YlUcbA%2F0jLKdpmTwvsdN5z88nAIe08%2F0HgxeG1iv%2B6Hlhjh7uiW0SDzYNI92L401uha3JKYk268UVRzdOzNQvAaJqoXzAc80dAV440NZ1WVVAAMRYQ2KrGJFmDUsq8saWSnjvIj8t78y%2FRa3JRnbHVfyFpfwoDiGpPgjzekyUiKNlU3OMlwuLMmzgvEojllYVE2Z1HhImvsnk%2BuhusTEoB21PAtSFodeFK3iYhXEH9WOG2%2FkOE833sfeG%2Ff5cfHtEFNXgYes0%2FXj7aGivUgJ9XpusCtoNcNYVVnJVrrDo0OmJAutHCpuZul4W9lLcfy7BnuLPT02%2ByXsCTk%2B9zhzswIN04YueNSK%2BPtM0jS88QdLqSLJDTLsuGZJNolm2yO0PXh3UPnz9Ix5bfIAqxPjvETQsDCEiPG4QbqNyhBZISxybLnZYCrW5H3Axp690%2F0BJdXtDZ5ITuM4xj3f4oUHGzc5JeJmZKpp%2FjwKh4wMV%2FV1yx3emLoR0MwbG4K%2F%2BZgVep3PnzXGDHZ6a3i%2Fk%2BJrONDN13%2Bnq6tBTYk4o7cLGhBtqCC4KwacGHpEVuoH5JNro%2FE6JfE6d5RydbiR76k%2BW5wioDHBIjw1euhHjUGRB0y5A97KoaPx6MlL%2BwgboUVtUFRI%2FLemgTpdtF59ii7pab08kuPcfWzs0l%2FRI5takWnFpka0zOgWRtYcuf9aIxZMxlwr6IiGpsb6j2DQUXPl%2FimXI599Ev7fWjoPD78A',
        'info_dict': {
            'id': '6ZP4cXvo9FaX3VLH7MF4CgY30JFpY_GA',
            'ext': 'mp4',
            'title': 'Cops investigate gorilla incident at Cincinnati Zoo',
            'description': 'md5:fee7441ab8aaeb3c693482394738102b',
            'duration': 350,
            'timestamp': 1464719713,
            'upload_date': '20160531',
            'thumbnail': r're:^https?://.*\.jpg$',
        },
        'params': {'skip_download': 'm3u8'},
    }]

    def _real_extract(self, url):
        item = traverse_obj(self._parse_json(zlib.decompress(base64.b64decode(
            urllib.parse.unquote(self._match_id(url))),
            -zlib.MAX_WBITS).decode(), None), ('video', 'items', 0, {dict})) or {}

        video_id = item['mpxRefId']
        video_url = self._get_video_url(item)
        if not video_url:
            # Old embeds redirect user to ParamountPlus but most links are 404
            pplus_url = f'https://www.paramountplus.com/shows/video/{video_id}'
            try:
                self._request_webpage(HEADRequest(pplus_url), video_id)
                return self.url_result(pplus_url, ParamountPlusIE)
            except ExtractorError:
                self.raise_no_formats('This video is no longer available', True, video_id)

        return self._extract_video(item, video_url, video_id)


class CBSNewsIE(CBSNewsBaseIE):
    IE_NAME = 'cbsnews'
    IE_DESC = 'CBS News'
    _VALID_URL = r'https?://(?:www\.)?cbsnews\.com/(?:news|video)/(?P<id>[\w-]+)'

    _TESTS = [
        {
            # 60 minutes
            'url': 'http://www.cbsnews.com/news/artificial-intelligence-positioned-to-be-a-game-changer/',
            'info_dict': {
                'id': 'Y_nf_aEg6WwO9OLAq0MpKaPgfnBUxfW4',
                'ext': 'flv',
                'title': 'Artificial Intelligence, real-life applications',
                'description': 'md5:a7aaf27f1b4777244de8b0b442289304',
                'thumbnail': r're:^https?://.*\.jpg$',
                'duration': 317,
                'uploader': 'CBSI-NEW',
                'timestamp': 1476046464,
                'upload_date': '20161009',
            },
            'skip': 'This video is no longer available',
        },
        {
            'url': 'https://www.cbsnews.com/video/fort-hood-shooting-army-downplays-mental-illness-as-cause-of-attack/',
            'info_dict': {
                'id': 'SNJBOYzXiWBOvaLsdzwH8fmtP1SCd91Y',
                'ext': 'mp4',
                'title': 'Fort Hood shooting: Army downplays mental illness as cause of attack',
                'description': 'md5:4a6983e480542d8b333a947bfc64ddc7',
                'upload_date': '20140404',
                'timestamp': 1396650660,
                'thumbnail': r're:^https?://.*\.jpg$',
                'duration': 205,
                'subtitles': {
                    'en': [{
                        'ext': 'dfxp',
                    }],
                },
            },
            'params': {
                'skip_download': 'm3u8',
            },
        },
        {
            # 48 hours
            'url': 'http://www.cbsnews.com/news/maria-ridulph-murder-will-the-nations-oldest-cold-case-to-go-to-trial-ever-get-solved/',
            'info_dict': {
                'id': 'maria-ridulph-murder-will-the-nations-oldest-cold-case-to-go-to-trial-ever-get-solved',
                'title': 'Cold as Ice',
                'description': 'Can a childhood memory solve the 1957 murder of 7-year-old Maria Ridulph?',
            },
            'playlist_mincount': 7,
        },
        {
            'url': 'https://www.cbsnews.com/video/032823-cbs-evening-news/',
            'info_dict': {
                'id': '_2wuO7hD9LwtyM_TwSnVwnKp6kxlcXgE',
                'ext': 'mp4',
                'title': 'CBS Evening News, March 28, 2023',
                'description': 'md5:db20615aae54adc1d55a1fd69dc75d13',
                'duration': 1189,
                'timestamp': 1680042600,
                'upload_date': '20230328',
                'season': 'Season 2023',
                'season_number': 2023,
                'episode': 'Episode 83',
                'episode_number': 83,
                'thumbnail': r're:^https?://.*\.jpg$',
            },
            'params': {
                'skip_download': 'm3u8',
            },
        },
    ]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)

        playlist = self._extract_playlist(webpage, display_id)
        if playlist:
            return playlist

        item = self._get_item(webpage, display_id)
        video_id = item.get('mpxRefId') or display_id
        video_url = self._get_video_url(item)
        if not video_url:
            self.raise_no_formats('No video content was found', expected=True, video_id=video_id)

        return self._extract_video(item, video_url, video_id)


class CBSLocalBaseIE(CBSNewsBaseIE):
    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)

        item = self._get_item(webpage, display_id)
        video_id = item.get('mpxRefId') or display_id
        anvato_id = None
        video_url = self._get_video_url(item)

        if not video_url:
            anv_params = self._search_regex(
                r'<iframe[^>]+\bdata-src="https?://w3\.mp\.lura\.live/player/prod/v3/anvload\.html\?key=([^"]+)"',
                webpage, 'Anvato URL', default=None)

            if not anv_params:
                playlist = self._extract_playlist(webpage, display_id)
                if playlist:
                    return playlist
                self.raise_no_formats('No video content was found', expected=True, video_id=video_id)

            anv_data = self._parse_json(base64.urlsafe_b64decode(f'{anv_params}===').decode(), video_id)
            anvato_id = anv_data['v']
            return self.url_result(
                smuggle_url(f'anvato:{anv_data.get("anvack") or self._ANVACK}:{anvato_id}', {
                    'token': anv_data.get('token') or 'default',
                }), AnvatoIE, url_transparent=True, _old_archive_ids=[make_archive_id(self, anvato_id)])

        return self._extract_video(item, video_url, video_id)


class CBSLocalIE(CBSLocalBaseIE):
    _VALID_URL = rf'https?://(?:www\.)?cbsnews\.com/(?:{CBSNewsBaseIE._LOCALE_RE})/(?:live/)?video/(?P<id>[\w-]+)'
    _TESTS = [{
        # Anvato video via defaultPayload JSON
        'url': 'https://www.cbsnews.com/newyork/video/1st-cannabis-dispensary-opens-in-queens/',
        'info_dict': {
            'id': '6376747',
            'ext': 'mp4',
            'title': '1st cannabis dispensary opens in Queens',
            'description': 'The dispensary is women-owned and located in Jamaica.',
            'uploader': 'CBS',
            'duration': 20,
            'timestamp': 1680193657,
            'upload_date': '20230330',
            'categories': ['Stations\\Spoken Word\\WCBSTV', 'Content\\Google', 'Content\\News', 'Content\\News\\Local News'],
            'tags': 'count:11',
            'thumbnail': 're:^https?://.*',
            '_old_archive_ids': ['cbslocal 6376747'],
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        # cbsnews.com video via defaultPayload JSON
        'url': 'https://www.cbsnews.com/newyork/live/video/20230330171655-the-city-is-sounding-the-alarm-on-dangerous-social-media-challenges/',
        'info_dict': {
            'id': 'sJqfw7YvgSC6ant2zVmzt3y1jYKoL5J3',
            'ext': 'mp4',
            'title': 'the city is sounding the alarm on dangerous social media challenges',
            'description': 'md5:8eccc9b1b73be5138a52e9c4350d2cd6',
            'thumbnail': 'https://images-cbsn.cbsnews.com/prod/2023/03/30/story_22509622_1680196925.jpg',
            'duration': 41.0,
            'timestamp': 1680196615,
            'upload_date': '20230330',
        },
        'params': {'skip_download': 'm3u8'},
    }]


class CBSLocalArticleIE(CBSLocalBaseIE):
    _VALID_URL = rf'https?://(?:www\.)?cbsnews\.com/(?:{CBSNewsBaseIE._LOCALE_RE})/news/(?P<id>[\w-]+)'
    _TESTS = [{
        # Anvato video via iframe embed
        'url': 'https://www.cbsnews.com/newyork/news/mta-station-agents-leaving-their-booths-to-provide-more-direct-customer-service/',
        'playlist_count': 2,
        'info_dict': {
            'id': 'mta-station-agents-leaving-their-booths-to-provide-more-direct-customer-service',
            'title': 'MTA station agents begin leaving their booths to provide more direct customer service',
            'description': 'The more than 2,200 agents will provide face-to-face customer service to passengers.',
        },
    }, {
        'url': 'https://www.cbsnews.com/losangeles/news/safety-advocates-say-fatal-car-seat-failures-are-public-health-crisis/',
        'md5': 'f0ee3081e3843f575fccef901199b212',
        'info_dict': {
            'id': '3401037',
            'ext': 'mp4',
            'title': 'Safety Advocates Say Fatal Car Seat Failures Are \'Public Health Crisis\'',
            'thumbnail': 're:^https?://.*',
            'timestamp': 1463440500,
            'upload_date': '20160516',
        },
        'skip': 'Video has been removed',
    }]


class CBSNewsLiveBaseIE(CBSNewsBaseIE):
    def _get_id(self, url):
        raise NotImplementedError('This method must be implemented by subclasses')

    def _real_extract(self, url):
        video_id = self._get_id(url)
        if not video_id:
            raise ExtractorError('Livestream is not available', expected=True)

        data = traverse_obj(self._download_json(
            'https://feeds-cbsn.cbsnews.com/2.0/rundown/', video_id, query={
                'partner': 'cbsnsite',
                'edition': video_id,
                'type': 'live',
            }), ('navigation', 'data', 0, {dict}))

        video_url = traverse_obj(data, (('videoUrlDAI', ('videoUrl', 'base')), {url_or_none}), get_all=False)
        if not video_url:
            raise UserNotLive(video_id=video_id)

        formats, subtitles = self._extract_m3u8_formats_and_subtitles(video_url, video_id, 'mp4', m3u8_id='hls')

        return {
            'id': video_id,
            'formats': formats,
            'subtitles': subtitles,
            'is_live': True,
            **traverse_obj(data, {
                'title': 'headline',
                'description': 'rundown_slug',
                'thumbnail': ('images', 'thumbnail_url_hd', {url_or_none}),
            }),
        }


class CBSLocalLiveIE(CBSNewsLiveBaseIE):
    _VALID_URL = rf'https?://(?:www\.)?cbsnews\.com/(?P<id>{CBSNewsBaseIE._LOCALE_RE})/live/?(?:[?#]|$)'
    _TESTS = [{
        'url': 'https://www.cbsnews.com/losangeles/live/',
        'info_dict': {
            'id': 'CBSN-LA',
            'ext': 'mp4',
            'title': str,
            'description': r're:KCBS/CBSN_LA.CRISPIN.\w+.RUNDOWN \w+ \w+',
            'thumbnail': r're:^https?://.*\.jpg$',
            'live_status': 'is_live',
        },
        'params': {'skip_download': 'm3u8'},
    }]

    def _get_id(self, url):
        return format_field(self._LOCALES, self._match_id(url), 'CBSN-%s')


class CBSNewsLiveIE(CBSNewsLiveBaseIE):
    IE_NAME = 'cbsnews:live'
    IE_DESC = 'CBS News Livestream'
    _VALID_URL = r'https?://(?:www\.)?cbsnews\.com/live/?(?:[?#]|$)'
    _TESTS = [{
        'url': 'https://www.cbsnews.com/live/',
        'info_dict': {
            'id': 'CBSN-US',
            'ext': 'mp4',
            'title': str,
            'description': r're:\w+ \w+ CRISPIN RUNDOWN',
            'thumbnail': r're:^https?://.*\.jpg$',
            'live_status': 'is_live',
        },
        'params': {'skip_download': 'm3u8'},
    }]

    def _get_id(self, url):
        return 'CBSN-US'


class CBSNewsLiveVideoIE(InfoExtractor):
    IE_NAME = 'cbsnews:livevideo'
    IE_DESC = 'CBS News Live Videos'
    _VALID_URL = r'https?://(?:www\.)?cbsnews\.com/live/video/(?P<id>[^/?#]+)'

    # Live videos get deleted soon. See http://www.cbsnews.com/live/ for the latest examples
    _TESTS = [{
        'url': 'http://www.cbsnews.com/live/video/clinton-sanders-prepare-to-face-off-in-nh/',
        'info_dict': {
            'id': 'clinton-sanders-prepare-to-face-off-in-nh',
            'ext': 'mp4',
            'title': 'Clinton, Sanders Prepare To Face Off In NH',
            'duration': 334,
        },
        'skip': 'Video gone',
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)

        video_info = self._download_json(
            'http://feeds.cbsn.cbsnews.com/rundown/story', display_id, query={
                'device': 'desktop',
                'dvr_slug': display_id,
            })

        return {
            'id': display_id,
            'display_id': display_id,
            'formats': self._extract_akamai_formats(video_info['url'], display_id),
            **traverse_obj(video_info, {
                'title': 'headline',
                'thumbnail': ('thumbnail_url_hd', {url_or_none}),
                'duration': ('segmentDur', {parse_duration}),
            }),
        }
