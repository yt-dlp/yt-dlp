import json
import threading
import uuid

from .common import FileDownloader
from . import HlsFD
from ..networking.common import Request
from ..networking.exceptions import network_exceptions


class ZaikoJwtFD(FileDownloader):
    """
    Downloads JWT protected Zaiko VODs with required pings
    Note, this is not a part of public API, and will be removed without notice.
    DO NOT USE
    """

    def real_download(self, filename, info_dict):
        self.to_screen(f'[{self.FD_NAME}] Downloading Zaiko JWT VOD HLS')
        fd = HlsFD(self.ydl, self.params)
        ping_params = info_dict['_ping_params']

        stop_event = threading.Event()
        refresh_thread = threading.Thread(
            target=self._ping_thread,
            args=(stop_event, ping_params),
        )
        refresh_thread.start()

        try:
            return fd.real_download(filename, info_dict)
        finally:
            stop_event.set()

    def _ping_thread(self, stop_event, ping_params):
        player_uuid = str(uuid.uuid4())[0:8]

        while not stop_event.wait(ping_params['interval'] / 1000):
            try:
                self.ydl.urlopen(Request(
                    f'https://live.zaiko.services/event/{ping_params["event_id"]}/status',
                    query={'options': ping_params['options']},
                    headers={'Referer': ping_params['referrer']})).read()

                self.ydl.urlopen(Request(
                    f'https://live.zaiko.services/playerapi/event/{ping_params["event_id"]}',
                    method='POST',
                    data=json.dumps({
                        'external_id': ping_params['external_id'],
                        'log': {
                            'video_quality': 480,
                            'is_playing': True,
                            'current_player_time': 0,
                            'full_screen': False,
                            'is_auto': True,
                            'player_uuid': player_uuid,
                        },
                    }).encode(),
                    headers={
                        'Content-Type': 'application/json',
                        'Origin': 'https://live.zaiko.services',
                        'Referer': ping_params['referrer'],
                    })).read()
            except network_exceptions as e:
                self.to_screen(f'[{self.FD_NAME}] Ping failed: {e}')
