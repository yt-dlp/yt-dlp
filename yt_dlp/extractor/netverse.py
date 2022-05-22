from .common import InfoExtractor
from ..utils import (
    traverse_obj,
    ExtractorError,
)

class NetverseBaseIE(InfoExtractor):
    def get_required_json(self, url):
        match = self._match_valid_url(url).groupdict()
        display_id,  sites_type = match["display_id"], match["type"]

        if sites_type == "watch":
            media_api_url = f"https://api.netverse.id/medias/api/v2/watchvideo/{display_id}"
        
        elif sites_type == "webseries":
            media_api_url = f"https://api.netverse.id/medias/api/v2/webseries/{display_id}"
        

        return self._download_json(media_api_url, display_id)
    
    def get_access_id(self, dailymotion_url):
        return dailymotion_url.split("/")[-1]

    def _call_metadata_api_from_video_url(self, dailymotion_url):
        access_id = self.get_access_id(dailymotion_url)
        metadata_json = self._call_metadata_api(access_id)
        return access_id, metadata_json

    def _call_metadata_api(self, access_id, req_file_type = "video", query = None):
        video_metadata_api_url = f"https://www.dailymotion.com/player/metadata/{req_file_type}/{access_id}"

        if query == None:
            required_query = {
                "embedder" : "https://www.netverse.id"
            }
        else :
            required_query = query
        
        return self._download_json(video_metadata_api_url,access_id, query = required_query)
            

class NetverseIE(NetverseBaseIE):
    _VALID_URL = r'https://www\.netverse\.id/(?P<type>watch)/(?P<display_id>[^/?#&]+)'
    # Netverse Watch
    _TESTS = [{
        'url' : 'https://www.netverse.id/watch/waktu-indonesia-bercanda-edisi-spesial-lebaran-2016',
        # "only_matching" : True,
        'info_dict' : {
            "access_id" : "k4yhqUwINAGtmHx3NkL",
            "id" : "x82urb7",
            "title" : "Waktu Indonesia Bercanda - Edisi Spesial Lebaran 2016",
            "ext" : "mp4",
            "season" : "Season 2016",
            "description" : "Mau ketawa-tiwi sambil asah otak? Waktu Indonesia Bercanda jawabannya. Kemampuan logika kalian akan diuji oleh Cak Lontong di kuis-kuis yang bikin gemes. Siap-siap bercanda ya karena ini waktunya Indonesia Bercanda.",
            "thumbnail" : "https://vplayed-uat.s3-ap-southeast-1.amazonaws.com/images/webseries/thumbnails/2021/11/619cfce45c827.jpeg",
            "episode_number" : 22,
            "series" : "Waktu Indonesia Bercanda",
            "episode" : "Episode 22",}
        }, {
        # series
        "url" : "https://www.netverse.id/watch/jadoo-seorang-model",
        "info_dict" : {
            "id" : "x88izwc",
            "access_id" : "x88izwc",
            "title" : "Jadoo Seorang Model",
            "ext" : "mp4",
            "season" : "Season 2",
            "description" : "Kisah Jadoo yang cerdas dan penuh kasih bersama keluarga dan teman-teman membuat pemirsa tertawa terbahak-bahak.",
            "thumbnail" : "https://storage.googleapis.com/netprime-live/images/webseries/thumbnails/2021/11/619cf63f105d3.jpeg",
            "episode_number" : 2,
            "series" : "Hello Jadoo",
            "episode" : "Episode 2",}
        }]
    
    def _real_extract(self, url):
        program_json = self.get_required_json(url)

        videos = traverse_obj(program_json,("response","videos"))

        title = videos.get("title")
        video_url = videos.get("dailymotion_url")
        season_name = videos.get("season_name")
        episode_order = videos.get("episode_order")

        program_detail = videos.get("program_detail")
        series_name = program_detail.get("title")
        description = program_detail.get("description")
        thumbnail_image = program_detail.get("thumbnail_image")

        # actually the video itself in daily motion, but in private
        # Maybe need to refactor
        access_id, real_video_json = self._call_metadata_api_from_video_url(video_url)
    
        video_id = real_video_json.get('id')
        
        # For m3u8 
        m3u8_file = traverse_obj(real_video_json, ("qualities","auto"))

        for format in m3u8_file:
            video_url = format.get("url")
            if video_url is None:
                continue
            self.video_format = self._extract_m3u8_formats(video_url, video_id = video_id)

        episode = None
        if episode == None:
            episode = f"Episode {episode_order}"

        self._sort_formats(self.video_format)
        return {
            "id" : video_id,
            "access_id" : access_id,
            "formats" : self.video_format,
            "title" : title,
            "season" : season_name,
            "thumbnail" : thumbnail_image,
            "description" : description,
            "episode_number" : episode_order,
            "series" : series_name,
            "episode" : episode,

        }

class NetverseVideoIE(NetverseBaseIE):
    _VALID_URL = r'https://www\.netverse\.id/(?P<type>video)/(?P<display_id>[^/?#&]+)'
    _TEST = {
        "url" : "https://www.netverse.id/video/pg067482-hellojadoo-season1"
    }
    def _real_extract(self, url):
        program_json = self.get_required_json(url)

        video = traverse_obj(program_json,("response","video_info"))

        title = video.get("title")
        description = video.get("description")
        video_url = video.get("dailymotion_url")
        season_name = video.get("season_name")
        episode_order = video.get("episode_order")

        program_detail = video.get("program_detail")
        series_name = program_detail.get("title")
        thumbnail_image = video.get("thumbnail_image")

        # actually the video itself in daily motion, but in private
        # Maybe need to refactor
        access_id, real_video_json = self._call_metadata_api_from_video_url(video_url)
        video_id = real_video_json.get('id')
        
        # For m3u8 
        m3u8_file = traverse_obj(real_video_json, ("qualities","auto"))

        for format in m3u8_file:
            video_url = format.get("url")
            if video_url is None:
                continue
            self.video_format = self._extract_m3u8_formats(video_url, video_id = video_id)

    
        self._sort_formats(self.video_format)
        return {
            "id" : video_id,
            "access_id" : access_id,
            "formats" : self.video_format,
            "title" : title,
            "season" : season_name,
            "thumbnail" : thumbnail_image,
            "description" : description,
            "episode_number" : episode_order,
            "series" : series_name,

        }

class NetversePlaylistIE(NetverseBaseIE):
    _VALID_URL = r'https://www\.netverse\.id/(?P<type>webseries)/(?P<display_id>[^/?#&]+)'

    def _real_extract(self, url):
        playlist_data = self.get_required_json(url)

        webseries_info = traverse_obj(playlist_data,("response", "webseries_info"))

        series_name = webseries_info.get("title")

        videos = traverse_obj(webseries_info, ("related", "data"))

        for video in videos :
            pass
        
        return {
            "_type" : "playlist"
        }




