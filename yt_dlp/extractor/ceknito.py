import datetime as dt
import re

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    int_or_none,
    parse_duration,
)


class CekniToIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?ceknito\.(cz|sk|eu)/video/(?P<id>[0-9]+)'
    _TESTS = [{  # 720p cz
        'url': 'https://www.ceknito.cz/video/480911',
        'md5': '85ed13dda7a0923f1c8967be85228678',
        'info_dict': {
            'id': '480911',
            'ext': 'mp4',
            'view_count': int,
            'uploader': 'Proxymo',
            'like_count': int,
            'duration': 186.0,
            'description': 'CEKNITO',
            'thumbnail': 'https://www.ceknito.sk/d/embed/001d/480911/player.jpg',
            'categories': ['Auto-moto'],
            'title': 'Autonomní vůz Mercedes-Benz F 015',
            'age_limit': 0,
            'timestamp': 1427252280,
            'upload_date': '20150325',
        },
    }, {  # flv fallback sk
        'url': 'https://www.ceknito.sk/video/168380',
        'md5': '4dab7267e19a58681136963e2171697b',
        'info_dict': {
            'id': '168380',
            'ext': 'flv',
            'like_count': int,
            'description': 'Nuda vysokoškolákov',
            'uploader': 'matoo1993',
            'categories': ['Zábava'],
            'thumbnail': 'https://www.ceknito.sk/d/embed/000a/168380/player.jpg',
            'view_count': int,
            'age_limit': 0,
            'title': 'Nuda vysokoškolákov',
            'upload_date': '20080614',
            'timestamp': 1213433040,
        },
    }, {  # mp4 fallback eu
        'url': 'https://www.ceknito.eu/video/365744',
        'md5': 'd666d41ce0030f0539e7eee0520cc4a1',
        'info_dict': {
            'id': '365744',
            'ext': 'mp4',
            'categories': ['Lietadlá a lode'],
            'thumbnail': 'https://www.ceknito.sk/d/embed/0016/365744/player.jpg',
            'view_count': int,
            'age_limit': 0,
            'title': 'UFO nad Bratislavou',
            'uploader': 'gino2',
            'like_count': int,
            'description': 'CEKNITO',
            'timestamp': 1247332680,
            'upload_date': '20090711',
        },
    }, {  # 360p cz age restricted
        'url': 'https://www.ceknito.cz/video/257225',
        'md5': 'a82bc2d992c86acd5b16fbde7ed28046',
        'info_dict': {
            'id': '257225',
            'ext': 'mp4',
            'like_count': int,
            'duration': 372.0,
            'view_count': int,
            'description': 'Sněhurva porno',
            'title': 'Sněhurva - Kreslené srandovní PORNO',
            'categories': ['Zábava'],
            'uploader': 'Shadow2045',
            'thumbnail': 'https://www.ceknito.sk/d/embed/000f/257225/player.jpg',
            'age_limit': 18,
            'timestamp': 1227392700,
            'upload_date': '20081122',
        },
    }, {  # edge case where the xml is not generated
        'url': 'https://www.ceknito.sk/video/2525',
        'md5': '65c7d20426a5c6142b7da58cf9434b6a',
        'info_dict': {
            'id': '2525',
            'ext': 'flv',
            'description': 'vec-gde_ste',
            'view_count': int,
            'title': 'VEC - Kde ste',
            'upload_date': '20070120',
            'thumbnail': 'https://www.ceknito.sk/d/embed/0000/2525/player.jpg',
            'timestamp': 1169292360,
            'uploader': 'misha',
            'categories': ['Hudba a tanec'],
            'like_count': int,
        },
        'expected_warnings': ['Unable to download XML'],
    }, {  # non-existent video
        'url': 'https://www.ceknito.sk/video/275000',
        'info_dict': {
            'id': '275000',
            'ext': 'flv',
        },
        'skip': 'Video does not exist',
    }]

    @staticmethod
    def convert_to_timestamp(date_str):
        months = {
            'ledna': 1, 'února': 2, 'března': 3, 'dubna': 4, 'května': 5, 'června': 6,
            'července': 7, 'srpna': 8, 'září': 9, 'října': 10, 'listopadu': 11, 'prosince': 12,
            'január': 1, 'február': 2, 'marec': 3, 'apríl': 4, 'máj': 5, 'jún': 6,
            'júl': 7, 'august': 8, 'september': 9, 'október': 10, 'november': 11, 'december': 12,
        }

        # The site only provides dates in a format like "20:05, 4.október.07" in Slovak
        # or alternatively "20:05, 4.října.07" on the Czech version on its play page
        match = re.match(r'([0-9]*):([0-9]*), ([0-9]*)\.([^\.]*)\.([0-9]*)', date_str.strip())
        if not match:
            return None

        hour, minute, day, month_name, year = match.groups()
        if month_name not in months:
            return None

        hour = int(hour)
        minute = int(minute)
        day = int(day)
        month = months[month_name]
        year = int('20' + year)

        # Handling DST before converting to timestamp
        tz = dt.timezone(dt.timedelta(hours=1), 'CET')
        dt_obj = dt.datetime(year, month, day, hour, minute, tzinfo=tz)
        start_dst = dt.datetime(year, 3, (31 - (dt.datetime(year, 3, 31).weekday() + 1) % 7), 2, tzinfo=tz)
        end_dst = dt.datetime(year, 10, (31 - (dt.datetime(year, 10, 31).weekday() + 1) % 7), 3, tzinfo=tz)

        if start_dst <= dt_obj < end_dst:
            dt_obj = dt_obj - dt.timedelta(hours=1)

        return int(dt_obj.timestamp())

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        file_id = self._search_regex(r'>var videoFID = \'([0-9a-f\/]*)\';<', webpage, 'file id')
        if file_id == '' and self._html_extract_title(webpage, default='').startswith('Video neexistuje'):
            raise ExtractorError('Video does not exist', expected=True)

        # Old videos don't have sources defined in the xml
        # however in these cases these fallback formats are used
        formats = [{
            'format_id': extension,
            'url': f'https://vid.ceknito.sk/{file_id}.{extension}',
            'source_preference': -2,
        } for extension in ['flv', 'mp4']]
        self._check_formats(formats, video_id)

        # There is an edge case where the xml may not exist at all, see id 2525
        info_xml = self._download_xml(f'https://www.ceknito.sk/xml/video.xml?fid={file_id}', video_id, fatal=False)
        if info_xml:
            duration = parse_duration(info_xml.find('duration').text) if info_xml.find('duration') is not None else None
            age_limit = 0 if info_xml.find('xrated') is None or info_xml.find('xrated').text == 'no' else 18

            if info_xml.find('sources') is not None:
                for source in info_xml.find('sources'):
                    formats.append({
                        'format_id': source.attrib['resolution'],
                        'url': source.attrib['url'],
                    })
        else:
            duration = None
            age_limit = None

        return {
            'id': video_id,
            'title': self._og_search_title(webpage) or self._html_search_regex(r'<h1>(.+?)</h1>', webpage, 'title'),
            'description': self._og_search_description(webpage),
            'thumbnail': self._og_search_thumbnail(webpage),
            'uploader': self._search_regex(
                r'<span class="one">P.idal:<br \/><strong><a href="http:\/\/www\.ceknito\...\/channel\/([a-zA-Z0-9]*)',
                webpage, 'uploader', fatal=False),
            'duration': duration,
            'formats': formats,
            'timestamp': self.convert_to_timestamp(
                self._search_regex(r'<span class="two">P.idan.:<br \/><strong>([^<]*)', webpage, 'timestamp', fatal=False)),
            'view_count': int_or_none(self._search_regex(r'<span class="info">Zobrazení <strong>([0-9]+)<\/strong>', webpage, 'view count', fatal=False)),
            'like_count': int_or_none(self._search_regex(r' \| Ob..bené <strong>([0-9]+)<\/strong>', webpage, 'like count', fatal=False)),
            'age_limit': age_limit,
            'categories': [self._search_regex(r'<span class="two">Kateg.ri.:<br \/><strong>([^<]*)', webpage, 'uploader', fatal=False)],
        }
