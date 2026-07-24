import re

from .common import InfoExtractor
from ..utils import (
    clean_html,
    compat_HTMLParseError,
    extract_attributes,
    get_element_by_attribute,
    get_element_by_class,
    get_element_html_by_class,
    get_element_text_and_html_by_tag,
    get_elements_by_class,
    get_elements_html_by_class,
    smuggle_url,
    unsmuggle_url,
)


def get_elements_by_tag(tag, html):
    while True:
        try:
            _, element = get_element_text_and_html_by_tag(tag, html)
            yield element
            html = html[html.index(element) + len(element):]
        except compat_HTMLParseError:
            return


class FenomioStreamIE(InfoExtractor):
    _FENOMIOSTREAM_INSTANCES = [
        # CUNI
        r'medicalmedia\.eu',
        r'pilot\.cuni\.fenomio\.stream',
        r'ua\.stream\.cuni\.cz',
        r'media\.fhs\.cuni\.cz',
        r'stream\.ims\.fsv\.cuni\.cz',
        r'video\.czp\.cuni\.cz',
        r'stream\.knihovna\.cuni\.cz',
        r'media\.ftvs\.cuni\.cz',
        r'stream\.cuni\.cz',
        r'pedmedia\.cuni\.cz',
        # AMU
        r'media\.amu\.cz',
        r'media\.test\.amu\.cz',
    ]
    _VALID_URL = r'^https://(?P<domain>(www\.)?({}))/(?P<lang>..)/media/(?P<id1>[0-9a-f]{{32}})(/(?P<id2>[0-9a-f]{{32}}))?'.format('|'.join(_FENOMIOSTREAM_INSTANCES))
    _TESTS = [{
        'url': 'https://stream.cuni.cz/en/media/c382f68514e24fa28d768f5c0997f757',
        'md5': '2049d066e009461c996020b25af218bd',
        'info_dict': {
            'id': 'c382f68514e24fa28d768f5c0997f757',
            'title': 'S03/E06 - Searching For Open Access Works',
            'creators': ['Milan Janíček', 'Zuza Wiorogórska'],
            'ext': 'mp4',
            'description': 'This session is a workshop whose goal is to help you doing your literature search in an open environment. We will present different search tools and show you how to use them. This training include practice time to allow you to search open access literature in your field.',
            'tags': ['open access', 'publications'],
            'license': 'CC BY 4.0',
            'thumbnail': 'https://stream.cuni.cz/shared/mediasnapshots/c3/c382f68514e24fa28d768f5c0997f757.jpg',
        },
    }, {
        'url': 'https://stream.knihovna.cuni.cz/cs/media/97c4c1f43ac946bf9fed1fb166e0ae6d',
        'md5': 'b4d3bd95926e86e1e9115675b9bd4c0c',
        'info_dict': {
            'id': '97c4c1f43ac946bf9fed1fb166e0ae6d',
            'ext': 'mp4',
            'tags': [],
            'creators': ['Jaroslav Pěnička'],
            'title': 'Jak nahrát video',
            'description': 'Jak nahrát video',
            'thumbnail': 'https://stream.knihovna.cuni.cz/shared/mediasnapshots/97/97c4c1f43ac946bf9fed1fb166e0ae6d.jpg',
        },
    }]

    def _real_extract(self, url):
        url, smuggled_data = unsmuggle_url(url)

        match = self._match_valid_url(url)
        domain = match.group('domain')
        lang = match.group('lang')
        id1 = match.group('id1')
        id2 = match.group('id2')
        webpage = self._download_webpage(url, id1)

        info_container = get_element_by_class('video-description-container', webpage)
        if not info_container:
            alert = get_element_by_class('alert-danger', webpage) or ''
            alert = get_element_by_class('m-0', alert) or 'Unknown error'
            alert = clean_html(alert)
            self.raise_login_required(alert)

        info = get_element_by_attribute('data-bind', 'visible: expandDescription()', info_container) or ''
        info_ps = list(get_elements_by_tag('p', info)) + [''] * 9

        title = self._html_search_regex(r'<h3>(.+)</h3>', info_container, 'title', flags=re.DOTALL, fatal=False)
        creators = [x.strip() for x in clean_html(info_ps[0]).split(';')]
        description = clean_html(info_ps[1])
        license_name = clean_html(info_ps[2]) or None
        tags = get_elements_by_class('tag', info)

        source_url = self._html_search_regex([r'<source[^>]+src="([^"]+)"', r'self.videoUrl *= *\'([^\']+)\''], webpage, 'source', fatal=True)

        playlist_info = get_element_html_by_class('video-playlist', webpage)
        video_id = id1
        if playlist_info:
            playlist_title = self._html_search_regex(r'<h4>.+Playlist ([^<]+)</h4>', playlist_info, 'playlist title', fatal=False)
            playlist_id = id1
            video_id = id2
            if self._yes_playlist(playlist_id, video_id, smuggled_data=smuggled_data, playlist_label=playlist_title, video_label=title):
                return {
                    '_type': 'playlist',
                    'id': playlist_id,
                    'title': playlist_title,
                    'entries': [
                        {
                            '_type': 'url',
                            'title': clean_html(playlist_item),
                            'url': smuggle_url('https://{}/{}{}'.format(domain, lang, extract_attributes(playlist_item)['href']), {'force_noplaylist': True}),
                            'ie_key': self.ie_key(),
                        }
                        for playlist_item in get_elements_html_by_class('playlist-item', playlist_info)
                    ],
                }
        formats, subtitles = self._extract_m3u8_formats_and_subtitles(source_url, video_id)

        return {
            'formats': formats,
            'subtitles': subtitles,
            'id': video_id,
            'title': title,
            'creators': creators,
            'description': description,
            'tags': tags,
            'license': license_name,
            'thumbnail': f'https://{domain}/shared/mediasnapshots/{video_id[:2]}/{video_id}.jpg',
        }
