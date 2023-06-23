from .common import InfoExtractor
from ..utils import extract_attributes, merge_dicts, remove_end


class RheinMainTVIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?rheinmaintv\.de/sendungen/(?:[\w-]+/)*(?P<video_id>(?P<display_id>[\w-]+)/vom-\d{2}\.\d{2}\.\d{4}(?:/\d+)?)'
    _TESTS = [{
        'url': 'https://www.rheinmaintv.de/sendungen/beitrag-video/auf-dem-weg-zur-deutschen-meisterschaft/vom-07.11.2022/',
        'info_dict': {
            'id': 'auf-dem-weg-zur-deutschen-meisterschaft-vom-07.11.2022',
            'ext': 'ismv',  # ismv+isma will be merged into mp4
            'alt_title': 'Auf dem Weg zur Deutschen Meisterschaft',
            'title': 'Auf dem Weg zur Deutschen Meisterschaft',
            'upload_date': '20221108',
            'view_count': int,
            'display_id': 'auf-dem-weg-zur-deutschen-meisterschaft',
            'thumbnail': r're:^https://.+\.jpg',
            'description': 'md5:48c59b74192bc819a9b34af1d5ed1eb9',
            'timestamp': 1667933057,
            'duration': 243.0,
        },
        'params': {'skip_download': 'ism'},
    }, {
        'url': 'https://www.rheinmaintv.de/sendungen/beitrag-video/formationsgemeinschaft-rhein-main-bei-den-deutschen-meisterschaften/vom-14.11.2022/',
        'info_dict': {
            'id': 'formationsgemeinschaft-rhein-main-bei-den-deutschen-meisterschaften-vom-14.11.2022',
            'ext': 'ismv',
            'title': 'Formationsgemeinschaft Rhein-Main bei den Deutschen Meisterschaften',
            'timestamp': 1668526214,
            'display_id': 'formationsgemeinschaft-rhein-main-bei-den-deutschen-meisterschaften',
            'alt_title': 'Formationsgemeinschaft Rhein-Main bei den Deutschen Meisterschaften',
            'view_count': int,
            'thumbnail': r're:^https://.+\.jpg',
            'duration': 345.0,
            'description': 'md5:9370ba29526984006c2cba1372e5c5a0',
            'upload_date': '20221115',
        },
        'params': {'skip_download': 'ism'},
    }, {
        'url': 'https://www.rheinmaintv.de/sendungen/beitrag-video/casino-mainz-bei-den-deutschen-meisterschaften/vom-14.11.2022/',
        'info_dict': {
            'id': 'casino-mainz-bei-den-deutschen-meisterschaften-vom-14.11.2022',
            'ext': 'ismv',
            'title': 'Casino Mainz bei den Deutschen Meisterschaften',
            'view_count': int,
            'timestamp': 1668527402,
            'alt_title': 'Casino Mainz bei den Deutschen Meisterschaften',
            'upload_date': '20221115',
            'display_id': 'casino-mainz-bei-den-deutschen-meisterschaften',
            'duration': 348.0,
            'thumbnail': r're:^https://.+\.jpg',
            'description': 'md5:70fc1660eeba96da17199e5bdff4c0aa',
        },
        'params': {'skip_download': 'ism'},
    }, {
        'url': 'https://www.rheinmaintv.de/sendungen/beitrag-video/bricks4kids/vom-22.06.2022/',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        display_id = mobj.group('display_id')
        video_id = mobj.group('video_id').replace('/', '-')
        webpage = self._download_webpage(url, video_id)

        source, img = self._search_regex(r'(?s)(?P<source><source[^>]*>)(?P<img><img[^>]*>)',
                                         webpage, 'video', group=('source', 'img'))
        source = extract_attributes(source)
        img = extract_attributes(img)

        raw_json_ld = list(self._yield_json_ld(webpage, video_id))
        json_ld = self._json_ld(raw_json_ld, video_id)
        json_ld.pop('url', None)

        ism_manifest_url = (
            source.get('src')
            or next(json_ld.get('embedUrl') for json_ld in raw_json_ld if json_ld.get('@type') == 'VideoObject')
        )
        formats, subtitles = self._extract_ism_formats_and_subtitles(ism_manifest_url, video_id)

        return merge_dicts({
            'id': video_id,
            'display_id': display_id,
            'title':
                self._html_search_regex(r'<h1><span class="title">([^<]*)</span>',
                                        webpage, 'headline', default=None)
                or img.get('title') or json_ld.get('title') or self._og_search_title(webpage)
                or remove_end(self._html_extract_title(webpage), ' -'),
            'alt_title': img.get('alt'),
            'description': json_ld.get('description') or self._og_search_description(webpage),
            'formats': formats,
            'subtitles': subtitles,
            'thumbnails': [{'url': img['src']}] if 'src' in img else json_ld.get('thumbnails'),
        }, json_ld)
