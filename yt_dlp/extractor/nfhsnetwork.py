from .common import InfoExtractor


from ..utils import (
    try_get,
    unified_strdate,
    unified_timestamp
)


class NFHSNetworkIE(InfoExtractor):
    IE_NAME = 'NFHSNetwork'
    _VALID_URL = r'https?://(?:www\.)?nfhsnetwork\.com/events/[\w-]+/(?P<id>(?:gam|evt|dd|)?[\w\d]{0,10})'
    _TESTS = [{
        # Auto-generated two-team sport (pixellot)
        'url': 'https://www.nfhsnetwork.com/events/rockford-high-school-rockford-mi/gamcf7e54cfbc',
        'info_dict': {
            'id': 'gamcf7e54cfbc',
            'ext': 'mp4',
            'title': 'Rockford vs Spring Lake - Girls Varsity Lacrosse 03/27/2021',
            'uploader': 'MHSAA - Michigan: Rockford High School, Rockford, MI',
            'uploader_id': 'cd2622cf76',
            'uploader_url': 'https://www.nfhsnetwork.com/schools/rockford-high-school-rockford-mi',
            'location': 'Rockford, Michigan',
            'timestamp': 1616859000,
            'upload_date': '20210327'
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        }
    }, {
        # Non-sport activity with description
        'url': 'https://www.nfhsnetwork.com/events/limon-high-school-limon-co/evt4a30e3726c',
        'info_dict': {
            'id': 'evt4a30e3726c',
            'ext': 'mp4',
            'title': 'Drama Performance Limon High School vs. Limon High School - 12/13/2020',
            'description': 'Join the broadcast of the Limon High School Musical Performance at 2 PM.',
            'uploader': 'CHSAA: Limon High School, Limon, CO',
            'uploader_id': '7d2d121332',
            'uploader_url': 'https://www.nfhsnetwork.com/schools/limon-high-school-limon-co',
            'location': 'Limon, Colorado',
            'timestamp': 1607893200,
            'upload_date': '20201213'
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        }
    }, {
        # Postseason game
        'url': 'https://www.nfhsnetwork.com/events/nfhs-network-special-events/dd8de71d45',
        'info_dict': {
            'id': 'dd8de71d45',
            'ext': 'mp4',
            'title': '2015 UA Holiday Classic Tournament: National Division  - 12/26/2015',
            'uploader': 'SoCal Sports Productions',
            'uploader_id': '063dba0150',
            'uploader_url': 'https://www.nfhsnetwork.com/affiliates/socal-sports-productions',
            'location': 'San Diego, California',
            'timestamp': 1451187000,
            'upload_date': '20151226'
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        }
    }, {
        # Video with no broadcasts object
        'url': 'https://www.nfhsnetwork.com/events/wiaa-wi/9aa2f92f82',
        'info_dict': {
            'id': '9aa2f92f82',
            'ext': 'mp4',
            'title': 'Competitive Equity  - 01/21/2015',
            'description': 'Committee members discuss points of their research regarding a competitive equity plan',
            'uploader': 'WIAA - Wisconsin: Wisconsin Interscholastic Athletic Association',
            'uploader_id': 'a49f7d1002',
            'uploader_url': 'https://www.nfhsnetwork.com/associations/wiaa-wi',
            'location': 'Stevens Point, Wisconsin',
            'timestamp': 1421856000,
            'upload_date': '20150121'
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        }
    }
    ]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        data = self._download_json(
            'https://cfunity.nfhsnetwork.com/v2/game_or_event/' + video_id,
            video_id)
        publisher = data.get('publishers')[0]  # always exists
        broadcast = (publisher.get('broadcasts') or publisher.get('vods'))[0]  # some (older) videos don't have a broadcasts object
        uploader = publisher.get('formatted_name') or publisher.get('name')
        uploaderID = publisher.get('publisher_key')
        pubType = publisher.get('type')
        uploaderPrefix = (
            "schools" if pubType == "school"
            else "associations" if "association" in pubType
            else "affiliates" if (pubType == "publisher" or pubType == "affiliate")
            else "schools")
        uploaderPage = 'https://www.nfhsnetwork.com/%s/%s' % (uploaderPrefix, publisher.get('slug'))
        location = '%s, %s' % (data.get('city'), data.get('state_name'))
        description = broadcast.get('description')
        isLive = broadcast.get('on_air') or broadcast.get('status') == 'on_air' or False

        timestamp = unified_timestamp(data.get('local_start_time'))
        upload_date = unified_strdate(data.get('local_start_time'))

        title = (
            self._og_search_title(webpage)
            or self._html_search_regex(r'<h1 class="sr-hidden">(.*?)</h1>', webpage, 'title'))
        title = title.split('|')[0].strip()

        video_type = 'broadcasts' if isLive else 'vods'
        key = broadcast.get('key') if isLive else try_get(publisher, lambda x: x['vods'][0]['key'])
        m3u8_url = self._download_json(
            'https://cfunity.nfhsnetwork.com/v2/%s/%s/url' % (video_type, key),
            video_id).get('video_url')

        formats = self._extract_m3u8_formats(m3u8_url, video_id, 'mp4', live=isLive)

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
            'description': description,
            'timestamp': timestamp,
            'uploader': uploader,
            'uploader_id': uploaderID,
            'uploader_url': uploaderPage,
            'location': location,
            'upload_date': upload_date,
            'is_live': isLive,
            '_format_sort_fields': ('res', 'tbr'),
        }
