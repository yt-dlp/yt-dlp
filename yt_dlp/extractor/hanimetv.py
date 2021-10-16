from __future__ import unicode_literals
from .common import InfoExtractor
from ..utils import (
    clean_html,
    int_or_none,
    str_or_none,
    try_get
)

from ..compat import (
    compat_str
)
import re


class HanimetvBaseIE(InfoExtractor):
    _VALID_URL = r'https?://(?P<host>(?:www\.)?(?:members\.)?hanime\.tv)/videos/hentai/(?P<id>[a-zA-Z0-9-]+$)'
    _TESTS = [{
        'url': 'https://hanime.tv/videos/hentai/enjo-kouhai-1',
        'md5': 'a3a08ac2180ed75ee731aff92d16f447',
        'info_dict': {
            'id': 'enjo-kouhai-1',
            'ext': 'mp4',
            'title': 'Enjo Kouhai 1',
            'age_limit': 18,
            'upload_date': '20200130',
            'description': 'md5:81b00795abd5ffa50a2e463ea321886e',
            'timestamp': 1580398865,
        }
    }, {
        'url': 'https://hanime.tv/videos/hentai/enjo-kouhai-2',
        'md5': '5fad67745e1ba911c041031d9e1ce2a7',
        'info_dict': {
            'id': 'enjo-kouhai-2',
            'ext': 'mp4',
            'title': 'Enjo Kouhai 2',
            'age_limit': 18,
            'upload_date': '20200228',
            'description': 'md5:5277f19882544683e698b91f9e2634e3',
            'timestamp': 1582850492,
        }
    }, {
        'url': 'https://hanime.tv/videos/hentai/enjo-kouhai-3',
        'md5': 'a3a08ac2180ed75ee731aff92d16f447',
        'info_dict': {
            'id': 'enjo-kouhai-3',
            'ext': 'mp4',
            'title': 'Enjo Kouhai 3',
            'age_limit': 18,
            'upload_date': '20200326',
            'timestamp': 1585237316,
            'description': 'md5:0d67e22b89a5f7e1ca079d974019d08d',
        }
    }, {
        'url': 'https://hanime.tv/videos/hentai/chizuru-chan-kaihatsu-nikki-1',
        'md5': 'b54b00535369c8cc0ad344cbef3429f5',
        'info_dict': {
            'id': 'chizuru-chan-kaihatsu-nikki-1',
            'ext': 'mp4',
            'title': 'Chizuru-chan Kaihatsu Nikki 1',
            'age_limit': 18,
            'upload_date': '20210930',
            'timestamp': 1633016879,
            'description': 'A serious honor student "Chizuru Shiina" was shunned by her classmates due to her being a teacher\'s pet, but none of that mattered whenever she ran into her favorite teacher that she so deeply admired...',
        }
    }, {
        'url': 'https://hanime.tv/videos/hentai/chizuru-chan-kaihatsu-nikki-2',
        'md5': 'b54b00535369c8cc0ad344cbef3429f5',
        'info_dict': {
            'id': 'chizuru-chan-kaihatsu-nikki-2',
            'ext': 'mp4',
            'title': 'Chizuru-chan Kaihatsu Nikki 2',
            'age_limit': 18,
            'upload_date': '20210930',
            'timestamp': 1633016880,
            'description': 'A serious honor student "Chizuru Shiina" was shunned by her classmates due to her being a teacher\'s pet, but none of that mattered whenever she ran into her favorite teacher that she so deeply admired...',
        }
    }
    ]

    HTTP_HEADERS = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.152 Safari/537.36'}

    DEFAULT_HOST = 'hanime.tv'

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        json_data = self._html_search_regex(r"window.__NUXT__=(.+?);<\/script>", webpage, 'Hanime.tv Inline JSON', fatal=True)
        json_data = self._parse_json(json_data, video_id)['state']['data']['video']
        server_data_dict = json_data['videos_manifest']['servers']
        url_list = list()
        for server in range(len(server_data_dict)):
            for stream in range(len(server_data_dict[server]['streams'])):
                stream_data_dict = server_data_dict[server]['streams']
                if len(url_list) == len(stream_data_dict):
                    break
                else:
                    tmp_list = {
                                'url': stream_data_dict[stream]['url'],
                                'width': int_or_none(stream_data_dict[stream]['width']),
                                'height': int_or_none(stream_data_dict[stream]['height'])
                    }

                    url_list.append(tmp_list)

        url_list = sorted(url_list, key=lambda val: val['width'] * val['height'])
        title = json_data['hentai_video']['name'] or video_id
        alt_title = try_get(json_data, lambda val: val['hentai_video']['titles'][0]['title'])
        description = clean_html(try_get(json_data, lambda val: val['hentai_video']['description']))
        publisher = try_get(json_data, lambda val: val['hentai_video']['brand'])
        tags = list()
        if (tag_dict := try_get(json_data, lambda val: val['hentai_video']['hentai_tags'])):
            for i in range(len(tag_dict)):
                tags.append(try_get(tag_dict, lambda val: val[i]['text'], compat_str))

        formats = list()

        for i in range(len(url_list)):

            if url_list[i]['url'] == '':
                continue

            formats.append(
                    {
                        'url': url_list[i]['url'],
                        'width': url_list[i].get('width'),
                        'height': url_list[i].get('height'),
                        'resolution': str_or_none(url_list[i]['width']) + "x" + str_or_none(url_list[i]['height']),
                        'container': 'mp4',
                        'ext': 'mp4',
                        'protocol': 'm3u8',
                        'preference': 1 if url_list[i]['height'] == 720 else None,
                    })

        self._remove_duplicate_formats(formats)
        self._sort_formats(formats)
        return {
            'id': video_id,
            'formats': formats,
            'description': description,
            'creator': publisher,
            'title': title,
            'alt_title': alt_title,
            'tags': tags,
            'release_date': try_get(json_data, lambda val: val['hentai_video']['released_at'][:10].replace('-', '')),
            'timestamp': try_get(json_data, lambda val: val['hentai_video']['released_at_unix']),
            'view_count': try_get(json_data, lambda val: val['hentai_video']['views']),
            'like_count': try_get(json_data, lambda val: val['hentai_video']['likes']),
            'dislike_count': try_get(json_data, lambda val: val['hentai_video']['dislikes']),
            'age_limit': 18,
        }


class HanimetvPlaylistIE(HanimetvBaseIE):
    _VALID_URL = r'https?://(?P<host>(?:www\.)?(?:members\.)?hanime\.tv)/videos/hentai/(?P<vid>.+)\?playlist_id=(?P<id>[a-zA-Z0-9-]+)'

    def _extract_entries(self, url, item_id, title):
        return [
            self.url_result(
                url,
                HanimetvBaseIE.ie_key(), video_id=item_id,
                video_title=title)
                ]

    def _entries(self, url, host, playlist_id):
        base_url = 'https://{}/videos/hentai/%s'.format(host)
        base_playlist_url = '{}?playlist_id=%s'.format(base_url)
        mobj = re.match(self._VALID_URL, url)
        curr_vid_id = mobj.group('vid')
        curr_vid = url
        first_video_id = curr_vid_id
        seek_next_vid = True
        interation_count = 1
        while (seek_next_vid):
            webpage = self._download_webpage(curr_vid, curr_vid_id, note="Downloading webpage: %s" % curr_vid)

            json_data = self._html_search_regex(r"window.__NUXT__=(.+?);<\/script>", webpage, 'Hanime.tv Inline JSON')
            json_data = self._parse_json(json_data, curr_vid_id)['state']['data']['video']
            curr_vid_id = json_data['hentai_video']['slug']
            curr_vid_url = base_url % curr_vid_id
            webpage = None

            if curr_vid_id != first_video_id or interation_count == 1:
                for e in self._extract_entries(curr_vid_url, interation_count, curr_vid_id):
                    yield e

                try:
                    next_vid_id = json_data['next_hentai_video']['slug']
                    next_vid_url = base_playlist_url % (next_vid_id, playlist_id)
                    curr_vid = next_vid_url
                except AttributeError:
                    seek_next_vid = False

                interation_count += 1

            else:
                seek_next_vid = False

    def _real_extract(self, url):
        mobj = re.match(self._VALID_URL, url)
        host = mobj.group('host')
        playlist_id = mobj.group('id')
        self.to_screen(self._entries(url, host, playlist_id))
        return self.playlist_result(self._entries(url, host, playlist_id), playlist_id)
