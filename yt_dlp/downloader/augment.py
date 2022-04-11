from __future__ import division, unicode_literals

import threading
import typing

if typing.TYPE_CHECKING:
    from .common import FileDownloader

from ..utils import (
    sanitized_Request,
)


class Augment():
    _AUGMENT_KEY = None

    def __init__(self, dl: 'FileDownloader', info_dict, params: dict) -> None:
        self.dl = dl
        self.ydl = dl.ydl

        if 'init_callback' in params:
            info_dict, params = params['init_callback'](info_dict, params)

        self.params = params
        self.info_dict = info_dict

        # children classes may:
        # - implement some more initialization tasks
        # - modify info_dict directly to make things pass through Augment
        # at their __init__

    def __enter__(self):
        self.start()
        return self

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
    """
    Augment for heartbeating.

    Keys:

    interval:  Interval to wait, in seconds.
    callback:  Callable to run periodically. Arguments are: (HeartbeatAugment)
               "url" and "data" are ignored once this key is used.
    url:       (easy mode) URL to reqeust to. Cannot be used with "callback" key
    data:      (optional) POST payload to pass. Use if needed.
    before_dl: Callable to run before download starts. Arguments are: (HeartbeatAugment)
               Can be used even if any of "callback", "url" and "data" are used.
    after_dl: Callable to run after download ends. Arguments are: (HeartbeatAugment)
    """
    _AUGMENT_KEY = 'heartbeat'

    def __init__(self, dl: 'FileDownloader', info_dict, params: dict) -> None:
        super().__init__(dl, info_dict, params)
        params, info_dict = self.params, self.info_dict

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

            def callback(a):
                self.ydl.urlopen(request).read()

            self.callback = callback
        else:
            raise Exception('Callback is not provided')

    def start(self):
        self.complete = False

        def heartbeat():
            try:
                self.callback(self)
            except Exception:
                self.to_screen('[download] Heartbeat failed')

            with self.lock:
                if self.complete:
                    self.timer[0] = None
                    self.complete = False
                else:
                    self.timer[0] = threading.Timer(self.interval, heartbeat)
                    self.timer[0].start()

        if 'before_dl' in self.params:
            self.params['before_dl'](self)

        heartbeat()

    def end(self):
        with self.lock:
            self.timer[0].cancel()
            self.complete = True
        if 'after_dl' in self.params:
            self.params['after_dl'](self)


AUGMENT_MAP = {v._AUGMENT_KEY: v for v in (HeartbeatAugment, )}
