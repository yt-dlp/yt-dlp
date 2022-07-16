from .common import InfoExtractor
from ..utils import ExtractorError, determine_ext, int_or_none, traverse_obj


class PlexWatchBaseIE(InfoExtractor):
    _CDN_ENDPOINT = {
        'vod': 'https://vod.provider.plex.tv',
        'live': 'https://epg.provider.plex.tv/channels/' # add /tune at the  end 
    }
    _PLEX_TOKEN = 'NytaXzMexGQ9-xW9yDjy' # change this if not work
    
    def _get_formats_and_subtitles(self, selected_media, display_id, sites_type='vod'):
        formats, subtitles = [], {}
        for media in selected_media:
            if determine_ext(media) == 'm3u8':
                fmt, subs = self._extract_m3u8_formats_and_subtitles(
                    f'{self._CDN_ENDPOINT[sites_type]}{media}?X-PLEX-TOKEN={self._PLEX_TOKEN}', display_id)
                formats.extend(fmt)
                self._merge_subtitles(subs, target=subtitles)
                
            # elif determine_ext(media) == 'mpd':
                # fmt, subs = self._extract_mpd_formats_and_subtitles(
                    # f'https://vod.provider.plex.tv/{media}?X-PLEX-TOKEN={plex_token}', display_id)
                # formats.extend(fmt)
                # self._merge_subtitles(subs, target=subtitles)
        
        return formats, subtitles

class PlexWatchIE(PlexWatchBaseIE):
    _VALID_URL = r'https?://watch\.plex\.tv/(?:\w+/)?(?:country/\w+/)?(?P<sites_type>movie)/(?P<id>[\w-]+)[?/#&]?'
    _TESTS = [{
        'url': 'https://watch.plex.tv/movie/bowery-at-midnight',
        'info_dict': {
            'id': '627585f7408eb57249d905d5',
            'display_id': 'bowery-at-midnight',
            'ext': 'mp4',
            'title': 'Bowery at Midnight',
            'description': 'md5:7ebaa1b530d98f042295e18d6f4f8c21',
            'duration': 3660,
            'thumbnail': 'https://image.tmdb.org/t/p/original/lDWHvIotQkogG77wHVuMT8mF8P.jpg',
        }
    }]
    
    def _real_extract(self, url):
        sites_type, display_id = self._match_valid_url(url).group('sites_type', 'id')
        webpage = self._download_webpage(url, display_id)
        
        nextjs_json = self._search_nextjs_data(webpage, display_id)['props']['pageProps']
        
        media_json = self._download_json(
            f'https://play.provider.plex.tv/playQueues', display_id, 
            query={'uri': nextjs_json['metadataItem']['playableKey']}, data=''.encode(),
            headers={'X-PLEX-TOKEN': self._PLEX_TOKEN, 'Accept': 'application/json', 'Cookie': ''})
            
        selected_media = []
        for media in media_json['MediaContainer']['Metadata']:
            if media.get('slug') == display_id:
                selected_media = traverse_obj(media, ('Media', ..., 'Part', ..., 'key'))
        
        formats, subtitles = self._get_formats_and_subtitles(selected_media, display_id, sites_type)
        self._sort_formats(formats)
        
        return {
            'id': nextjs_json['metadataItem']['playableID'],
            'display_id': display_id,
            'formats': formats,
            'subtitles': subtitles,
            'title': traverse_obj(nextjs_json, ('metadataItem', 'title')),
            'description': traverse_obj(nextjs_json, ('metadataItem', 'summary')),
            'thumbnail': traverse_obj(nextjs_json, ('metadataItem', 'thumb')),
            'duration': int_or_none(traverse_obj(nextjs_json, ('metadataItem', 'duration')), 1000),   
        }
        
        
class PlexWatchEpisodeIE(PlexWatchBaseIE):
    IE_NAME = 'PlexWatch:episode'
    _VALID_URL = r'https?://watch\.plex\.tv/(?:\w+/)?(?:country/\w+/)?(?P<sites_type>movie|show)/(?P<id>[\w-]+)/season/\d+/episode/\d+'
    _TESTS = [{
        'url': 'https://watch.plex.tv/show/popeye-the-sailor/season/1/episode/1',
        'info_dict': {
            'id': '5ebdfbd4808e8b0040551a4c',
            'ext': 'mp4',
            'display_id': 'popeye-the-sailor',
            'description': 'md5:d3fcad5bd678b43428f93944b66c2752',
            'thumbnail': 'https://image.tmdb.org/t/p/original/r3SwiK3IANuAAvb1a0oShu8HKcV.jpg',
            'title': 'Barbecue for Two',
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
        }
    }]
    def _real_extract(self, url):
        sites_type, display_id = self._match_valid_url(url).group('sites_type', 'id')
        webpage = self._download_webpage(url, display_id)
        
        nextjs_json = self._search_nextjs_data(webpage, display_id)['props']['pageProps']
        
        media_json = self._download_json(
            f'https://play.provider.plex.tv/playQueues', display_id, 
            query={'uri': nextjs_json['metadataItem']['playableKey']}, data=''.encode(),
            headers={'X-PLEX-TOKEN': self._PLEX_TOKEN, 'Accept': 'application/json', 'Cookie': ''})
        #print(media_json)    
        selected_media = []
        for media in media_json['MediaContainer']['Metadata']:
            selected_media = traverse_obj(media, ('Media', ..., 'Part', ..., 'key'))
        #print(selected_media)
        formats, subtitles = self._get_formats_and_subtitles(selected_media, display_id, 'vod')
        self._sort_formats(formats)
        
        return {
            'id': nextjs_json['metadataItem']['playableID'],
            'display_id': display_id,
            'formats': formats,
            'subtitles': subtitles,
            'title': traverse_obj(nextjs_json, ('metadataItem', 'title')),
            'description': traverse_obj(nextjs_json, ('metadataItem', 'summary')),
            'thumbnail': traverse_obj(nextjs_json, ('metadataItem', 'thumb')),
            'duration': int_or_none(traverse_obj(nextjs_json, ('metadataItem', 'duration')), 1000),   
        }


class PlexWatchSeasonIE(PlexWatchBaseIE):
    _VALID_URL = r'https?://watch\.plex\.tv/show/(?P<season>[\w-]+)/season/(?P<season_num>\d+)'
    _TESTS =[{
        'url': 'https://watch.plex.tv/show/a-cooks-tour-2/season/1',
        'info_dict': {
            'id': '624c6b291e79c48d83a2b04e',
            'title': 'A Cook\'s Tour',
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
        
        webpage = self._download_webpage(url, season_name)
        nextjs_json = self._search_nextjs_data(webpage, season_name)['props']['pageProps']
        
        episode_list = traverse_obj(nextjs_json, ('episodes', ..., 'index'))
        return self.playlist_result(
            self._get_episode_result(episode_list, season_name, season_num),
            traverse_obj(nextjs_json, ('metadataItem', 'playableID')),
            traverse_obj(nextjs_json, ('metadataItem', 'parentTitle')),
            traverse_obj(nextjs_json, ('metadataItem', 'summary')))
 
class PlexWatchLive(PlexWatchBaseIE):
    _VALID_URL = r'https?://watch\.plex\.tv/live-tv/channel/(?P<id>[\w-]+)'
            
