from .common import InfoExtractor
from ..utils import (
    extract_attributes,
    float_or_none,
    get_element_by_class,
    strip_or_none,
    unified_timestamp,
)


class VRTIE(InfoExtractor):
    IE_DESC = 'VRT NWS, Flanders News, Flandern Info and Sporza'
    _VALID_URL = r'https?://(?:www\.)?(?P<site>vrt\.be/vrtnws|sporza\.be)/[a-z]{2}/\d{4}/\d{2}/\d{2}/(?P<id>[^/?&#]+)'
    _TESTS = [{
        'url': 'https://www.vrt.be/vrtnws/nl/2019/05/15/beelden-van-binnenkant-notre-dame-een-maand-na-de-brand/',
        'md5': 'e1663accf5cf13f375f3cd0d10476669',
        'info_dict': {
            'id': 'pbs-pub-7855fc7b-1448-49bc-b073-316cb60caa71$vid-2ca50305-c38a-4762-9890-65cbd098b7bd',
            'ext': 'mp4',
            'title': 'Beelden van binnenkant Notre-Dame, één maand na de brand',
            'description': 'Op maandagavond 15 april ging een deel van het dakgebinte van de Parijse kathedraal in vlammen op.',
            'timestamp': 1557924660,
            'upload_date': '20190515',
            'duration': 31.2,
        },
    }, {
        'url': 'https://sporza.be/nl/2019/05/15/de-belgian-cats-zijn-klaar-voor-het-ek/',
        'md5': '910bba927566e9ab992278f647eb4b75',
        'info_dict': {
            'id': 'pbs-pub-f2c86a46-8138-413a-a4b9-a0015a16ce2c$vid-1f112b31-e58e-4379-908d-aca6d80f8818',
            'ext': 'mp4',
            'title': 'De Belgian Cats zijn klaar voor het EK mét Ann Wauters',
            'timestamp': 1557923760,
            'upload_date': '20190515',
            'duration': 115.17,
        },
    }, {
        'url': 'https://www.vrt.be/vrtnws/en/2019/05/15/belgium_s-eurovision-entry-falls-at-the-first-hurdle/',
        'only_matching': True,
    }, {
        'url': 'https://www.vrt.be/vrtnws/de/2019/05/15/aus-fuer-eliott-im-halbfinale-des-eurosongfestivals/',
        'only_matching': True,
    }]
    _CLIENT_MAP = {
        'vrt.be/vrtnws': 'vrtnieuws',
        'sporza.be': 'sporza',
    }

    def _real_extract(self, url):
        site, display_id = self._match_valid_url(url).groups()
        webpage = self._download_webpage(url, display_id)
        attrs = extract_attributes(self._search_regex(
            r'(<[^>]+class="vrtvideo( [^"]*)?"[^>]*>)', webpage, 'vrt video'))

        asset_id = attrs['data-video-id']
        publication_id = attrs.get('data-publication-id')
        if publication_id:
            asset_id = publication_id + '$' + asset_id
        client = attrs.get('data-client-code') or self._CLIENT_MAP[site]

        title = strip_or_none(get_element_by_class(
            'vrt-title', webpage) or self._html_search_meta(
            ['og:title', 'twitter:title', 'name'], webpage))
        description = self._html_search_meta(
            ['og:description', 'twitter:description', 'description'], webpage)
        if description == '…':
            description = None
        timestamp = unified_timestamp(self._html_search_meta(
            'article:published_time', webpage))

        return {
            '_type': 'url_transparent',
            'id': asset_id,
            'display_id': display_id,
            'title': title,
            'description': description,
            'thumbnail': attrs.get('data-posterimage'),
            'timestamp': timestamp,
            'duration': float_or_none(attrs.get('data-duration'), 1000),
            'url': 'https://mediazone.vrt.be/api/v1/%s/assets/%s' % (client, asset_id),
            'ie_key': 'Canvas',
        }
