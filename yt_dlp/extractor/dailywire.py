import json
from .common import InfoExtractor
from ..utils import (
    determine_ext,
    float_or_none,
    join_nonempty,
    traverse_obj,
    url_or_none,
)


class DailyWireBaseIE(InfoExtractor):
    _GRAPHQL_API = 'https://v2server.dailywire.com/app/graphql'
    _GRAPHQL_QUERIES = {
        'getEpisodeBySlug': 'query getEpisodeBySlug($slug: String!) {episode(where: {slug: $slug}) {id,title,status,slug,isLive,description,createdAt,scheduleAt,updatedAt,image,allowedCountryNames,allowedContinents,rating,show {id,name,slug,belongsTo},segments {id,image,title,liveChatAccess,audio,video,duration,watchTime,description,videoAccess,muxAssetId,muxPlaybackId,captions {id}},createdBy {firstName,lastName},discussionId}}',
        'getVideoBySlug': 'query getVideoBySlug($slug: String!) {video(where: {slug: $slug}) {id,name,slug,status,description,metadata,image,clips {id,name,slug,image,show {id,name,slug},video {id,name,slug},thumbnail,duration,clipAccess,createdAt,updatedAt},scheduleAt,allowedContinents,allowedCountryNames,rating,thumbnail,videoURL,logoImage,duration,createdBy {firstName,lastName},createdAt,updatedAt,watchTime,liveChatAccess,videoAccess,captions {id}}}',
        'getClipBySlug': 'query getClipBySlug($slug: String!) {clip(where: {slug: $slug}) {id,name,slug,description,image,show {id,name,slug},video {id,status,name,slug},thumbnail,duration,clipAccess,createdBy {firstName,lastName},createdAt,updatedAt,videoURL,captions {id}}}',
        'getShowBySlug': 'query getShowBySlug($slug: String!) {show(where: {slug: $slug}) {id,slug,belongsTo,name,description,image,logoImage,backgroundImage,hostImage,createdAt,updatedAt,author {firstName,lastName},episodes(where: {status_not_in: [DRAFT, UNPUBLISHED]},first: 1,orderBy: createdAt_DESC) {id,image,title,slug,status,createdAt,scheduleAt,description,show {id,name,slug,belongsTo},segments {id,title,muxAssetId,muxPlaybackId,audio}},seasons(orderBy: weight_DESC) {id,name,slug,orderBy}}}',
        'getSeasonEpisodes': 'query getSeasonEpisodes($where: getSeasonEpisodesInput!, $first: Int, $skip: Int) {getSeasonEpisodes(where: $where, first: $first, skip: $skip) {id,episode {id,title,slug,image,description,updatedAt,scheduleAt,createdAt,discussionId,isLive,status}}}',
    }
    _GRAPHQL_VIDEO_QUERIES = {
        'episode': 'getEpisodeBySlug',
        'videos': 'getVideoBySlug',
        'clips': 'getClipBySlug',
    }
    _GRAPHQL_JSON_PATH = {
        'getEpisodeBySlug': ('data', 'episode'),
        'getVideoBySlug': ('data', 'video'),
        'getClipBySlug': ('data', 'clip'),
        'getSeasonEpisodes': ('data', 'getSeasonEpisodes'),
        'getShowBySlug': ('data', 'show'),
    }
    _ACCESS_TOKEN = None

    def _get_auth(self):
        t = self._get_cookies('https://www.dailywire.com').get('accessToken')
        if t:
            self._ACCESS_TOKEN = t.value

    def _call_api(self, slug, query, variables):
        headers = {
                'Apollographql-Client-Name': 'DW_WEBSITE',
                'Content-Type': 'application/json',
                'Origin': 'https://www.dailywire.com',
                'Referer': 'https://www.dailywire.com/'}
        
        self._get_auth() ### I doubt this is how you are supposed to set _TOKEN
        if self._ACCESS_TOKEN:
            headers['Authorization'] = f'Bearer {self._ACCESS_TOKEN}'
        
        json_data = self._download_json(
                self._GRAPHQL_API, slug, 'Downloading JSON from GraphQL API', data=json.dumps({
                'query': self._GRAPHQL_QUERIES[query], 'variables': variables}).encode(), headers=headers)

        return traverse_obj(json_data, self._GRAPHQL_JSON_PATH.get(query, ()))


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
            'creator': 'Caroline Roberts',
            'series_id': 'ckzplm0a097fn0826r2vc3j7h',
            'series': 'China: The Enemy Within',
        }
    }, {
        'url': 'https://www.dailywire.com/episode/ep-124-bill-maher',
        'info_dict': {
            'id': 'cl0ngbaalplc80894sfdo9edf',
            'ext': 'mp3',
            'display_id': 'ep-124-bill-maher',
            'title': 'Ep. 124 - Bill Maher',
            'thumbnail': 'https://daily-wire-production.imgix.net/episodes/cl0ngbaalplc80894sfdo9edf/cl0ngbaalplc80894sfdo9edf-1647065568518.jpg',
            'creator': 'Caroline Roberts',
            'description': 'md5:adb0de584bcfa9c41374999d9e324e98',
            'series_id': 'cjzvep7270hp00786l9hwccob',
            'series': 'The Sunday Special',
        }
    }, {
        'url': 'https://www.dailywire.com/videos/the-hyperions',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        sites_type, slug = self._match_valid_url(url).group('sites_type', 'id')
        episode_info = self._call_api(slug, self._GRAPHQL_VIDEO_QUERIES[sites_type], {'slug': slug})

        urls = traverse_obj(episode_info,
            (('segments', 'clips'), ..., ('video', 'audio')), expected_type=url_or_none) or [
            episode_info.get('videoURL') if episode_info.get('videoURL') != 'Access Denied' else None]

        ### print(urls)

        ### add warning about auth if no formats and no auth ?

        formats, subtitles = [], {}
        for url in urls:
            if determine_ext(url) != 'm3u8':
                formats.append({'url': url})
                continue
            format_, subs_ = self._extract_m3u8_formats_and_subtitles(url, slug)
            formats.extend(format_)
            self._merge_subtitles(subs_, target=subtitles)
        return {
            'id': episode_info['id'],
            'display_id': slug,
            'title': traverse_obj(episode_info, 'title', 'name'),
            'description': episode_info.get('description'),
            'creator': join_nonempty(('createdBy', 'firstName'), ('createdBy', 'lastName'), from_dict=episode_info, delim=' '),
            'duration': float_or_none(episode_info.get('duration')),
            'is_live': episode_info.get('isLive'),
            'thumbnail': traverse_obj(episode_info, 'thumbnail', 'image', expected_type=url_or_none),
            'formats': formats,
            'subtitles': subtitles,
            'series_id': traverse_obj(episode_info, ('show', 'id')),
            'series': traverse_obj(episode_info, ('show', 'name')),
        } ### test to make sure all values are properly extracted


class DailyWirePodcastIE(DailyWireBaseIE): ### need to rewrite this
    _VALID_URL = r'https?://(?:www\.)dailywire(?:\.com)/(?P<sites_type>podcasts)/(?P<podcaster>[\w-]+/(?P<id>[\w-]+))'
    _TESTS = [{
        'url': 'https://www.dailywire.com/podcasts/morning-wire/get-ready-for-recession-6-15-22',
        'info_dict': {
            'id': 'cl4f01d0w8pbe0a98ydd0cfn1',
            'ext': 'm4a',
            'display_id': 'get-ready-for-recession-6-15-22',
            'title': 'Get Ready for Recession | 6.15.22',
            'description': 'md5:c4afbadda4e1c38a4496f6d62be55634',
            'thumbnail': 'https://daily-wire-production.imgix.net/podcasts/ckx4otgd71jm508699tzb6hf4-1639506575562.jpg',
            'duration': 900.117667,
        }
    }]

    def _real_extract(self, url):
        raise Exception('currently broken') ###
        slug, episode_info = self._get_json(url)
        audio_id = traverse_obj(episode_info, 'audioMuxPlaybackId', 'VUsAipTrBVSgzw73SpC2DAJD401TYYwEp')

        return {
            'id': episode_info['id'],
            'url': f'https://stream.media.dailywire.com/{audio_id}/audio.m4a',
            'display_id': slug,
            'title': episode_info.get('title'),
            'duration': float_or_none(episode_info.get('duration')),
            'thumbnail': episode_info.get('thumbnail'),
            'description': episode_info.get('description'),
        }


class DailyWireShowIE(DailyWireBaseIE):
    _VALID_URL = r'https?://(?:www\.)dailywire(?:\.com)/(?P<sites_type>show)/(?P<id>[\w-]+)'
    _TESTS = [
    ]
    
    def _real_extract(self, url):
        sites_type, slug = self._match_valid_url(url).group('sites_type', 'id')
        
        show = self._call_api(slug, 'getShowBySlug', {'slug': slug})
        
        for season in show.get('seasons', []):
            season['episodes'] = []
            while episode_page := self._call_api(season['slug'], 'getSeasonEpisodes', {'where': {'season': {'id': season['id']}},
                                                 'first': 10, 'skip': len(season['episodes']) or None}):
                season['episodes'] += [episode['episode'] for episode in episode_page]
        
        return self.playlist_result(
            [self.url_result(f'https://www.dailywire.com/episode/{e["slug"]}')
             for season in show['seasons'] for e in season['episodes']],
            show.get('id'), show.get('name'), show.get('description'))

