import json
import re
import urllib.parse

from yt_dlp.extractor.common import ExtractorError
from yt_dlp.utils import int_or_none, traverse_obj

from .common import InfoExtractor


class RokuChannelIE(InfoExtractor):
    # The regex captures either /watch/<id> or /details/<series_id>/<slug>[/season-<season>]
    _VALID_URL = r'https?://(?:www\.)?therokuchannel\.roku\.com/(?:(?:watch/(?P<id>[0-9a-f]{32}))|(?:details/(?P<series_id>[0-9a-f]{32})/(?P<slug>[^/]+)(?:/season-(?P<season>\d+))?))'
    _TESTS = [{
        # Single episode test (using a details URL with an episode slug)
        'url': 'https://therokuchannel.roku.com/details/a9474f67937c5986aa1ac0747f5bb615/beastmaster-s1-e1-the-legend-continues',
        'md5': 'b8a683e430a79e20295cff9848bea865',
        'info_dict': {
            'id': 'a9474f67937c5986aa1ac0747f5bb615',
            'ext': 'mp4',
            'title': 'The Legend Continues',
            'description': 'Dar begins his quest to rescue his love, Kyra, after the Terron warriors abduct her.',
            'episode_number': 1,
            'season_number': 1,
            'series': 'BeastMaster',
            'release_date': '19991004',  # from releaseDate "1999-10-04T00:00:00Z"
            'duration': 3600.0,
        },
        'skip': 'Requires live website and valid cookies',
    }, {
        # Season playlist test.
        'url': 'https://therokuchannel.roku.com/details/48af1a617b1654a8a73cddefddedc7b8/beastmaster/season-2',
        'playlist_count': 22,
        'info_dict': {
            'id': '48af1a617b1654a8a73cddefddedc7b8',
            'title': 'BeastMaster - Season 2',
        },
        'skip': 'Requires live website and valid cookies',
    }, {
        # Full series playlist test.
        'url': 'https://therokuchannel.roku.com/details/48af1a617b1654a8a73cddefddedc7b8/beastmaster',
        'playlist_count': 64,
        'info_dict': {
            'id': '48af1a617b1654a8a73cddefddedc7b8',
            'title': 'BeastMaster',
        },
        'skip': 'Requires live website and valid cookies',
    }, {
        # Only-matching test for a DRM-protected movie.
        'url': 'https://therokuchannel.roku.com/details/b1f983c03f27531388474c46372b956c/friday-after-next',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        mobj = re.match(self._VALID_URL, url)
        # If the URL contains a "-s#-e#" pattern anywhere, treat it as a single episode extraction.
        if re.search(r'-s\d+e\d+', url, re.IGNORECASE):
            return self._real_extract_single(url, mobj)
        # For /details/ URLs, decide based on presence of season info:
        if mobj.group('series_id'):
            # Query the API details using the series_id.
            details = self._get_details(mobj.group('series_id'))
            # If no "seasons" key is present, assume it's a single episode.
            if 'seasons' not in details:
                return self._real_extract_single(url, mobj)
            # Otherwise, if a season number is provided, extract that season's episodes.
            if mobj.group('season'):
                return self._real_extract_playlist(url, mobj)
            # Otherwise treat the URL as representing the full series.
            return self._real_extract_series(url, mobj)
        # Otherwise, if the URL is of /watch/ type, extract single video.
        return self._real_extract_single(url, mobj)

    def _get_details(self, video_id):
        # Build the full API URL with detailed query parameters.
        base_url = f'https://therokuchannel.roku.com/api/v2/homescreen/content/https%3A%2F%2Fcontent.sr.roku.com%2Fcontent%2Fv1%2Froku-trc%2F{video_id}'
        query = (
            '?expand=credits,viewOptions,categoryObjects,viewOptions.providerDetails,series,season,season.episodes,next,episodes,seasons,seasons.episodes'
            '&include=type,title,imageMap.detailPoster,imageMap.detailBackground,bobs.detailScreen,categoryObjects,runTimeSeconds,castAndCrew,'
            'savable,stationDma,kidsDirected,releaseDate,releaseYear,description,descriptions,indicators,genres,credits.birthDate,credits.meta,'
            'credits.order,credits.name,credits.role,credits.personId,credits.images,parentalRatings,reverseChronological,contentRatingClass,'
            'languageDialogBody,detailScreenOptions,viewOptions,episodeNumber,seasonNumber,sportInfo,eventState,series.title,season,'
            'seasons.title,seasons.seasonNumber,seasons.description,seasons.descriptions,seasons.releaseYear,seasons.castAndCrew,'
            'seasons.credits.birthDate,seasons.credits.meta,seasons.credits.order,seasons.credits.name,seasons.credits.role,'
            'seasons.credits.personId,seasons.credits.images,seasons.imageMap.detailBackground,seasons.episodes.title,'
            'seasons.episodes.description,seasons.episodes.descriptions.40,seasons.episodes.descriptions.60,'
            'seasons.episodes.episodeNumber,seasons.episodes.seasonNumber,seasons.episodes.images,'
            'seasons.episodes.imageMap.grid,seasons.episodes.indicators,seasons.episodes.releaseDate,'
            'seasons.episodes.viewOptions,episodes.episodeNumber,episodes.seasonNumber,episodes.viewOptions'
            '&filter=categoryObjects:genreAppropriate eq true,seasons.episodes:(not empty(viewOptions)):all'
            '&featureInclude=bookmark,watchlist,linearSchedule'
        )
        full_url = base_url + query
        try:
            details = self._download_json(full_url, video_id,
                                          note='Downloading detailed content info',
                                          fatal=False)
            return details or {}
        except ExtractorError:
            return {}

    def _real_extract_single(self, url, mobj):
        # Single episode extraction using the API details.
        video_id = mobj.group('id') or mobj.group('series_id')
        details = self._get_details(video_id)
        title = details.get('title', '').strip()
        description = details.get('description', '').strip()
        webpage = self._download_webpage(url, video_id)
        mpd_url = self._search_regex(
            r'(https?://vod-playlist\.sr\.roku\.com/1\.mpd\?[^\'" >]+)',
            webpage, 'mpd URL', fatal=False)
        if not mpd_url:
            # Fallback: use CSRF token and playback API.
            self._download_webpage('https://therokuchannel.roku.com/', video_id,
                                   note='Initializing session', fatal=False)
            csrf_info = self._download_json('https://therokuchannel.roku.com/api/v1/csrf',
                                            video_id, note='Downloading CSRF token',
                                            fatal=False)
            csrf_token = csrf_info.get('csrf') if csrf_info else None
            headers = {
                'authority': 'therokuchannel.roku.com',
                'accept': '*/*',
                'accept-language': 'en-US,en;q=0.9',
                'user-agent': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                               'AppleWebKit/537.36 (KHTML, like Gecko) '
                               'Chrome/102.0.5005.63 Safari/537.36'),
                'referer': 'https://therokuchannel.roku.com/',
                'Content-Type': 'application/json',
            }
            if csrf_token:
                headers['csrf-token'] = csrf_token
            playback_payload = {
                'rokuId': video_id,
                'mediaFormat': 'mpeg-dash',
                'drmType': 'widevine',
                'quality': 'fhd',
                'providerId': 'rokuavod',
            }
            playback_json = self._download_json(
                'https://therokuchannel.roku.com/api/v3/playback',
                video_id,
                data=json.dumps(playback_payload).encode('utf-8'),
                headers=headers,
                note='Downloading playback JSON',
                fatal=True)
            videos = traverse_obj(playback_json, ('playbackMedia', 'videos'), expected_type=list) or []
            dash_url = None
            for video in videos:
                if video.get('streamFormat') == 'dash':
                    dash_url = video.get('url')
                    break
            if not dash_url:
                raise ExtractorError('Unable to extract dash URL from API', expected=True)
            parsed = urllib.parse.urlparse(dash_url)
            query_params = urllib.parse.parse_qs(parsed.query)
            if 'origin' in query_params:
                mpd_url = urllib.parse.unquote(query_params['origin'][0]).split('?')[0]
            else:
                mpd_url = dash_url
        formats = self._extract_mpd_formats(mpd_url, video_id, mpd_id='dash')
        return {
            'id': video_id,
            'title': title,
            'description': description,
            'formats': formats,
        }

    def _real_extract_playlist(self, url, mobj):
        # Extract episodes for a specific season.
        series_id = mobj.group('series_id')
        season_num = int_or_none(mobj.group('season')) or 1
        base_url = f'https://therokuchannel.roku.com/api/v2/homescreen/content/https%3A%2F%2Fcontent.sr.roku.com%2Fcontent%2Fv1%2Froku-trc%2F{series_id}'
        params = {
            'expand': 'credits,viewOptions,categoryObjects,viewOptions.providerDetails,series,season,season.episodes,next,episodes,seasons,seasons.episodes',
            'include': (
                'type,title,imageMap.detailPoster,imageMap.detailBackground,bobs.detailScreen,'
                'categoryObjects,runTimeSeconds,castAndCrew,savable,stationDma,kidsDirected,'
                'releaseDate,releaseYear,description,descriptions,indicators,genres,credits.birthDate,'
                'credits.meta,credits.order,credits.name,credits.role,seasons.credits.personId,credits.images,'
                'parentalRatings,reverseChronological,contentRatingClass,languageDialogBody,detailScreenOptions,'
                'viewOptions,episodeNumber,seasonNumber,sportInfo,eventState,series.title,season,'
                'seasons.title,seasons.seasonNumber,seasons.description,seasons.descriptions,'
                'seasons.releaseYear,seasons.castAndCrew,seasons.credits.birthDate,seasons.credits.meta,'
                'seasons.credits.order,seasons.credits.name,seasons.credits.role,seasons.credits.personId,'
                'seasons.credits.images,seasons.imageMap.detailBackground,seasons.episodes.title,'
                'seasons.episodes.description,seasons.episodes.descriptions.40,seasons.episodes.descriptions.60,'
                'seasons.episodes.episodeNumber,seasons.episodes.seasonNumber,seasons.episodes.images,'
                'seasons.episodes.imageMap.grid,seasons.episodes.indicators,seasons.episodes.releaseDate,'
                'seasons.episodes.viewOptions,episodes.episodeNumber,episodes.seasonNumber,episodes.viewOptions'
            ),
            'filter': 'categoryObjects:genreAppropriate eq true,seasons.episodes:(not empty(viewOptions)):all',
            'featureInclude': 'bookmark,watchlist,linearSchedule',
        }
        series_data = self._download_json(base_url, series_id,
                                          note='Downloading series data',
                                          fatal=True, query=params)
        series_title = series_data.get('title') or mobj.group('slug')
        entries = []
        if series_data.get('seasons'):
            for season in series_data.get('seasons', []):
                if int_or_none(season.get('seasonNumber')) == season_num:
                    for episode in season.get('episodes') or []:
                        episode_id = episode.get('id') or traverse_obj(episode, ('meta', 'id'))
                        if not episode_id:
                            continue
                        episode_url = f'https://therokuchannel.roku.com/watch/{episode_id}'
                        entry = self.url_result(episode_url, ie_key=self.ie_key(), video_id=episode_id)
                        entry.update({
                            'title': f'{series_title} - S{season.get("seasonNumber")}E{episode.get("episodeNumber")} - {episode.get("title", "")}',
                            'season_number': int_or_none(season.get('seasonNumber')),
                            'episode_number': int_or_none(episode.get('episodeNumber')),
                        })
                        entries.append(entry)
                    break
        if not entries:
            raise ExtractorError(f'No episodes found for season {season_num}', expected=True)
        return self.playlist_result(entries, series_id, f'{series_title} - Season {season_num}')

    def _real_extract_series(self, url, mobj):
        # Extract all episodes across all seasons.
        series_id = mobj.group('series_id')
        base_url = f'https://therokuchannel.roku.com/api/v2/homescreen/content/https%3A%2F%2Fcontent.sr.roku.com%2Fcontent%2Fv1%2Froku-trc%2F{series_id}'
        params = {
            'expand': 'credits,viewOptions,categoryObjects,viewOptions.providerDetails,series,season,season.episodes,next,episodes,seasons,seasons.episodes',
            'include': (
                'type,title,imageMap.detailPoster,imageMap.detailBackground,bobs.detailScreen,'
                'categoryObjects,runTimeSeconds,castAndCrew,savable,stationDma,kidsDirected,'
                'releaseDate,releaseYear,description,descriptions,indicators,genres,credits.birthDate,'
                'credits.meta,credits.order,credits.name,credits.role,seasons.credits.personId,credits.images,'
                'parentalRatings,reverseChronological,contentRatingClass,languageDialogBody,detailScreenOptions,'
                'viewOptions,episodeNumber,seasonNumber,sportInfo,eventState,series.title,season,'
                'seasons.title,seasons.seasonNumber,seasons.description,seasons.descriptions,'
                'seasons.releaseYear,seasons.castAndCrew,seasons.credits.birthDate,seasons.credits.meta,'
                'seasons.credits.order,seasons.credits.name,seasons.credits.role,seasons.credits.personId,'
                'seasons.credits.images,seasons.imageMap.detailBackground,seasons.episodes.title,'
                'seasons.episodes.description,seasons.episodes.descriptions.40,seasons.episodes.descriptions.60,'
                'seasons.episodes.episodeNumber,seasons.episodes.seasonNumber,seasons.episodes.images,'
                'seasons.episodes.imageMap.grid,seasons.episodes.indicators,seasons.episodes.releaseDate,'
                'seasons.episodes.viewOptions,episodes.episodeNumber,episodes.seasonNumber,episodes.viewOptions'
            ),
            'filter': 'categoryObjects:genreAppropriate eq true,seasons.episodes:(not empty(viewOptions)):all',
            'featureInclude': 'bookmark,watchlist,linearSchedule',
        }
        series_data = self._download_json(base_url, series_id,
                                          note='Downloading series data',
                                          fatal=True, query=params)
        series_title = series_data.get('title') or mobj.group('slug')
        entries = []
        if series_data.get('seasons'):
            for season in series_data.get('seasons', []):
                for episode in season.get('episodes') or []:
                    episode_id = episode.get('id') or traverse_obj(episode, ('meta', 'id'))
                    if not episode_id:
                        continue
                    episode_url = f'https://therokuchannel.roku.com/watch/{episode_id}'
                    entry = self.url_result(episode_url, ie_key=self.ie_key(), video_id=episode_id)
                    entry.update({
                        'title': f'{series_title} - S{season.get("seasonNumber")}E{episode.get("episodeNumber")} - {episode.get("title", "")}',
                        'season_number': int_or_none(season.get('seasonNumber')),
                        'episode_number': int_or_none(episode.get('episodeNumber')),
                    })
                    entries.append(entry)
        else:
            for episode in series_data.get('episodes', []):
                episode_id = episode.get('id') or traverse_obj(episode, ('meta', 'id'))
                if not episode_id:
                    continue
                episode_url = f'https://therokuchannel.roku.com/watch/{episode_id}'
                entry = self.url_result(episode_url, ie_key=self.ie_key(), video_id=episode_id)
                entry.update({
                    'title': f'{series_title} - S{episode.get("seasonNumber")}E{episode.get("episodeNumber")} - {episode.get("title", "")}',
                    'season_number': int_or_none(episode.get('seasonNumber')),
                    'episode_number': int_or_none(episode.get('episodeNumber')),
                })
                entries.append(entry)
        if not entries:
            raise ExtractorError('No episodes found for series', expected=True)
        return self.playlist_result(entries, series_id, series_title)
