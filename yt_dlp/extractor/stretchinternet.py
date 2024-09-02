from .common import InfoExtractor


class StretchInternetIE(InfoExtractor):
    _VALID_URL = r'https?://portal\.stretchinternet\.com/[^/]+/(?:portal|full)\.htm\?.*?\beventId=(?P<id>\d+)'
    _TEST = {
        'url': 'https://portal.stretchinternet.com/umary/portal.htm?eventId=573272&streamType=video',
        'info_dict': {
            'id': '573272',
            'ext': 'mp4',
            'title': 'UNIVERSITY OF MARY WRESTLING VS UPPER IOWA',
            # 'timestamp': 1575668361,
            # 'upload_date': '20191206',
            'uploader_id': '99997',
        },
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)

        media_url = self._download_json(
            'https://core.stretchlive.com/trinity/event/tcg/' + video_id,
            video_id)[0]['media'][0]['url']
        event = self._download_json(
            'https://neo-client.stretchinternet.com/portal-ws/getEvent.json',
            video_id, query={'eventID': video_id, 'token': 'asdf'})['event']

        return {
            'id': video_id,
            'title': event['title'],
            # TODO: parse US timezone abbreviations
            # 'timestamp': event.get('dateTimeString'),
            'url': 'https://' + media_url,
            'uploader_id': event.get('ownerID'),
        }
