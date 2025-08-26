import base64
import re
import urllib.parse

from .common import InfoExtractor
from ..networking import HEADRequest
from ..networking.exceptions import HTTPError
from ..utils import (
    ExtractorError,
    determine_ext,
    filter_dict,
    float_or_none,
    int_or_none,
    parse_qs,
    traverse_obj,
    try_get,
    update_url_query,
    urlhandle_detect_ext,
)


class WistiaBaseIE(InfoExtractor):
    _VALID_ID_REGEX = r'(?P<id>[a-z0-9]{10})'
    _VALID_URL_BASE = r'https?://(?:\w+\.)?wistia\.(?:net|com)/(?:embed/)?'
    _EMBED_BASE_URL = 'http://fast.wistia.net/embed/'

    def _download_embed_config(self, config_type, config_id, referer):
        base_url = self._EMBED_BASE_URL + f'{config_type}/{config_id}'
        video_password = self.get_param('videopassword')
        embed_config = self._download_json(
            base_url + '.json', config_id, headers={
                'Referer': referer if referer.startswith('http') else base_url,  # Some videos require this.
            }, query=filter_dict({'password': video_password}))

        error = traverse_obj(embed_config, 'error')
        if error:
            raise ExtractorError(
                f'Error while getting the playlist: {error}', expected=True)

        if traverse_obj(embed_config, (
                'media', ('embed_options', 'embedOptions'), 'plugin',
                'passwordProtectedVideo', 'on', any)) == 'true':
            if video_password:
                raise ExtractorError('Invalid video password', expected=True)
            raise ExtractorError(
                'This content is password-protected. Use the --video-password option', expected=True)

        return embed_config

    def _get_real_ext(self, url):
        ext = determine_ext(url, default_ext='bin')
        if ext == 'bin':
            urlh = self._request_webpage(
                HEADRequest(url), None, note='Checking media extension',
                errnote='HEAD request returned error', fatal=False)
            if urlh:
                ext = urlhandle_detect_ext(urlh, default='bin')
        return 'mp4' if ext == 'mov' else ext

    def _extract_media(self, embed_config):
        data = embed_config['media']
        video_id = data['hashedId']
        title = data['name']

        formats = []
        thumbnails = []
        for a in data['assets']:
            aurl = a.get('url')
            if not aurl:
                continue
            astatus = a.get('status')
            atype = a.get('type')
            if (astatus is not None and astatus != 2) or atype in ('preview', 'storyboard'):
                continue
            elif atype in ('still', 'still_image'):
                thumbnails.append({
                    'url': aurl.replace('.bin', f'.{self._get_real_ext(aurl)}'),
                    'width': int_or_none(a.get('width')),
                    'height': int_or_none(a.get('height')),
                    'filesize': int_or_none(a.get('size')),
                })
            else:
                aext = a.get('ext') or self._get_real_ext(aurl)
                display_name = a.get('display_name')
                format_id = atype
                if atype and atype.endswith('_video') and display_name:
                    format_id = f'{atype[:-6]}-{display_name}'
                f = {
                    'format_id': format_id,
                    'url': aurl,
                    'tbr': int_or_none(a.get('bitrate')) or None,
                    'quality': 1 if atype == 'original' else None,
                }
                if display_name == 'Audio':
                    f.update({
                        'vcodec': 'none',
                    })
                else:
                    f.update({
                        'width': int_or_none(a.get('width')),
                        'height': int_or_none(a.get('height')),
                        'vcodec': a.get('codec'),
                    })
                if a.get('container') == 'm3u8' or aext == 'm3u8':
                    ts_f = f.copy()
                    ts_f.update({
                        'ext': 'ts',
                        'format_id': f['format_id'].replace('hls-', 'ts-'),
                        'url': f['url'].replace('.bin', '.ts'),
                    })
                    formats.append(ts_f)
                    f.update({
                        'ext': 'mp4',
                        'protocol': 'm3u8_native',
                    })
                else:
                    f.update({
                        'container': a.get('container'),
                        'ext': aext,
                        'filesize': int_or_none(a.get('size')),
                    })
                formats.append(f)

        subtitles = {}
        for caption in data.get('captions', []):
            language = caption.get('language')
            if not language:
                continue
            subtitles[language] = [{
                'url': self._EMBED_BASE_URL + 'captions/' + video_id + '.vtt?language=' + language,
            }]

        return {
            'id': video_id,
            'title': title,
            'description': data.get('seoDescription'),
            'formats': formats,
            'thumbnails': thumbnails,
            'duration': float_or_none(data.get('duration')),
            'timestamp': int_or_none(data.get('createdAt')),
            'subtitles': subtitles,
        }

    @classmethod
    def _extract_from_webpage(cls, url, webpage):
        from .teachable import TeachableIE

        if list(TeachableIE._extract_embed_urls(url, webpage)):
            return

        yield from super()._extract_from_webpage(url, webpage)

    @classmethod
    def _extract_wistia_async_embed(cls, webpage):
        # https://wistia.com/support/embed-and-share/video-on-your-website
        # https://wistia.com/support/embed-and-share/channel-embeds
        yield from re.finditer(
            r'''(?sx)
                <(?:div|section)[^>]+class=([\"'])(?:(?!\1).)*?(?P<type>wistia[a-z_0-9]+)\s*\bwistia_async_(?P<id>[a-z0-9]{10})\b(?:(?!\1).)*?\1
            ''', webpage)

    @classmethod
    def _extract_url_media_id(cls, url):
        mobj = re.search(r'(?:wmediaid|wvideo(?:id)?)]?=(?P<id>[a-z0-9]{10})', urllib.parse.unquote_plus(url))
        if mobj:
            return mobj.group('id')


class WistiaIE(WistiaBaseIE):
    _VALID_URL = rf'(?:wistia:|{WistiaBaseIE._VALID_URL_BASE}(?:iframe|medias)/){WistiaBaseIE._VALID_ID_REGEX}'
    _EMBED_REGEX = [
        r'''(?x)
            <(?:meta[^>]+?content|(?:iframe|script)[^>]+?src)=["\']
            (?P<url>(?:https?:)?//(?:fast\.)?wistia\.(?:net|com)/embed/(?:iframe|medias)/[a-z0-9]{10})
            ''']
    _TESTS = [{
        # with hls video
        'url': 'wistia:807fafadvk',
        'md5': 'daff0f3687a41d9a71b40e0e8c2610fe',
        'info_dict': {
            'id': '807fafadvk',
            'ext': 'mp4',
            'title': 'Drip Brennan Dunn Workshop',
            'description': 'a JV Webinars video',
            'upload_date': '20160518',
            'timestamp': 1463607249,
            'duration': 4987.11,
        },
        'skip': 'video unavailable',
    }, {
        'url': 'wistia:a6ndpko1wg',
        'md5': '10c1ce9c4dde638202513ed17a3767bd',
        'info_dict': {
            'id': 'a6ndpko1wg',
            'ext': 'mp4',
            'title': 'BXO-S02-E02-Boxed_Water-v4.mp4',
            'upload_date': '20210324',
            'description': 'md5:3b9296a45aa46010767451b3691b1105',
            'duration': 966.0,
            'timestamp': 1616614369,
            'thumbnail': r're:https?://embed(?:-ssl)?\.wistia\.com/.+\.(?:jpg|png)',
        },
    }, {
        'url': 'wistia:5vd7p4bct5',
        'md5': 'b9676d24bf30945d97060638fbfe77f0',
        'info_dict': {
            'id': '5vd7p4bct5',
            'ext': 'mp4',
            'title': 'md5:eaa9f64c4efd7b5f098b9b6118597679',
            'description': 'md5:a9bea0315f0616aa5df2dc413ddcdd0f',
            'upload_date': '20220915',
            'timestamp': 1663258727,
            'duration': 623.019,
            'thumbnail': r're:https?://embed(?:-ssl)?\.wistia\.com/.+\.(?:jpg|png)',
        },
    }, {
        'url': 'wistia:sh7fpupwlt',
        'only_matching': True,
    }, {
        'url': 'http://fast.wistia.net/embed/iframe/sh7fpupwlt',
        'only_matching': True,
    }, {
        'url': 'http://fast.wistia.com/embed/iframe/sh7fpupwlt',
        'only_matching': True,
    }, {
        'url': 'http://fast.wistia.net/embed/medias/sh7fpupwlt.json',
        'only_matching': True,
    }]
    _WEBPAGE_TESTS = [{
        'url': 'https://www.weidert.com/blog/wistia-channels-video-marketing-tool',
        'info_dict': {
            'id': 'cqwukac3z1',
            'ext': 'mp4',
            'title': 'How Wistia Channels Can Help Capture Inbound Value From Your Video Content',
            'duration': 158.125,
            'timestamp': 1618974400,
            'description': 'md5:27abc99a758573560be72600ef95cece',
            'upload_date': '20210421',
            'thumbnail': r're:https?://embed(?:-ssl)?\.wistia\.com/.+\.(?:jpg|png)',
        },
        'skip': 'Invalid URL',
    }, {
        'url': 'https://study.com/academy/lesson/north-american-exploration-failed-colonies-of-spain-france-england.html#lesson',
        'md5': 'b9676d24bf30945d97060638fbfe77f0',
        'info_dict': {
            'id': '5vd7p4bct5',
            'ext': 'mp4',
            'title': 'paywall_north-american-exploration-failed-colonies-of-spain-france-england',
            'upload_date': '20220915',
            'timestamp': 1663258727,
            'duration': 623.019,
            'thumbnail': r're:https?://embed(?:-ssl)?\.wistia\.com/.+\.(?:jpg|png)',
            'description': 'a Paywall Videos video',
        },
    }, {
        'url': 'https://support.wistia.com/en/articles/8233354-embedding-your-media',
        'info_dict': {
            'id': '8233354-embedding-your-media',
            'title': 'Embedding Your Media | Wistia Help Center',
            'age_limit': 0,
            'description': 'md5:32a5edc0e266cd61e2d15be28873d614',
            'thumbnail': r're:https?://downloads\.intercomcdn\.com/.+\.jpg',
        },
        'playlist_count': 2,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        embed_config = self._download_embed_config('medias', video_id, url)
        return self._extract_media(embed_config)

    @classmethod
    def _extract_embed_urls(cls, url, webpage):
        urls = list(super()._extract_embed_urls(url, webpage))
        for match in cls._extract_wistia_async_embed(webpage):
            if match.group('type') != 'wistia_channel':
                urls.append('wistia:{}'.format(match.group('id')))
        for match in re.finditer(r'(?:data-wistia-?id=["\']|Wistia\.embed\(["\']|id=["\']wistia_)(?P<id>[a-z0-9]{10})',
                                 webpage):
            urls.append('wistia:{}'.format(match.group('id')))
        if not WistiaChannelIE._extract_embed_urls(url, webpage):  # Fallback
            media_id = cls._extract_url_media_id(url)
            if media_id:
                urls.append('wistia:{}'.format(match.group('id')))
        return urls


class WistiaPlaylistIE(WistiaBaseIE):
    _VALID_URL = rf'{WistiaBaseIE._VALID_URL_BASE}playlists/{WistiaBaseIE._VALID_ID_REGEX}'

    _TESTS = [{
        'url': 'https://fast.wistia.net/embed/playlists/aodt9etokc',
        'info_dict': {
            'id': 'aodt9etokc',
        },
        'playlist_count': 3,
    }]

    def _real_extract(self, url):
        playlist_id = self._match_id(url)
        playlist = self._download_embed_config('playlists', playlist_id, url)

        entries = []
        for media in (try_get(playlist, lambda x: x[0]['medias']) or []):
            embed_config = media.get('embed_config')
            if not embed_config:
                continue
            entries.append(self._extract_media(embed_config))

        return self.playlist_result(entries, playlist_id)


class WistiaChannelIE(WistiaBaseIE):
    _VALID_URL = rf'(?:wistiachannel:|{WistiaBaseIE._VALID_URL_BASE}channel/){WistiaBaseIE._VALID_ID_REGEX}'

    _TESTS = [{
        # JSON Embed API returns 403, should fall back to webpage
        'url': 'https://fast.wistia.net/embed/channel/yvyvu7wjbg?wchannelid=yvyvu7wjbg',
        'info_dict': {
            'id': 'yvyvu7wjbg',
            'title': 'Copysmith Tutorials and Education!',
            'description': 'Learn all things Copysmith via short and informative videos!',
        },
        'playlist_mincount': 7,
        'skip': 'Invalid URL',
    }, {
        'url': 'https://fast.wistia.net/embed/channel/3802iirk0l',
        'info_dict': {
            'id': '3802iirk0l',
            'title': 'The Roof',
        },
        'playlist_mincount': 20,
    }, {
        # link to popup video, follow --no-playlist
        'url': 'https://fast.wistia.net/embed/channel/3802iirk0l?wchannelid=3802iirk0l&wmediaid=sp5dqjzw3n',
        'info_dict': {
            'id': 'sp5dqjzw3n',
            'ext': 'mp4',
            'title': 'The Roof S2: The Modern CRO',
            'thumbnail': r're:https?://embed(?:-ssl)?\.wistia\.com/.+\.(?:jpg|png)',
            'duration': 86.487,
            'description': 'A sales leader on The Roof? Man, they really must be letting anyone up here this season.\n',
            'timestamp': 1619790290,
            'upload_date': '20210430',
        },
        'params': {'noplaylist': True, 'skip_download': True},
    }]
    _WEBPAGE_TESTS = [{
        'url': 'https://www.profitwell.com/recur/boxed-out',
        'info_dict': {
            'id': '6jyvmqz6zs',
            'title': 'Boxed Out',
            'description': 'md5:14a8a93a1dbe236718e6a59f8c8c7bae',
        },
        'playlist_mincount': 30,
        'skip': 'Site no longer embeds Wistia playlists',
    }, {
        # section instead of div
        'url': 'https://360learning.com/studio/onboarding-joei/',
        'info_dict': {
            'id': 'z874k93n2o',
            'title': 'Onboarding Joei.',
            'description': 'Coming to you weekly starting Feb 19th.',
        },
        'playlist_mincount': 20,
    }, {
        'url': 'https://amplitude.com/amplify-sessions?amp%5Bwmediaid%5D=pz0m0l0if3&amp%5Bwvideo%5D=pz0m0l0if3&wchannelid=emyjmwjf79&wmediaid=i8um783bdt',
        'info_dict': {
            'id': 'pz0m0l0if3',
            'title': 'A Framework for Improving Product Team Performance',
            'ext': 'mp4',
            'timestamp': 1653935275,
            'upload_date': '20220530',
            'description': 'Learn how to help your company improve and achieve your product related goals.',
            'duration': 1854.39,
            'thumbnail': r're:https?://embed(?:-ssl)?\.wistia\.com/.+\.(?:jpg|png)',
        },
        'skip': 'Invalid URL',
    }]

    def _real_extract(self, url):
        channel_id = self._match_id(url)
        media_id = self._extract_url_media_id(url)
        if not self._yes_playlist(channel_id, media_id, playlist_label='channel'):
            return self.url_result(f'wistia:{media_id}', 'Wistia')

        try:
            data = self._download_embed_config('channel', channel_id, url)
        except (ExtractorError, HTTPError):
            # Some channels give a 403 from the JSON API
            self.report_warning('Failed to download channel data from API, falling back to webpage.')
            webpage = self._download_webpage(f'https://fast.wistia.net/embed/channel/{channel_id}', channel_id)
            data = self._parse_json(
                self._search_regex(rf'wchanneljsonp-{channel_id}\'\]\s*=[^\"]*\"([A-Za-z0-9=/]*)', webpage, 'jsonp', channel_id),
                channel_id, transform_source=lambda x: urllib.parse.unquote_plus(base64.b64decode(x).decode('utf-8')))

        # XXX: can there be more than one series?
        series = traverse_obj(data, ('series', 0), default={})

        entries = [
            self.url_result(f'wistia:{video["hashedId"]}', WistiaIE, title=video.get('name'))
            for video in traverse_obj(series, ('sections', ..., 'videos', ...)) or []
            if video.get('hashedId')
        ]

        return self.playlist_result(
            entries, channel_id, playlist_title=series.get('title'), playlist_description=series.get('description'))

    @classmethod
    def _extract_embed_urls(cls, url, webpage):
        yield from super()._extract_embed_urls(url, webpage)
        for match in cls._extract_wistia_async_embed(webpage):
            if match.group('type') == 'wistia_channel':
                # original url may contain wmediaid query param
                yield update_url_query(f'wistiachannel:{match.group("id")}', parse_qs(url))
