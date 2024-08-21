import re

from .common import InfoExtractor
from ..utils import (
    clean_html,
    extract_attributes,
    get_element_by_class,
    get_element_html_by_id,
    get_element_text_and_html_by_tag,
    parse_duration,
    strip_or_none,
    traverse_obj,
    try_call,
)


class ListenNotesIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?listennotes\.com(?:/\w+)?/podcasts/[^/]+/[^/]+-(?P<id>.+)/'
    _TESTS = [{
        'url': 'https://www.listennotes.com/podcasts/thriving-on-overload/tim-oreilly-on-noticing-KrDgvNb_u1n/',
        'md5': '5b91a32f841e5788fb82b72a1a8af7f7',
        'info_dict': {
            'id': 'KrDgvNb_u1n',
            'ext': 'mp3',
            'title': 'md5:32236591a921adf17bbdbf0441b6c0e9',
            'description': 'md5:397ca2eb42b6fb4083c4d3d3ebd568cd',
            'duration': 2215.0,
            'channel': 'Amplifying Cognition',
            'channel_id': 'ed84wITivxF',
            'episode_id': 'e1312583fa7b4e24acfbb5131050be00',
            'thumbnail': 'https://cdn-images-3.listennotes.com/podcasts/amplifying-cognition-ross-dawson-Iemft4Gdr0k-ed84wITivxF.300x300.jpg',
            'channel_url': 'https://www.listennotes.com/podcasts/amplifying-cognition-ross-dawson-ed84wITivxF/',
            'cast': ['Tim O’Reilly', 'Cookie Monster', 'Lao Tzu', 'Wallace Steven', 'Eric Raymond', 'Christine Peterson', 'John Maynard Keyne', 'Ross Dawson'],
        },
    }, {
        'url': 'https://www.listennotes.com/podcasts/ask-noah-show/episode-177-wireguard-with-lwEA3154JzG/',
        'md5': '62fb4ffe7fc525632a1138bf72a5ce53',
        'info_dict': {
            'id': 'lwEA3154JzG',
            'ext': 'mp3',
            'title': 'Episode 177: WireGuard with Jason Donenfeld',
            'description': 'md5:24744f36456a3e95f83c1193a3458594',
            'duration': 3861.0,
            'channel': 'Ask Noah Show',
            'channel_id': '4DQTzdS5-j7',
            'episode_id': '8c8954b95e0b4859ad1eecec8bf6d3a4',
            'channel_url': 'https://www.listennotes.com/podcasts/ask-noah-show-noah-j-chelliah-4DQTzdS5-j7/',
            'thumbnail': 'https://cdn-images-3.listennotes.com/podcasts/ask-noah-show-noah-j-chelliah-gD7vG150cxf-4DQTzdS5-j7.300x300.jpg',
            'cast': ['noah showlink', 'noah show', 'noah dashboard', 'jason donenfeld'],
        },
    }, {
        'url': 'https://www.listennotes.com/es/podcasts/cl%C3%ADmax/cl%C3%ADmax-11082024-pvezIxrZJ6U/',
        'md5': 'e0f3703b5036ebbaefd2d081c4e0716f',
        'info_dict': {
            'id': 'pvezIxrZJ6U',
            'ext': 'mp3',
            'title': 'md5:9e081c1685e13aa558d295ee09ba7a5b',
            'description': 'md5:d14d88387fc65fdc46fdd2ea47aa7a6c',
            'duration': 3600.0,
            'channel': 'Clímax',
            'channel_id': 'A5vWP_fxE37',
            'episode_id': '76ef936f8cf34fcab95e73a49e5b7926',
            'thumbnail': 'https://cdn-images-3.listennotes.com/podcasts/clímax-los40-Hz3YXx0kj8q-A5vWP_fxE37.300x300.jpg',
            'channel_url': 'https://www.listennotes.com/podcasts/clímax-los40-A5vWP_fxE37/',
            'cast': None,
        },
    }]

    def _clean_description(self, description):
        return clean_html(re.sub(r'(</?(div|p)>\s*)+', '<br/><br/>', description or ''))

    def _real_extract(self, url):
        audio_id = self._match_id(url)
        webpage = self._download_webpage(url, audio_id)
        data = self._search_json(
            r'<script id="original-content"[^>]+\btype="application/json">', webpage, 'content', audio_id)
        data.update(extract_attributes(get_element_html_by_id(
            r'episode-play-button-toolbar|episode-no-play-button-toolbar', webpage, escape_value=False)))

        duration, description = self._search_regex(
            r'(?P<duration>[\d:]+)\s*-\s*(?P<description>.+)',
            self._html_search_meta(['og:description', 'description', 'twitter:description'], webpage),
            'description', fatal=False, group=('duration', 'description')) or (None, None)

        return {
            'id': audio_id,
            'url': data['audio'],
            'title': (data.get('data-title')
                      or try_call(lambda: get_element_text_and_html_by_tag('h1', webpage)[0])
                      or self._html_search_meta(('og:title', 'title', 'twitter:title'), webpage, 'title')),
            'description': (self._clean_description(get_element_by_class('ln-text-p', webpage))
                            or strip_or_none(description)),
            'duration': parse_duration(traverse_obj(data, 'audio_length', 'data-duration') or duration),
            'episode_id': traverse_obj(data, 'uuid', 'data-episode-uuid'),
            **traverse_obj(data, {
                'thumbnail': 'data-image',
                'channel': 'data-channel-title',
                'cast': ('nlp_entities', ..., 'name'),
                'channel_url': 'channel_url',
                'channel_id': 'channel_short_uuid',
            }),
        }
