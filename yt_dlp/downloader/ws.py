from __future__ import division, unicode_literals

import threading
import os
import signal
import asyncio
from websockets import connect

from .common import FileDownloader
from .external import FFmpegFD
from ..compat import compat_str


class LiveStreamSinkBaseFD(FileDownloader):
    """ Just a sink to ffmpeg for downloading fragments in any form """

    def real_download(self, filename, info_dict):
        new_infodict = {}
        new_infodict.update(info_dict)
        new_infodict['url'] = '-'

        async def call_conn(proc, stdin):
            try:
                self.real_connection(stdin, info_dict)
            finally:
                stdin.flush()
                stdin.close()
                os.kill(os.getpid(), signal.SIGINT)

        class FFmpegStdinFD(FFmpegFD):
            def on_process_started(self, proc, stdin):
                asyncio.run(call_conn(proc, stdin))

        return FFmpegStdinFD(self.ydl, self.params or {}).download(filename, new_infodict)

    async def real_connection(self, sink, info_dict):
        """
        Override this in subclasses.
        Just return the function if the stream have finished.
        """


class WebSocketFragmentFD(LiveStreamSinkBaseFD):
    async def real_connection(self, sink, info_dict):
        async with connect(info_dict['url'], extra_headers=info_dict.get('http_headers', {})) as ws:
            while True:
                recv = await ws.recv()
                if isinstance(recv, compat_str):
                    recv = recv.encode('utf8')
                sink.write(recv)
