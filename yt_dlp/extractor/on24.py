# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..compat import (
    compat_str,
    compat_urlparse,
)
from ..utils import strip_or_none


class On24IE(InfoExtractor):
    IE_NAME = 'on24'
    IE_DESC = 'ON24'

    _VALID_URL = r'''(?x)
                (?:
                    https?://event\.on24\.com/
                        (?:
                            wcc/r/(?P<id_1>\d{7})/(?P<key_1>[0-9A-F]{32})|
                            eventRegistration/
                                (?:
                                    console/EventConsoleApollo\.jsp\?|
                                    EventLobbyServlet\?target=lobby30\.jsp&
                                )
                                (?:uimode=nextgeneration&)?(?:&)?eventid=(?P<id_2>\d{7})(?:&sessionid=1)?.*&key=(?P<key_2>[0-9A-F]{32})
                        )
                )
                '''

    _TESTS = [{
        'url': 'https://event.on24.com/eventRegistration/console/EventConsoleApollo.jsp?uimode=nextgeneration&eventid=2197467&sessionid=1&key=5DF57BE53237F36A43B478DD36277A84&contenttype=A&eventuserid=305999&playerwidth=1000&playerheight=650&caller=previewLobby&text_language_id=en&format=fhaudio&newConsole=false',
        'info_dict': {
            'id': '2197467',
            'ext': 'wav',
            'title': 'Pearson Test of English General/Pearson English International Certificate Teacher Training Guide',
            'upload_date': '20200219',
            'timestamp': 1582149600.0,
        }
    }, {
        'url': 'https://event.on24.com/wcc/r/2639291/82829018E813065A122363877975752E?mode=login&email=johnsmith@gmail.com',
        'only_matching': True,
    }, {
        'url': 'https://event.on24.com/eventRegistration/console/EventConsoleApollo.jsp?&eventid=2639291&sessionid=1&username=&partnerref=&format=fhvideo1&mobile=&flashsupportedmobiledevice=&helpcenter=&key=82829018E813065A122363877975752E&newConsole=true&nxChe=true&newTabCon=true&text_language_id=en&playerwidth=748&playerheight=526&eventuserid=338788762&contenttype=A&mediametricsessionid=384764716&mediametricid=3558192&usercd=369267058&mode=launch',
        'only_matching': True,
    }]

    @staticmethod
    def _is_absolute(url):
        return bool(compat_urlparse.urlparse(url).netloc)

    def _real_extract(self, url):
        mobj = re.match(self._VALID_URL, url)
        event_id = mobj.group('id_1') or mobj.group('id_2')
        event_key = mobj.group('key_1') or mobj.group('key_2')

        event_data = self._download_json(
            'https://event.on24.com/apic/utilApp/EventConsoleCachedServlet',
            event_id, query={
                'eventId': event_id,
                'displayProfile': 'player',
                'key': event_key,
                'contentType': 'A'
            })
        
        event_id = compat_str(event_data.get('presentationLogInfo', {}).get('eventid')) or event_id

        info_media = event_data.get('mediaUrlInfo', {})
        info_media.sort(key=lambda m: m['id'])

        formats = []
        for m in info_media:
            media_url = compat_str(m['url'])
            if not self._is_absolute(media_url):
                media_url = 'https://event.on24.com/media/news/corporatevideo/events/%s' % media_url
            if m['code'] == 'fhvideo1':
                formats.append({
                    'format_id': 'video',
                    'url': media_url,
                    'ext': 'mp4',
                    'vcodec': 'avc1.640020',
                    'acodec': 'mp4a.40.2',
                })
            elif m['code'] == 'audio':
                formats.append({
                    'format_id': 'audio',
                    'url': media_url,
                    'ext': 'wav',
                    'vcodec': 'none',
                    'acodec': 'wav'
                })
        self._sort_formats(formats)

        return {
            'id': event_id,
            'title': strip_or_none(event_data.get('description')),
            'language': event_data.get('localelanguagecode'),
            'timestamp': (event_data.get('session', {}).get('startdate') / 1000
                          if event_data.get('session', {}).get('startdate') is not None else None),
            'webpage_url': 'https://event.on24.com/wcc/r/%s/%s' % (event_id, event_key),
            'view_count': event_data.get('registrantcount'),
            'formats': formats,
        }
