import json
import re

from .common import InfoExtractor
from .. import traverse_obj
from ..utils import (
    ExtractorError,
    clean_html,
    determine_ext,
    get_element_by_class,
    int_or_none,
    js_to_json,
    merge_dicts,
    parse_bitrate,
    parse_resolution,
    remove_end,
    str_or_none,
    url_or_none,
    urlencode_postdata,
)


class IcareusIE(InfoExtractor):
    _DOMAINS = '|'.join(map(re.escape, (
        'asahitv.fi',
        'helsinkikanava.fi',
        'hyvinvointitv.fi',
        'inez.fi',
        'permanto.fi',
        'suite.icareus.com',
        'videos.minifiddlers.org',
    )))
    _VALID_URL = rf'(?P<base_url>https?://(?:www\.)?(?:{_DOMAINS}))/[^?#]+/player/[^?#]+\?(?:[^#]+&)?(?:assetId|eventId)=(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://www.helsinkikanava.fi/fi_FI/web/helsinkikanava/player/vod?assetId=68021894',
        'md5': 'ca0b62ffc814a5411dfa6349cf5adb8a',
        'info_dict': {
            'id': '68021894',
            'ext': 'mp4',
            'title': 'Perheiden parhaaksi',
            'description': 'md5:295785ea408e5ac00708766465cc1325',
            'thumbnail': 'https://www.helsinkikanava.fi/image/image_gallery?img_id=68022501',
            'upload_date': '20200924',
            'timestamp': 1600938300,
        },
    }, {  # Recorded livestream
        'url': 'https://www.helsinkikanava.fi/fi/web/helsinkikanava/player/event/view?eventId=76241489',
        'md5': '014327e69dfa7b949fcc861f6d162d6d',
        'info_dict': {
            'id': '76258304',
            'ext': 'mp4',
            'title': 'Helsingin kaupungin ja HUSin tiedotustilaisuus koronaepidemiatilanteesta 24.11.2020',
            'description': 'md5:3129d041c6fbbcdc7fe68d9a938fef1c',
            'thumbnail': 'https://icareus-suite.secure2.footprint.net/image/image_gallery?img_id=76288630',
            'upload_date': '20201124',
            'timestamp': 1606206600,
        },
    }, {  # Non-m3u8 stream
        'url': 'https://suite.icareus.com/fi/web/westend-indians/player/vod?assetId=47567389',
        'md5': '72fc04ee971bbedc44405cdf16c990b6',
        'info_dict': {
            'id': '47567389',
            'ext': 'mp4',
            'title': 'Omatoiminen harjoittelu - Laukominen',
            'description': '',
            'thumbnail': 'https://suite.icareus.com/image/image_gallery?img_id=47568162',
            'upload_date': '20200319',
            'timestamp': 1584658080,
        },
    }, {
        'url': 'https://asahitv.fi/fi/web/asahi/player/vod?assetId=89415818',
        'only_matching': True,
    }, {
        'url': 'https://hyvinvointitv.fi/fi/web/hyvinvointitv/player/vod?assetId=89149730',
        'only_matching': True,
    }, {
        'url': 'https://inez.fi/fi/web/inez-media/player/vod?assetId=71328822',
        'only_matching': True,
    }, {
        'url': 'https://www.permanto.fi/fi/web/alfatv/player/vod?assetId=135497515',
        'only_matching': True,
    }, {
        'url': 'https://videos.minifiddlers.org/web/international-minifiddlers/player/vod?assetId=1982759',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        base_url, temp_id = self._match_valid_url(url).groups()
        webpage = self._download_webpage(url, temp_id)

        video_id = self._search_regex(r"_icareus\['itemId'\]\s*=\s*'(\d+)'", webpage, 'video_id')
        organization_id = self._search_regex(r"_icareus\['organizationId'\]\s*=\s*'(\d+)'", webpage, 'organization_id')

        assets = self._download_json(
            self._search_regex(r'var\s+publishingServiceURL\s*=\s*"(http[^"]+)";', webpage, 'api_base'),
            video_id, data=urlencode_postdata({
                'version': '03',
                'action': 'getAssetPlaybackUrls',
                'organizationId': organization_id,
                'assetId': video_id,
                'token': self._search_regex(r"_icareus\['token'\]\s*=\s*'([a-f0-9]+)'", webpage, 'icareus_token'),
            }))

        subtitles = {
            remove_end(sdesc.split(' ')[0], ':'): [{'url': url_or_none(surl)}]
            for _, sdesc, surl in assets.get('subtitles') or []
        }

        formats = [{
            'format': item.get('name'),
            'format_id': 'audio',
            'vcodec': 'none',
            'url': url_or_none(item['url']),
            'tbr': int_or_none(self._search_regex(
                r'\((\d+)\s*k\)', item.get('name') or '', 'audio bitrate', default=None)),
        } for item in assets.get('audio_urls') or [] if url_or_none(item.get('url'))]

        for item in assets.get('urls') or []:
            video_url = url_or_none(item.get('url'))
            if video_url is None:
                continue
            ext = determine_ext(video_url)
            if ext == 'm3u8':
                fmts, subs = self._extract_m3u8_formats_and_subtitles(
                    video_url, video_id, 'mp4', m3u8_id='hls', fatal=False)
                formats.extend(fmts)
                self._merge_subtitles(subs, target=subtitles)
            else:
                fmt = item.get('name')
                formats.append({
                    'url': video_url,
                    'format': fmt,
                    'tbr': parse_bitrate(fmt),
                    'format_id': str_or_none(item.get('id')),
                    **parse_resolution(fmt),
                })

        info, token, live_title = self._search_json_ld(webpage, video_id, default={}), None, None
        if not info:
            token = self._search_regex(
                r'data\s*:\s*{action:"getAsset".*?token:\'([a-f0-9]+)\'}', webpage, 'token', default=None)
            if not token:
                live_title = get_element_by_class('unpublished-info-item future-event-title', webpage)

        if token:
            metadata = self._download_json(
                f'{base_url}/icareus-suite-api-portlet/publishing',
                video_id, fatal=False, data=urlencode_postdata({
                    'version': '03',
                    'action': 'getAsset',
                    'organizationId': organization_id,
                    'assetId': video_id,
                    'languageId': 'en_US',
                    'userId': '0',
                    'token': token,
                })) or {}
            info = {
                'title': metadata.get('name'),
                'description': metadata.get('description'),
                'timestamp': int_or_none(metadata.get('date'), scale=1000),
                'duration': int_or_none(metadata.get('duration')),
                'thumbnail': url_or_none(metadata.get('thumbnailMedium')),
            }
        elif live_title:  # Recorded livestream
            info = {
                'title': live_title,
                'description': get_element_by_class('unpublished-info-item future-event-description', webpage),
                'timestamp': int_or_none(self._search_regex(
                    r'var startEvent\s*=\s*(\d+);', webpage, 'uploadDate', fatal=False), scale=1000),
            }

        thumbnails = info.get('thumbnails') or [{
            'url': url_or_none(info.get('thumbnail') or assets.get('thumbnail')),
        }]

        return merge_dicts({
            'id': video_id,
            'title': None,
            'formats': formats,
            'subtitles': subtitles,
            'description': clean_html(info.get('description')),
            'thumbnails': thumbnails if thumbnails[0]['url'] else None,
        }, info)


class IcareusNextIE(InfoExtractor):
    _DOMAINS = '|'.join(
        re.escape(domain)
        for domain in (
            'players.icareus.com',
            'helsinkikanava.fi',
        )
    )
    _VALID_URL = (
        rf'(?P<base_url>https?://(?:www\.)?(?:{_DOMAINS}))/(?P<language>.+?)/(video|event)/details/(?P<id>\d+)',
        r'https?://players.icareus.com/(?P<brand>.+?)/embed/vod/(?P<id>\d+)',
    )
    _TESTS = [
        {  # Regular VOD
            'url': 'https://www.helsinkikanava.fi/fi/video/details/68021894',
            'md5': '3e048a91cd6be16d34b98a1548ceed27',
            'info_dict': {
                'id': '68021894',
                'ext': 'mp4',
                'title': 'Perheiden parhaaksi',
                'description': 'md5:fe4e4ec742a34f53022f3a0409b0f6e7',
                'thumbnail': 'https://dvcf59enpgt5y.cloudfront.net/image/image_gallery?img_id=68021900',
            },
        },
        {  # Recorded livestream
            'url': 'https://www.helsinkikanava.fi/fi/event/details/76241489',
            'md5': 'a063a7ef36969ced44af9fe3d10a7f47',
            'info_dict': {
                'id': '76241489',
                'ext': 'mp4',
                'title': 'Helsingin kaupungin ja HUSin tiedotustilaisuus koronaepidemiatilanteesta 24.11.2020',
                'description': 'md5:3129d041c6fbbcdc7fe68d9a938fef1c',
                'thumbnail': 'https://dvcf59enpgt5y.cloudfront.net/image/image_gallery?img_id=76288630',
            },
        },
        {  # Embedded player
            'url': 'https://players.icareus.com/elonet/embed/vod/256250758',
            'md5': '420616d561582b9491f0a622b1a3d831',
            'info_dict': {
                'id': '256250758',
                'ext': 'mp4',
                'title': 'Shell Hurriganes',
                'description': 'Shell Hurriganes',
                'thumbnail': 'https://dvcf59enpgt5y.cloudfront.net/image/image_gallery?img_id=266941624',
            },
        },
    ]

    def _is_playback_data_dict(self, element, display_id):
        if isinstance(element, dict):
            if 'src' in element and 'videoInfo' in element and str_or_none(element.get('id')) == str(display_id):
                return True
        return False

    def _find_playback_data(self, webpage: str, display_id: str):
        # Adapted from Goplay
        nextjs_data = traverse_obj(
            re.findall(r'<script[^>]*>\s*self\.__next_f\.push\(\s*(\[.+?])\s*\);?\s*</script>', webpage),
            (
                ...,
                {js_to_json},
                {json.loads},
                ...,
                {
                    lambda s: self._search_json(
                        r'\w+\s*:\s*',
                        s,
                        'next js data',
                        None,
                        contains_pattern=r'\[(?s:.+)\]',
                        default=None,
                    ),
                },
                ...,
            ),
        )

        for element in nextjs_data:
            if self._is_playback_data_dict(element, display_id):
                return element

        # If the playback data is not found in the first pass, try to find it in the children of the RSC data
        for element in traverse_obj(nextjs_data, (..., 'children', ...)):
            if self._is_playback_data_dict(element, display_id):
                return element

        return None

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        playback_data = self._find_playback_data(webpage, display_id)
        if playback_data is None:
            raise ExtractorError('No playback data found', expected=True, video_id=display_id)
        video_id = str(playback_data['id'])
        video_info = playback_data['videoInfo']

        subtitles = {}
        for sub_info in video_info.get('subtitles') or []:
            _, sdesc, surl = sub_info[:3]
            sub_name = remove_end(sdesc.split(' ')[0], ':')
            subtitles[sub_name] = [{'url': url_or_none(surl)}]

        formats = []
        for audio_url_datum in video_info.get('audio_urls') or []:
            audio_url = audio_url_datum.get('url')
            if audio_url is None:
                continue
            formats.append(
                {
                    'format': audio_url_datum.get('name'),
                    'format_id': 'audio',
                    'vcodec': 'none',
                    'url': audio_url,
                    'tbr': None,
                },
            )

        for url_datum in video_info.get('urls') or []:
            video_url = url_or_none(url_datum.get('url'))
            if video_url is None:
                continue
            ext = determine_ext(video_url)
            if ext == 'm3u8':
                fmts, subs = self._extract_m3u8_formats_and_subtitles(
                    video_url,
                    video_id,
                    'mp4',
                    m3u8_id='hls',
                    fatal=False,
                )
                formats.extend(fmts)
                self._merge_subtitles(subs, target=subtitles)
            else:
                pass  # TODO: unsupported for now, no examples of this

        # This is weird, but it's the more robust way to find the video file URL for now
        if m := re.search(r'\{\\"videoFileUrl\\":\\"(http.+?)\\"', webpage):
            try:
                if video_file_url := url_or_none(json.loads(f'"{m.group(1)}"')):
                    formats.append(
                        {
                            'url': video_file_url,
                            'format_id': 'download',
                        },
                    )
            except json.JSONDecodeError:
                pass

        thumbnails = []
        if thumbnail := url_or_none(video_info.get('thumbnail')):
            thumbnails.append({'url': thumbnail})

        description = clean_html(self._html_search_meta(['description'], webpage))
        title = clean_html(self._html_search_meta(['og:title'], webpage))

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
            'subtitles': subtitles,
            'description': description,
            'thumbnails': thumbnails or None,
        }
