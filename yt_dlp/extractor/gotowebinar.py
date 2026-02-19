from .common import InfoExtractor
from ..utils import ExtractorError, parse_iso8601, traverse_obj


class GoToWebinarIE(InfoExtractor):
    _VALID_URL = r'''(?x)https?://
        (register|attendee)\.gotowebinar\.com/recording/viewRecording/
        (?P<webinar_key>[0-9]+)/(?P<recording_key>[0-9]+)/(?P<email>[^?#]+)
        (?:\?(?:[^#]+&)?registrantKey=(?P<registrant_key>[0-9]+))?'''
    _TESTS = [
        {
            # Source: https://associationofanaesthetists-publications.onlinelibrary.wiley.com/doi/am-pdf/10.1111/anae.15209
            'url': 'https://register.gotowebinar.com/recording/viewRecording/8054623469383961613/3917240379133570566/andrewmortimore@anaesthetists.org?registrantKey=2674782344143402252&type=ABSENTEEEMAILRECORDINGLINK',
            'info_dict': {
                'id': '8054623469383961613',
                'title': 'Webinar: COVID-19: By Trainees, For Trainees ',
                'description': 'md5:9702e0662f45ee74ff2168de4d6d5d6a',
                'creators': ['E-education Dept'],
                'timestamp': 1590824700,
                'upload_date': '20200530',
                'ext': 'mp4',
            },
        },
        {
            'url': 'https://attendee.gotowebinar.com/recording/viewRecording/7594846188203875084/5457693551948244743/stoll@berkeley.edu',
            'info_dict': {
                'id': '7594846188203875084',
                'title': 'Climate change, mental health, and eco-anxiety:  How the global pandemic can help us prepare',
                'description': 'md5:390f0dffd516a53a4728bd755c85def4',
                'creators': ['Environmental  Public Health'],
                'timestamp': 1586548800,
                'upload_date': '20200410',
                'ext': 'mp4',
            },
        },
    ]

    def _real_extract(self, url):
        webinar_key, email, registrant_key = self._match_valid_url(url).group(
            'webinar_key', 'email', 'registrant_key',
        )

        if not registrant_key:
            registrant_metadata = self._download_json(
                f'https://globalattspa.gotowebinar.com/api/webinars/{webinar_key}/registrants?email={email}',
                webinar_key,
                note='Downloading registrant metadata',
                errnote='Unable to download registrant metadata',
            )
            if not (registrant_key := registrant_metadata.get('registrantKey')):
                raise ExtractorError('Unable to retrieve registrant key')

        recording_data = self._download_json(
            f'https://api.services.gotomeeting.com/registrationservice/api/v1/webinars/{webinar_key}/registrants/{registrant_key}/recordingAssets?type=FOLLOWUPEMAILRECORDINGLINK&client=spa',
            webinar_key,
            note='Downloading important recording metadata',
            errnote='Unable to important download recording metadata',
        )

        metadata = self._download_json(
            f'https://global.gotowebinar.com/api/webinars/{webinar_key}',
            webinar_key,
            note='Downloading non-important recording metadata',
            errnote='Unable to non-important download recording metadata',
            fatal=False,
        )

        return {
            'id': webinar_key,
            'url': recording_data.get('cdnLocation'),
            'ext': 'mp4',
            'is_live': False,
            **traverse_obj(metadata, {
                'title': ('subject', {str}),
                'description': ('description', {str}),
                'creators': ('organizerName', {str}, all),
                'timestamp': ('times', 0, 'startTime', {parse_iso8601}),
            }),
        }
