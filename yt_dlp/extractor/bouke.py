from .common import InfoExtractor
from .youtube import YoutubeIE
from ..utils import (
    extract_attributes,
    get_element_html_by_class,
    parse_iso8601,
)
from ..utils.traversal import traverse_obj


class BoukeMediaIE(InfoExtractor):
    _VALID_URL = r'https://(?:www\.)?bouke\.media/[^?&#]+/(?P<id>\d+)'
    IE_NAME = 'bouke:media'

    _TESTS = [{
        'url': 'https://www.bouke.media/emission/les-cadeaux-du-pere-noel-numero-2/19914',
        'info_dict': {
            'id': '19914',
            'ext': 'mp4',
            'title': 'Les cadeaux du Père Noël numéro 2',
            'description': 'md5:574c6c3021f9ccd538fcc8eb20cac0e9',
            'duration': 764.949,
            'thumbnail': 'https://tvlocales-posters.freecaster.com/videos/bouke/a09f9b89-f9df-4ff0-9521-cb464481d79b/Jvn1VTUU4jEgPs72tKa3ZWMC/1280x720.jpg',
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        # Youtube Embed
        'url': 'https://www.bouke.media/emission/les-cadeaux-du-pere-noel-numero-1/19913',
        'info_dict': {
            'id': 'q9R5_uIDEeQ',
            'ext': 'mp4',
            'title': 'Les cadeaux du Père Noël #1',
            'description': 'Retrouvez les cadeaux du Père Noël sur Bouke.media',
            'media_type': 'video',
            'uploader': 'Boukè',
            'channel': 'Boukè',
            'channel_id': 'UCcXqRZgKHMIDDZ0U_hksp4w',
            'channel_url': 'https://www.youtube.com/channel/UCcXqRZgKHMIDDZ0U_hksp4w',
            'channel_follower_count': int,
            'view_count': int,
            'age_limit': 0,
            'duration': 818,
            'thumbnail': 'https://i.ytimg.com/vi/q9R5_uIDEeQ/maxresdefault.jpg',
            'categories': ['Entertainment'],
            'tags': [],
            'timestamp': 1766575966,
            'upload_date': '20251224',
            'playable_in_embed': True,
            'availability': 'unlisted',
            'live_status': 'not_live',
        },
        'expected_warnings': ['DASH manifest missing'],
        'params': {'skip_download': 'm3u8'},
    }]

    SEEN_RES = {
        '5.mp4': (960, 540),
        '9.mp4': (1280, 720),
        '3.mp4': (640, 360),
    }

    def _find_res(self, url):
        res = url.split('_')[-1]
        resolution = self.SEEN_RES.get(res)
        return resolution if resolution else (0, 0)

    def _extract_formats(self, data):
        formats = []
        for info in data.get('src'):
            vid = info.get('video_id')
            vtype = info.get('type')
            url = info.get('src')
            if 'mpegurl' in vtype:
                formats.extend(
                    self._extract_m3u8_formats(url, vid))
            elif 'dash' in vtype:
                formats.extend(
                    self._extract_mpd_formats(url, vid))
            if 'mp4' in vtype:
                width, height = self._find_res(url)
                formats.append({
                    'url': url,
                    'height': height,
                    'width': width})
        return formats

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        embed_class = get_element_html_by_class('freecaster-player', webpage)
        youtube_embeds = YoutubeIE._extract_embed_urls(url, webpage)
        title = self._og_search_title(webpage, default='')
        description = self._og_search_description(webpage, default='')
        for embed_url in youtube_embeds:
            self.to_screen('Youtube embed found')
            return self.url_result(embed_url, YoutubeIE, video_id, title)
        if embed_class is None:
            self.raise_no_formats('No video found in this media')
        embed_id = extract_attributes(embed_class).get('data-video-id')
        data = self._download_json(
            f'https://tvlocales-player-v12.freecaster.com/embed/{embed_id}.json', embed_id,
        ).get('video')

        return {
            'id': video_id,
            'formats': self._extract_formats(data),
            'title': title,
            'description': description,
            **traverse_obj(data, {
                'thumbnail': ('poster'),
                'duration': ('duration'),
                'upload_date': ('published_at', {parse_iso8601}, {str}),
            }),
        }
