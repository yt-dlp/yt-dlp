from .common import InfoExtractor


class RadioDeIE(InfoExtractor):
    _WORKING = False
    IE_NAME = 'radio.de'
    _VALID_URL = r'https?://(?P<id>.+?)\.(?:radio\.(?:de|at|fr|pt|es|pl|it)|rad\.io)'
    _TEST = {
        'url': 'http://ndr2.radio.de/',
        'info_dict': {
            'id': 'ndr2',
            'ext': 'mp3',
            'title': 're:^NDR 2 [0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}$',
            'description': 'md5:591c49c702db1a33751625ebfb67f273',
            'thumbnail': r're:^https?://.*\.png',
            'is_live': True,
        },
        'params': {
            'skip_download': True,
        },
    }

    def _real_extract(self, url):
        radio_id = self._match_id(url)
        webpage = self._download_webpage(url, radio_id)
        jscode = self._search_regex(
            r"'components/station/stationService':\s*\{\s*'?station'?:\s*(\{.*?\s*\}),\n",
            webpage, 'broadcast')

        broadcast = self._parse_json(jscode, radio_id)
        title = broadcast['name']
        description = broadcast.get('description') or broadcast.get('shortDescription')
        thumbnail = broadcast.get('picture4Url') or broadcast.get('picture4TransUrl') or broadcast.get('logo100x100')

        formats = [{
            'url': stream['streamUrl'],
            'ext': stream['streamContentFormat'].lower(),
            'acodec': stream['streamContentFormat'],
            'abr': stream['bitRate'],
            'asr': stream['sampleRate'],
        } for stream in broadcast['streamUrls']]

        return {
            'id': radio_id,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'is_live': True,
            'formats': formats,
        }
