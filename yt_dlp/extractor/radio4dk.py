from .common import InfoExtractor
from ..utils import (
    extract_attributes,
    get_element_html_by_attribute,
    get_element_html_by_class,
    get_elements_html_by_class,
    unescapeHTML,
    unified_strdate,
)


class Radio4DkIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?radio4\.dk/program/[^/]+/?\?[^#]*\bgid=(?P<id>\d+)\b'

    _TESTS = [{
        'url': 'https://www.radio4.dk/program/morgen-r4dio/?gid=37214&title=radio4-morgen-13-juni-kl-6-7',
        'md5': 'a53588d3a53635495e5a47b133128d9e',
        'info_dict': {
            'id': '37214',
            'title': 'Radio4 Morgen - 13. juni kl. 6-7',
            'ext': 'mp3',
            'release_date': '20220613',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        details_attibutes = extract_attributes(get_element_html_by_attribute('data-gid', video_id, webpage))
        url = details_attibutes['href']
        title = details_attibutes['data-title']
        date_episode_span_html = ""
        for date_episode_html in get_elements_html_by_class('date_title', webpage):
            # check each span for the correct gid
            gid_html = get_element_html_by_class('gid', date_episode_html)
            gid = self._search_regex('<span[^>]+>(\d+)</span>', gid_html, 'gid')
            if gid == video_id:
                date_episode_span_html = get_element_html_by_class('programDate ep_date_js', date_episode_html)
                break
        episode_date = self._search_regex('<span[^>]+>(.*)</span>', date_episode_span_html, 'episode date')
        return {
            'url': url,
            'id': video_id,
            'title': unescapeHTML(title),
            'release_date': unified_strdate(episode_date)
        }
