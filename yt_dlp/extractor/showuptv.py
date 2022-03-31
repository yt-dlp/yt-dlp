# coding: utf-8
from .common import InfoExtractor


class ShowupTvIE(InfoExtractor):
    IE_NAME = 'showup.tv'
    _VALID_URL = r"https?://(?:www\.)?showup\.tv/(?P<id>.+)"

    _TESTS = [{
        "url": "https://showup.tv/username",
        "info_dict": {
            "id": '74a3b99f18d933e74da387d9b8df91fd',
            "ext": "mp4",
            'live_status': 'is_live',
            'url': r're:^rtmp://.*\.showup\.tv:1935/webrtc/[a-z0-9]{32}_aac$',
            'title': r're:username \d{4}-\d{2}-\d{1,2} \d{1,2}:\d{1,2}',
        },
        "skip": "Website content changes dynamically, depending which users are online and available for download/streaming, replace username with proper user and id with streamID",
    }]

    def _real_extract(self, url):
        uploader_id = self._match_id(url)

        self._set_cookie("showup.tv", "accept_rules", "true")
        webpage = self._download_webpage(url, uploader_id)

        stream_id = self._html_search_regex(r"player\.streamID = '(.*?)'", webpage, "stream_id")
        server_url = self._html_search_regex(r"player\.transcoderAddr = '(.*?)'", webpage, "server_url")
        rtmp_url = "rtmp://%s:1935/webrtc/%s_aac" % (server_url, stream_id)

        return {
            "id": stream_id,
            "title": uploader_id,
            "url": rtmp_url,
            "ext": "mp4",
            'is_live': True,
        }
