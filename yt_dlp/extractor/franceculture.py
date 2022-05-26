import json
import re

from .common import InfoExtractor
from ..utils import int_or_none, traverse_obj


class FranceCultureIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?radiofrance\.fr/franceculture/podcasts/(?:[^/]+/)*(?P<id>[^/?#&]+)'
    _TESTS = [
        {
            'url': 'https://www.radiofrance.fr/franceculture/podcasts/science-en-questions/la-physique-d-einstein-aiderait-elle-a-comprendre-le-cerveau-8440487',
            'info_dict': {
                'id': 'la-physique-d-einstein-aiderait-elle-a-comprendre-le-cerveau-8440487',
                'ext': 'mp3',
                'title': 'La physique d’Einstein aiderait-elle à comprendre le cerveau ?',
                'description': 'Existerait-il un pont conceptuel entre la physique de l’espace-temps et les neurosciences ?',
                'thumbnail': 'https://cdn.radiofrance.fr/s3/cruiser-production/2022/05/d184e7a3-4827-4494-bf94-04ed7b120db4/1200x630_gettyimages-200171095-001.jpg',
                'uploader': None,
                'upload_date': '20220514',
                'duration': 2750,
            },
        },
    ]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)

        info = {
            'id': display_id,
            'title': self._html_search_regex(
                r'(?s)<h1[^>]*itemprop="[^"]*name[^"]*"[^>]*>(.+?)</h1>',
                webpage,
                'title',
                default=self._og_search_title(webpage),
            ),
            'description': self._html_search_regex(
                r'(?s)<meta name="description" content="([^"]+)',
                webpage,
                'description',
                default=None,
            ),
            'thumbnail': self._og_search_thumbnail(webpage),
            'uploader': self._html_search_regex(
                r'(?s)<span class="author">(.*?)</span>',
                webpage,
                'uploader',
                default=None,
            ),
            'upload_date': ''.join(self._search_regex(
                r'"datePublished":"(\d{4})-(\d{2})-(\d{2})T',  # type: ignore
                webpage,  # type: ignore
                'timestamp',
                fatal=False, group=(1, 2, 3)))
        }

        video_data = self._parse_json(
            self._search_regex(  # type: ignore
                r'({"@type":"AudioObject","contentUrl":"[^"]+","duration":"[^"]+","encodingFormat":"mp3","potentialAction":{"@type":"Action","name":"ListenAction"}})',
                webpage,
                'video data',
            ),
            display_id
        )
        video_url = video_data['contentUrl']
        ext = video_data['encodingFormat']

        # 'P0Y0M0DT0H38M28S'
        duration = sum(
            [
                durations[0] * durations[1]
                for durations in zip(
                    [
                        int(duration)
                        for duration in re.split(r'[PYMDTOHMS]', video_data['duration'])
                        if duration
                    ],
                    [
                        365 * 60 * 60 * 24,  # how many seconds in a year
                        30 * 60 * 60 * 24,  # how many seconds in a month
                        60 * 60 * 24,  # how many seconds in a day
                        60 * 60,  # how many seconds in an hour
                        60,  # how many second an in minute
                        1,  # how many seconds in a second
                    ],
                )
            ]
        )

        return {
            'display_id': display_id,
            'url': video_url,
            'ext': ext,
            'vcodec': 'none' if ext == 'mp3' else None,
            'duration': int_or_none(duration),
            **info,
        }
