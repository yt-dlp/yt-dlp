from .youtube import YoutubeIE
from ..utils import clean_html, int_or_none, traverse_obj, url_or_none, urlencode_postdata


class DigiviewIE(YoutubeIE):
    IE_DESC = 'Digiview'
    IE_NAME = 'digiview'
    _VALID_URL = r'https?://(?:www\.)?ladigitale\.dev/digiview/#/v/(?P<id>[0-9a-f]+)'
    _TESTS = [
        {
            # normal video
            'url': 'https://ladigitale.dev/digiview/#/v/67a8e50aee2ec',
            'info_dict': {
                'title': 'Big Buck Bunny 60fps 4K - Official Blender Foundation Short Film',
            },
        },
        {
            # cut video
            'url': 'https://ladigitale.dev/digiview/#/v/67a8e51d0dd58',
            'info_dict': {
                'title': 'Big Buck Bunny 60fps 4K - Official Blender Foundation Short Film',
            },
        },
    ]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        video_data = self._download_json(
            'https://ladigitale.dev/digiview/inc/recuperer_video.php', video_id,
            data=urlencode_postdata({'id': video_id}))

        clip_id = video_data['videoId']
        return {
            '_type': 'url_transparent',
            'url': f'https://www.youtube.com/watch?v={clip_id}',
            'ie_key': YoutubeIE.ie_key(),
            'id': clip_id,
            **traverse_obj(video_data, {
                'section_start': ('debut', {int_or_none}),
                'section_end': ('fin', {int_or_none}),
                'description': ('description', {clean_html}),
                'title': ('titre', {str}),
                'thumbnail': ('vignette', {url_or_none}),
                'view_count': ('vues', {int_or_none}),
            }),
        }
