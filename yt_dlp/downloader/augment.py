from __future__ import division, unicode_literals

import threading

from .common import FileDownloader
from ..utils import (
    sanitized_Request,
)


class Augment():
    _AUGMENT_KEY = None

    def __init__(self, dl: FileDownloader, info_dict, params: dict) -> None:
        self.dl = dl
        self.ydl = dl.ydl
        self.params = params
        self.info_dict = info_dict
        # children classes may implement some more initialization tasks
        # at their __init__

    def __enter__(self):
        self.start()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end()

    def start(self):
        """
            Starts augmented service.
            Calling start() 2 or more times without end()ing is not permitted.
        """
        raise Exception('Implement in inheriting class')

    def end(self):
        """ Stops augmented service, as well as cleanups """
        raise Exception('Implement in inheriting class')


class HeartbeatAugment(Augment):
    _AUGMENT_KEY = 'heartbeat'

    def __init__(self, dl: FileDownloader, info_dict, params: dict) -> None:
        super().__init__(dl, info_dict, params)

        self.interval = params.get('interval', 30)
        self.lock = threading.Lock()
        self.timer = [None]

        if 'callback' in params:
            self.callback = params['callback']
        elif 'url' in params:
            heartbeat_url = params['url']
            heartbeat_data = params.get('data')
            if isinstance(heartbeat_data, str):
                heartbeat_data = heartbeat_data.encode()
            request = sanitized_Request(heartbeat_url, heartbeat_data)

            def callback():
                try:
                    self.ydl.urlopen(request).read()
                except Exception:
                    self.to_screen('[download] Heartbeat failed')

            self.callback = callback
        else:
            raise Exception('Callback is not provided')

    def start(self):
        self.complete = False
        def heartbeat():
            self.callback()

            with self.lock:
                if not self.complete:
                    self.timer[0] = threading.Timer(self.interval, heartbeat)
                    self.timer[0].start()
        
        if 'before_dl' in self.params:
            self.params['before_dl']()

        heartbeat()

    def end(self):
        if self.lock:
            with self.lock:
                self.timer[0].cancel()
                self.complete = True
