from .common import InfoExtractor
from ..utils import (
    float_or_none,
    traverse_obj,
)


class DailyWireBaseIE(InfoExtractor):
    _JSON_PATH = {
        'episode': ('props', 'pageProps', 'episodeData', 'episode'),
        'videos': ('props', 'pageProps', 'videoData', 'video'),
        'podcasts': ('props', 'pageProps', 'episode'),
    }

    def _get_json(self, url, group):
        # need no-check-certificate
        sites_type, slug = self._match_valid_url(url).group('sites_type', group)
        webpage = self._download_webpage(url, slug)

        json_data = self._search_nextjs_data(webpage, slug)
        episode_info = traverse_obj(
            json_data, self._JSON_PATH[sites_type])

        return slug, episode_info


class DailyWireIE(DailyWireBaseIE):
    _VALID_URL = r'https?://(?:www\.)dailywire(?:\.com)/(?P<sites_type>episode|videos)/(?P<episode_name>[\w-]+)'
    _TESTS = [{
        'url': 'https://www.dailywire.com/episode/1-fauci',
        'info_dict': {
            'id': 'ckzsl50xwqpy508502drqpb12',
            'ext': 'mp4',
            'title': '1. Fauci',
        }
    }, {
        'url': 'https://www.dailywire.com/episode/ep-124-bill-maher',
        'info_dict': {
            'id': 'cl355p7u74t900894oxp1bnae',
            'ext': 'mp4',
            'title': 'Ep. 125 - William Barr ',
        }
    }, {
        'url': '"https://www.dailywire.com/videos/the-hyperions',
        'info_dict': {
            'id': 'cl0iejfq5ktmw0a1478mc0bqj',
            'ext': 'mp4',
            'title': 'The Hyperions',
        }
    }]

    def _real_extract(self, url):
        slug, episode_info = self._get_json(url, 'episode_name')
        formats, subtitle = [], {}
        for segment in episode_info.get('segments') or episode_info['videoUrl']:
            subs = {}
            if segment.get('audio') in ('Access Denied', None) and segment.get('video') in ('Access Denied', None):
                continue
            if segment.get('video') not in ('Access Denied', None):
                format_, subs = self._extract_m3u8_formats_and_subtitles(
                    segment.get('audio') or segment.get('video'), slug
                )
                formats.extend(format_)
            if segment.get('audio') not in ('Access Denied', None):
                format_ = {
                    'url': segment.get('audio'),
                }
                formats.append(format_)

            self._merge_subtitles(subtitle, subs)

        self._sort_formats(formats)
        return {
            'id': episode_info['id'],
            'title': episode_info.get('title') or episode_info.get('name'),
            'formats': formats,
            'subtitles': subtitle,
            'description': episode_info.get('description'),
            'thumbnail': episode_info.get('image'),
            'duration': float_or_none(episode_info.get('duration')),
            'is_live': episode_info.get('isLive'),
            'creator': f'{episode_info.get("first_name")} {episode_info.get("last_name")}'
        }


class DailyWirePodcastIE(DailyWireBaseIE):
    _VALID_URL = r'https?://(?:www\.)dailywire(?:\.com)/(?P<sites_type>podcasts)/(?P<podcaster>[\w-]+/(?P<slug>[\w-]+))'
    _TESTS = [{
        'url': 'https://www.dailywire.com/podcasts/morning-wire/get-ready-for-recession-6-15-22',
        'info_dict': {
            'id': 'cl4f01d0w8pbe0a98ydd0cfn1',
            'title': 'Get Ready for Recession | 6.15.22',
            'ext': 'm4a',
            'description': 'The S\u0026P 500 officially slides into a bear market and recession is ahead, the January 6 committee says Trump knew he lost, and the PGA suspends 17 players who’ve joined a new Saudi league. Get the facts first on Morning Wire. ',
            'thumbnail': 'https://daily-wire-production.imgix.net/podcasts/ckx4otgd71jm508699tzb6hf4-1639506575562.jpg',
        }
    }]

    def _real_extract(self, url):
        slug, episode_info = self._get_json(url, 'slug')

        audio_id = episode_info.get('audioMuxPlaybackId') or episode_info.get('VUsAipTrBVSgzw73SpC2DAJD401TYYwEp')
        return {
            'url': f'https://stream.media.dailywire.com/{audio_id}/audio.m4a',
            'id': episode_info['id'],
            'title': episode_info.get('title'),
            'duration': float_or_none(episode_info.get('duration')),
            'thumbnail': episode_info.get('thumbnail'),
            'description': episode_info.get('description'),

        }
