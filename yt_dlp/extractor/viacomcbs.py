from yt_dlp.utils.traversal import traverse_obj

from .common import InfoExtractor


class ViacomcbsIE(InfoExtractor):

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        mgid = self._html_search_regex(r'\"videoServiceUrl\":.*(mgid[\w:\.\-]+).*mica.*json', webpage, 'mgid')
        title = self._html_search_regex(r'\"shortTitle\":\"([\w\s]+)\"', webpage, 'title')

        formats, subtitles = self._extract_m3u8_formats_and_subtitles(self._get_video_url(mgid, video_id), video_id)

        return {
            'id': video_id,
            'title': title,
            'description': self._og_search_description(webpage),
            'formats': formats,
            'subtitles': subtitles,
        }

    def _get_video_url(self, mgid, video_id):
        config = self._download_json(
            f'https://topaz.viacomcbs.digital/topaz/api/{mgid}/mica.json?clientPlatform=desktop', video_id)
        return traverse_obj(config, ('stitchedstream', 'source'))
