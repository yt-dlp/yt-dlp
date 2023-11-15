import re
import uuid

from .common import InfoExtractor
from ..compat import (
    compat_str,
    compat_urlparse,
)
from ..utils import (
    ExtractorError,
    float_or_none,
    int_or_none,
    try_get,
    url_or_none,
)


class PlutoTVIE(InfoExtractor):
    _VALID_URL = r'''(?x)
        https?://(?:www\.)?pluto\.tv(?:/[^/]+)?/on-demand
        /(?P<video_type>movies|series)
        /(?P<series_or_movie_slug>[^/]+)
        (?:
            (?:/seasons?/(?P<season_no>\d+))?
            (?:/episode/(?P<episode_slug>[^/]+))?
        )?
        /?(?:$|[#?])'''

    _INFO_URL = 'https://service-vod.clusters.pluto.tv/v3/vod/slugs/'
    _INFO_QUERY_PARAMS = {
        'appName': 'web',
        'appVersion': 'na',
        'clientID': compat_str(uuid.uuid1()),
        'clientModelNumber': 'na',
        'serverSideAds': 'false',
        'deviceMake': 'unknown',
        'deviceModel': 'web',
        'deviceType': 'web',
        'deviceVersion': 'unknown',
        'sid': compat_str(uuid.uuid1()),
    }
    _TESTS = [
        {
            'url': 'https://pluto.tv/on-demand/series/i-love-money/season/2/episode/its-in-the-cards-2009-2-3',
            'md5': 'ebcdd8ed89aaace9df37924f722fd9bd',
            'info_dict': {
                'id': '5de6c598e9379ae4912df0a8',
                'ext': 'mp4',
                'title': 'It\'s In The Cards',
                'episode': 'It\'s In The Cards',
                'description': 'The teams face off against each other in a 3-on-2 soccer showdown.  Strategy comes into play, though, as each team gets to select their opposing teams’ two defenders.',
                'series': 'I Love Money',
                'season_number': 2,
                'episode_number': 3,
                'duration': 3600,
            }
        }, {
            'url': 'https://pluto.tv/on-demand/series/i-love-money/season/1/',
            'playlist_count': 11,
            'info_dict': {
                'id': '5de6c582e9379ae4912dedbd',
                'title': 'I Love Money - Season 1',
            }
        }, {
            'url': 'https://pluto.tv/on-demand/series/i-love-money/',
            'playlist_count': 26,
            'info_dict': {
                'id': '5de6c582e9379ae4912dedbd',
                'title': 'I Love Money',
            }
        }, {
            'url': 'https://pluto.tv/on-demand/movies/arrival-2015-1-1',
            'md5': '3cead001d317a018bf856a896dee1762',
            'info_dict': {
                'id': '5e83ac701fa6a9001bb9df24',
                'ext': 'mp4',
                'title': 'Arrival',
                'description': 'When mysterious spacecraft touch down across the globe, an elite team - led by expert translator Louise Banks (Academy Award® nominee Amy Adams) – races against time to decipher their intent.',
                'duration': 9000,
            }
        }, {
            'url': 'https://pluto.tv/en/on-demand/series/manhunters-fugitive-task-force/seasons/1/episode/third-times-the-charm-1-1',
            'only_matching': True,
        }, {
            'url': 'https://pluto.tv/it/on-demand/series/csi-vegas/episode/legacy-2021-1-1',
            'only_matching': True,
        },
        {
            'url': 'https://pluto.tv/en/on-demand/movies/attack-of-the-killer-tomatoes-1977-1-1-ptv1',
            'md5': '7db56369c0da626a32d505ec6eb3f89f',
            'info_dict': {
                'id': '5b190c7bb0875c36c90c29c4',
                'ext': 'mp4',
                'title': 'Attack of the Killer Tomatoes',
                'description': 'A group of scientists band together to save the world from mutated tomatoes that KILL! (1978)',
                'duration': 5700,
            }
        }
    ]

    def _to_ad_free_formats(self, video_id, formats, subtitles):
        ad_free_formats, ad_free_subtitles, m3u8_urls = [], {}, set()
        for fmt in formats:
            res = self._download_webpage(
                fmt.get('url'), video_id, note='Downloading m3u8 playlist',
                fatal=False)
            if not res:
                continue
            first_segment_url = re.search(
                r'^(https?://.*/)0\-(end|[0-9]+)/[^/]+\.ts$', res,
                re.MULTILINE)
            if first_segment_url:
                m3u8_urls.add(
                    compat_urlparse.urljoin(first_segment_url.group(1), '0-end/master.m3u8'))
                continue
            first_segment_url = re.search(
                r'^(https?://.*/).+\-0+[0-1]0\.ts$', res,
                re.MULTILINE)
            if first_segment_url:
                m3u8_urls.add(
                    compat_urlparse.urljoin(first_segment_url.group(1), 'master.m3u8'))
                continue

        for m3u8_url in m3u8_urls:
            fmts, subs = self._extract_m3u8_formats_and_subtitles(
                m3u8_url, video_id, 'mp4', 'm3u8_native', m3u8_id='hls', fatal=False)
            ad_free_formats.extend(fmts)
            ad_free_subtitles = self._merge_subtitles(ad_free_subtitles, subs)
        if ad_free_formats:
            formats, subtitles = ad_free_formats, ad_free_subtitles
        else:
            self.report_warning('Unable to find ad-free formats')
        return formats, subtitles

    def _get_video_info(self, video_json, slug, series_name=None):
        video_id = video_json.get('_id', slug)
        formats, subtitles = [], {}
        for video_url in try_get(video_json, lambda x: x['stitched']['urls'], list) or []:
            if video_url.get('type') != 'hls':
                continue
            url = url_or_none(video_url.get('url'))

            fmts, subs = self._extract_m3u8_formats_and_subtitles(
                url, video_id, 'mp4', 'm3u8_native', m3u8_id='hls', fatal=False)
            formats.extend(fmts)
            subtitles = self._merge_subtitles(subtitles, subs)

        formats, subtitles = self._to_ad_free_formats(video_id, formats, subtitles)

        info = {
            'id': video_id,
            'formats': formats,
            'subtitles': subtitles,
            'title': video_json.get('name'),
            'description': video_json.get('description'),
            'duration': float_or_none(video_json.get('duration'), scale=1000),
        }
        if series_name:
            info.update({
                'series': series_name,
                'episode': video_json.get('name'),
                'season_number': int_or_none(video_json.get('season')),
                'episode_number': int_or_none(video_json.get('number')),
            })
        return info

    def _real_extract(self, url):
        mobj = self._match_valid_url(url).groupdict()
        info_slug = mobj['series_or_movie_slug']
        video_json = self._download_json(self._INFO_URL + info_slug, info_slug, query=self._INFO_QUERY_PARAMS)

        if mobj['video_type'] == 'series':
            series_name = video_json.get('name', info_slug)
            season_number, episode_slug = mobj.get('season_number'), mobj.get('episode_slug')

            videos = []
            for season in video_json['seasons']:
                if season_number is not None and season_number != int_or_none(season.get('number')):
                    continue
                for episode in season['episodes']:
                    if episode_slug is not None and episode_slug != episode.get('slug'):
                        continue
                    videos.append(self._get_video_info(episode, episode_slug, series_name))
            if not videos:
                raise ExtractorError('Failed to find any videos to extract')
            if episode_slug is not None and len(videos) == 1:
                return videos[0]
            playlist_title = series_name
            if season_number is not None:
                playlist_title += ' - Season %d' % season_number
            return self.playlist_result(videos,
                                        playlist_id=video_json.get('_id', info_slug),
                                        playlist_title=playlist_title)
        return self._get_video_info(video_json, info_slug)
