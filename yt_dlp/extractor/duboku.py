import base64
import re
import urllib.parse

from .common import InfoExtractor
from ..compat import compat_urlparse
from ..utils import (
    ExtractorError,
    clean_html,
    extract_attributes,
    get_elements_by_class,
    int_or_none,
    js_to_json,
    smuggle_url,
    unescapeHTML,
)


def _get_elements_by_tag_and_attrib(html, tag=None, attribute=None, value=None, escape_value=True):
    """Return the content of the tag with the specified attribute in the passed HTML document"""

    if tag is None:
        tag = '[a-zA-Z0-9:._-]+'
    if attribute is None:
        attribute = ''
    else:
        attribute = r'\s+(?P<attribute>%s)' % re.escape(attribute)
    if value is None:
        value = ''
    else:
        value = re.escape(value) if escape_value else value
        value = '=[\'"]?(?P<value>%s)[\'"]?' % value

    retlist = []
    for m in re.finditer(r'''(?xs)
        <(?P<tag>%s)
         (?:\s+[a-zA-Z0-9:._-]+(?:=[a-zA-Z0-9:._-]*|="[^"]*"|='[^']*'|))*?
         %s%s
         (?:\s+[a-zA-Z0-9:._-]+(?:=[a-zA-Z0-9:._-]*|="[^"]*"|='[^']*'|))*?
        \s*>
        (?P<content>.*?)
        </\1>
    ''' % (tag, attribute, value), html):
        retlist.append(m)

    return retlist


def _get_element_by_tag_and_attrib(html, tag=None, attribute=None, value=None, escape_value=True):
    retval = _get_elements_by_tag_and_attrib(html, tag, attribute, value, escape_value)
    return retval[0] if retval else None


class DubokuIE(InfoExtractor):
    IE_NAME = 'duboku'
    IE_DESC = 'www.duboku.io'

    _VALID_URL = r'(?:https?://[^/]+\.duboku\.io/vodplay/)(?P<id>[0-9]+-[0-9-]+)\.html.*'
    _TESTS = [{
        'url': 'https://w.duboku.io/vodplay/1575-1-1.html',
        'info_dict': {
            'id': '1575-1-1',
            'ext': 'mp4',
            'series': '白色月光',
            'title': 'contains:白色月光',
            'season_number': 1,
            'episode_number': 1,
            'season': 'Season 1',
            'episode_id': '1',
            'season_id': '1',
            'episode': 'Episode 1',
        },
        'params': {
            'skip_download': 'm3u8 download',
        },
    }, {
        'url': 'https://w.duboku.io/vodplay/1588-1-1.html',
        'info_dict': {
            'id': '1588-1-1',
            'ext': 'mp4',
            'series': '亲爱的自己',
            'title': 'contains:第1集',
            'season_number': 1,
            'episode_number': 1,
            'episode': 'Episode 1',
            'season': 'Season 1',
            'episode_id': '1',
            'season_id': '1',
        },
        'params': {
            'skip_download': 'm3u8 download',
        },
    }]

    _PLAYER_DATA_PATTERN = r'player_data\s*=\s*(\{\s*(.*)})\s*;?\s*</script'

    def _real_extract(self, url):
        video_id = self._match_id(url)
        temp = video_id.split('-')
        series_id = temp[0]
        season_id = temp[1]
        episode_id = temp[2]

        webpage_url = 'https://w.duboku.io/vodplay/%s.html' % video_id
        webpage_html = self._download_webpage(webpage_url, video_id)

        # extract video url

        player_data = self._search_regex(
            self._PLAYER_DATA_PATTERN, webpage_html, 'player_data')
        player_data = self._parse_json(player_data, video_id, js_to_json)

        # extract title

        temp = get_elements_by_class('title', webpage_html)
        series_title = None
        title = None
        for html in temp:
            mobj = re.search(r'<a\s+.*>(.*)</a>', html)
            if mobj:
                href = extract_attributes(mobj.group(0)).get('href')
                if href:
                    mobj1 = re.search(r'/(\d+)\.html', href)
                    if mobj1 and mobj1.group(1) == series_id:
                        series_title = clean_html(mobj.group(0))
                        series_title = re.sub(r'[\s\r\n\t]+', ' ', series_title)
                        title = clean_html(html)
                        title = re.sub(r'[\s\r\n\t]+', ' ', title)
                        break

        data_url = player_data.get('url')
        if not data_url:
            raise ExtractorError('Cannot find url in player_data')
        player_encrypt = player_data.get('encrypt')
        if player_encrypt == 1:
            data_url = urllib.parse.unquote(data_url)
        elif player_encrypt == 2:
            data_url = urllib.parse.unquote(base64.b64decode(data_url).decode('ascii'))

        # if it is an embedded iframe, maybe it's an external source
        headers = {'Referer': webpage_url}
        if player_data.get('from') == 'iframe':
            # use _type url_transparent to retain the meaningful details
            # of the video.
            return {
                '_type': 'url_transparent',
                'url': smuggle_url(data_url, {'referer': webpage_url}),
                'id': video_id,
                'title': title,
                'series': series_title,
                'season_number': int_or_none(season_id),
                'season_id': season_id,
                'episode_number': int_or_none(episode_id),
                'episode_id': episode_id,
            }

        formats = self._extract_m3u8_formats(data_url, video_id, 'mp4', headers=headers)

        return {
            'id': video_id,
            'title': title,
            'series': series_title,
            'season_number': int_or_none(season_id),
            'season_id': season_id,
            'episode_number': int_or_none(episode_id),
            'episode_id': episode_id,
            'formats': formats,
            'http_headers': headers
        }


class DubokuPlaylistIE(InfoExtractor):
    IE_NAME = 'duboku:list'
    IE_DESC = 'www.duboku.io entire series'

    _VALID_URL = r'(?:https?://[^/]+\.duboku\.io/voddetail/)(?P<id>[0-9]+)\.html.*'
    _TESTS = [{
        'url': 'https://w.duboku.io/voddetail/1575.html',
        'info_dict': {
            'id': 'startswith:1575',
            'title': '白色月光',
        },
        'playlist_count': 12,
    }, {
        'url': 'https://w.duboku.io/voddetail/1554.html',
        'info_dict': {
            'id': 'startswith:1554',
            'title': '以家人之名',
        },
        'playlist_mincount': 30,
    }]

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        if mobj is None:
            raise ExtractorError('Invalid URL: %s' % url)
        series_id = mobj.group('id')
        fragment = compat_urlparse.urlparse(url).fragment

        webpage_url = 'https://w.duboku.io/voddetail/%s.html' % series_id
        webpage_html = self._download_webpage(webpage_url, series_id)

        # extract title

        title = _get_element_by_tag_and_attrib(webpage_html, 'h1', 'class', 'title')
        title = unescapeHTML(title.group('content')) if title else None
        if not title:
            title = self._html_search_meta('keywords', webpage_html)
        if not title:
            title = _get_element_by_tag_and_attrib(webpage_html, 'title')
            title = unescapeHTML(title.group('content')) if title else None

        # extract playlists

        playlists = {}
        for div in _get_elements_by_tag_and_attrib(
                webpage_html, attribute='id', value='playlist\\d+', escape_value=False):
            playlist_id = div.group('value')
            playlist = []
            for a in _get_elements_by_tag_and_attrib(
                    div.group('content'), 'a', 'href', value='[^\'"]+?', escape_value=False):
                playlist.append({
                    'href': unescapeHTML(a.group('value')),
                    'title': unescapeHTML(a.group('content'))
                })
            playlists[playlist_id] = playlist

        # select the specified playlist if url fragment exists
        playlist = None
        playlist_id = None
        if fragment:
            playlist = playlists.get(fragment)
            playlist_id = fragment
        else:
            first = next(iter(playlists.items()), None)
            if first:
                (playlist_id, playlist) = first
        if not playlist:
            raise ExtractorError(
                'Cannot find %s' % fragment if fragment else 'Cannot extract playlist')

        # return url results
        return self.playlist_result([
            self.url_result(
                compat_urlparse.urljoin('https://w.duboku.io', x['href']),
                ie=DubokuIE.ie_key(), video_title=x.get('title'))
            for x in playlist], series_id + '#' + playlist_id, title)
