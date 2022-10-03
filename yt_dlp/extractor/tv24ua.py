import base64
import re
from urllib.parse import unquote

from .common import InfoExtractor
from ..utils import (
    determine_ext,
    extract_attributes,
    get_elements_html_by_class,
    js_to_json,
    mimetype2ext,
    smuggle_url,
    traverse_obj,
)


class TV24UAVideoIE(InfoExtractor):
    _VALID_URL = r'https?://24tv\.ua/news/showPlayer\.do.*?(?:\?|&)objectId=(?P<id>\d+)'
    _EMBED_REGEX = [rf'<iframe[^>]+?src=["\']?(?P<url>{_VALID_URL})["\']?']
    IE_NAME = '24tv.ua'
    _TESTS = [{
        'url': 'https://24tv.ua/news/showPlayer.do?objectId=2074790&videoUrl=2022/07/2074790&w=640&h=360',
        'info_dict': {
            'id': '2074790',
            'ext': 'mp4',
            'title': 'У Харкові ворожа ракета прилетіла в будинок, де слухали пісні про "офіцерів-росіян"',
            'thumbnail': r're:^https?://.*\.jpe?g',
        }
    }, {
        'url': 'https://24tv.ua/news/showPlayer.do?videoUrl=2022/07/2074790&objectId=2074790&w=640&h=360',
        'only_matching': True,
    }]

    _WEBPAGE_TESTS = [
        {
            # iframe embed created from share menu.
            'url': 'data:text/html,%3Ciframe%20src=%22https://24tv.ua/news/showPlayer.do?objectId=1886193&videoUrl'
                   '=2022/03/1886193&w=640&h=360%22%20width=%22640%22%20height=%22360%22%20frameborder=%220%22'
                   '%20scrolling=%22no%22%3E%3C/iframe%3E',
            'info_dict': {
                'id': '1886193',
                'ext': 'mp4',
                'title': 'Росіяни руйнують Бородянку на Київщині та стріляють з літаків по мешканцях: шокуючі фото',
                'thumbnail': r're:^https?://.*\.jpe?g',
            }
        },
        {
            'url': 'https://24tv.ua/vipalyuyut-nashi-mista-sela-dsns-pokazali-motoroshni-naslidki_n1883966',
            'info_dict': {
                'id': '1883966',
                'ext': 'mp4',
                'title': 'Випалюють наші міста та села, – моторошні наслідки обстрілів на Чернігівщині',
                'thumbnail': r're:^https?://.*\.jpe?g',
            },
            'params': {'allowed_extractors': ['Generic', '24tv.ua']},
        }
    ]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        formats = []
        subtitles = {}
        for j in re.findall(r'vPlayConfig\.sources\s*=\s*(?P<json>\[{\s*(?s:.+?)\s*}])', webpage):
            sources = self._parse_json(j, video_id, fatal=False, ignore_extra=True, transform_source=js_to_json, errnote='') or []
            for source in sources:
                if mimetype2ext(traverse_obj(source, 'type')) == 'm3u8':
                    f, s = self._extract_m3u8_formats_and_subtitles(source['src'], video_id)
                    formats.extend(f)
                    self._merge_subtitles(subtitles, s)
                else:
                    formats.append({
                        'url': source['src'],
                        'ext': determine_ext(source['src']),
                    })
        thumbnail = traverse_obj(
            self._search_json(
                r'var\s*vPlayConfig\s*=\s*', webpage, 'thumbnail',
                video_id, default=None, transform_source=js_to_json), 'poster')
        self._sort_formats(formats)
        return {
            'id': video_id,
            'formats': formats,
            'subtitles': subtitles,
            'thumbnail': thumbnail or self._og_search_thumbnail(webpage),
            'title': self._html_extract_title(webpage) or self._og_search_title(webpage),
            'description': self._og_search_description(webpage, default=None),
        }


class TV24UAGenericPassthroughIE(InfoExtractor):
    _VALID_URL = r'https?://(?:[a-zA-Z0-9]+?\.)?24tv\.ua/(?P<id>[^/]+?_n\d+)'

    _TESTS = [{
        # Generic iframe, not within media_embed
        'url': 'https://24tv.ua/vipalyuyut-nashi-mista-sela-dsns-pokazali-motoroshni-naslidki_n1883966',
        'info_dict': {
            'id': '1883966',
            'ext': 'mp4',
            'title': 'Випалюють наші міста та села, – моторошні наслідки обстрілів на Чернігівщині',
            'thumbnail': r're:^https?://.*\.jpe?g',
        }
    }, {
        # Generic iframe embed of TV24UAPlayerIE, within media_embed
        'url': 'https://24tv.ua/harkivyani-zgaduyut-misto-do-viyni-shhemlive-video_n1887584',
        'info_dict': {
            'id': 'harkivyani-zgaduyut-misto-do-viyni-shhemlive-video_n1887584',
            'title': 'Харків\'яни згадують місто до війни: щемливе відео'
        },
        'playlist': [{
            'info_dict': {
                'id': '1887584',
                'ext': 'mp4',
                'title': 'Харків\'яни згадують місто до війни: щемливе відео',
                'thumbnail': r're:^https?://.*\.jpe?g',
            },
        }]
    }, {
        # 2 media_embeds with YouTube iframes
        'url': 'https://24tv.ua/bronetransporteri-ozbroyenni-zsu-shho-vidomo-pro-bronovik-wolfhound_n2167966',
        'info_dict': {
            'id': 'bronetransporteri-ozbroyenni-zsu-shho-vidomo-pro-bronovik-wolfhound_n2167966',
            'title': 'Броньовик Wolfhound: гігант, який допомагає ЗСУ знищувати окупантів на фронті',
        },
        'playlist_count': 2
    }, {
        'url': 'https://men.24tv.ua/fitnes-bloger-sprobuvav-vikonati-trenuvannya-naysilnishoyi-lyudini_n2164538',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        data_urls = []
        # The site contains escaped iframe embeds within an attribute.
        # Once escaped, generic can handle them, so we use a data url to pass the escaped html back.
        for html in get_elements_html_by_class('media_embed', webpage):
            data = unquote(extract_attributes(html).get('data-html'))
            data_urls.append(f'data:text/html;base64,{base64.b64encode(data.encode("utf-8")).decode("utf-8")}')

        if not data_urls:
            return self.url_result(url, 'Generic')
        return self.playlist_from_matches(
            [smuggle_url(url, {'to_generic': True}) for url in data_urls], display_id, ie='Generic',
            playlist_title=self._og_search_title(webpage) or self._html_extract_title(webpage))
