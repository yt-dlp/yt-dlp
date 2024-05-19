from .common import InfoExtractor
from ..utils import (
    int_or_none,
    find_xpath_attr,
    xpath_text,
    update_url_query,
)
from ..compat import compat_urllib_parse_unquote


class NozIE(InfoExtractor):
    _WORKING = False
    _VALID_URL = r'https?://(?:www\.)?noz\.de/video/(?P<id>[0-9]+)/'
    _TESTS = [{
        'url': 'http://www.noz.de/video/25151/32-Deutschland-gewinnt-Badminton-Lnderspiel-in-Melle',
        'info_dict': {
            'id': '25151',
            'ext': 'mp4',
            'duration': 215,
            'title': '3:2 - Deutschland gewinnt Badminton-Länderspiel in Melle',
            'description': 'Vor rund 370 Zuschauern gewinnt die deutsche Badminton-Nationalmannschaft am Donnerstag ein EM-Vorbereitungsspiel gegen Frankreich in Melle. Video Moritz Frankenberg.',
            'thumbnail': r're:^http://.*\.jpg',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        description = self._og_search_description(webpage)

        edge_url = self._html_search_regex(
            r'<script\s+(?:type="text/javascript"\s+)?src="(.*?/videojs_.*?)"',
            webpage, 'edge URL')
        edge_content = self._download_webpage(edge_url, 'meta configuration')

        config_url_encoded = self._search_regex(
            r'so\.addVariable\("config_url","[^,]*,(.*?)"',
            edge_content, 'config URL'
        )
        config_url = compat_urllib_parse_unquote(config_url_encoded)

        doc = self._download_xml(config_url, 'video configuration')
        title = xpath_text(doc, './/title')
        thumbnail = xpath_text(doc, './/article/thumbnail/url')
        duration = int_or_none(xpath_text(
            doc, './/article/movie/file/duration'))
        formats = []
        for qnode in doc.findall('.//article/movie/file/qualities/qual'):
            http_url_ele = find_xpath_attr(
                qnode, './html_urls/video_url', 'format', 'video/mp4')
            http_url = http_url_ele.text if http_url_ele is not None else None
            if http_url:
                formats.append({
                    'url': http_url,
                    'format_name': xpath_text(qnode, './name'),
                    'format_id': '%s-%s' % ('http', xpath_text(qnode, './id')),
                    'height': int_or_none(xpath_text(qnode, './height')),
                    'width': int_or_none(xpath_text(qnode, './width')),
                    'tbr': int_or_none(xpath_text(qnode, './bitrate'), scale=1000),
                })
            else:
                f4m_url = xpath_text(qnode, 'url_hd2')
                if f4m_url:
                    formats.extend(self._extract_f4m_formats(
                        update_url_query(f4m_url, {'hdcore': '3.4.0'}),
                        video_id, f4m_id='hds', fatal=False))
                m3u8_url_ele = find_xpath_attr(
                    qnode, './html_urls/video_url',
                    'format', 'application/vnd.apple.mpegurl')
                m3u8_url = m3u8_url_ele.text if m3u8_url_ele is not None else None
                if m3u8_url:
                    formats.extend(self._extract_m3u8_formats(
                        m3u8_url, video_id, 'mp4', 'm3u8_native',
                        m3u8_id='hls', fatal=False))

        return {
            'id': video_id,
            'formats': formats,
            'title': title,
            'duration': duration,
            'description': description,
            'thumbnail': thumbnail,
        }
