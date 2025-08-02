import re

from .common import InfoExtractor
from ..utils import (
    extract_attributes,
    int_or_none,
    mimetype2ext,
    parse_iso8601,
)


class MedialaanIE(InfoExtractor):
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
                            )/video/(?:[^/]+/)*[^/?&#]+~p
                        )
                        (?P<id>\d+)
                    '''
    _TESTS = [{
        'url': 'https://www.bndestem.nl/video/de-terugkeer-van-ally-de-aap-en-wie-vertrekt-er-nog-bij-nac~p193993',
        'info_dict': {
            'id': '193993',
            'ext': 'mp4',
            'title': 'De terugkeer van Ally de Aap en wie vertrekt er nog bij NAC?',
            'thumbnail': r're:https?://images\.mychannels\.video/imgix/.+',
            'timestamp': 1611663540,
            'upload_date': '20210126',
            'duration': 238,
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'https://www.gelderlander.nl/video/kanalen/degelderlander~c320/series/snel-nieuws~s984/noodbevel-in-doetinchem-politie-stuurt-mensen-centrum-uit~p194093',
        'only_matching': True,
    }, {
        'url': 'https://embed.mychannels.video/sdk/production/193993?options=TFTFF_default',
        'only_matching': True,
    }, {
        'url': 'https://embed.mychannels.video/script/production/193993',
        'only_matching': True,
    }, {
        'url': 'https://embed.mychannels.video/production/193993',
        'only_matching': True,
    }, {
        'url': 'https://mychannels.video/embed/193993',
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
            'duration': 62,
            'thumbnail': r're:https?://video-images\.persgroep\.be/aws_generated.+\.jpg',
            'timestamp': 1751730795,
            'upload_date': '20250705',
        },
        'params': {'extractor_args': {'generic': {'impersonate': ['chrome']}}},
    }]

    @classmethod
    def _extract_embed_urls(cls, url, webpage):
        entries = []
        for element in re.findall(r'(<div[^>]+data-mychannels-type="video"[^>]*>)', webpage):
            mychannels_id = extract_attributes(element).get('data-mychannels-id')
            if mychannels_id:
                entries.append('https://mychannels.video/embed/' + mychannels_id)
        return entries

    def _real_extract(self, url):
        production_id = self._match_id(url)
        production = self._download_json(
            'https://embed.mychannels.video/sdk/production/' + production_id,
            production_id, query={'options': 'UUUU_default'})['productions'][0]
        title = production['title']

        formats = []
        for source in (production.get('sources') or []):
            src = source.get('src')
            if not src:
                continue
            ext = mimetype2ext(source.get('type'))
            if ext == 'm3u8':
                formats.extend(self._extract_m3u8_formats(
                    src, production_id, 'mp4', 'm3u8_native',
                    m3u8_id='hls', fatal=False))
            else:
                formats.append({
                    'ext': ext,
                    'url': src,
                })

        return {
            'id': production_id,
            'title': title,
            'formats': formats,
            'thumbnail': production.get('posterUrl'),
            'timestamp': parse_iso8601(production.get('publicationDate'), ' '),
            'duration': int_or_none(production.get('duration')) or None,
        }
