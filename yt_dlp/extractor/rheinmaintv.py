from .common import InfoExtractor
from ..utils import extract_attributes, remove_end


class RheinMainTVIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?rheinmaintv\.de/sendungen/(?:[a-z-]+/)*(?P<video_id>(?P<display_id>[a-z-]+)/vom-[0-9]{2}\.[0-9]{2}\.[0-9]{4}(?:/[0-9]+)?)'
    _TESTS = [{
        'url': 'https://www.rheinmaintv.de/sendungen/beitrag-video/auf-dem-weg-zur-deutschen-meisterschaft/vom-07.11.2022/',
        'info_dict': {
            'id': 'auf-dem-weg-zur-deutschen-meisterschaft-vom-07.11.2022',
            'display_id': 'auf-dem-weg-zur-deutschen-meisterschaft',
            'title': 'Auf dem Weg zur Deutschen Meisterschaft',
            'alt_title': 'Auf dem Weg zur Deutschen Meisterschaft',
            'description': 'Die Lateinformation der FG Rhein-Main fährt am kommenden Wochenende zur Deutschen Meisterschaft nach Bremen. Im Training holen sich die Tänzerinnen und Tänzer den letzten Schliff.',
            'ext': 'mp4',
            'subtitles': {},
            'thumbnail': 'https://rmtvmedia0.blob.core.windows.net/a0631411-b183-484b-ab6a-4e37a5831402/FormationsgemeinschaftRheinMain.jpg?sv=2016-05-31&sr=c&sig=iYdkgclsnXr2vDF%2B93jKTq702tsaWMtdxeeJHjV8iK4%3D&st=2022-11-07T17%3A44%3A17Z&se=3022-11-08T17%3A44%3A17Z&sp=r',
            'timestamp': 1667933057,
            'duration': 243.0,
            'view_count': int,
            'upload_date': '20221108'
        }
    }, {
        'url': 'https://www.rheinmaintv.de/sendungen/beitrag-video/formationsgemeinschaft-rhein-main-bei-den-deutschen-meisterschaften/vom-14.11.2022/',
        'info_dict': {
            'id': 'formationsgemeinschaft-rhein-main-bei-den-deutschen-meisterschaften-vom-14.11.2022',
            'display_id': 'formationsgemeinschaft-rhein-main-bei-den-deutschen-meisterschaften',
            'title': 'Formationsgemeinschaft Rhein-Main bei den Deutschen Meisterschaften',
            'alt_title': 'Formationsgemeinschaft Rhein-Main bei den Deutschen Meisterschaften',
            'description': 'Die Lateinformation wollte bei den Deutschen Meisterschaften in die Zwischenrunde. Leider schaffte es das Team nicht.',
            'ext': 'mp4',
            'subtitles': {},
            'thumbnail': 'https://rmtvmedia0.blob.core.windows.net/b43ca3fa-39b4-4129-9512-116c342b9a05/04_Latein.jpg?sv=2016-05-31&sr=c&sig=I6TEvoc8M2fzN6PwvIuPZ1VxxL06GnvxrjMTo7C3ys0%3D&st=2022-11-14T14%3A30%3A14Z&se=3022-11-15T14%3A30%3A14Z&sp=r',
            'timestamp': 1668526214,
            'duration': 345.0,
            'view_count': int,
            'upload_date': '20221115'
        }
    }, {
        'url': 'https://www.rheinmaintv.de/sendungen/beitrag-video/casino-mainz-bei-den-deutschen-meisterschaften/vom-14.11.2022/',
        'info_dict': {
            'id': 'casino-mainz-bei-den-deutschen-meisterschaften-vom-14.11.2022',
            'display_id': 'casino-mainz-bei-den-deutschen-meisterschaften',
            'title': 'Casino Mainz bei den Deutschen Meisterschaften',
            'alt_title': 'Casino Mainz bei den Deutschen Meisterschaften',
            'description': 'Die Standardformation aus Mainz hoffte auch auf den Sprung in die Zwischenrunde, doch auch für sie war Schluss nach der Vorrunde.',
            'ext': 'mp4',
            'subtitles': {},
            'thumbnail': 'https://rmtvmedia0.blob.core.windows.net/e1cf7655-91b9-4b7e-b19f-a79852c7b41f/06_Standard.jpg?sv=2016-05-31&sr=c&sig=jQPJSdxCxJMX8yUZkFUPNrv1qISb0pCouK9MzAMSOMc%3D&st=2022-11-14T14%3A50%3A02Z&se=3022-11-15T14%3A50%3A02Z&sp=r',
            'timestamp': 1668527402,
            'duration': 348.0,
            'view_count': int,
            'upload_date': '20221115'
        }
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

        # Work around the method self._json_ld (called by self._search_json_ld), which
        # extracts the useless 'contentUrl' (as 'url') instead of the essential 'embedUrl'.
        raw_json_ld = list(self._yield_json_ld(webpage, video_id))
        json_ld = self._json_ld(raw_json_ld, video_id)

        ism_manifest_url = (
            source.get('src')
            or next(json_ld.get('embedUrl') for json_ld in raw_json_ld if json_ld.get('@type') == 'VideoObject')
        )
        formats, subtitles = self._extract_ism_formats_and_subtitles(ism_manifest_url, video_id)

        return {
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
            'timestamp': json_ld.get('timestamp'),
            'duration': json_ld.get('duration'),
            'view_count': json_ld.get('view_count')
        }
