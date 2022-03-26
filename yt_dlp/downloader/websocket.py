import os
import signal
import asyncio
import threading

try:
    import websockets
except (ImportError, SyntaxError):
    # websockets 3.10 on python 3.6 causes SyntaxError
    # See https://github.com/yt-dlp/yt-dlp/issues/2633
    has_websockets = False
else:
    has_websockets = True

from .common import FileDownloader
from .external import FFmpegFD


class FFmpegSinkFD(FileDownloader):
    """ A sink to ffmpeg for downloading fragments in any form """

    def real_download(self, filename, info_dict):
        info_copy = info_dict.copy()
        info_copy['url'] = '-'

        async def call_conn(proc, stdin):
            try:
                await self.real_connection(stdin, info_dict)
            except (BrokenPipeError, OSError):
                pass
            finally:
                try:
                    stdin.flush()
                    stdin.close()
                except OSError:
                    pass
                os.kill(os.getpid(), signal.SIGINT)

        class FFmpegStdinFD(FFmpegFD):
            @classmethod
            def get_basename(cls):
                return FFmpegFD.get_basename()

            def on_process_started(self, proc, stdin):
                thread = threading.Thread(target=asyncio.run, daemon=True, args=(call_conn(proc, stdin), ))
                thread.start()

        return FFmpegStdinFD(self.ydl, self.params or {}).download(filename, info_copy)

    async def real_connection(self, sink, info_dict):
        """ Override this in subclasses """
        raise NotImplementedError('This method must be implemented by subclasses')


class WebSocketFragmentFD(FFmpegSinkFD):
    async def real_connection(self, sink, info_dict):
        async with websockets.connect(info_dict['url'], extra_headers=info_dict.get('http_headers', {})) as ws:
            while True:
                recv = await ws.recv()
                if isinstance(recv, str):
                    recv = recv.encode('utf8')
                sink.write(recv)
