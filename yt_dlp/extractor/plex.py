from .common import InfoExtractor
from ..utils import determine_ext, traverse_obj


class PlexWatchIE(InfoExtractor):
    _VALID_URL = r'https?://watch\.plex\.tv/movie/(?P<id>[\w-]+)'
    _TESTS = [{
        'url': 'https://watch.plex.tv/movie/bowery-at-midnight',
        'info_dict': {
            'id': 'fixme',
            'ext': 'mp4',
        }
    }]
    
    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        
        # btw, we can use _next/<hex> to get the same json
        nextjs_json = self._search_nextjs_data(webpage, display_id)['props']['pageProps']
        
        # # should POST method, this method apply api rate limit, so don't use this too much
        # # should return authToken
        # required_token = self._download_json(
            # 'https://plex.tv/api/v2/users/anonymous', display_id, data=''.encode())
        
        plex_token = 'NytaXzMexGQ9-xW9yDjy' #or required_token['authToken']
        
        # should POST method with empty request body
        # this requests need X-PLEX-TOKEN to defined in the header
        media_json = self._download_json(
            f'https://play.provider.plex.tv/playQueues', display_id, 
            query={'uri': nextjs_json['metadataItem']['playableKey']}, data=''.encode(),
            headers={'X-PLEX-TOKEN': plex_token, 'Accept': 'application/json'})
        
        selected_media = None
        for media in media_json['MediaContainer']['Metadata']:
            if media.get('slug') == display_id:
                selected_media = traverse_obj(media, ('Media', ..., 'Part', ..., 'key'))
        print(selected_media)
        
        formats, subtitles = [], {}
        for media in selected_media:
            if determine_ext(media) == 'm3u8':
                fmt, subs = self._extract_m3u8_formats_and_subtitles(
                    f'{media}?X-PLEX-TOKEN={plex_token}', display_id)
                formats.extend(fmt)
                self._merge_subtitles(subs, target=subtitles)
                
            elif determine_ext(media) == 'mpd':
                fmt, subs = self._extract_mpd_formats_and_subtitles(
                    f'{media}?X-PLEX-TOKEN={plex_token}', display_id)
                formats.extend(fmt)
                self._merge_subtitles(subs, target=subtitles)
        
        self._sort_formats(formats)
        
        