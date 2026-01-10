from .common import InfoExtractor
from ..utils import determine_ext, int_or_none, smuggle_url, traverse_obj, unsmuggle_url, url_or_none


class XumoIE(InfoExtractor):
    _VALID_URL = r'https?://play\.?xumo\.com/[^?#]+/(?P<id>XM[A-Z0-9]{12})'
    _TESTS = [{
        # movie
        'url': 'https://play.xumo.com/free-movies/a-circus-tale-and-a-love-song/XM041I5U497VD3',
        'params': {
            'check_formats': True,
        },
        'md5': 'eaac858a8db4ee5a67d6d16920c24e15',
        'info_dict': {
            'id': 'XM041I5U497VD3',
            'title': 'A Circus Tale & A Love Song',
            'ext': 'mp4',
            'description': 'md5:aa6372f4785c528ff04c94a275f63446',
            'duration': 6887,
            'release_year': 2016,
            'thumbnail': r're:^https?://.*\.jpg$',
        },
    }, {
        # entire series
        'url': 'https://play.xumo.com/tv-shows/super-mario-world/XM0AN69OG47PRN',
        'params': {
            'skip_download': True,
        },
        'playlist_count': 10,
        'info_dict': {
            'id': 'XM0AN69OG47PRN',
            'title': 'Super Mario World',
        },
    }, {
        # episode of series
        'url': 'https://play.xumo.com/tv-shows/99991299/XM02D369HADFRR',
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
        },
    }, {
        # video from network-based alternate URL scheme
        'url': 'https://play.xumo.com/networks/fakenetworkname/99991299/XM02D369HADFRR',
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
        },
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
        ],
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

        for caption in traverse_obj(info_json, ('providers', ..., 'captions', ...)):
            subtitles.setdefault(caption.get('lang') or 'und', []).append({
                'url': caption.get('url'),
            })
        return formats, subtitles

    def _real_extract(self, url):

        url, smuggled_data = unsmuggle_url(url)

        media_id = self._match_valid_url(url).group('id')
        media_metadata = self._download_json(f'{self._INFO_URL}{media_id}.json', media_id, query=self._INFO_QUERY_PARAMS)

        title = media_metadata.get('title')
        content_type = media_metadata['contentType']

        if content_type == 'SERIES':
            # series => return set of URLs pointing to individual episodes and smuggle series title to avoid extra API call for each episode
            return self.playlist_result([
                self.url_result(
                    smuggle_url(f'https://play.xumo.com/tv-shows/x/{episode["id"]}', {'series': title}),
                    XumoIE, episode['id'], episode.get('episodeTitle'))
                for episode in traverse_obj(media_metadata, ('seasons', ..., 'episodes', ...))
            ], media_id, title)

        # video => return video info

        season_number = None
        series_title = None

        is_episode = content_type == 'EPISODIC'

        if is_episode:
            season_number = int_or_none(media_metadata.get('season'))
            if smuggled_data:
                series_title = traverse_obj(smuggled_data, 'series')
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
            'series': series_title,
        }
