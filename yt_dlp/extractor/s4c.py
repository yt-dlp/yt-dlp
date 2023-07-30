from .common import InfoExtractor

from ..utils import (
    traverse_obj
)


class S4CIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?s4c\.cymru/clic/programme/(?P<id>[0-9]+)'
    _TESTS = [{
        'url': 'https://www.s4c.cymru/clic/programme/861362209',
        'info_dict': {
            'id': '861362209',
            'ext': 'mp4',
            'title': 'Y Swn',
            'description': 'When Margaret Thatcher\'s government breaks a promise to establish a Welsh language channel in 1979 it unleashes a wave of anger across Wales.  This film portrays the efforts of the Welsh Language Society and Plaid Cymru to realise a television channel and Gwynfor Evans\'s declaration to fast until death over the matter.  A unique film about one of the most colourful chapters in modern Welsh history.',
            'duration': 5340
        }
    },
        {
        'url': 'https://www.s4c.cymru/clic/programme/856636948',
        'info_dict': {
            'id': '856636948',
            'ext': 'mp4',
            'title': 'Am Dro',
            'duration': 2880,
            'description': 'In this programme Geraint will be leading the crew on a walk through Llanelli while introducing them to some unusual creatures. Barney will be taking them on a walk along the border near Oswestry. Ena will be following St David\'s footsteps in Pembrokeshire, while Ann-Marie will take them up the mountain in Eglwysilan before descending to the town of Senghenydd',
        }
    },
    ]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        programme_metadata = self._download_json(f'https://www.s4c.cymru/df/full_prog_details?lang=e&programme_id={video_id}', video_id)

        programme_details = programme_metadata.get('full_prog_details') or []
        metadata = {
            'id': video_id,
            **traverse_obj(programme_details[0], {
                'description': ('full_billing', {str.strip}),
                'duration': ('duration', {lambda x: int(x) * 60}),
            })
        }

        title = programme_details[0].get('programme_title') or programme_details[0].get('series_title')

        metadata['title'] = title

        player_config = self._download_json(f'https://player-api.s4c-cdn.co.uk/player-configuration/prod?programme_id={video_id}&signed=0&lang=en&mode=od&appId=clic&streamName=', video_id)

        filename = player_config.get('filename')

        streaming_urls = self._download_json(f'https://player-api.s4c-cdn.co.uk/streaming-urls/prod?mode=od&application=clic&region=WW&extra=false&thirdParty=false&filename={filename}', filename)

        m3u8_url = streaming_urls.get('hls')

        formats = self._extract_m3u8_formats(
            m3u8_url, video_id, 'mp4', 'm3u8_native', m3u8_id='hls',
            note='Downloading HD m3u8 information', errnote='Unable to download HD m3u8 information')
        metadata['formats'] = formats
        return metadata
