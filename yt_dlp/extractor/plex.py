from .common import InfoExtractor
from ..utils import ExtractorError, determine_ext, traverse_obj


class PlexWatchIE(InfoExtractor):
    _VALID_URL = r'https?://watch\.plex\.tv/movie/(?P<id>[\w-]+)'
    _TESTS = [{
        'url': 'https://watch.plex.tv/movie/bowery-at-midnight',
        'info_dict': {
            'id': 'fixme',
            'ext': 'mp4',
        }
    }]
    
    def get_plex_token(self, client_id, display_id):
        # check token on the server, return hardcoded token if the api return error (typically HTTP 429) 
        required_token = self._download_json(
                'https://plex.tv/api/v2/users/anonymous', display_id, data=''.encode(), 
                headers={'X-Plex-Client-Identifier': client_id, 'Content-Type': 'application/json', 'Cookie': ''},
                note='Trying to get AuthToken', expected_status=429, fatal=False)
                
        return required_token.get('authToken') or 'NytaXzMexGQ9-xW9yDjy'
        
    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        
        nextjs_json = self._search_nextjs_data(webpage, display_id)['props']['pageProps']
        
        plex_token = self.get_plex_token(self._get_cookies(url).get("clientIdentifier").value, display_id)
        
        media_json = self._download_json(
            f'https://play.provider.plex.tv/playQueues', display_id, 
            query={'uri': nextjs_json['metadataItem']['playableKey']}, data=''.encode(),
            headers={'X-PLEX-TOKEN': plex_token, 'Accept': 'application/json', 'Cookie': ''})
        
        selected_media = []
        for media in media_json['MediaContainer']['Metadata']:
            if media.get('slug') == display_id:
                selected_media = traverse_obj(media, ('Media', ..., 'Part', ..., 'key'))
        
        formats, subtitles = [], {}
        for media in selected_media:
            if determine_ext(media) == 'm3u8':
                fmt, subs = self._extract_m3u8_formats_and_subtitles(
                    f'https://vod.provider.plex.tv{media}?X-PLEX-TOKEN={plex_token}', display_id)
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
            
        }
        
        