import itertools
import json

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    determine_ext,
    float_or_none,
    join_nonempty,
    parse_iso8601,
    traverse_obj,
    url_or_none,
)


class DailyWireBaseIE(InfoExtractor):
    _GRAPHQL_API = 'https://v2server.dailywire.com/app/graphql'
    _GRAPHQL_QUERIES = {
        'getClipBySlug': 'query getClipBySlug($slug:String!){clip(where:{slug:$slug}){id,name,slug,description,image,show{id,name,slug},thumbnail,duration,createdBy{firstName,lastName},createdAt,videoURL}}',
        'getEpisodeBySlug': 'query getEpisodeBySlug($slug:String!){episode(where:{slug:$slug}){id,title,slug,description,createdAt,image,show{id,name,slug},segments{audio,video,duration,},createdBy{firstName,lastName}}}',
        'getPodcastEpisodes': 'query getPodcastEpisodes($where: PodcastEpisodeWhereInput, $orderBy: PodcastEpisodeOrderBy, $skip: Int, $first: Int) {listPodcastEpisode(where: $where, orderBy: $orderBy, skip: $skip, first: $first) {...ResPodcastEpisode}}, fragment ResPodcastEpisode on getPodcastEpisodeRes {id,title,description,slug,thumbnail,createdAt,audio,duration,podcast {id,name,slug,author {firstName,lastName}},season {id,name,slug}}',
        'getSeasonEpisodes': 'query getSeasonEpisodes($where:getSeasonEpisodesInput!,$first:Int,$skip:Int){getSeasonEpisodes(where:$where,first:$first,skip:$skip){episode{slug}}}',
        'getShowBySlug': 'query getShowBySlug($slug:String!){show(where:{slug:$slug}){id,name,description,image,seasons(orderBy:weight_DESC){id,name,slug}}}',
        'getVideoBySlug': 'query getVideoBySlug($slug:String!){video(where:{slug:$slug}){id,name,slug,description,image,thumbnail,videoURL,duration,createdBy{firstName,lastName},createdAt}}',
    }
    _GRAPHQL_VIDEO_QUERIES = {
        'clips': 'getClipBySlug',
        'episode': 'getEpisodeBySlug',
        'videos': 'getVideoBySlug',
    }
    _GRAPHQL_JSON_PATH = {
        'getClipBySlug': ('data', 'clip'),
        'getEpisodeBySlug': ('data', 'episode'),
        'getPodcastEpisodes': ('data', 'listPodcastEpisode'),
        'getSeasonEpisodes': ('data', 'getSeasonEpisodes', ..., 'episode', 'slug'),
        'getShowBySlug': ('data', 'show'),
        'getVideoBySlug': ('data', 'video'),
    }
    _API_HEADERS = {
        'Apollographql-Client-Name': 'DW_WEBSITE',
        'Content-Type': 'application/json',
        'Origin': 'https://www.dailywire.com',
        'Referer': 'https://www.dailywire.com/',
    }

    def _real_initialize(self):
        if access_token := self._get_cookies('https://www.dailywire.com').get('accessToken'):
            self._API_HEADERS['Authorization'] = f'Bearer {access_token.value}'

    def _call_api(self, slug, query, variables, message='Downloading JSON from GraphQL API'):
        json_data = self._download_json(
            self._GRAPHQL_API, slug, message, data=json.dumps(
                {'query': self._GRAPHQL_QUERIES[query], 'variables': variables}).encode(),
            headers=self._API_HEADERS)

        return traverse_obj(json_data, self._GRAPHQL_JSON_PATH.get(query, ()))

    def _paginate(self, slug, query, where):
        for i in itertools.count(0):
            page = self._call_api(
                slug, query, {'where': where, 'first': 10, 'skip': i * 10},
                message=f'Downloading page {i + 1}')
            if not page:
                break
            yield page


class DailyWireIE(DailyWireBaseIE):
    _VALID_URL = r'https?://(?:www\.)dailywire(?:\.com)/(?P<sites_type>episode|videos|clips)/(?P<id>[\w-]+)'
    _TESTS = [{
        'url': 'https://www.dailywire.com/episode/1-fauci',
        'info_dict': {
            'id': 'ckzsl50xnqpy30850in3v4bu7',
            'ext': 'mp4',
            'display_id': '1-fauci',
            'title': '1. Fauci',
            'description': 'md5:9df630347ef85081b7e97dd30bc22853',
            'thumbnail': 'https://daily-wire-production.imgix.net/episodes/ckzsl50xnqpy30850in3v4bu7/ckzsl50xnqpy30850in3v4bu7-1648237399554.jpg',
            'series_id': 'ckzplm0a097fn0826r2vc3j7h',
            'series': 'China: The Enemy Within',
            'upload_date': '20220218',
            'creators': ['Caroline Roberts'],
            'timestamp': 1645182003,
        },
    }, {
        'url': 'https://www.dailywire.com/videos/the-hyperions',
        'only_matching': True,
    }, {
        'skip': 'premium only',
        'url': 'https://www.dailywire.com/episode/ep-3-avery-s-niece-new',
        'info_dict': {
            'id': 'clm8geguv3qku0870ewvcu0ed',
            'display_id': 'ep-3-avery-s-niece-new',
            'title': 'Ep 3 - Avery’s Niece',
            'description': 'md5:861ab336bd2bab2abebc25a1479a42e0',
            'thumbnail': 'https://daily-wire-production.imgix.net/episodes/clm8geguv3qku0870ewvcu0ed/clm8geguv3qku0870ewvcu0ed-1694047935734.png',
            'series_id': 'clim20ue5f8160838ecz7ba8q',
            'ext': 'mp4',
            'subtitles': {'en-US': [{'ext': 'vtt'}]},
            'timestamp': 1694062826,
            'series': 'Convicting a Murderer',
            'creators': ['Scott Bowler '],
            'upload_date': '20230907',
        },
    }, {
        'skip': 'premium only',
        'url': 'https://www.dailywire.com/clips/the-making-of-run-hide-fight',
        'info_dict': {
            'id': 'ckjutyd6810dd0806ivcq2526',
            'display_id': 'the-making-of-run-hide-fight',
            'title': 'The Making of Run Hide Fight',
            'description': 'md5:085297d753b73ad87bdd8b050cc10d2c',
            'thumbnail': 'https://image.media.dailywire.com/K7OqsPwWH5c9hpWT68CHeZ4vRUtoz5Le/thumbnail.png',
            'duration': 916.790889,
            'creators': ['Paul Snyder'],
            'upload_date': '20210113',
            'timestamp': 1610506443,
            'ext': 'mp4',
        },
    }, {
        'skip': 'premium only',
        'url': 'https://www.dailywire.com/videos/choosing-death-the-legacy-of-roe',
        'info_dict': {
            'id': 'cl3260dva6pjr097819zw506s',
            'display_id': 'choosing-death-the-legacy-of-roe',
            'title': 'Choosing Death [The Legacy of Roe]',
            'description': 'md5:b07597f0ef32130365427a05fd1ccd25',
            'duration': 2618.0738,
            'timestamp': 1652308821,
            'upload_date': '20220511',
            'thumbnail': 'https://image.media.dailywire.com/FBgIBgmq635VuqTgWKjcGviEjJ2vJ02Zz/thumbnail.png',
            'subtitles': {'en-US': [{'ext': 'vtt'}]},
            'ext': 'mp4',
        },
    }]

    def _real_extract(self, url):
        sites_type, slug = self._match_valid_url(url).group('sites_type', 'id')
        episode_data = self._call_api(slug, self._GRAPHQL_VIDEO_QUERIES[sites_type], {'slug': slug})

        if not episode_data:
            raise ExtractorError('video not found')

        urls = traverse_obj(episode_data,
                            (('segments', 'clips'), ..., ('video', 'audio'))
                            ) or [episode_data.get('videoURL')]

        if 'Access Denied' in urls:
            self.report_warning(f'It looks like {slug} requires a login. Try passing cookies and try again.')

        urls = [url_or_none(u) for u in urls if url_or_none(u)]

        formats, subtitles = [], {}
        for url in urls:
            if determine_ext(url) != 'm3u8':
                formats.append({'url': url})
                continue
            format_, subs_ = self._extract_m3u8_formats_and_subtitles(url, slug)
            formats.extend(format_)
            self._merge_subtitles(subs_, target=subtitles)
        return {
            'id': episode_data.get('id'),
            'display_id': slug,
            'title': traverse_obj(episode_data, 'title', 'name'),
            'description': episode_data.get('description'),
            'creator': join_nonempty(('createdBy', 'firstName'), ('createdBy', 'lastName'),
                                     from_dict=episode_data, delim=' '),
            'duration': float_or_none(episode_data.get('duration')),
            'timestamp': parse_iso8601(episode_data.get('createdAt')),
            'is_live': episode_data.get('isLive'),
            'thumbnail': traverse_obj(episode_data, 'thumbnail', 'image', expected_type=url_or_none),
            'formats': formats,
            'subtitles': subtitles,
            'series_id': traverse_obj(episode_data, ('show', 'id')),
            'series': traverse_obj(episode_data, ('show', 'name')),
        }


class DailyWirePodcastIE(DailyWireBaseIE):
    _VALID_URL = r'https?://(?:www\.)dailywire(?:\.com)/(?P<sites_type>podcasts)/(?P<podcaster>[\w-]+)/?(?P<id>[\w-]+)?'
    _TESTS = [{
        'note': 'serves shorter ad-free stream with paid cookies',
        'url': 'https://www.dailywire.com/podcasts/morning-wire/get-ready-for-recession-6-15-22',
        'info_dict': {
            'id': 'cl4f01d0w8pbe0a98ydd0cfn1',
            'ext': 'm4a',
            'display_id': 'get-ready-for-recession-6-15-22',
            'title': 'Get Ready for Recession | 6.15.22',
            'description': 'md5:c4afbadda4e1c38a4496f6d62be55634',
            'thumbnail': 'https://daily-wire-production.imgix.net/podcasts/ckx4otgd71jm508699tzb6hf4-1667859984424.jpg',
            'duration': 900.117667,
            'timestamp': 1655261631,
            'season_id': 'morning-wire-morning-wire-podcast-season',
            'series_id': 'morning-wire',
            'creators': ['Georgia Howe'],
            'season': '2022',
            'series': 'Morning Wire',
            'upload_date': '20220615',
        },
    }, {
        'url': 'https://www.dailywire.com/podcasts/enough',
        'info_dict': {
            'id': 'ckx4kvm8710i80869lvuu1b8z',
            'title': 'Enough',
            'display_id': 'enough',
        },
        'playlist_mincount': 7,
    }]

    def _real_extract(self, url):
        podcaster, slug = self._match_valid_url(url).group('podcaster', 'id')

        def _extract_pod_ep_info(episode_data):
            print(episode_data)
            return {
                'id': episode_data.get('id'),
                'url': episode_data.get('audio'),
                'display_id': episode_data.get('slug'),
                'title': episode_data.get('title'),
                'duration': float_or_none(episode_data.get('duration')),
                'timestamp': parse_iso8601(episode_data.get('createdAt')),
                'thumbnail': episode_data.get('thumbnail'),
                'description': episode_data.get('description'),
                'creator': join_nonempty(('podcast', 'author', 'firstName'),
                                         ('podcast', 'author', 'lastName'),
                                         from_dict=episode_data, delim=' '),
                'season': traverse_obj(episode_data, ('season', 'name')),
                'season_id': traverse_obj(episode_data, ('season', 'slug')),
                'series': traverse_obj(episode_data, ('podcast', 'name')),
                'series_id': traverse_obj(episode_data, ('podcast', 'slug')),
            }

        if slug:
            episodes = self._call_api(slug, 'getPodcastEpisodes', {'where': {'slug': slug}})
            if episode_data := traverse_obj(episodes, ..., get_all=False):
                return _extract_pod_ep_info(episode_data)
        else:
            episodes = [
                episode for page in
                self._paginate(podcaster, 'getPodcastEpisodes', {'podcast': {'slug': podcaster}})
                for episode in page
            ]

            if episodes:
                podcast_data = traverse_obj(episodes, (..., 'podcast'), {}, get_all=False)
                return self.playlist_result(
                    [_extract_pod_ep_info(e) for e in episodes],
                    podcast_data.get('id'), podcast_data.get('name'), podcast_data.get('description'),
                    display_id=podcast_data.get('slug'), thumbnail=podcast_data.get('coverImage'))

        raise ExtractorError('Podcast not found')


class DailyWireShowIE(DailyWireBaseIE):
    _VALID_URL = r'https?://(?:www\.)dailywire(?:\.com)/(?P<sites_type>show)/(?P<id>[\w-]+)'
    _TESTS = [{
        'skip': 'premium only',
        'url': 'https://www.dailywire.com/show/apollo-11-what-we-saw',
        'playlist_mincount': 28,
        'info_dict': {
            'id': 'ckixsvamonvl40862ysxve50i',
            'thumbnail': 'https://daily-wire-production.imgix.net/shows/ckixsvamonvl40862ysxve50i-1679082975554.jpg',
            'title': 'What We Saw',
            'description': 'md5:98d2a7d5cc8175494a4ca611058ed440',
        },
        'params': {
            'skip_download': True,
        },
        'playlist': [{
            'info_dict': {
                'id': 'cltf80tk79fxi0942c7h394b5',
                'season_id': 'what-we-saw-season-3-an-empire-of-terror-season',
                'ext': 'mp4',
                'display_id': 'season-3-an-empire-of-terror',
                'display_id': 'season-3-an-empire-of-terror',
                'series_id': 'ckixsvamonvl40862ysxve50i',
                'title': 'Season 3: An Empire of Terror',
                'description': 'What We Saw: An Empire of Terror premieres on March 6, 2024.',
                'creators': ['Scott Bowler '],
                'upload_date': '20240306',
                'timestamp': 1709704832,
                'thumbnail': 'https://daily-wire-production.imgix.net/episodes/cltf80tk79fxi0942c7h394b5/cltf80tk79fxi0942c7h394b5-1709694601671.png',
                'series': 'What We Saw',
            }}]
    }]

    def _real_extract(self, url):
        slug = self._match_valid_url(url).group('id')

        show_data = self._call_api(slug, 'getShowBySlug', {'slug': slug})
        if not show_data:
            raise ExtractorError('Show not found')

        for season_data in show_data.get('seasons', []):
            season_data['episodes'] = [
                episode for page in
                self._paginate(season_data.get('slug'), 'getSeasonEpisodes', {'season': {'id': season_data.get('id')}})
                for episode in page
            ]

        return self.playlist_result(
            [self.url_result(f'https://www.dailywire.com/episode/{episode_slug}',
             season_id=season_data.get('slug'), season=season_data.get('title'), url_transparent=True)
             for season_data in show_data.get('seasons', []) for episode_slug in season_data['episodes']],
            show_data.get('id'), show_data.get('name'), show_data.get('description'),
            thumbnail=show_data.get('image'))
