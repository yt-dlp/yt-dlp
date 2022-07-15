from .common import InfoExtractor
from ..utils import ExtractorError, determine_ext, int_or_none, traverse_obj


class PlexWatchIE(InfoExtractor):
    _VALID_URL = r'https?://watch\.plex\.tv/(?:\w+/)?(?:country/\w+/)?(?:\w+)/(?P<id>[\w-]+)[?/#&]?'
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
    
    _PLEX_TOKEN = 'NytaXzMexGQ9-xW9yDjy' # change this if not work
    
    def _real_extract(self, url):
        display_id = self._match_id(url)
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
        
        formats, subtitles = [], {}
        for media in selected_media:
            if determine_ext(media) == 'm3u8':
                fmt, subs = self._extract_m3u8_formats_and_subtitles(
                    f'https://vod.provider.plex.tv{media}?X-PLEX-TOKEN={self._PLEX_TOKEN}', display_id)
                formats.extend(fmt)
                self._merge_subtitles(subs, target=subtitles)
                
            # elif determine_ext(media) == 'mpd':
                # fmt, subs = self._extract_mpd_formats_and_subtitles(
                    # f'https://vod.provider.plex.tv/{media}?X-PLEX-TOKEN={plex_token}', display_id)
                # formats.extend(fmt)
                # self._merge_subtitles(subs, target=subtitles)
        
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
        
        