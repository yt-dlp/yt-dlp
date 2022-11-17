import re
import urllib.parse

from .common import InfoExtractor
from ..utils import make_archive_id, unescapeHTML


class HTML5MediaEmbedIE(InfoExtractor):
    _VALID_URL = False
    IE_NAME = 'html5'
    _WEBPAGE_TESTS = [
        {
            'url': 'https://html.com/media/',
            'info_dict': {
                'title': 'HTML5 Media',
                'description': 'md5:933b2d02ceffe7a7a0f3c8326d91cc2a',
            },
            'playlist_count': 2
        }
    ]

    def _extract_from_webpage(self, url, webpage):
        video_id, title = self._generic_id(url), self._generic_title(url, webpage)
        entries = self._parse_html5_media_entries(url, webpage, video_id, m3u8_id='hls') or []
        for num, entry in enumerate(entries, start=1):
            entry.update({
                'id': f'{video_id}-{num}',
                'title': f'{title} ({num})',
                '_old_archive_ids': [
                    make_archive_id('generic', f'{video_id}-{num}' if len(entries) > 1 else video_id),
                ],
            })
            yield entry


class QuotedHTMLIE(InfoExtractor):
    """For common cases of quoted/escaped html parts in the webpage"""
    _VALID_URL = False
    IE_NAME = 'generic:quoted-html'
    IE_DESC = False  # Do not list
    _WEBPAGE_TESTS = [{
        # 2 YouTube embeds in data-html
        'url': 'https://24tv.ua/bronetransporteri-ozbroyenni-zsu-shho-vidomo-pro-bronovik-wolfhound_n2167966',
        'info_dict': {
            'id': 'bronetransporteri-ozbroyenni-zsu-shho-vidomo-pro-bronovik-wolfhound_n2167966',
            'title': 'Броньовик Wolfhound: гігант, який допомагає ЗСУ знищувати окупантів на фронті',
            'thumbnail': r're:^https?://.*\.jpe?g',
            'timestamp': float,
            'upload_date': str,
            'description': 'md5:6816e1e5a65304bd7898e4c7eb1b26f7',
            'age_limit': 0,
        },
        'playlist_count': 2
    }, {
        # Generic iframe embed of TV24UAPlayerIE within data-html
        'url': 'https://24tv.ua/harkivyani-zgaduyut-misto-do-viyni-shhemlive-video_n1887584',
        'info_dict': {
            'id': '1887584',
            'ext': 'mp4',
            'title': 'Харків\'яни згадують місто до війни: щемливе відео',
            'thumbnail': r're:^https?://.*\.jpe?g',
        },
        'params': {'skip_download': True}
    }, {
        # YouTube embeds on Squarespace (data-html): https://github.com/ytdl-org/youtube-dl/issues/21294
        'url': 'https://www.harvardballetcompany.org/past-productions',
        'info_dict': {
            'id': 'past-productions',
            'title': 'Productions — Harvard Ballet Company',
            'age_limit': 0,
            'description': 'Past Productions',
        },
        'playlist_mincount': 26
    }, {
        # Squarespace video embed, 2019-08-28, data-html
        'url': 'http://ootboxford.com',
        'info_dict': {
            'id': 'Tc7b_JGdZfw',
            'title': 'Out of the Blue, at Childish Things 10',
            'ext': 'mp4',
            'description': 'md5:a83d0026666cf5ee970f8bd1cfd69c7f',
            'uploader_id': 'helendouglashouse',
            'uploader': 'Helen & Douglas House',
            'upload_date': '20140328',
            'availability': 'public',
            'view_count': int,
            'channel': 'Helen & Douglas House',
            'comment_count': int,
            'uploader_url': 'http://www.youtube.com/user/helendouglashouse',
            'duration': 253,
            'channel_url': 'https://www.youtube.com/channel/UCTChGezrZVmlYlpMlkmulPA',
            'playable_in_embed': True,
            'age_limit': 0,
            'channel_follower_count': int,
            'channel_id': 'UCTChGezrZVmlYlpMlkmulPA',
            'tags': 'count:6',
            'categories': ['Nonprofits & Activism'],
            'like_count': int,
            'thumbnail': 'https://i.ytimg.com/vi/Tc7b_JGdZfw/hqdefault.jpg',
        },
        'params': {
            'skip_download': True,
        },
    }]

    def _extract_from_webpage(self, url, webpage):
        combined = ''
        for _, html in re.findall(r'(?s)\bdata-html=(["\'])((?:(?!\1).)+)\1', webpage):
            # unescapeHTML can handle &quot; etc., unquote can handle percent encoding
            unquoted_html = unescapeHTML(urllib.parse.unquote(html))
            if unquoted_html != html:
                combined += unquoted_html
        if combined:
            yield from self._extract_generic_embeds(url, combined)
