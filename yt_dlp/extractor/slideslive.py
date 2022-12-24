from .common import InfoExtractor
from ..utils import (
    smuggle_url,
    traverse_obj,
    unified_timestamp,
    url_or_none,
)


class SlidesLiveIE(InfoExtractor):
    _VALID_URL = r'https?://slideslive\.com/(?P<id>[0-9]+)'
    _TESTS = [{
        # service_name = yoda
        'url': 'https://slideslive.com/38902413/gcc-ia16-backend',
        'info_dict': {
            'id': '38902413',
            'ext': 'mp4',
            'title': 'GCC IA16 backend',
            'timestamp': 1648189972,
            'upload_date': '20220325',
            'thumbnail': r're:^https?://.*\.jpg',
        },
        'params': {
            'skip_download': 'm3u8',
        },
    }, {
        # service_name = yoda
        'url': 'https://slideslive.com/38935785',
        'info_dict': {
            'id': '38935785',
            'ext': 'mp4',
            'title': 'Offline Reinforcement Learning: From Algorithms to Practical Challenges',
            'upload_date': '20211115',
            'timestamp': 1636996003,
            'thumbnail': r're:^https?://.*\.jpg',
        },
        'params': {
            'skip_download': 'm3u8',
        },
    }, {
        # service_name = yoda
        'url': 'https://slideslive.com/38973182/how-should-a-machine-learning-researcher-think-about-ai-ethics',
        'info_dict': {
            'id': '38973182',
            'ext': 'mp4',
            'title': 'How Should a Machine Learning Researcher Think About AI Ethics?',
            'upload_date': '20220201',
            'thumbnail': r're:^https?://.*\.jpg',
            'timestamp': 1643728135,
        },
        'params': {
            'skip_download': 'm3u8',
        },
    }, {
        # service_name = youtube
        'url': 'https://slideslive.com/38897546/special-metaprednaska-petra-ludwiga-hodnoty-pro-lepsi-spolecnost',
        'md5': '8a79b5e3d700837f40bd2afca3c8fa01',
        'info_dict': {
            'id': 'jmg02wCJD5M',
            'display_id': '38897546',
            'ext': 'mp4',
            'title': 'SPECIÁL: Meta-přednáška Petra Ludwiga - Hodnoty pro lepší společnost',
            'description': 'Watch full version of this video at https://slideslive.com/38897546.',
            'channel_url': 'https://www.youtube.com/channel/UCZWdAkNYFncuX0khyvhqnxw',
            'channel': 'SlidesLive Videos - G1',
            'channel_id': 'UCZWdAkNYFncuX0khyvhqnxw',
            'uploader_id': 'UCZWdAkNYFncuX0khyvhqnxw',
            'uploader': 'SlidesLive Videos - G1',
            'uploader_url': 'http://www.youtube.com/channel/UCZWdAkNYFncuX0khyvhqnxw',
            'live_status': 'not_live',
            'upload_date': '20160710',
            'timestamp': 1618786715,
            'duration': 6827,
            'like_count': int,
            'view_count': int,
            'comment_count': int,
            'channel_follower_count': int,
            'age_limit': 0,
            'thumbnail': r're:^https?://.*\.jpg',
            'playable_in_embed': True,
            'availability': 'unlisted',
            'tags': [],
            'categories': ['People & Blogs'],
        },
    }, {
        # service_name = youtube
        'url': 'https://slideslive.com/38903721/magic-a-scientific-resurrection-of-an-esoteric-legend',
        'only_matching': True,
    }, {
        # service_name = url
        'url': 'https://slideslive.com/38922070/learning-transferable-skills-1',
        'only_matching': True,
    }, {
        # service_name = vimeo
        'url': 'https://slideslive.com/38921896/retrospectives-a-venue-for-selfreflection-in-ml-research-3',
        'only_matching': True,
    }]

    def _extract_custom_m3u8_info(self, m3u8_data):
        m3u8_dict = {}

        lookup = {
            'PRESENTATION-TITLE': 'title',
            'PRESENTATION-UPDATED-AT': 'timestamp',
            'PRESENTATION-THUMBNAIL': 'thumbnail',
            'PLAYLIST-TYPE': 'playlist_type',
            'VOD-VIDEO-SERVICE-NAME': 'service_name',
            'VOD-VIDEO-ID': 'service_id',
            'VOD-VIDEO-SERVERS': 'video_servers',
            'VOD-SUBTITLES': 'subtitles',
        }

        for line in m3u8_data.splitlines():
            if not line.startswith('#EXT-SL-'):
                continue
            tag, _, value = line.partition(':')
            key = lookup.get(tag.lstrip('#EXT-SL-'))
            if not key:
                continue
            m3u8_dict[key] = value

        # Some values are stringified JSON arrays
        for key in ('video_servers', 'subtitles'):
            if key in m3u8_dict:
                m3u8_dict[key] = self._parse_json(m3u8_dict[key], None, fatal=False) or []

        return m3u8_dict

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        player_token = self._search_regex(r'data-player-token="([^"]+)"', webpage, 'player token')
        player_data = self._download_webpage(
            f'https://ben.slideslive.com/player/{video_id}', video_id,
            note='Downloading player info', query={'player_token': player_token})
        player_info = self._extract_custom_m3u8_info(player_data)

        service_name = player_info['service_name'].lower()
        assert service_name in ('url', 'yoda', 'vimeo', 'youtube')
        service_id = player_info['service_id']

        subtitles = {}
        for sub in traverse_obj(player_info, ('subtitles', ...), expected_type=dict):
            webvtt_url = url_or_none(sub.get('webvtt_url'))
            if not webvtt_url:
                continue
            subtitles.setdefault(sub.get('language') or 'en', []).append({
                'url': webvtt_url,
                'ext': 'vtt',
            })

        info = {
            'id': video_id,
            'title': player_info.get('title') or self._html_search_meta('title', webpage, default=''),
            'timestamp': unified_timestamp(player_info.get('timestamp')),
            'is_live': player_info.get('playlist_type') != 'vod',
            'thumbnail': url_or_none(player_info.get('thumbnail')),
            'subtitles': subtitles,
        }

        if service_name in ('url', 'yoda'):
            if service_name == 'url':
                info['url'] = service_id
            else:
                cdn_hostname = player_info['video_servers'][0]
                formats = []
                formats.extend(self._extract_m3u8_formats(
                    f'https://{cdn_hostname}/{service_id}/master.m3u8',
                    video_id, 'mp4', m3u8_id='hls', fatal=False, live=True))
                formats.extend(self._extract_mpd_formats(
                    f'https://{cdn_hostname}/{service_id}/master.mpd',
                    video_id, mpd_id='dash', fatal=False))
                info.update({
                    'formats': formats,
                })
        else:
            info.update({
                '_type': 'url_transparent',
                'url': service_id,
                'ie_key': service_name.capitalize(),
                'display_id': video_id,
            })
            if service_name == 'vimeo':
                info['url'] = smuggle_url(
                    f'https://player.vimeo.com/video/{service_id}',
                    {'http_headers': {'Referer': url}})

        return info
