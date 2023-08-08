from .common import InfoExtractor


class MagentaMusikIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?magentamusik\.de/(?P<id>.*)'

    _TESTS = [{
        'url': 'https://www.magentamusik.de/marty-friedman-woa-2023-9208205928595409235',
        'md5': 'd82dd4748f55fc91957094546aaf8584',
        'info_dict': {
            'id': '9208205928595409235',
            'ext': 'mp4',
            'title': 'Marty Friedman: W:O:A 2023',
            'duration': 2760
        }
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        video_id = self._html_search_regex(r'"assetId":"[^\d]+([0-9]+)"', webpage, 'video_id')

        json = self._download_json("https://wcps.t-online.de/cvss/magentamusic/vodplayer/v3/player/58935/%s/Main%%20Movie" % video_id, video_id)
      
        xml_url = json['content']['feature']['representations'][0]['contentPackages'][0]['media']['href']
        metadata = json['content']['feature'].get('metadata')
        title = None
        description = None
        if metadata:
            title = metadata.get('title')
            duration = metadata.get('runtimeInSeconds')
           

        xml = self._download_xml(xml_url, video_id)
        final_url = xml[0][0][0].attrib['src']

        formats = self._extract_m3u8_formats(
            final_url, video_id, ext='mp4')

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
            'duration': duration
        }
