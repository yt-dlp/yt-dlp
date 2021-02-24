from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    float_or_none,
    int_or_none,
    try_get,
    unescapeHTML,
)


class WistiaBaseIE(InfoExtractor):
    _VALID_ID_REGEX = r'(?P<id>[a-z0-9]{10})'
    _VALID_URL_BASE = r'https?://(?:fast\.)?wistia\.(?:net|com)/embed/'
    _EMBED_BASE_URL = 'http://fast.wistia.com/embed/'

    def _download_embed_config(self, config_type, config_id, referer):
        base_url = self._EMBED_BASE_URL + '%ss/%s' % (config_type, config_id)
        embed_config = self._download_json(
            base_url + '.json', config_id, headers={
                'Referer': referer if referer.startswith('http') else base_url,  # Some videos require this.
            })

        if isinstance(embed_config, dict) and embed_config.get('error'):
            raise ExtractorError(
                'Error while getting the playlist', expected=True)

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


class WistiaIE(WistiaBaseIE):
    _VALID_URL = r'(?:wistia:|%s(?:iframe|medias)/)%s' % (WistiaBaseIE._VALID_URL_BASE, WistiaBaseIE._VALID_ID_REGEX)

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

    # https://wistia.com/support/embed-and-share/video-on-your-website
    @staticmethod
    def _extract_url(webpage):
        urls = WistiaIE._extract_urls(webpage)
        return urls[0] if urls else None

    @staticmethod
    def _extract_urls(webpage):
        urls = []
        for match in re.finditer(
                r'<(?:meta[^>]+?content|(?:iframe|script)[^>]+?src)=["\'](?P<url>(?:https?:)?//(?:fast\.)?wistia\.(?:net|com)/embed/(?:iframe|medias)/[a-z0-9]{10})', webpage):
            urls.append(unescapeHTML(match.group('url')))
        for match in re.finditer(
                r'''(?sx)
                    <div[^>]+class=(["'])(?:(?!\1).)*?\bwistia_async_(?P<id>[a-z0-9]{10})\b(?:(?!\1).)*?\1
                ''', webpage):
            urls.append('wistia:%s' % match.group('id'))
        for match in re.finditer(r'(?:data-wistia-?id=["\']|Wistia\.embed\(["\']|id=["\']wistia_)(?P<id>[a-z0-9]{10})', webpage):
            urls.append('wistia:%s' % match.group('id'))
        return urls

    def _real_extract(self, url):
        video_id = self._match_id(url)
        embed_config = self._download_embed_config('media', video_id, url)
        return self._extract_media(embed_config)


class WistiaPlaylistIE(WistiaBaseIE):
    _VALID_URL = r'%splaylists/%s' % (WistiaIE._VALID_URL_BASE, WistiaIE._VALID_ID_REGEX)

    _TEST = {
        'url': 'https://fast.wistia.net/embed/playlists/aodt9etokc',
        'info_dict': {
            'id': 'aodt9etokc',
        },
        'playlist_count': 3,
    }

    def _real_extract(self, url):
        playlist_id = self._match_id(url)
        playlist = self._download_embed_config('playlist', playlist_id, url)

        entries = []
        for media in (try_get(playlist, lambda x: x[0]['medias']) or []):
            embed_config = media.get('embed_config')
            if not embed_config:
                continue
            entries.append(self._extract_media(embed_config))

        return self.playlist_result(entries, playlist_id)
