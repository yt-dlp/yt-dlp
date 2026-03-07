import functools
import math

from .common import InfoExtractor
from ..utils import (
    InAdvancePagedList,
    OnDemandPagedList,
    clean_html,
    filter_dict,
    float_or_none,
    int_or_none,
    parse_duration,
    parse_iso8601,
    parse_qs,
    str_or_none,
    update_url,
    url_or_none,
)
from ..utils.traversal import (
    require,
    traverse_obj,
    trim_str,
)


class OmnyfmIE(InfoExtractor):
    _VALID_URL = r'https?://omny\.fm/shows/(?P<uploader_id>[\w-]+)/(?P<id>(?!playlists$)[\w-]+)(?:/embed)?(?=[?#"\']|$)'
    _EMBED_REGEX = [fr'<iframe[^>]+\bsrc=(["\'])(?P<url>{_VALID_URL}[^"\']*)\1']
    _TESTS = [{
        'url': 'https://omny.fm/shows/sleep-hub/cannabinoids-and-sleep',
        'md5': 'e45ec0ce43da757a0be6ca117ec01bdc',
        'info_dict': {
            'id': 'cannabinoids-and-sleep',
            'ext': 'mp3',
            'title': 'Cannabinoids and Sleep',
            'categories': 'count:1',
            'chapters': [
                {'start_time': 0, 'title': 'Introduction'},
                {'start_time': 138, 'title': 'Theme: Cannabinoids and Sleep'},
                {'start_time': 1487, 'title': 'Clinical Tip'},
                {'start_time': 1635, 'title': 'Pick of the Month'},
                {'start_time': 1795, 'title': 'What\'s Coming Up?'},
            ],
            'description': 'md5:c0fd2d29f3148382d344cfbd012fb00d',
            'duration': 1840.274,
            'episode': 'Episode 48',
            'episode_number': 48,
            'modified_date': r're:\d{8}',
            'modified_timestamp': int,
            'section_start': 0,
            'tags': 'count:6',
            'thumbnail': r're:https?://www\.omnycontent\.com/.+',
            'timestamp': 1574013600,
            'upload_date': '20191117',
            'uploader': 'Sleep Talk',
            'uploader_id': 'sleep-hub',
        },
    }, {
        'url': 'https://omny.fm/shows/the-origin-of-things/a-song-of-hope/embed',
        'md5': 'd7600ef33e3f139ff1bb8946f3651b15',
        'info_dict': {
            'id': 'a-song-of-hope',
            'ext': 'mp3',
            'title': 'A song of hope',
            'categories': 'count:3',
            'description': 'md5:f8e710765c341a48cfda8dacd428f56d',
            'duration': 478.955,
            'episode': 'Episode 17',
            'episode_number': 17,
            'modified_date': r're:\d{8}',
            'modified_timestamp': int,
            'season': 'Season 3',
            'season_number': 3,
            'section_start': 0,
            'tags': 'count:27',
            'thumbnail': r're:https?://www\.omnycontent\.com/.+',
            'timestamp': 1679445000,
            'upload_date': '20230322',
            'uploader': 'The Origin Of Things',
            'uploader_id': 'the-origin-of-things',
        },
    }]
    _WEBPAGE_TESTS = [{
        'url': 'https://www.asahi.com/special/podcasts/item/?itemid=311a5f48-ad71-4548-b1f2-af5e00747fbc',
        'md5': '4c788bf03323734524a7c0f98d9956ed',
        'info_dict': {
            'id': 'sdgs-271',
            'ext': 'mp3',
            'title': '「どこかのだれかの人生のにおいがする」 SDGsを音声番組で身近に #271',
            'categories': 'count:5',
            'description': 'md5:fa086ecce764d81c51648a82d0fe4850',
            'duration': 1870.524,
            'episode': 'Episode 271',
            'episode_number': 271,
            'modified_date': r're:\d{8}',
            'modified_timestamp': int,
            'season': 'Season 1',
            'season_number': 1,
            'section_start': 0,
            'tags': 'count:4',
            'thumbnail': r're:https?://www\.omnycontent\.com/.+',
            'timestamp': 1670266800,
            'upload_date': '20221205',
            'uploader': '朝日新聞ポッドキャスト',
            'uploader_id': 'asahi',
            'webpage_url': 'https://omny.fm/shows/asahi/sdgs-271',
        },
    }]

    def _real_extract(self, url):
        uploader_id, audio_id = self._match_valid_url(url).group('uploader_id', 'id')
        webpage = self._download_webpage(url, audio_id)
        nextjs_data = self._search_nextjs_data(webpage, audio_id)
        clip = traverse_obj(nextjs_data, ('props', 'pageProps', 'clip', {dict}))

        return {
            'id': audio_id,
            'section_start': traverse_obj(parse_qs(url), ('t', -1, {parse_duration})) or 0,
            'uploader_id': uploader_id,
            'vcodec': 'none',
            **traverse_obj(clip, {
                'title': ('Title', {clean_html}, filter),
                'chapters': ('Chapters', ..., {
                    'title': ('Name', {clean_html}, filter),
                    'start_time': ('Position', {parse_duration}),
                }),
                'description': ('Description', {clean_html}, filter),
                'duration': ('DurationSeconds', {float_or_none}),
                'episode_number': ('Episode', {int_or_none}),
                'filesize': ('PublishedAudioSizeInBytes', {int_or_none}),
                'modified_timestamp': ('ModifiedAtUtc', {parse_iso8601}),
                'season_number': ('Season', {int_or_none}),
                'tags': ('Tags', ..., {clean_html}, filter),
                'thumbnail': ('ImageUrl', {update_url(query=None)}),
                'timestamp': ('PublishedUtc', {parse_iso8601}),
                'url': ('AudioUrl', {url_or_none}, {require('audio URL')}),
                'webpage_url': ('PublishedUrl', {url_or_none}),
            }),
            **traverse_obj(clip, ('Program', {
                'categories': ('Categories', ..., {clean_html}, filter),
                'uploader': ('Name', {clean_html}, filter),
            })),
        }


class OmnyfmPlaylistBaseIE(InfoExtractor):
    _API_BASE = 'https://api.omny.fm'
    _BASE_URL = 'https://omny.fm/shows'
    _PAGE_SIZE = 100

    def _yield_clips(self, clips, uploader_id):
        for audio_id in traverse_obj(clips, (
            'Clips', ..., 'Slug', {str_or_none},
        )):
            yield self.url_result(
                f'{self._BASE_URL}/{uploader_id}/{audio_id}', OmnyfmIE)


class OmnyfmPlaylistIE(OmnyfmPlaylistBaseIE):
    _VALID_URL = r'https?://omny\.fm/shows/(?P<uploader_id>[\w-]+)/playlists(?:/(?P<id>[\w-]+))?(?:/embed)?/?(?=[?#"\']|$)'
    _EMBED_REGEX = [fr'<iframe[^>]+\bsrc=(["\'])(?P<url>{_VALID_URL}[^"\']*)\1']
    _TESTS = [{
        'url': 'https://omny.fm/shows/sleep-hub/playlists/sleep-talk',
        'info_dict': {
            'id': 'sleep-talk',
            'title': 'Sleep Talk - Talking all things sleep',
            'description': 'md5:c1d7e5bf32100a432307d2d32c4ab74a',
            'thumbnail': r're:https?://www\.omnycontent\.com/.+',
        },
        'playlist_mincount': 79,
    }, {
        'url': 'https://omny.fm/shows/bayfm-program03/playlists',
        'info_dict': {
            'id': 'bayfm-program03',
        },
        'playlist_count': 4,
    }]
    _WEBPAGE_TESTS = [{
        'url': 'https://www.asahi.com/articles/ASP763WDKP4JDIFI002.html',
        'info_dict': {
            'id': 'podcast',
            'title': 'ニュースの現場から',
            'description': 'md5:ed1f78462ebed09258ca31b1da5ff640',
            'thumbnail': r're:https?://www\.omnycontent\.com/.+',
            'webpage_url': 'https://omny.fm/shows/asahi/playlists/podcast',
        },
        'playlist_mincount': 2367,
    }]

    def _fetch_page(self, uploader_id, playlist_id, page):
        if page == 0:
            self._clip_id = None

        clips = self._download_json(
            f'{self._API_BASE}/programs/{uploader_id}/playlists/{playlist_id}/clips',
            playlist_id, f'Downloading page {page + 1}', query=filter_dict({
                'clipId': self._clip_id,
                'direction': 'AfterExclusive',
                'pageSize': self._PAGE_SIZE,
            }))

        yield from self._yield_clips(clips, uploader_id)

        if clips.get('NextClipsAvailable'):
            self._clip_id = traverse_obj(clips, ('Clips', ..., 'Id', {str_or_none}, all, -1))

    def _real_extract(self, url):
        uploader_id, playlist_id = self._match_valid_url(url).group('uploader_id', 'id')
        webpage = self._download_webpage(url, playlist_id)
        nextjs_data = self._search_nextjs_data(webpage, playlist_id)
        page_props = traverse_obj(nextjs_data, ('props', 'pageProps', {dict}))

        if not playlist_id:
            entries = [self.url_result(
                f'{self._BASE_URL}/{uploader_id}/playlists/{playlist_id}', OmnyfmPlaylistIE,
            ) for playlist_id in traverse_obj(page_props, (
                'playlistsWithClips', ..., 'playlist', 'Slug', {str_or_none},
            ))]

            return self.playlist_result(entries, uploader_id)

        playlist = traverse_obj(page_props, ('playlist', {dict}))
        entries = InAdvancePagedList(
            functools.partial(self._fetch_page, uploader_id, playlist_id),
            math.ceil(int(playlist['NumberOfClips']) / self._PAGE_SIZE), self._PAGE_SIZE)

        return self.playlist_result(
            entries, playlist_id,
            **traverse_obj(playlist, {
                'title': ('Title', {clean_html}, filter),
                'description': ('Description', {clean_html}, filter),
                'thumbnail': ('ArtworkUrl', {update_url(query=None)}),
                'webpage_url': ('EmbedUrl', {url_or_none}, {trim_str(end='/embed')}),
            }))


class OmnyfmShowIE(OmnyfmPlaylistBaseIE):
    _VALID_URL = r'https?://omny\.fm/shows/(?P<id>[\w-]+)/?(?:[?#]|$)'
    _TESTS = [{
        'url': 'https://omny.fm/shows/the-origin-of-things',
        'info_dict': {
            'id': 'the-origin-of-things',
            'title': 'The Origin Of Things',
            'description': 'md5:52b7fba08201d050639c78ea88cc782e',
            'thumbnail': r're:https?://www\.omnycontent\.com/.+',
        },
        'playlist_mincount': 75,
    }]

    def _fetch_page(self, uploader_id, organization_id, program_id, page):
        clips = self._download_json(
            f'{self._API_BASE}/orgs/{organization_id}/programs/{program_id}/clips',
            uploader_id, f'Downloading page {page + 1}', query={
                'cursor': page,
                'pageSize': self._PAGE_SIZE,
            })

        yield from self._yield_clips(clips, uploader_id)

    def _real_extract(self, url):
        uploader_id = self._match_id(url)
        webpage = self._download_webpage(url, uploader_id)
        nextjs_data = self._search_nextjs_data(webpage, uploader_id)
        program = traverse_obj(nextjs_data, ('props', 'pageProps', 'program', {dict}))

        organization_id = traverse_obj(program, (
            'OrganizationId', {str_or_none}, {require('organization ID')}))
        program_id = traverse_obj(program, ('Id', {str_or_none}, {require('program ID')}))
        entries = OnDemandPagedList(
            functools.partial(self._fetch_page, uploader_id, organization_id, program_id), self._PAGE_SIZE)

        return self.playlist_result(
            entries, uploader_id,
            **traverse_obj(program, {
                'title': ('Name', {clean_html}, filter),
                'description': ('Description', {clean_html}, filter),
                'thumbnail': ('ArtworkUrl', {update_url(query=None)}),
            }))
