from .common import InfoExtractor
from ..utils import (
    int_or_none,
    try_get,
    unified_timestamp,
)


class CiscoWebexIE(InfoExtractor):
    IE_NAME = 'ciscowebex'
    IE_DESC = 'Cisco Webex'
    _VALID_URL = r'''(?x)
                    (?P<url>https?://(?P<subdomain>[^/#?]*)\.webex\.com/(?:
                        (?P<siteurl_1>[^/#?]*)/(?:ldr|lsr).php\?(?:[^#]*&)*RCID=(?P<rcid>[0-9a-f]{32})|
                        (?:recordingservice|webappng)/sites/(?P<siteurl_2>[^/#?]*)/recording/(?:playback/|play/)?(?P<id>[0-9a-f]{32})
                    ))'''

    _TESTS = [{
        'url': 'https://demosubdomain.webex.com/demositeurl/ldr.php?RCID=e58e803bc0f766bb5f6376d2e86adb5b',
        'only_matching': True,
    }, {
        'url': 'http://demosubdomain.webex.com/demositeurl/lsr.php?RCID=bc04b4a7b5ea2cc3a493d5ae6aaff5d7',
        'only_matching': True,
    }, {
        'url': 'https://demosubdomain.webex.com/recordingservice/sites/demositeurl/recording/88e7a42f7b19f5b423c54754aecc2ce9/playback',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        rcid = mobj.group('rcid')
        if rcid:
            webpage = self._download_webpage(url, None, note='Getting video ID')
            url = self._search_regex(self._VALID_URL, webpage, 'redirection url', group='url')
        url = self._request_webpage(url, None, note='Resolving final URL').geturl()
        mobj = self._match_valid_url(url)
        subdomain = mobj.group('subdomain')
        siteurl = mobj.group('siteurl_1') or mobj.group('siteurl_2')
        video_id = mobj.group('id')

        stream = self._download_json(
            'https://%s.webex.com/webappng/api/v1/recordings/%s/stream' % (subdomain, video_id),
            video_id, fatal=False, query={'siteurl': siteurl})
        if not stream:
            self.raise_login_required(method='cookies')

        video_id = stream.get('recordUUID') or video_id

        formats = [{
            'format_id': 'video',
            'url': stream['fallbackPlaySrc'],
            'ext': 'mp4',
            'vcodec': 'avc1.640028',
            'acodec': 'mp4a.40.2',
        }]
        if stream.get('preventDownload') is False:
            mp4url = try_get(stream, lambda x: x['downloadRecordingInfo']['downloadInfo']['mp4URL'])
            if mp4url:
                formats.append({
                    'format_id': 'video',
                    'url': mp4url,
                    'ext': 'mp4',
                    'vcodec': 'avc1.640028',
                    'acodec': 'mp4a.40.2',
                })
            audiourl = try_get(stream, lambda x: x['downloadRecordingInfo']['downloadInfo']['audioURL'])
            if audiourl:
                formats.append({
                    'format_id': 'audio',
                    'url': audiourl,
                    'ext': 'mp3',
                    'vcodec': 'none',
                    'acodec': 'mp3',
                })
        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': stream['recordName'],
            'description': stream.get('description'),
            'uploader': stream.get('ownerDisplayName'),
            'uploader_id': stream.get('ownerUserName') or stream.get('ownerId'),  # mail or id
            'timestamp': unified_timestamp(stream.get('createTime')),
            'duration': int_or_none(stream.get('duration'), 1000),
            'webpage_url': 'https://%s.webex.com/recordingservice/sites/%s/recording/playback/%s' % (subdomain, siteurl, video_id),
            'formats': formats,
        }
