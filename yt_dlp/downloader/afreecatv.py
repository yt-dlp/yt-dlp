import threading
import time

from .common import FileDownloader
from . import HlsFD
from ..extractor.afreecatv import _cloudfront_auth_request


class AfreecaTVFD(FileDownloader):
    """
    Downloader with CloudFront cookie refresh for AfreecaTV/Sooplive subscription VODs
    """

    def real_download(self, filename, info_dict):
        refresh_params = info_dict.get('_cookie_refresh_params')
        if not refresh_params:
            return HlsFD(self.ydl, self.params).real_download(filename, info_dict)

        fd = HlsFD(self.ydl, self.params)

        stop_event = threading.Event()
        refresh_params.setdefault('_last_refresh', time.time())
        referer_url = info_dict.get('webpage_url') or ''
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
            if not m3u8_url:
                return None
            expiration_time = None
            for cookie in self.ydl.cookiejar.get_cookies_for_url(m3u8_url):
                if 'CloudFront' in cookie.name and cookie.expires:
                    if expiration_time is None or cookie.expires < expiration_time:
                        expiration_time = cookie.expires
            return expiration_time

        while not stop_event.wait(5):
            current_time = time.time()
            expiration_time = _get_cloudfront_cookie_expiration(m3u8_url)
            last_refresh_check = refresh_params.get('_last_refresh', current_time)

            should_refresh = (
                (expiration_time and current_time >= expiration_time - 15)
                or (not expiration_time and current_time - last_refresh_check >= 75)
            )

            if should_refresh:
                try:
                    self.ydl.urlopen(_cloudfront_auth_request(
                        m3u8_url, strm_id, video_id, referer_url)).read()
                    refresh_params['_last_refresh'] = current_time
                except Exception:
                    pass
