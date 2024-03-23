import asyncio
import contextlib
import os
import threading
import time

from .common import FileDownloader
from .external import FFmpegFD
from ..dependencies import websockets


class _WebSocketFD(FileDownloader):
    async def connect(self, stdin, info_dict):
        try:
            await self.real_connection(stdin, info_dict)
        except OSError:
            pass
        finally:
            with contextlib.suppress(OSError):
                stdin.flush()
                stdin.close()

    async def real_connection(self, sink, info_dict):
        async with websockets.connect(info_dict['url'], extra_headers=info_dict.get('http_headers', {})) as ws:
            while True:
                recv = await ws.recv()
                if isinstance(recv, str):
                    recv = recv.encode('utf8')
                sink.write(recv)


class WebSocketFragmentFD(_WebSocketFD):
    """ A sink to ffmpeg for downloading fragments in any form """

    def real_download(self, filename, info_dict):
        info_copy = info_dict.copy()
        info_copy['url'] = '-'
        connect = self.connect

        class FFmpegStdinFD(FFmpegFD):
            @classmethod
            def get_basename(cls):
                return FFmpegFD.get_basename()

            def on_process_started(self, proc, stdin):
                thread = threading.Thread(target=asyncio.run, daemon=True, args=(connect(stdin, info_dict), ))
                thread.start()

        return FFmpegStdinFD(self.ydl, self.params or {}).download(filename, info_copy)


class WebSocketToFileFD(_WebSocketFD):
    """ A sink to a file for downloading fragments in any form """
    def real_download(self, filename, info_dict):
        tempname = self.temp_name(filename)
        try:
            with open(tempname, 'wb') as w:
                started = time.time()
                status = {
                    'filename': info_dict.get('_filename'),
                    'status': 'downloading',
                    'elapsed': 0,
                    'downloaded_bytes': 0,
                }
                self._hook_progress(status, info_dict)

                thread = threading.Thread(target=asyncio.run, daemon=True, args=(self.connect(w, info_dict), ))
                thread.start()
                time_and_size, avg_len = [], 10
                while thread.is_alive():
                    time.sleep(0.1)

                    downloaded, curr = w.tell(), time.time()
                    # taken from ffmpeg attachment
                    time_and_size.append((downloaded, curr))
                    time_and_size = time_and_size[-avg_len:]
                    if len(time_and_size) > 1:
                        last, early = time_and_size[0], time_and_size[-1]
                        average_speed = (early[0] - last[0]) / (early[1] - last[1])
                    else:
                        average_speed = None

                    status.update({
                        'downloaded_bytes': downloaded,
                        'speed': average_speed,
                        'elapsed': curr - started,
                    })
                    self._hook_progress(status, info_dict)
        except KeyboardInterrupt:
            pass
        finally:
            os.replace(tempname, filename)
        return True
