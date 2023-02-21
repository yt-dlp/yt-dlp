from .common import InfoExtractor
from ..utils import (
    determine_ext,
    int_or_none,
    smuggle_url,
    traverse_obj,
    unsmuggle_url,
    url_or_none
)


class XumoIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?xumo\.tv/[^?#]+/(?P<id>XM[A-Z0-9]{12})'
    _TESTS = [{
        # movie
        'url': 'https://www.xumo.tv/free-movies/zombie-high/XM01OEG1MIJVJR',
        'params': {
            'check_formats': True
        },
        'md5': '2843529c1abf5f86f61165637f89cbae',
        'info_dict': {
            'id': 'XM01OEG1MIJVJR',
            'title': 'Zombie High',
            'ext': 'mp4',
            'description': 'md5:b620cc0afc18a91fb69275047f6c4d22',
            'duration': 5436,
            'release_year': 1987,
            'thumbnail': r're:^https?://.*\.jpg$'
        }
    }, {
        # series
        'url': 'https://www.xumo.tv/tv-shows/super-mario-world/XM0AN69OG47PRN',
        'params': {
            'skip_download': True
        },
        'playlist_count': 10,
        'info_dict': {
            'id': 'XM0AN69OG47PRN',
            'title': 'Super Mario World'
        }
    }, {
        # video from network URL
        'url': 'https://www.xumo.tv/networks/free-movies/99991299/XM02D369HADFRR',
        'md5': 'ed2f396272b39f2e0fe47f02b9ae34cc',
        'info_dict': {
            'id': 'XM02D369HADFRR',
            'title': 'Fire Sale // Misadventures In Robin Hood Woods',
            'ext': 'mp4',
            'series': 'Super Mario World',
            'season_number': 1,
            'episode_number': 2,
            'episode': 'Fire Sale // Misadventures In Robin Hood Woods',
            'description': 'md5:48134d36781cf4b225ec0ee4f05356d3',
            'thumbnail': r're:^https?://.*\.jpg$',
            'season': 'Season 1',
            'duration': 1368,
        }
    }, {
        # episode from generated URL
        'url': 'https://www.xumo.tv/free-movies/x/XM02D369HADFRR',
        'md5': 'ed2f396272b39f2e0fe47f02b9ae34cc',
        'info_dict': {
            'id': 'XM02D369HADFRR',
            'title': 'Fire Sale // Misadventures In Robin Hood Woods',
            'ext': 'mp4',
            'series': 'Super Mario World',
            'season_number': 1,
            'episode_number': 2,
            'episode': 'Fire Sale // Misadventures In Robin Hood Woods',
            'description': 'md5:48134d36781cf4b225ec0ee4f05356d3',
            'thumbnail': r're:^https?://.*\.jpg$',
            'season': 'Season 1',
            'duration': 1368,
        }
    }]

    _INFO_URL = 'https://valencia-app-mds.xumo.com/v2/assets/asset/'
    _INFO_QUERY_PARAMS = {
        'f': [
            'connectorId',
            'title',
            'providers',
            'descriptions',
            'runtime',
            'originalReleaseYear',
            'cuePoints',
            'ratings',
            'hasCaptions',
            'availableSince',
            'genres',
            'season',
            'episode',
            'seasons',
            'season:all',
            'episodes.episodeTitle',
            'episodes.runtime',
            'episodes.descriptions',
            'episodes.hasCaptions',
            'episodes.ratings',
        ]
    }

    def _get_video_links(self, video_id, info_json):
        formats, subtitles = [], {}

        for source in traverse_obj(info_json, ('providers', ..., 'sources', ...)) or []:
            fmts, subs = [], {}

            format_url = url_or_none(source.get('uri'))
            if not format_url:
                continue
            ext = determine_ext(format_url)
            if ext == 'm3u8':
                fmts, subs = self._extract_m3u8_formats_and_subtitles(
                    format_url, video_id, m3u8_id='hls', fatal=False)
            elif ext == 'mpd':
                fmts, subs = self._extract_mpd_formats_and_subtitles(
                    format_url, video_id, mpd_id='dash', fatal=False)
            elif format_url.endswith('.ism/Manifest'):
                fmts, subs = self._extract_ism_formats_and_subtitles(
                    format_url, video_id, ism_id='mss', fatal=False)

            if source.get('drm'):
                for f in fmts:
                    f['has_drm'] = True

            formats.extend(fmts)
            subtitles = self._merge_subtitles(subtitles, subs)

        for caption in traverse_obj(info_json, ('providers', ..., 'captions', ...)) or []:
            sub_url = caption.get('url')
            ext = determine_ext(sub_url)
            if ext not in ('vtt', 'srt'):
                continue
            lang = caption.get('lang') or 'und'
            subtitles.setdefault(lang, []).append({'ext': ext, 'url': caption.get('url')})

        return formats, subtitles

    def _real_extract(self, url):

        url, smuggled_data = unsmuggle_url(url)

        media_id = self._match_valid_url(url).group('id')
        media_metadata = self._download_json(f'{self._INFO_URL}{media_id}.json', media_id, query=self._INFO_QUERY_PARAMS)

        title = media_metadata.get('title')
        content_type = media_metadata['contentType']

        if content_type == 'SERIES':
            # series => return set of URLs pointing to episodes
            video_links = []
            for episode in traverse_obj(media_metadata, ('seasons', ..., 'episodes', ...)) or []:
                smuggled_url = smuggle_url('https://www.xumo.tv/free-movies/x/' + episode['id'], {'series_title': traverse_obj(media_metadata, 'title')})
                video_links.append(self.url_result(smuggled_url, video_title=episode.get('episodeTitle')))
            return self.playlist_result(video_links, playlist_id=media_id, playlist_title=title)

        # video => return video info

        season_number = None
        series_title = None

        is_episode = content_type == 'EPISODIC'

        if is_episode:
            season_number = int_or_none(media_metadata.get('season'))
            if smuggled_data:
                series_title = traverse_obj(smuggled_data, 'series_title')
            else:
                series_data = self._download_json(f'{self._INFO_URL}{media_metadata["connectorId"]}.json', media_id, query=self._INFO_QUERY_PARAMS)
                series_title = traverse_obj(series_data, 'title')

        formats, subtitles = self._get_video_links(media_id, media_metadata)

        return {
            'id': media_id,
            'title': title,
            'description': traverse_obj(media_metadata, ('descriptions', ('large', 'medium', 'small', 'tiny')), get_all=False),
            'release_year': media_metadata.get('originalReleaseYear'),
            'duration': media_metadata.get('runtime'),
            'thumbnail': f'https://image.xumo.com/v1/assets/asset/{media_id}/1024x576.jpg',
            'formats': formats,
            'subtitles': subtitles,
            'episode_number': media_metadata.get('episode'),
            'season_number': season_number,
            'episode': title if is_episode else None,
            'series': series_title
        }
