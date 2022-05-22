from .common import InfoExtractor
from ..utils import (
    traverse_obj,
    ExtractorError,
)

class NetverseIE(InfoExtractor):
    _VALID_URL = r'https://www\.netverse\.id/(?P<type>watch|live)/(?P<display_id>[^/?#&]+)'
    _TEST = {
        'url' : 'https://www.netverse.id/watch/waktu-indonesia-bercanda-edisi-spesial-lebaran-2016',
        'info_dict' : {
            "access_id" : "k4yhqUwINAGtmHx3NkL",
            "id" : "x82urb7",
            # "title" : "Waktu Indonesia Bercanda Edisi Spesial Lebaran",
            "title" : "Waktu Indonesia Bercanda - Edisi Spesial Lebaran 2016",
            "ext" : "mp4",
            }
        }
    
    def get_required_json(self, url):
        match = self._match_valid_url(url).groupdict()
        display_id, video_type = match["display_id"], match["type"]
        media_api_url = f"https://api.netverse.id/medias/api/v2/watchvideo/{display_id}"

        return self._download_json(media_api_url, display_id)

    def _real_extract(self, url):
        video_json = self.get_required_json(url)

        title = traverse_obj(video_json, ("response", "videos", "title"))
        video_url = traverse_obj(video_json, ("response", "videos", "dailymotion_url"))
        # actually the video itself in daily motion, but in private
        # Maybe need to refactor
        access_id = video_url.split("/")[-1]

        video_metadata_api_url = f"https://www.dailymotion.com/player/metadata/video/{access_id}"
        required_query = {
            "embedder" : "https://www.netverse.id"
        }
        real_video_json = self._download_json(video_metadata_api_url,access_id, query = required_query)
        # print(real_video_json)
        video_id = real_video_json.get('id')
        
        # For m3u8 
        m3u8_file = traverse_obj(real_video_json, ("qualities","auto"))

        for format in m3u8_file:
            video_url = format.get("url")
            self.video_format = self._extract_m3u8_formats(video_url, video_id = video_id)

    
        self._sort_formats(self.video_format)
        return {
            "id" : video_id,
            "access_id" : access_id,
            "formats" : self.video_format,
            "title" : title,

        }


        


