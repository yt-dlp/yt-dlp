from __future__ import unicode_literals


from .common import InfoExtractor
from ..utils import int_or_none


class TwentyThreeVideoIE(InfoExtractor):
    IE_NAME = '23video'
    _VALID_URL = r'https?://(?P<domain>[^.]+\.(?:twentythree\.net|23video\.com|filmweb\.no))/v\.ihtml/player\.html\?(?P<query>.*?\bphoto(?:_|%5f)id=(?P<id>\d+).*)'
    _TESTS = [{
        'url': 'https://video.twentythree.net/v.ihtml/player.html?showDescriptions=0&source=site&photo%5fid=20448876&autoPlay=1',
        'md5': '75fcf216303eb1dae9920d651f85ced4',
        'info_dict': {
            'id': '20448876',
            'ext': 'mp4',
            'title': 'Video Marketing Minute: Personalized Video',
            'timestamp': 1513855354,
            'upload_date': '20171221',
            'uploader_id': '12258964',
            'uploader': 'Rasmus Bysted',
        }
    }, {
        'url': 'https://bonnier-publications-danmark.23video.com/v.ihtml/player.html?token=f0dc46476e06e13afd5a1f84a29e31e8&source=embed&photo%5fid=36137620',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        domain, query, photo_id = self._match_valid_url(url).groups()
        base_url = 'https://%s' % domain
        photo_data = self._download_json(
            base_url + '/api/photo/list?' + query, photo_id, query={
                'format': 'json',
            }, transform_source=lambda s: self._search_regex(r'(?s)({.+})', s, 'photo data'))['photo']
        title = photo_data['title']

        formats = []

        audio_path = photo_data.get('audio_download')
        if audio_path:
            formats.append({
                'format_id': 'audio',
                'url': base_url + audio_path,
                'filesize': int_or_none(photo_data.get('audio_size')),
                'vcodec': 'none',
            })

        def add_common_info_to_list(l, template, id_field, id_value):
            f_base = template % id_value
            f_path = photo_data.get(f_base + 'download')
            if not f_path:
                return
            l.append({
                id_field: id_value,
                'url': base_url + f_path,
                'width': int_or_none(photo_data.get(f_base + 'width')),
                'height': int_or_none(photo_data.get(f_base + 'height')),
                'filesize': int_or_none(photo_data.get(f_base + 'size')),
            })

        for f in ('mobile_high', 'medium', 'hd', '1080p', '4k'):
            add_common_info_to_list(formats, 'video_%s_', 'format_id', f)

        thumbnails = []
        for t in ('quad16', 'quad50', 'quad75', 'quad100', 'small', 'portrait', 'standard', 'medium', 'large', 'original'):
            add_common_info_to_list(thumbnails, '%s_', 'id', t)

        return {
            'id': photo_id,
            'title': title,
            'timestamp': int_or_none(photo_data.get('creation_date_epoch')),
            'duration': int_or_none(photo_data.get('video_length')),
            'view_count': int_or_none(photo_data.get('view_count')),
            'comment_count': int_or_none(photo_data.get('number_of_comments')),
            'uploader_id': photo_data.get('user_id'),
            'uploader': photo_data.get('display_name'),
            'thumbnails': thumbnails,
            'formats': formats,
        }
