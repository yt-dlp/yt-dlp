from .common import InfoExtractor
from ..utils import (
    clean_html,
    determine_ext,
    extract_attributes,
    int_or_none,
    parse_resolution,
    str_or_none,
    url_or_none,
)
from ..utils.traversal import find_elements, traverse_obj


class MedialaanBaseIE(InfoExtractor):
    def _extract_from_mychannels_api(self, mychannels_id):
        webpage = self._download_webpage(
            f'https://mychannels.video/embed/{mychannels_id}', mychannels_id)
        brand_config = self._search_json(
            r'window\.mychannels\.brand_config\s*=', webpage, 'brand config', mychannels_id)
        response = self._download_json(
            f'https://api.mychannels.world/v1/embed/video/{mychannels_id}',
            mychannels_id, headers={'X-Mychannels-Brand': brand_config['brand']})

        formats = []
        for stream in traverse_obj(response, (
            'streams', lambda _, v: url_or_none(v['url']),
        )):
            source_url = stream['url']
            ext = determine_ext(source_url)
            if ext == 'm3u8':
                formats.extend(self._extract_m3u8_formats(
                    source_url, mychannels_id, 'mp4', m3u8_id='hls', fatal=False))
            else:
                format_id = traverse_obj(stream, ('quality', {str}))
                formats.append({
                    'ext': ext,
                    'format_id': format_id,
                    'url': source_url,
                    **parse_resolution(format_id),
                })

        return {
            'id': mychannels_id,
            'formats': formats,
            **traverse_obj(response, {
                'title': ('title', {clean_html}),
                'description': ('description', {clean_html}, filter),
                'duration': ('durationMs', {int_or_none(scale=1000)}, {lambda x: x if x >= 0 else None}),
                'genres': ('genre', 'title', {str}, filter, all, filter),
                'is_live': ('live', {bool}),
                'release_timestamp': ('publicationTimestampMs', {int_or_none(scale=1000)}),
                'tags': ('tags', ..., 'title', {str}, filter, all, filter),
                'thumbnail': ('image', 'baseUrl', {url_or_none}),
            }),
            **traverse_obj(response, ('channel', {
                'channel': ('title', {clean_html}),
                'channel_id': ('id', {str_or_none}),
            })),
            **traverse_obj(response, ('organisation', {
                'uploader': ('title', {clean_html}),
                'uploader_id': ('id', {str_or_none}),
            })),
            **traverse_obj(response, ('show', {
                'series': ('title', {clean_html}),
                'series_id': ('id', {str_or_none}),
            })),
        }


class MedialaanIE(MedialaanBaseIE):
    _VALID_URL = r'''(?x)
                    https?://
                        (?:
                            (?:embed\.)?mychannels.video/embed/|
                            embed\.mychannels\.video/(?:s(?:dk|cript)/)?production/|
                            (?:www\.)?(?:
                                (?:
                                    7sur7|
                                    demorgen|
                                    hln|
                                    joe|
                                    qmusic
                                )\.be|
                                (?:
                                    [abe]d|
                                    bndestem|
                                    destentor|
                                    gelderlander|
                                    pzc|
                                    tubantia|
                                    volkskrant
                                )\.nl
                            )/videos?/(?:[^/?#]+/)*[^/?&#]+(?:-|~p)
                        )
                        (?P<id>\d+)
                    '''
    _TESTS = [{
        'url': 'https://www.bndestem.nl/video/de-terugkeer-van-ally-de-aap-en-wie-vertrekt-er-nog-bij-nac~p193993',
        'info_dict': {
            'id': '193993',
            'ext': 'mp4',
            'title': 'De terugkeer van Ally de Aap en wie vertrekt er nog bij NAC?',
            'description': 'In een nieuwe Gegenpressing video bespreken Yadran Blanco en Dennis Kas het nieuws omrent NAC.',
            'duration': 238,
            'channel': 'BN DeStem',
            'channel_id': '418',
            'genres': ['Sports'],
            'release_date': '20210126',
            'release_timestamp': 1611663540,
            'series': 'Korte Reportage',
            'series_id': '972',
            'tags': 'count:2',
            'thumbnail': r're:https?://images\.mychannels\.video/imgix/.+\.(?:jpe?g|png)',
            'uploader': 'BN De Stem',
            'uploader_id': '26',
        },
    }, {
        'url': 'https://www.gelderlander.nl/video/kanalen/degelderlander~c320/series/snel-nieuws~s984/noodbevel-in-doetinchem-politie-stuurt-mensen-centrum-uit~p194093',
        'info_dict': {
            'id': '194093',
            'ext': 'mp4',
            'title': 'Noodbevel in Doetinchem: politie stuurt mensen centrum uit',
            'description': 'md5:77e85b2cb26cfff9dc1fe2b1db524001',
            'duration': 44,
            'channel': 'De Gelderlander',
            'channel_id': '320',
            'genres': ['News'],
            'release_date': '20210126',
            'release_timestamp': 1611690600,
            'series': 'Snel Nieuws',
            'series_id': '984',
            'tags': 'count:1',
            'thumbnail': r're:https?://images\.mychannels\.video/imgix/.+\.(?:jpe?g|png)',
            'uploader': 'De Gelderlander',
            'uploader_id': '25',
        },
    }, {
        'url': 'https://www.7sur7.be/videos/production/lla-tendance-tiktok-qui-enflamme-lespagne-707650',
        'info_dict': {
            'id': '707650',
            'ext': 'mp4',
            'title': 'La tendance TikTok qui enflamme l’Espagne',
            'description': 'md5:c7ec4cb733190f227fc8935899f533b5',
            'duration': 70,
            'channel': 'Lifestyle',
            'channel_id': '770',
            'genres': ['Beauty & Lifestyle'],
            'release_date': '20240906',
            'release_timestamp': 1725617330,
            'series': 'Lifestyle',
            'series_id': '1848',
            'tags': 'count:1',
            'thumbnail': r're:https?://images\.mychannels\.video/imgix/.+\.(?:jpe?g|png)',
            'uploader': '7sur7',
            'uploader_id': '67',
        },
    }, {
        'url': 'https://mychannels.video/embed/313117',
        'info_dict': {
            'id': '313117',
            'ext': 'mp4',
            'title': str,
            'description': 'md5:255e2e52f6fe8a57103d06def438f016',
            'channel': 'AD',
            'channel_id': '238',
            'genres': ['News'],
            'live_status': 'is_live',
            'release_date': '20241225',
            'release_timestamp': 1735169425,
            'series': 'Nieuws Update',
            'series_id': '3337',
            'tags': 'count:1',
            'thumbnail': r're:https?://images\.mychannels\.video/imgix/.+\.(?:jpe?g|png)',
            'uploader': 'AD',
            'uploader_id': '1',
        },
        'params': {'skip_download': 'Livestream'},
    }, {
        'url': 'https://embed.mychannels.video/sdk/production/193993',
        'only_matching': True,
    }, {
        'url': 'https://embed.mychannels.video/script/production/193993',
        'only_matching': True,
    }, {
        'url': 'https://embed.mychannels.video/production/193993',
        'only_matching': True,
    }, {
        'url': 'https://embed.mychannels.video/embed/193993',
        'only_matching': True,
    }]
    _WEBPAGE_TESTS = [{
        'url': 'https://www.demorgen.be/snelnieuws/tom-waes-promoot-alcoholtesten-op-werchter-ik-ben-de-laatste-persoon-die-met-de-vinger-moet-wijzen~b7457c0d/',
        'info_dict': {
            'id': '1576607',
            'ext': 'mp4',
            'title': 'Tom Waes blaastest',
            'channel': 'De Morgen',
            'channel_id': '352',
            'description': 'Tom Waes werkt mee aan een alcoholcampagne op Werchter',
            'duration': 62,
            'genres': ['News'],
            'release_date': '20250705',
            'release_timestamp': 1751730795,
            'series': 'Nieuwsvideo\'s',
            'series_id': '1683',
            'tags': 'count:1',
            'thumbnail': r're:https?://video-images\.persgroep\.be/aws_generated.+\.jpg',
            'uploader': 'De Morgen',
            'uploader_id': '17',
        },
        'params': {'extractor_args': {'generic': {'impersonate': ['chrome']}}},
    }]

    @classmethod
    def _extract_embed_urls(cls, url, webpage):
        yield from traverse_obj(webpage, (
            {find_elements(tag='div', attr='data-mychannels-type', value='video', html=True)},
            ..., {extract_attributes}, 'data-mychannels-id', {str}, filter,
            {lambda x: f'https://mychannels.video/embed/{x}'}))

    def _real_extract(self, url):
        mychannels_id = self._match_id(url)

        return self._extract_from_mychannels_api(mychannels_id)
