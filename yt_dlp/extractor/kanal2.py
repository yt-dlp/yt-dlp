# coding: utf-8
from __future__ import unicode_literals
from datetime import datetime
import re
import time
from .common import InfoExtractor
from ..utils import ExtractorError


class Kanal2IE(InfoExtractor):
    SUBTITLE_DATE_RE = re.compile(r'\((\d{2}\.\d{2}\.\d{4}\s\d{2}:\d{2})\)$')

    _VALID_URL = r'(?P<base>https?://.+\.postimees\.ee)[a-zA-Z0-9/._-]+\?[a-zA-Z0-9=&._-]*id=(?P<id>[a-zA-Z0-9_-]+)[^ ]*'
    _TESTS = [
        {
            'note': 'Test standard url (#18547)',
            'url': 'https://kanal2.postimees.ee/pluss/video/?id=40792',
            'md5': 'cecaf3e17706d725b1f23e886b67f8d3',
            'info_dict': {
                'id': '40792',
                'ext': 'mp4',
                'title': 'Aedniku aabits / Osa 53  (05.08.2016 20:00)',
                'thumbnail': 'https://kanal-dl.babahhcdn.com/kanal/2016/08/05/0053_HNqKsIA/img/2.jpg',
                'description': 'Aedniku aabits" on saade, mis pakub kaasaelamist ja teadmisi nii algajatele, kui juba kogenud rohenäppudele. Kõik alates vajalikest näpunäidetest, nutikatest lahendustest, uudistoodetest kuni taimede hingeeluni ning aias kasutatava tehnikani välja.',
                'upload_date': '20160805',
                'timestamp': 1470416400,
            }
        },
    ]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        playlist = self.get_playlist(video_id)

        info = {
            'id': video_id,
            'title': self.get_title(playlist['info']),
            'description': playlist['info'].get('description'),
            'webpage_url': playlist['data'].get('url'),
            'thumbnail': playlist['data'].get('image'),
            'formats': self.get_formats(playlist, video_id),
            'timestamp': self.get_timestamp(playlist['info']['subtitle']),
        }

        return info

    def get_title(self, info):
        title = info['title']

        if info['subtitle']:
            title += ' / ' + info['subtitle']

        return title

    def get_timestamp(self, subtitle):
        # Extract timestamp from:
        #  "subtitle": "Osa 53  (05.08.2016 20:00)",
        match = self._search_regex(self.SUBTITLE_DATE_RE, subtitle, 'dateandtime', default=None)
        if not match:
            return None

        # https://stackoverflow.com/a/27914405/2314626
        date = datetime.strptime(match, '%d.%m.%Y %H:%M')
        unixtime = time.mktime(date.timetuple())

        return int(unixtime)

    def get_formats(self, playlist, video_id):
        formats = []
        session = self.get_session(playlist['data']['path'], video_id)
        sid = session.get('session')
        for stream in playlist['data']['streams']:
            formats.append({
                'protocol': 'm3u8',
                'ext': 'mp4',
                'url': stream.get('file') + '&s=' + sid,
            })

        self._sort_formats(formats)

        return formats

    def get_playlist(self, video_id):
        url = 'https://kanal2.postimees.ee/player/playlist/%(video_id)s?type=episodes' % {'video_id': video_id}
        headers = {
            'X-Requested-With': 'XMLHttpRequest',
        }

        return self._download_json(url, video_id, headers=headers)

    def get_session(self, path, video_id):
        url = 'https://sts.postimees.ee/session/register'
        headers = {
            'X-Original-URI': path,
            'Accept': 'application/json',
        }
        session = self._download_json(url, video_id, headers=headers,
                                      note='Creating session',
                                      errnote='Error creating session')
        if session['reason'] != 'OK':
            raise ExtractorError('%s: Unable to obtain session' % self.IE_NAME)

        return session
