from .common import InfoExtractor
from .once import OnceIE
from ..compat import compat_urllib_parse_unquote
from ..utils import (
    ExtractorError,
    int_or_none,
    try_get,
    unified_timestamp,
)


class VoxMediaVolumeIE(OnceIE):
    _VALID_URL = r'https?://volume\.vox-cdn\.com/embed/(?P<id>[0-9a-f]{9})'

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        setup = self._parse_json(self._search_regex(
            r'setup\s*=\s*({.+});', webpage, 'setup'), video_id)
        player_setup = setup.get('player_setup') or setup
        video_data = player_setup.get('video') or {}
        formatted_metadata = video_data.get('formatted_metadata') or {}
        info = {
            'id': video_id,
            'title': player_setup.get('title') or video_data.get('title_short'),
            'description': video_data.get('description_long') or video_data.get('description_short'),
            'thumbnail': formatted_metadata.get('thumbnail') or video_data.get('brightcove_thumbnail'),
            'timestamp': unified_timestamp(formatted_metadata.get('video_publish_date')),
        }
        asset = try_get(setup, lambda x: x['embed_assets']['chorus'], dict) or {}

        formats = []
        hls_url = asset.get('hls_url')
        if hls_url:
            formats.extend(self._extract_m3u8_formats(
                hls_url, video_id, 'mp4', 'm3u8_native', m3u8_id='hls', fatal=False))
        mp4_url = asset.get('mp4_url')
        if mp4_url:
            tbr = self._search_regex(r'-(\d+)k\.', mp4_url, 'bitrate', default=None)
            format_id = 'http'
            if tbr:
                format_id += '-' + tbr
            formats.append({
                'format_id': format_id,
                'url': mp4_url,
                'tbr': int_or_none(tbr),
            })
        if formats:
            self._sort_formats(formats)
            info['formats'] = formats
            info['duration'] = int_or_none(asset.get('duration'))
            return info

        for provider_video_type in ('ooyala', 'youtube', 'brightcove'):
            provider_video_id = video_data.get('%s_id' % provider_video_type)
            if not provider_video_id:
                continue
            if provider_video_type == 'brightcove':
                info['formats'] = self._extract_once_formats(provider_video_id)
                self._sort_formats(info['formats'])
            else:
                info.update({
                    '_type': 'url_transparent',
                    'url': provider_video_id if provider_video_type == 'youtube' else '%s:%s' % (provider_video_type, provider_video_id),
                    'ie_key': provider_video_type.capitalize(),
                })
            return info
        raise ExtractorError('Unable to find provider video id')


class VoxMediaIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?(?:(?:theverge|vox|sbnation|eater|polygon|curbed|racked|funnyordie)\.com|recode\.net)/(?:[^/]+/)*(?P<id>[^/?]+)'
    _TESTS = [{
        # Volume embed, Youtube
        'url': 'http://www.theverge.com/2014/6/27/5849272/material-world-how-google-discovered-what-software-is-made-of',
        'info_dict': {
            'id': 'j4mLW6x17VM',
            'ext': 'mp4',
            'title': 'Material world: how Google discovered what software is made of',
            'description': 'md5:dfc17e7715e3b542d66e33a109861382',
            'upload_date': '20190710',
            'uploader_id': 'TheVerge',
            'uploader': 'The Verge',
        },
        'add_ie': ['Youtube'],
    }, {
        # Volume embed, Youtube
        'url': 'http://www.theverge.com/2014/10/21/7025853/google-nexus-6-hands-on-photos-video-android-phablet',
        'md5': 'fd19aa0cf3a0eea515d4fd5c8c0e9d68',
        'info_dict': {
            'id': 'Gy8Md3Eky38',
            'ext': 'mp4',
            'title': 'The Nexus 6: hands-on with Google\'s phablet',
            'description': 'md5:d9f0216e5fb932dd2033d6db37ac3f1d',
            'uploader_id': 'TheVerge',
            'upload_date': '20141021',
            'uploader': 'The Verge',
            'timestamp': 1413907200,
        },
        'add_ie': ['Youtube'],
        'skip': 'similar to the previous test',
    }, {
        # Volume embed, Youtube
        'url': 'http://www.vox.com/2016/3/31/11336640/mississippi-lgbt-religious-freedom-bill',
        'info_dict': {
            'id': '22986359b',
            'ext': 'mp4',
            'title': "Mississippi's laws are so bad that its anti-LGBTQ law isn't needed to allow discrimination",
            'description': 'md5:fc1317922057de31cd74bce91eb1c66c',
            'upload_date': '20150915',
            'timestamp': 1442332800,
            'duration': 285,
        },
        'add_ie': ['Youtube'],
        'skip': 'similar to the previous test',
    }, {
        # youtube embed
        'url': 'http://www.vox.com/2016/3/24/11291692/robot-dance',
        'md5': '83b3080489fb103941e549352d3e0977',
        'info_dict': {
            'id': 'FcNHTJU1ufM',
            'ext': 'mp4',
            'title': 'How "the robot" became the greatest novelty dance of all time',
            'description': 'md5:b081c0d588b8b2085870cda55e6da176',
            'upload_date': '20160324',
            'uploader_id': 'voxdotcom',
            'uploader': 'Vox',
        },
        'add_ie': ['Youtube'],
        'skip': 'Page no longer contain videos',
    }, {
        # SBN.VideoLinkset.entryGroup multiple ooyala embeds
        'url': 'http://www.sbnation.com/college-football-recruiting/2015/2/3/7970291/national-signing-day-rationalizations-itll-be-ok-itll-be-ok',
        'info_dict': {
            'id': 'national-signing-day-rationalizations-itll-be-ok-itll-be-ok',
            'title': '25 lies you will tell yourself on National Signing Day',
            'description': 'It\'s the most self-delusional time of the year, and everyone\'s gonna tell the same lies together!',
        },
        'playlist': [{
            'md5': '721fededf2ab74ae4176c8c8cbfe092e',
            'info_dict': {
                'id': 'p3cThlMjE61VDi_SD9JlIteSNPWVDBB9',
                'ext': 'mp4',
                'title': 'Buddy Hield vs Steph Curry (and the world)',
                'description': 'Let’s dissect only the most important Final Four storylines.',
            },
        }, {
            'md5': 'bf0c5cc115636af028be1bab79217ea9',
            'info_dict': {
                'id': 'BmbmVjMjE6esPHxdALGubTrouQ0jYLHj',
                'ext': 'mp4',
                'title': 'Chasing Cinderella 2016: Syracuse basketball',
                'description': 'md5:e02d56b026d51aa32c010676765a690d',
            },
        }],
        'skip': 'Page no longer contain videos',
    }, {
        # volume embed, Brightcove Once
        'url': 'https://www.recode.net/2014/6/17/11628066/post-post-pc-ceo-the-full-code-conference-video-of-microsofts-satya',
        'md5': '2dbc77b8b0bff1894c2fce16eded637d',
        'info_dict': {
            'id': '1231c973d',
            'ext': 'mp4',
            'title': 'Post-Post-PC CEO: The Full Code Conference Video of Microsoft\'s Satya Nadella',
            'description': 'The longtime veteran was chosen earlier this year as the software giant\'s third leader in its history.',
            'timestamp': 1402938000,
            'upload_date': '20140616',
            'duration': 4114,
        },
        'add_ie': ['VoxMediaVolume'],
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = compat_urllib_parse_unquote(self._download_webpage(url, display_id))

        def create_entry(provider_video_id, provider_video_type, title=None, description=None):
            video_url = {
                'youtube': '%s',
                'ooyala': 'ooyala:%s',
                'volume': 'http://volume.vox-cdn.com/embed/%s',
            }[provider_video_type] % provider_video_id
            return {
                '_type': 'url_transparent',
                'url': video_url,
                'title': title or self._og_search_title(webpage),
                'description': description or self._og_search_description(webpage),
            }

        entries = []
        entries_data = self._search_regex([
            r'Chorus\.VideoContext\.addVideo\((\[{.+}\])\);',
            r'var\s+entry\s*=\s*({.+});',
            r'SBN\.VideoLinkset\.entryGroup\(\s*(\[.+\])',
        ], webpage, 'video data', default=None)
        if entries_data:
            entries_data = self._parse_json(entries_data, display_id)
            if isinstance(entries_data, dict):
                entries_data = [entries_data]
            for video_data in entries_data:
                provider_video_id = video_data.get('provider_video_id')
                provider_video_type = video_data.get('provider_video_type')
                if provider_video_id and provider_video_type:
                    entries.append(create_entry(
                        provider_video_id, provider_video_type,
                        video_data.get('title'), video_data.get('description')))

        provider_video_id = self._search_regex(
            r'data-ooyala-id="([^"]+)"', webpage, 'ooyala id', default=None)
        if provider_video_id:
            entries.append(create_entry(provider_video_id, 'ooyala'))

        volume_uuid = self._search_regex(
            r'data-volume-uuid="([^"]+)"', webpage, 'volume uuid', default=None)
        if volume_uuid:
            entries.append(create_entry(volume_uuid, 'volume'))

        if len(entries) == 1:
            return entries[0]
        else:
            return self.playlist_result(entries, display_id, self._og_search_title(webpage), self._og_search_description(webpage))
