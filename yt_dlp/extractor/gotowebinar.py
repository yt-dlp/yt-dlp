from .common import InfoExtractor
from ..utils import ExtractorError


class GoTo_WebinarIE(InfoExtractor):
    _VALID_URL = r'https?://(register|attendee)\.gotowebinar\.com/recording/viewRecording/(?P<webinar_key>[0-9]+)/(?P<recording_key>[0-9]+)/(?P<email>[^?]+)(?:\?registrantKey=(?P<registrant_key>[0-9]+))?'
    _TESTS = [
        {
            # Source: https://community.intel.com/t5/Processors/Deriving-core-numbering-on-sockets-without-disabled-tiles/m-p/1263389
            'url': 'https://register.gotowebinar.com/recording/viewRecording/8573274081823101697/1166504161772360449/mfratkin@tacc.utexas.edu?registrantKey=6636963737074316811&type=ATTENDEEEMAILRECORDINGLINK',
            'info_dict': {
                'id': '8573274081823101697-1166504161772360449',
                'title': 'Topology and Cache Coherence in Knights Landing and Skylake Xeon Processors',
                'description': 'md5:2d673910d31bfb4918a0605ea60561dd',
                'creators': ['IXPUG Committee'],
                'ext': 'mp4',
            },
        },
    ]

    def _real_extract(self, url):
        webinar_key, recording_key, email, registrant_key = self._match_valid_url(url).group('webinar_key', 'recording_key', 'email', 'registrant_key')
        video_id = f'{webinar_key}-{recording_key}'

        if not registrant_key:
            registrant_metadata = self._download_json(
                f'https://globalattspa.gotowebinar.com/api/webinars/{webinar_key}/registrants?email={email}',
                video_id,
                note='Downloading registrant metadata',
                errnote='Unable to download registrant metadata')
            if not (registrant_key := registrant_metadata.get('registrantKey')):
                raise ExtractorError('Unable to retrieve registrant key')

        important_metadata = self._download_json(
            f'https://api.services.gotomeeting.com/registrationservice/api/v1/webinars/{webinar_key}/registrants/{registrant_key}/recordingAssets?type=FOLLOWUPEMAILRECORDINGLINK&client=spa',
            video_id,
            note='Downloading important recording metadata',
            errnote='Unable to important download recording metadata')

        non_important_metadata = self._download_json(
            f'https://global.gotowebinar.com/api/webinars/{webinar_key}',
            video_id,
            note='Downloading non-important recording metadata',
            errnote='Unable to non-important download recording metadata',
            fatal=False)

        creator = non_important_metadata.get('organizerName')

        return {
            'id': video_id,
            'url': important_metadata.get('cdnLocation'),
            'ext': 'mp4',
            'is_live': False,
            'title': non_important_metadata.get('subject'),
            'description': non_important_metadata.get('description'),
            'creators': [creator] if creator else None,
        }
