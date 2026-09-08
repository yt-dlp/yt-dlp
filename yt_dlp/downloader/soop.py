import threading
import time

from .common import FileDownloader
from . import HlsFD
from ..extractor.afreecatv import _cloudfront_auth_request
from ..networking.exceptions import network_exceptions


class SoopVodFD(FileDownloader):
    """
    Downloads Soop subscription VODs with required cookie refresh requests
    Note, this is not a part of public API, and will be removed without notice.
    DO NOT USE
    """

    def real_download(self, filename, info_dict):
        self.to_screen(f'[{self.FD_NAME}] Downloading Soop subscription VOD HLS')
        fd = HlsFD(self.ydl, self.params)
        refresh_params = info_dict['_cookie_refresh_params']
        referer_url = info_dict['webpage_url']

        stop_event = threading.Event()
        refresh_thread = threading.Thread(
            target=self._cookie_refresh_thread,
            args=(stop_event, refresh_params, referer_url),
        )
        refresh_thread.start()

        try:
            return fd.real_download(filename, info_dict)
        finally:
            stop_event.set()

    def _cookie_refresh_thread(self, stop_event, refresh_params, referer_url):
        m3u8_url = refresh_params['m3u8_url']
        strm_id = refresh_params['strm_id']
        video_id = refresh_params['video_id']

        def _get_cloudfront_cookie_expiration(m3u8_url):
            cookies = self.ydl.cookiejar.get_cookies_for_url(m3u8_url)
            return min((cookie.expires for cookie in cookies if 'CloudFront' in cookie.name and cookie.expires), default=0)

        while not stop_event.wait(5):
            current_time = time.time()
            expiration_time = _get_cloudfront_cookie_expiration(m3u8_url)
            last_refresh_check = refresh_params.get('_last_refresh', 0)

            # Cookie TTL is 90 seconds, but let's give ourselves a 15-second cushion
            should_refresh = (
                (expiration_time and current_time >= expiration_time - 15)
                or (not expiration_time and current_time - last_refresh_check >= 75)
            )

            if should_refresh:
                try:
                    self.ydl.urlopen(_cloudfront_auth_request(
                        m3u8_url, strm_id, video_id, referer_url)).read()
                    refresh_params['_last_refresh'] = current_time
                except network_exceptions as e:
                    self.to_screen(f'[{self.FD_NAME}] Cookie refresh attempt failed: {e}')
