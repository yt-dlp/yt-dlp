import urllib.parse

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    HEADRequest,
    determine_ext,
    float_or_none,
    int_or_none,
    parse_age_limit,
    traverse_obj,
    variadic,
)


class PlexWatchBaseIE(InfoExtractor):
    _NETRC_MACHINE = 'plex'

    # Obtained from https://plex.tv/media/providers?X-Plex-Token=<plex_token>
    _CDN_ENDPOINT = {
        'vod': 'https://vod.provider.plex.tv',
        'live': 'https://epg.provider.plex.tv',
        'tv.plex.provider.epg': 'https://epg.provider.plex.tv',
        'tv.plex.provider.vod': 'https://vod.provider.plex.tv',
        'tv.plex.provider.metadata': 'https://metadata.provider.plex.tv',
    }

    _TOKEN = None
    _CLIENT_IDENTIFIER = None

    def _handle_login_error(self, error, error_message='', fatal=True):
        error_json_message = self._parse_json(error.cause.read(), 'login_error')['errors'][0]['message']
        if not fatal and error.cause.code == 429:
            self.report_warning(f'Login error : {error_json_message}, caused by {error.cause} {error_message}')
            return
        raise ExtractorError(f'{error_json_message} {error_message}', cause=error.cause)

    def _initialize_pre_login(self):
        if not self._TOKEN:
            self._request_webpage(
                HEADRequest('https://watch.plex.tv/'), None, note='Fetching clientIdentifier')
            cookie_ = {cookie.name: cookie.value for cookie in self.cookiejar}
            self._CLIENT_IDENTIFIER = cookie_.get('clientIdentifier')

    # FIXME: Fix the token can't be used to manifest url (need to add request in signin)
    def _perform_login(self, username, password):
        try:
            resp_api = self._download_json(
                'https://plex.tv/api/v2/users/signin', None, note='Logging in',
                query={'X-Plex-Client-Identifier': self._CLIENT_IDENTIFIER},
                data=f'login={username}&password={password}&rememberMe=true'.encode(),
                headers={'Accept': 'application/json'}, expected_status=429)
            PlexWatchBaseIE._TOKEN = resp_api.get('authToken')
        except ExtractorError as e:
            if not isinstance(e, urllib.error.HTTPError):
                raise
            self._handle_login_error(e, fatal=False)

    def _real_initialize(self):
        if self._TOKEN:
            return
        try:
            resp_api = self._download_json(
                'https://plex.tv/api/v2/users/anonymous', None, data=b'',
                note='Logging in anonymously (Note: rate limited)',
                headers={
                    'X-Plex-Provider-Version': '6.2.0',
                    'Accept': 'application/json',
                    'X-Plex-Product': 'Plex Mediaverse',
                    'X-Plex-Client-Identifier': self._CLIENT_IDENTIFIER.encode()
                })
        except ExtractorError as e:
            if not isinstance(e, urllib.error.HTTPError):
                raise
            self._handle_login_error(e)

        PlexWatchBaseIE._TOKEN = resp_api['authToken']

    def _get_formats_and_subtitles(self, selected_media, display_id, sites_type='vod', metadata_field={}, format_field={}):
        formats, subtitles = [], {}
        fmts, subs = [], {}
        for media in variadic(selected_media):
            media_url = f'{self._CDN_ENDPOINT[sites_type]}{media}?X-Plex-Token={self._TOKEN}'
            media_ext = determine_ext(media)

            if media_ext == 'm3u8' or media.endswith('hls'):
                fmts, subs = self._extract_m3u8_formats_and_subtitles(media_url, display_id)

            elif media_ext == 'mpd':
                fmts, subs = self._extract_mpd_formats_and_subtitles(media_url, display_id)

            else:
                fmts = [{'url': media_url, 'ext': 'mp4'}]

            for f in fmts:
                if f.get('url'):
                    f.update(format_field)

            formats.extend(fmts)
            self._merge_subtitles(subs, target=subtitles)
        return formats, subtitles

    def _get_clips(self, nextjs_json, display_id):
        self.write_debug('Trying to download Extras/trailer')
        show_ratingkey = nextjs_json.get('ratingKey')

        media_json_list = []
        for clip_ratingkey in traverse_obj(nextjs_json, ('Extras', 'Metadata', ..., 'ratingKey')) or []:
            trailer_info = self._download_json(
                'https://play.provider.plex.tv/playQueues', display_id,
                query={'uri': f'provider://tv.plex.provider.metadata/library/metadata/{show_ratingkey}/extras/{clip_ratingkey}'},
                data=b'', headers={'X-PLEX-TOKEN': PlexWatchBaseIE._TOKEN, 'Accept': 'application/json'})
            media_json_list.append(trailer_info)

        for media in traverse_obj(media_json_list, (..., 'MediaContainer', 'Metadata', ...)) or []:
            for media_ in traverse_obj(media, ('Media', ..., 'Part', ..., 'key')):
                fmt, sub = self._get_formats_and_subtitles(media_, display_id, format_field={'format_note': 'Extras video'})
                for f in fmt:
                    f['preference'] = -10
                yield {
                    'id': media['ratingKey'],
                    'title': media['title'],
                    'formats': fmt,
                    'subtitles': sub,
                }

    def _extract_movie(self, webpage, display_id, sites_type, **kwargs):
        nextjs_json = self._search_nextjs_data(webpage, display_id)['props']['pageProps']['metadataItem']
        json_ld_json = self._search_json_ld(webpage, display_id)

        media_json = self._download_json(
            'https://play.provider.plex.tv/playQueues', display_id,
            query={'uri': nextjs_json['playableKey']}, data=b'',
            headers={'X-PLEX-TOKEN': PlexWatchBaseIE._TOKEN, 'Accept': 'application/json'})['MediaContainer']['Metadata']

        selected_media = []

        media_index = 0
        for media in media_json:
            if media.get('slug') == display_id or sites_type == 'show':
                media_index = media_json.index(media)
                selected_media = traverse_obj(media, ('Media', ..., 'Part', ..., 'key'))
                break

        formats, subtitles = self._get_formats_and_subtitles(selected_media, display_id)
        self._sort_formats(formats)

        return {
            'id': nextjs_json.get('playableID') or nextjs_json['ratingKey'],
            'display_id': display_id,
            'formats': formats,
            'subtitles': subtitles,
            'title': nextjs_json.get('title') or self._og_search_title(webpage) or json_ld_json.get('title'),
            'alt_title': nextjs_json.get('originalTitle'),
            'description': (nextjs_json.get('summary') or self._og_search_description(webpage)
                            or json_ld_json.get('description')),
            'thumbnail': (traverse_obj(media_json, (media_index, 'thumb')) or nextjs_json.get('thumb')
                          or self._og_search_thumbnail(webpage)),
            'duration': (int_or_none(
                traverse_obj(media_json, (media_index, 'duration')) or nextjs_json.get('duration')
                or json_ld_json.get('duration'), 1000)),
            'cast': (traverse_obj(nextjs_json, ('Role', ..., 'tag'))
                     or traverse_obj(media_json, (media_index, 'Role', ..., 'tag'))),
            'rating': (parse_age_limit(
                traverse_obj(media_json, (media_index, 'contentRating')) or nextjs_json.get('contentRating'))),
            'categories': traverse_obj(nextjs_json, ('Genre', ..., 'tag')),
            'release_date': self._html_search_meta('video:release_date', webpage),
            'average_rating': float_or_none(
                traverse_obj(media_json, (media_index, 'rating')) or json_ld_json.get('average_rating')),
            'series': json_ld_json.get('series'),
            'episode': json_ld_json.get('episode'),
            'view_count': int_or_none(traverse_obj(media_json, (media_index, 'viewCount'))),
            'comments': [{
                'author': review.get('tag'),
                'text': review.get('text')
            } for review in nextjs_json.get('Review') or {}] or None,
            'comment_count': int_or_none(len(nextjs_json.get('review') or [])),
            **kwargs,
        }

    def _extract_data(self, url, **kwargs):
        sites_type, display_id = self._match_valid_url(url).group('sites_type', 'id')
        webpage = self._download_webpage(url, display_id)
        nextjs_json = self._search_nextjs_data(webpage, display_id)['props']['pageProps']['metadataItem']

        movie_entry = [self._extract_movie(webpage, display_id, sites_type, **kwargs)] if nextjs_json.get('playableKey') else []

        # TODO: change 'Movie' to actual movie id
        if self._yes_playlist(nextjs_json['ratingKey'], 'Movie'):
            trailer_entry = list(self._get_clips(nextjs_json, display_id)) if nextjs_json.get('Extras') else []
            movie_entry.extend(trailer_entry)
            return self.playlist_result(movie_entry, nextjs_json['ratingKey'], nextjs_json.get('title'))
        else:
            if len(movie_entry) == 0:
                raise ExtractorError('No movie/episode video found')
            else:
                return movie_entry[0]


class PlexWatchMovieIE(PlexWatchBaseIE):
    _VALID_URL = r'https?://watch\.plex\.tv/(?:\w+/)?(?:country/\w+/)?(?P<sites_type>movie)/(?P<id>[\w-]+)'
    _TESTS = [{
        # movie only
        'url': 'https://watch.plex.tv/movie/bowery-at-midnight',
        'info_dict': {
            'id': '627585f7408eb57249d905d5',
            'display_id': 'bowery-at-midnight',
            'ext': 'mp4',
            'title': 'Bowery at Midnight',
            'description': 'md5:7ebaa1b530d98f042295e18d6f4f8c21',
            'duration': 3723,
            'thumbnail': 'https://image.tmdb.org/t/p/original/lDWHvIotQkogG77wHVuMT8mF8P.jpg',
            'cast': 'count:22',
            'categories': ['Horror', 'Action', 'Comedy', 'Crime', 'Thriller'],
            'release_date': '1942-10-30',
            'view_count': int,
            'comment_count': int,

        }
    }, {
        # trailer only
        'url': 'https://watch.plex.tv/movie/the-sea-beast-2',
        'info_dict': {
            'id': '5d77709a6afb3d002061df55',
            'title': 'The Sea Beast'
        },
        'playlist_count': 4,
    }, {
        # movie and trailer
        'url': 'https://watch.plex.tv/movie/wheels-on-meals',
        'info_dict': {
            'id': '5d776d10594b2b001e700571',
            'title': 'Wheels on Meals',
        },
        'playlist_count': 2,
    }]

    def _real_extract(self, url):
        return self._extract_data(url)


class PlexWatchEpisodeIE(PlexWatchBaseIE):
    _VALID_URL = r'https?://watch\.plex\.tv/(?:\w+/)?(?:country/\w+/)?(?P<sites_type>show)/(?P<id>[\w-]+)/season/(?P<season_num>\d+)/episode/(?P<episode_num>\d+)'
    _TESTS = [{
        'url': 'https://watch.plex.tv/show/popeye-the-sailor/season/1/episode/1',
        'info_dict': {
            'id': '5ebdfbd4808e8b0040551a4c',
            'ext': 'mp4',
            'display_id': 'popeye-the-sailor',
            'description': 'md5:d3fcad5bd678b43428f93944b66c2752',
            'thumbnail': 'https://image.tmdb.org/t/p/original/r3SwiK3IANuAAvb1a0oShu8HKcV.jpg',
            'title': 'Barbecue for Two',
            'episode_number': 1,
            'episode': 'Barbecue for Two',
            'season': 'Season 1',
            'season_number': 1,
            'release_date': '1960-06-10',
            'series': 'Popeye the Sailor',
            'duration': 1376,
            'view_count': int,
            'comment_count': int,
        }
    }, {
        'url': 'https://watch.plex.tv/show/a-cooks-tour-2/season/1/episode/3',
        'info_dict': {
            'id': '624c6c71d8d423a47b4fa7a7',
            'ext': 'mp4',
            'description': 'md5:54aec1794285c7e977e87d726439b01f',
            'display_id': 'a-cooks-tour-2',
            'title': 'Cobra Heart, Food That Makes You Manly',
            'thumbnail': 'https://metadata-static.plex.tv/b/gracenote/b4452f949f600db816b3e6a51ce0674a.jpg',
            'episode': 'Cobra Heart, Food That Makes You Manly',
            'episode_number': 3,
            'season_number': 1,
            'season': 'Season 1',
            'release_date': '2002-03-19',
            'series': 'A Cook\'s Tour',
            'average_rating': 10.0,
            'view_count': int,
            'duration': 1287,
            'comment_count': int,
        }
    }]

    def _real_extract(self, url):
        episode, season = self._match_valid_url(url).group('episode_num', 'season_num')
        return self._extract_data(url, episode_number=int(episode), season_number=int(season))


class PlexWatchSeasonIE(PlexWatchBaseIE):
    _VALID_URL = r'https?://watch\.plex\.tv/show/(?P<season>[\w-]+)/season/(?P<season_num>\d+)/?(?:$|[#?])'
    _TESTS = [{
        'url': 'https://watch.plex.tv/show/a-cooks-tour-2/season/1',
        'info_dict': {
            'id': '624c6b291e79c48d83a2b04e',
            'title': 'A Cook\'s Tour',
            'season': 'A Cook\'s Tour',
            'season_number': '1',
        },
        'playlist_count': 22,
    }]

    def _get_episode_result(self, episode_list, season_name, season_index):
        for episode in episode_list:
            yield self.url_result(
                f'https://watch.plex.tv/show/{season_name}/season/{season_index}/episode/{episode}',
                ie=PlexWatchEpisodeIE)

    def _real_extract(self, url):
        season_name, season_num = self._match_valid_url(url).group('season', 'season_num')

        nextjs_json = self._search_nextjs_data(
            self._download_webpage(url, season_name), season_name)['props']['pageProps']

        return self.playlist_result(
            self._get_episode_result(
                traverse_obj(nextjs_json, ('episodes', ..., 'index')), season_name, season_num),
            traverse_obj(nextjs_json, ('metadataItem', 'playableID')),
            traverse_obj(nextjs_json, ('metadataItem', 'parentTitle')),
            traverse_obj(nextjs_json, ('metadataItem', 'summary')),
            season=traverse_obj(nextjs_json, ('metadataItem', 'parentTitle')), season_number=season_num)


class PlexWatchLiveIE(PlexWatchBaseIE):
    _VALID_URL = r'https?://watch\.plex\.tv/live-tv/channel/(?P<id>[\w-]+)'
    _TESTS = [{
        'url': 'https://watch.plex.tv/live-tv/channel/euronews',
        'info_dict': {
            'id': '5e20b730f2f8d5003d739db7-60089d90f682a3002c348299',
            'ext': 'mp4',
            'title': r're:[\w\s-]+[\d-]+\s*[\d+:]+',
            'display_id': 'euronews',
            'live_status': 'is_live',
        }
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)

        nextjs_json = self._search_nextjs_data(
            self._download_webpage(url, display_id), display_id)['props']['pageProps']['channel']
        media_json = self._download_json(
            f'https://epg.provider.plex.tv/channels/{nextjs_json["id"]}/tune',
            display_id, data=b'', headers={'X-PLEX-TOKEN': PlexWatchBaseIE._TOKEN, 'Accept': 'application/json'})

        formats, subtitles = self._get_formats_and_subtitles(
            traverse_obj(media_json, (
                'MediaContainer', 'MediaSubscription', ..., 'MediaGrabOperation', ..., 'Metadata', ..., 'Media', ..., 'Part', ..., 'key')),
            display_id, 'live')

        return {
            'id': nextjs_json['id'],
            'display_id': display_id,
            'title': traverse_obj(media_json, ('MediaContainer', 'MediaSubscription', 0, 'title')),
            'formats': formats,
            'subtitles': subtitles,
            'live_status': 'is_live',
        }


class PlexAppIE(PlexWatchBaseIE):
    _VALID_URL = r'https://app\.plex\.tv/\w+/#!/provider/(?P<provider>(tv\.plex\.provider\.((?!music)\w+)))/details\?key\s*=\s*(?P<key>%2Flibrary%2Fmetadata%2F(?P<id>[a-f0-9]+))'
    _TESTS = [{
        # movie
        'url': 'https://app.plex.tv/desktop/#!/provider/tv.plex.provider.vod/details?key=%2Flibrary%2Fmetadata%2F5e0c0cda7440fc0020ab9ff5&context=library%3Ahub.movies.documentary~16~7',
        'info_dict': {
            'id': '5e0c0cda7440fc0020ab9ff5',
            'display_id': 'nazi-concentration-and-prison-camps',
            'ext': 'mp4',
            'title': 'Nazi Concentration and Prison Camps',
            'thumbnail': 'https://image.tmdb.org/t/p/original/uNxkPkR2GGG71JSyh2Lqptnwcwm.jpg',
            'cast': ['Dwight D. Eisenhower', 'Jack Taylor'],
            'duration': 3517,
            'description': 'md5:cc021d47035520acf2e027b8b4d244c2',
            'categories': ['Documentary', 'History'],
            'release_date': '2017-04-22',
            'average_rating': 8.3,
            'view_count': int,
            'comment_count': int,
        },
        'params': {
            'skip_download': True
        },
    }, {
        # episode
        'url': 'https://app.plex.tv/desktop/#!/provider/tv.plex.provider.vod/details?key=%2Flibrary%2Fmetadata%2F62b0fbd90776e5797e7d92fe&context=library%3Ahub.movies.reality-tv~8~9',
        'info_dict': {
            'id': '62b0fbd90776e5797e7d92fe',
            'ext': 'mp4',
            'duration': 1350,
            'description': 'Gorilla makes funny gestures and postures; horse makes funny faces; duck honking a horn.',
            'view_count': int,
            'title': 'If you\'re happy and you know it',
            'episode_number': 1,
            'season_number': 1,
            'episode': 'If you\'re happy and you know it',
            'display_id': 'funniest-pets-and-people',
            'thumbnail': 'https://cf-images.us-east-1.prod.boltdns.net/v1/jit/6058083015001/d958c52a-3e73-4902-8623-adfe2f36ea3f/main/1280x720/11m15s61ms/match/image.jpg',
            'season': 'Season 1',
            'series': 'Funniest Pets & People',
            'release_date': '2006-10-03',
            'comment_count': int,
        },
        'params': {
            'skip_download': True,
        }
    }, {
        # season
        'url': 'https://app.plex.tv/desktop/#!/provider/tv.plex.provider.vod/details?key=%2Flibrary%2Fmetadata%2F62a8b77b93fc109a6d020761&context=library%3Ahub.movies.reality-tv~8~9',
        'info_dict': {
            'id': '62a8b77b93fc109a6d020761',
            'title': 'Funniest Pets & People',
            'season': 'Funniest Pets & People',
            'season_number': '1',
            'thumbnail': 'https://image.tmdb.org/t/p/original/ngm14GVJ6jULL3zKK6puuVagRLH.jpg',
        },
        'playlist_count': 15,
    }, {
        # Extras
        'url': 'https://app.plex.tv/desktop/#!/provider/tv.plex.provider.metadata/details?key=%2Flibrary%2Fmetadata%2F5ef5ee0d1ce3fd004039976a&context=library%3Ahub.home.top_watchlisted~4~1',
        'info_dict': {
            'id': '5ef5ee0d1ce3fd004039976a',
            'title': 'Lightyear',
            'cast': 'count:33',
            'thumbnail': r're:https://image\.tmdb\.org/t/p/original/\w+\.jpg',
            'duration': 6000,
            'rating': 10,
            'average_rating': 7.5,
        },
        'playlist_count': 24,
    }]

    def _real_extract(self, url):
        provider, key, display_id = self._match_valid_url(url).group('provider', 'key', 'id')
        key = urllib.parse.unquote(key)
        media_json = self._download_json(
            f'{self._CDN_ENDPOINT[provider]}{key}', display_id, headers={'Accept': 'application/json'},
            query={
                'uri': f'provider://{provider}{key}',
                'X-Plex-Token': PlexWatchBaseIE._TOKEN
            })['MediaContainer']['Metadata'][0]

        # check if publicPagesURL, if exists redirect to PlexWatch*IE, else handle manually
        if media_json.get('publicPagesURL'):
            self.write_debug('got publicPagesURL, redirect to PlexWatch*IE')

            additional_info = {
                'view_count': int_or_none(media_json.get('viewCount')),
                'thumbnail': media_json.get('thumb'),
                'duration': int_or_none(media_json.get('duration'), 1000),
                'cast': traverse_obj(media_json, ('Role', ..., 'tag')),
                'rating': parse_age_limit(media_json.get('contentRating')),
                'average_rating': float_or_none(media_json.get('rating')),
            }
            return self.url_result(media_json.get('publicPagesURL'), url_transparent=True, **additional_info)

        else:
            if media_json.get('type') in ('episode', 'movie'):
                selected_media = traverse_obj(
                    media_json, ('Media', ..., 'Part', ..., 'key'))

                formats, subtitles = self._get_formats_and_subtitles(selected_media, display_id, provider)
                return {
                    'id': display_id,
                    'ext': 'mp4',
                    'title': media_json.get('title'),
                    'description': media_json.get('summary'),
                    'formats': formats,
                    'subtitles': subtitles,
                    'thumbnail': media_json.get('thumb'),
                    'duration': int_or_none(media_json.get('duration'), 1000),
                    'cast': traverse_obj(media_json, ('Role', ..., 'tag')),
                    'rating': parse_age_limit(media_json.get('contentRating')),
                    'view_count': media_json.get('viewCount')
                }
