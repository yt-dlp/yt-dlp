from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    clean_html,
    extract_attributes,
    get_element_by_class,
    get_element_html_by_class,
    get_elements_html_by_class,
    int_or_none,
    traverse_obj,
)


class OmroepFlevolandIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?omroepflevoland\.nl/(?:gemist/(?:radio|video)|[^/?#]+)/(?P<id>\d+)'

    _TESTS = [{
        'url': 'https://www.omroepflevoland.nl/gemist/video/260929-dif',
        'info_dict': {
            'id': '260929',
            'title': 'Dit is Flevoland nieuws',
            'timestamp': 1790694000,
            'upload_date': '20260929',
        },
        'playlist_count': 1,
        'playlist': [{
            'info_dict': {
                'id': '42687eeb73d587873df63c4efecf5f5e',
                'ext': 'mp4',
                'title': 'Dit is Flevoland nieuws',
                'thumbnail': r're:https://www\.omroepflevoland\.nl/image/lg/stills/.+',
            },
        }],
    }, {
        'url': 'https://www.omroepflevoland.nl/nieuws/525564/lelystad-zamelt-96-kilo-consumentenvuurwerk-in-via-anonieme-inleveractie',
        'info_dict': {
            'id': '525564',
            'title': 'Lelystad zamelt 96 kilo consumentenvuurwerk in via anonieme inleveractie',
            'timestamp': 1790654460,
            'upload_date': '20260929',
        },
        'playlist_count': 1,
        'playlist': [{
            'info_dict': {
                'id': '231331648',
                'ext': 'mp4',
                'title': 'Lelystad zamelt 96 kilo consumentenvuurwerk in via anonieme inleveractie',
                'thumbnail': r're:https://www\.omroepflevoland\.nl/image/lg/stills/.+',
            },
        }],
    }, {
        'url': 'https://www.omroepflevoland.nl/nieuws/525139/nieuwsoverzicht-2509-or-huis-van-aanslag-nu-verboden-gebied-*-grip-op-onveilige-jeugdhonken',
        'info_dict': {
            'id': '525139',
            'title': 'Nieuwsoverzicht 25/09\xa0| Huis van aanslag nu verboden gebied\xa0• Grip op onveilige jeugdhonken',
            'timestamp': 1790352497,
            'upload_date': '20260925',
        },
        'playlist_count': 1,
        'playlist': [{
            'info_dict': {
                'id': '228411742',
                'ext': 'mp4',
                'title': 'Nieuwsoverzicht 25/09\xa0| Huis van aanslag nu verboden gebied\xa0• Grip op onveilige jeugdhonken',
                'thumbnail': r're:https://www\.omroepflevoland\.nl/image/lg/stills/.+',
            },
        }],
    }, {
        'url': 'https://www.omroepflevoland.nl/sport/525222/almere-city-verliest-na-ongekende-slotfase-bij-fc-dordrecht',
        'info_dict': {
            'id': '525222',
            'title': 'Almere City verliest na ongekende slotfase bij FC Dordrecht',
            'timestamp': 1790361803,
            'upload_date': '20260925',
        },
        'playlist_count': 3,
        'playlist': [{
            'info_dict': {
                'id': '229180222',
                'ext': 'mp4',
                # no video caption, copies article title
                'title': 'Almere City verliest na ongekende slotfase bij FC Dordrecht',
                'thumbnail': r're:https://www\.omroepflevoland\.nl/image/lg/stills/.+',
            },
        }, {
            'info_dict': {
                'id': '229180245',
                'ext': 'mp4',
                'title': 'Marley Dors',
                'thumbnail': r're:https://www\.omroepflevoland\.nl/image/lg/stills/.+',
            },
        }, {
            'info_dict': {
                'id': '229180244',
                'ext': 'mp4',
                'title': 'Trainer Anoush Dastgir',
                'thumbnail': r're:https://www\.omroepflevoland\.nl/image/lg/stills/.+',
            },
        }],
    }, {
        'url': 'https://www.omroepflevoland.nl/nieuws/525563/n50-tussen-ens-en-kampen-dicht-vanwege-spoedreparatie',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(url, video_id)

        regiogroei_element = get_element_html_by_class('regioGroeiDiv', webpage)
        if regiogroei_element is None:
            raise ExtractorError('Could not extract page metadata')
        groei_meta = extract_attributes(regiogroei_element)

        article_title = traverse_obj(groei_meta, ('data-name',))

        entries = []
        for video_container in get_elements_html_by_class('fn-video-container', webpage):
            entry = {
                'title': clean_html(get_element_by_class('caroussel__caption', video_container)) or article_title,
                **traverse_obj(extract_attributes(get_element_html_by_class('fn-videoplayer', video_container)), {
                    # These IDs look something like "1054221373_42687eeb73d587873df63c4efecf5f5e"
                    # where the latter part seems stable but the former is generated
                    'id': ('data-source-id', {lambda i: i.rsplit('_', 1)[-1]}),
                    'url': ('data-file',),
                    'thumbnail': ('data-image',),
                }),
            }
            # I didn't make these up, that's really how they really do it
            entry['is_live'] = entry['url'].endswith('.m3u8')
            if not entry['is_live']:
                entry['subtitles'] = {'nl': [{'url': entry['url'].rsplit('.', 1)[0].replace('/middel/', '/srt/') + '.srt'}]}
            entries.append(entry)

        return {
            '_type': 'playlist',
            'entries': entries,
            'id': video_id,
            'title': article_title,
            'timestamp': traverse_obj(groei_meta, ('data-article-pub-date-timestamp', {int_or_none})),
        }
