from .common import InfoExtractor
from ..utils import (
    int_or_none,
    strip_or_none,
    try_get,
    urljoin,
)


class On24IE(InfoExtractor):
    IE_NAME = 'on24'
    IE_DESC = 'ON24'

    _ID_RE = r'(?P<id>\d{7})'
    _KEY_RE = r'(?P<key>[0-9A-F]{32})'
    _URL_BASE_RE = r'https?://event\.on24\.com'
    _URL_QUERY_RE = rf'(?:[^#]*&)?eventid={_ID_RE}&(?:[^#]+&)?key={_KEY_RE}'
    _VALID_URL = [
        rf'{_URL_BASE_RE}/wcc/r/{_ID_RE}/{_KEY_RE}',
        rf'{_URL_BASE_RE}/eventRegistration/console/(?:EventConsoleApollo\.jsp|apollox/mainEvent/?)\?{_URL_QUERY_RE}',
        rf'{_URL_BASE_RE}/eventRegistration/EventLobbyServlet/?\?{_URL_QUERY_RE}',
    ]

    _TESTS = [{
        'url': 'https://event.on24.com/eventRegistration/console/EventConsoleApollo.jsp?uimode=nextgeneration&eventid=2197467&sessionid=1&key=5DF57BE53237F36A43B478DD36277A84&contenttype=A&eventuserid=305999&playerwidth=1000&playerheight=650&caller=previewLobby&text_language_id=en&format=fhaudio&newConsole=false',
        'info_dict': {
            'id': '2197467',
            'ext': 'wav',
            'title': 'Pearson Test of English General/Pearson English International Certificate Teacher Training Guide',
            'upload_date': '20200219',
            'timestamp': 1582149600.0,
            'view_count': int,
        },
    }, {
        'url': 'https://event.on24.com/wcc/r/2639291/82829018E813065A122363877975752E?mode=login&email=johnsmith@gmail.com',
        'only_matching': True,
    }, {
        'url': 'https://event.on24.com/eventRegistration/console/EventConsoleApollo.jsp?&eventid=2639291&sessionid=1&username=&partnerref=&format=fhvideo1&mobile=&flashsupportedmobiledevice=&helpcenter=&key=82829018E813065A122363877975752E&newConsole=true&nxChe=true&newTabCon=true&text_language_id=en&playerwidth=748&playerheight=526&eventuserid=338788762&contenttype=A&mediametricsessionid=384764716&mediametricid=3558192&usercd=369267058&mode=launch',
        'only_matching': True,
    }, {
        'url': 'https://event.on24.com/eventRegistration/EventLobbyServlet?target=reg20.jsp&eventid=3543176&key=BC0F6B968B67C34B50D461D40FDB3E18&groupId=3143628',
        'only_matching': True,
    }, {
        'url': 'https://event.on24.com/eventRegistration/console/apollox/mainEvent?&eventid=4843671&sessionid=1&username=&partnerref=&format=fhvideo1&mobile=&flashsupportedmobiledevice=&helpcenter=&key=4EAC9B5C564CC98FF29E619B06A2F743&newConsole=true&nxChe=true&newTabCon=true&consoleEarEventConsole=false&consoleEarCloudApi=false&text_language_id=en&playerwidth=748&playerheight=526&referrer=https%3A%2F%2Fevent.on24.com%2Finterface%2Fregistration%2Fautoreg%2Findex.html%3Fsessionid%3D1%26eventid%3D4843671%26key%3D4EAC9B5C564CC98FF29E619B06A2F743%26email%3D000a3e42-7952-4dd6-8f8a-34c38ea3cf02%2540platform%26firstname%3Ds%26lastname%3Ds%26deletecookie%3Dtrue%26event_email%3DN%26marketing_email%3DN%26std1%3D0642572014177%26std2%3D0642572014179%26std3%3D550165f7-a44e-4725-9fe6-716f89908c2b%26std4%3D0&eventuserid=745776448&contenttype=A&mediametricsessionid=640613707&mediametricid=6810717&usercd=745776448&mode=launch',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        event_id, event_key = self._match_valid_url(url).group('id', 'key')

        event_data = self._download_json(
            'https://event.on24.com/apic/utilApp/EventConsoleCachedServlet',
            event_id, query={
                'eventId': event_id,
                'displayProfile': 'player',
                'key': event_key,
                'contentType': 'A',
            })
        event_id = str(try_get(event_data, lambda x: x['presentationLogInfo']['eventid'])) or event_id
        language = event_data.get('localelanguagecode')

        formats = []
        for media in event_data.get('mediaUrlInfo', []):
            media_url = urljoin('https://event.on24.com/media/news/corporatevideo/events/', str(media.get('url')))
            if not media_url:
                continue
            media_type = media.get('code')
            if media_type == 'fhvideo1':
                formats.append({
                    'format_id': 'video',
                    'url': media_url,
                    'language': language,
                    'ext': 'mp4',
                    'vcodec': 'avc1.640020',
                    'acodec': 'mp4a.40.2',
                })
            elif media_type == 'audio':
                formats.append({
                    'format_id': 'audio',
                    'url': media_url,
                    'language': language,
                    'ext': 'wav',
                    'vcodec': 'none',
                    'acodec': 'wav',
                })

        return {
            'id': event_id,
            'title': strip_or_none(event_data.get('description')),
            'timestamp': int_or_none(try_get(event_data, lambda x: x['session']['startdate']), 1000),
            'webpage_url': f'https://event.on24.com/wcc/r/{event_id}/{event_key}',
            'view_count': event_data.get('registrantcount'),
            'formats': formats,
        }
