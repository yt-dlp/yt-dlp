from base64 import b64decode
from .common import InfoExtractor


class ClapDatIE(InfoExtractor):
    _VALID_URL = r"https?://(?:www\.)?clapdat\.com/video/(?P<id>.+)"
    _TESTS = [
        {
            "url": "https://www.clapdat.com/video/swedish-elin-table-fuck-mbqruzusw3",
            "md5": "44278ac7495ce68b9bea9c0566efa9b8",
            "info_dict": {
                "id": "mbqruzusw3",
                "url": "https://s2.clapdat.com/videos/2025/may/f0t52rh0nrnvwnbe78fq.mp4",
                "ext": "mp4",
                "title": "Swedish Elin table fuck",
                "description": "md5:d41d8cd98f00b204e9800998ecf8427e",
                "formats": 'count:1', 
                "uploader": "sweman",
                "age_limit": 18,
                "thumbnail": "https://x1.clapdat.com/images/2025/may/w1jlikst4ale7oz49bza.jpg"
            },
        }
    ]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        file_str = self.decode_file_string(self._html_search_regex(r'videoPage:{[^{]+file:"([^"]*)', webpage, "file"))
        file_domain = self._html_search_regex(r'videoPage:{[^{]+file_domain:"([^"]*)', webpage, "file_domain")
        return {
            "id": self._html_search_regex(r'videoPage:{[^{]*id:"([^"]*)', webpage, "id"),
            "title": self._html_search_regex(r'videoPage:{[^{]+title:"([^"]*)', webpage, "title",default=None),
            "thumbnail": self._html_search_regex(r'videoPage:{[^{]+image:"([^"]*)",', webpage, "thumbnail", default=None) + '.jpg',
            "description": self._html_search_regex(r'videoPage:{[^{]+description:"([^"]*)', webpage, "description",default=None),
            "formats": [
                {"url": f"https://{file_domain}/{file_str}", "ext": file_str.split(".")[-1]}
            ]            
            ,
            "uploader": self._html_search_regex(r'videoPage:{[^{]+uploader:"([^"]*)', webpage, "uploader",default=None),
            "age_limit": 18
        }

    def decode_file_string(self, b64str):
        b64str = b64str[0:19] + b64str[209:]
        return b64decode(b64str).decode()


