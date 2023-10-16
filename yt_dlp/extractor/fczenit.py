from .common import InfoExtractor
from ..utils import (
    int_or_none,
    float_or_none,
)


class FczenitIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?fc-zenit\.ru/video/(?P<id>[0-9]+)'
    _TEST = {
        'url': 'http://fc-zenit.ru/video/41044/',
        'md5': '0e3fab421b455e970fa1aa3891e57df0',
        'info_dict': {
            'id': '41044',
            'ext': 'mp4',
            'title': 'Так пишется история: казанский разгром ЦСКА на «Зенит-ТВ»',
            'timestamp': 1462283735,
            'upload_date': '20160503',
        },
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        msi_id = self._search_regex(
            r"(?s)config\s*=\s*{.+?video_id\s*:\s*'([^']+)'", webpage, 'msi id')

        msi_data = self._download_json(
            'http://player.fc-zenit.ru/msi/video', msi_id, query={
                'video': msi_id,
            })['data']
        title = msi_data['name']

        formats = [{
            'format_id': q.get('label'),
            'url': q['url'],
            'height': int_or_none(q.get('label')),
        } for q in msi_data['qualities'] if q.get('url')]

        tags = [tag['label'] for tag in msi_data.get('tags', []) if tag.get('label')]

        return {
            'id': video_id,
            'title': title,
            'thumbnail': msi_data.get('preview'),
            'formats': formats,
            'duration': float_or_none(msi_data.get('duration')),
            'timestamp': int_or_none(msi_data.get('date')),
            'tags': tags,
        }
