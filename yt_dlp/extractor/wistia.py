import re

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    float_or_none,
    int_or_none,
    try_call,
    try_get,
    parse_qs,
    traverse_obj,
    update_url_query,
)

import urllib.parse
import urllib.error
from base64 import b64decode


class WistiaBaseIE(InfoExtractor):
    _VALID_ID_REGEX = r'(?P<id>[a-z0-9]{10})'
    _VALID_URL_BASE = r'https?://(?:\w+\.)?wistia\.(?:net|com)/(?:embed/)?'
    _EMBED_BASE_URL = 'http://fast.wistia.net/embed/'

    def _download_embed_config(self, config_type, config_id, referer):
        base_url = self._EMBED_BASE_URL + '%s/%s' % (config_type, config_id)
        embed_config = self._download_json(
            base_url + '.json', config_id, headers={
                'Referer': referer if referer.startswith('http') else base_url,  # Some videos require this.
            })

        error = traverse_obj(embed_config, 'error')
        if error:
            raise ExtractorError(
                f'Error while getting the playlist: {error}', expected=True)

        return embed_config

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
                    'url': aurl,
                    'width': int_or_none(a.get('width')),
                    'height': int_or_none(a.get('height')),
                    'filesize': int_or_none(a.get('size')),
                })
            else:
                aext = a.get('ext')
                display_name = a.get('display_name')
                format_id = atype
                if atype and atype.endswith('_video') and display_name:
                    format_id = '%s-%s' % (atype[:-6], display_name)
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

        self._sort_formats(formats)

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

        for entry in super()._extract_from_webpage(url, webpage):
            yield {
                **entry,
                '_type': 'url_transparent',
                'uploader': try_call(lambda: re.match(r'(?:https?://)?([^/]+)/', url).group(1)),
            }

    @classmethod
    def _extract_wistia_async_embed(cls, webpage):
        # https://wistia.com/support/embed-and-share/video-on-your-website
        # https://wistia.com/support/embed-and-share/channel-embeds
        yield from re.finditer(
            r'''(?sx)
                <(?:div|section)[^>]+class=([\"'])(?:(?!\1).)*?(?P<type>wistia[a-z_0-9]+)\s*\bwistia_async_(?P<id>[a-z0-9]{10})\b(?:(?!\1).)*?\1
            ''', webpage)


class WistiaIE(WistiaBaseIE):
    _VALID_URL = r'(?:wistia:|%s(?:iframe|medias)/)%s' % (WistiaBaseIE._VALID_URL_BASE, WistiaBaseIE._VALID_ID_REGEX)
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
            'ext': 'bin',
            'title': 'Episode 2: Boxed Water\'s retention is thirsty',
            'upload_date': '20210324',
            'description': 'md5:da5994c2c2d254833b412469d9666b7a',
            'duration': 966.0,
            'timestamp': 1616614369,
            'thumbnail': 'https://embed-ssl.wistia.com/deliveries/53dc60239348dc9b9fba3755173ea4c2.bin',
        }
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
            'ext': 'bin',
            'title': 'How Using Wistia Channels Helps Capture More Inbound Value From Your Video Content',
            'description': 'md5:d7f3ab63b8419a20777b139449a9ba1f',
            'age_limit': 0,
            'duration': 158.125,
            'thumbnail': 'https://www.weidert.com/hubfs/Blog/2021-blog-images/WW_PPC_Wistia_Artwork_N1_V2.png#keepProtocol',
            'uploader': 'www.weidert.com',
            'upload_date': str,  # generic uses Last-Modified, so this is subject to change
            'timestamp': float,
        }
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
                urls.append('wistia:%s' % match.group('id'))
        for match in re.finditer(r'(?:data-wistia-?id=["\']|Wistia\.embed\(["\']|id=["\']wistia_)(?P<id>[a-z0-9]{10})',
                                 webpage):
            urls.append('wistia:%s' % match.group('id'))
        return urls


class WistiaPlaylistIE(WistiaBaseIE):
    _VALID_URL = r'%splaylists/%s' % (WistiaBaseIE._VALID_URL_BASE, WistiaBaseIE._VALID_ID_REGEX)

    _TEST = {
        'url': 'https://fast.wistia.net/embed/playlists/aodt9etokc',
        'info_dict': {
            'id': 'aodt9etokc',
        },
        'playlist_count': 3,
    }

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
    _VALID_URL = r'(?:wistiachannel:|%schannel/)%s' % (WistiaBaseIE._VALID_URL_BASE, WistiaBaseIE._VALID_ID_REGEX)

    _TESTS = [{
        # JSON Embed API returns 403, should fall back to webpage
        'url': 'https://fast.wistia.net/embed/channel/yvyvu7wjbg?wchannelid=yvyvu7wjbg',
        'info_dict': {
            'id': 'yvyvu7wjbg',
            'title': 'Copysmith Tutorials and Education!',
            'description': 'Learn all things Copysmith via short and informative videos!'
        },
        'playlist_mincount': 10,
        'expected_warnings': ['falling back to webpage'],
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
            'ext': 'bin',
            'title': 'The Roof S2: The Modern CRO',
            'thumbnail': 'https://embed-ssl.wistia.com/deliveries/dadfa9233eaa505d5e0c85c23ff70741.bin',
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
            'title': 'Boxed Out | ProfitWell',
            'description': 'md5:1b1eb10bee670851bf69299aaef2d2a4',
            'upload_date': str,  # generic uses Last-Modified, which is changed everytime a video is added
            'timestamp': float,
            'uploader': 'www.profitwell.com',
            'thumbnail': 'https://www.profitwell.com/hubfs/Screen%20Shot%202020-11-17%20at%201.01.45%20PM.png#keepProtocol',
            'age_limit': 0,
        },
        'playlist_mincount': 30,
    }, {
        # section instead of div
        'url': 'https://360learning.com/studio/onboarding-joei/',
        'info_dict': {
            'id': 'z874k93n2o',
            'title': 'Onboarding Joei - our content director | 360Learning',
            'description': 'md5:f9de04c83c0ca710aa1ca56d45823c67',
            'thumbnail': 'https://images.prismic.io/360learning/3d45dbe9-d7ad-41d4-8954-066f4015d0a5_onboardingJoei.png?auto=compress,format',
            'age_limit': 0,
            'uploader': '360learning.com',
        },
        'playlist_mincount': 20,
    }]

    def _real_extract(self, url):
        channel_id = self._match_id(url)
        params = parse_qs(url)
        media_id = traverse_obj(params, ('wmediaid', 0))
        if not self._yes_playlist(channel_id, media_id, playlist_label='channel'):
            return self.url_result(f'wistia:{media_id}', 'Wistia')

        try:
            data = self._download_embed_config('channel', channel_id, url)
        except (ExtractorError, urllib.error.HTTPError):
            # Some channels give a 403 from the JSON API
            self.report_warning('Failed to download channel data from API, falling back to webpage.')
            webpage = self._download_webpage(f'https://fast.wistia.net/embed/channel/{channel_id}', channel_id)
            data = self._parse_json(
                self._search_regex(r'wchanneljsonp-%s\'\]\s*=[^\"]*\"([A-Za-z0-9=/]*)' % channel_id, webpage, 'jsonp', channel_id),
                channel_id, transform_source=lambda x: urllib.parse.unquote_plus(b64decode(x).decode('utf-8')))

        # XXX: the response suggests there can be multiple "series" but I've never seen one
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
