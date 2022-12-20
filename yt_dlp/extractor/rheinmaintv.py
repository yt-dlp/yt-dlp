from ..utils import extract_attributes, float_or_none, int_or_none, parse_iso8601
from .common import InfoExtractor


class RheinMainTVIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?rheinmaintv\.de/sendungen/(?:[a-z-]+/)*(?P<display_id>[a-z-]+)/vom-(?P<date>[0-9]{2}\.[0-9]{2}\.[0-9]{4})(?:/(?P<serial_number>[0-9]+))?'
    _TESTS = [{
        'url': 'https://www.rheinmaintv.de/sendungen/beitrag-video/formationsgemeinschaft-rhein-main-bei-den-deutschen-meisterschaften/vom-14.11.2022/',
        ##'md5': ...,  # changing
        'info_dict': {
            'id': 'vom 14.11.2022',
            'ext': 'mp4',
            'title': 'Formationsgemeinschaft Rhein-Main bei den Deutschen Meisterschaften',
            'alt_title': 'Formationsgemeinschaft Rhein-Main bei den Deutschen Meisterschaften',
            'description': 'Die Lateinformation wollte bei den Deutschen Meisterschaften in die Zwischenrunde. Leider schaffte es das Team nicht.',
            'display_id': 'formationsgemeinschaft-rhein-main-bei-den-deutschen-meisterschaften',
            'formats': [{}, {}, {}, {}, {}, {}, {}, {}, {}],  # contents of the dicts aren't checked
            'subtitles': {},
            'thumbnail': 'https://rmtvmedia0.blob.core.windows.net/b43ca3fa-39b4-4129-9512-116c342b9a05/04_Latein.jpg?sv=2016-05-31&sr=c&sig=I6TEvoc8M2fzN6PwvIuPZ1VxxL06GnvxrjMTo7C3ys0%3D&st=2022-11-14T14%3A30%3A14Z&se=3022-11-15T14%3A30%3A14Z&sp=r',
            'timestamp': 1668526214,
            'duration': 345.0,
            'view_count': int,
            'upload_date': '20221115'
        },
        ##'ism_manifest_url': 'https://rmtvmedia.streaming.mediaservices.windows.net/30dd92a2-20ad-4a02-97cc-c33edf83fe25/FGRheinMainDM2022.ism/manifest'
    }, {
        'url': 'https://www.rheinmaintv.de/sendungen/beitrag-video/casino-mainz-bei-den-deutschen-meisterschaften/vom-14.11.2022/',
        ##'md5': ...,  # changing
        'info_dict': {
            'id': 'vom 14.11.2022',
            'ext': 'mp4',
            'title': 'Casino Mainz bei den Deutschen Meisterschaften',
            'alt_title': 'Casino Mainz bei den Deutschen Meisterschaften',
            'description': 'Die Standardformation aus Mainz hoffte auch auf den Sprung in die Zwischenrunde, doch auch für sie war Schluss nach der Vorrunde.',
            'display_id': 'casino-mainz-bei-den-deutschen-meisterschaften',
            'formats': [{}, {}, {}, {}, {}, {}, {}, {}, {}],  # contents of the dicts aren't checked
            'subtitles': {},
            'thumbnail': 'https://rmtvmedia0.blob.core.windows.net/e1cf7655-91b9-4b7e-b19f-a79852c7b41f/06_Standard.jpg?sv=2016-05-31&sr=c&sig=jQPJSdxCxJMX8yUZkFUPNrv1qISb0pCouK9MzAMSOMc%3D&st=2022-11-14T14%3A50%3A02Z&se=3022-11-15T14%3A50%3A02Z&sp=r',
            'timestamp': 1668527402,
            'duration': 348.0,
            'view_count': int,
            'upload_date': '20221115'
        },
        ##'ism_manifest_url': 'https://rmtvmedia.streaming.mediaservices.windows.net/ee75c842-1751-44bc-bc16-bd9dcefc4303/CasinoMainz.ism/manifest'
    }]

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        display_id = mobj.group('display_id')
        video_id = 'vom %s' % mobj.group('date')
        if mobj.group('serial_number'):
             video_id += ' (%s)' % mobj.group('serial_number')
        webpage = self._download_webpage(url, video_id)

        headline = self._html_search_regex(r'<h1><span class="title">([^<]*)</span>', webpage, 'headline')

        source, img = self._search_regex(r'(?s)(?P<source><source[^>]*>)(?P<img><img[^>]*>)', webpage, 'video', group=('source', 'img'))
        source = extract_attributes(source)
        img = extract_attributes(img)

        ##json = self._search_json_ld(webpage, video_id)  # extracts the useless 'contentUrl' (as 'url') instead of the essential 'embedUrl'
        json = self._parse_json(self._search_regex(r'(?s)<script type="application/ld\+json">([^<]*)</script>', webpage, 'json'), video_id)
        ##json = None  # go without ld+json altogether

        def get(dictionary, *keys):  # return ..utils.traverse_obj(dictionary, keys)
            for k in keys:
                if dictionary is None:
                    return None
                dictionary = dictionary.get(k)
            return dictionary

        formats, subtitles = self._extract_ism_formats_and_subtitles(source['src'] or get(json, 'embedUrl'), video_id)  # attribute 'src' is mandatory

        def removeprefix(string, prefix):
            return string[len(prefix):] if string.startswith(prefix) else None
        
        def extract_format(internet_media_type, media):  # subtype of media (aka type)
            return removeprefix(internet_media_type, media + '/') if internet_media_type is not None else None

        extension = extract_format(source.get('type'), 'video')  # use video format as filename extension (!?)
        if extension:
            for f in formats:
                f['ext'] = extension

        return {
            'id': video_id,
            'title': headline or img.get('title') or get(json, 'name') or self._og_search_title(webpage) or self._html_extract_title(webpage).removesuffix(' -'),
            'alt_title': img['alt'],  # attribute 'alt' is mandatory
            'description': get(json, 'description') or self._og_search_description(webpage),
            'display_id': display_id,
            'formats': formats,
            'subtitles': subtitles,
            'thumbnail': img['src'] or get(json, 'thumbnailUrl'),  # attribute 'src' is mandatory
            'timestamp': parse_iso8601(get(json, 'uploadDate')),
            'duration': float_or_none(get(json, 'duration')),
            'view_count': int_or_none(get(json, 'interactionStatistic', 'userInteractionCount'))
        }
