import re
import time

from yt_dlp.utils import filter_dict, unsmuggle_url, unified_timestamp, UnsupportedError
from yt_dlp import variadic

from .common import InfoExtractor
from ..utils import merge_dicts


DEFAULT_CONFIGURATION = {
    'chrome_options': [
        # '--headless',
        '--disable-gpu',
        '--disable-extensions',
        '--proxy-server="direct://"',
        '--proxy-bypass-list=*',
        '--start-maximized',
        '--disable-dev-shm-usage',
        '--no-sandbox',
    ],
    'implicitly_wait': 10,
}


class SeleniumPageRenderingIE(InfoExtractor):
    _VALID_URL = (
        r'https?://.*\.pandavideo\.com.*/embed/.*v=(?P<id>[a-f0-9\-]+)',
        r'https?://player\.scaleup\.com.*/embed/(?P<id>[a-f0-9\-]+)',
        r'https?://.*\.amplifyapp\.com.*/embed/(?P<id>[a-f0-9\-]+)?.*',
    )
    _TESTS = [{
        'url': 'https://player-vz-ee438fcb-865.tv.pandavideo.com.br/embed/'
               '?color=f6c5c5&v=6035f7c1-83fe-4847-93c3-e2f4827e60f3',
        'info_dict': {},
    }]

    def _download_webpage(self, url_or_request, display_id, headers=None, *_args, **_kwargs):
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions
        from selenium.common.exceptions import SessionNotCreatedException

        for _r in range(3):
            try:
                chrome_options = Options()
                for arq in DEFAULT_CONFIGURATION.get('chrome_options'):
                    chrome_options.add_argument(arq)
                chrome_options.add_argument("--auto-open-devtools-for-tabs")
                driver = webdriver.Chrome(options=chrome_options)
                try:
                    driver.execute_cdp_cmd('Network.enable', {})
                    if headers:
                        driver.execute_cdp_cmd(
                            'Network.setExtraHTTPHeaders', {'headers': headers}
                        )
                    driver.execute_cdp_cmd('Network.enable', {})
                    driver.execute_script("window.performance.getEntries();")
                    driver.get(url_or_request)
                    driver.implicitly_wait(DEFAULT_CONFIGURATION.get('implicitly_wait') or 10)
                    # Wait for the page to render and the video to appear
                    src = 'UnsupportedError'
                    for _ in range(3):
                        try:
                            wait = WebDriverWait(driver, 5)
                            video = wait.until(
                                expected_conditions.visibility_of_element_located(
                                    (By.CSS_SELECTOR, 'video')
                                )
                            )
                            try:
                                src = video.find_element(By.CSS_SELECTOR, 'source').get_attribute('src')
                            except Exception:
                                # '.amplifyapp.com' in src
                                src = video.get_attribute('src')
                            if 'pandavideo' in url_or_request and display_id not in src:
                                raise UnsupportedError(url_or_request)
                            break
                        except Exception:
                            pass
                    if not src or src == 'UnsupportedError':
                        raise UnsupportedError(url_or_request)
                    page_source = driver.page_source
                    if '.amplifyapp.com/embed' in url_or_request and '.amplifyapp.com' in src:
                        endswith_m3u8 = '.m3u8'
                        swith_m3u8 = 'playlist.m3u8'
                        # it_found = False
                        for retr in range(10):
                            time.sleep(1)
                            total_entries = driver.execute_script("return window.performance.getEntries().length")
                            for i in range(total_entries):
                                try:
                                    entrie = driver.execute_script(f"return window.performance.getEntries()[{i}]")
                                    if (
                                        (endswith_m3u8 and entrie['name'].endswith(endswith_m3u8)) or
                                        (swith_m3u8 and swith_m3u8 in entrie['name'])
                                    ):
                                        it_found = True
                                        return page_source.replace(src, entrie['name'])
                                except Exception:
                                    pass
                        # 'blob:https://main.d3va5qt152jv36.amplifyapp.com/e457b561-f699-4842-8c7f-8f0dab7629b4'
                    return page_source
                finally:
                    try:
                        if driver:
                            driver.quit()
                    except Exception:
                        pass
            except SessionNotCreatedException:
                time.sleep(1)
        raise UnsupportedError(url_or_request)

    def _og_search_thumbnail(self, html, **kargs):
        if 'data-poster="' not in html:
            return kargs.get('default')
        return html.split('data-poster="')[1].split('"')[0]

    def _get_headers(self, url):
        headers = self.get_param('http_headers').copy() or DEFAULT_CONFIGURATION.get('headers')
        if headers:
            return headers
        url, smuggled_data = unsmuggle_url(url, {})
        return filter_dict({
            'Accept-Encoding': 'identity',
            'Referer': smuggled_data.get('referer'),
        })

    def _real_extract(self, url):
        original_url = url
        display_id = self._match_id(url)
        headers = self._get_headers(url)
        try:
            full_response = self._request_webpage(url, display_id, headers=headers)
            timestamp = unified_timestamp(full_response.headers.get('Last-Modified')),
        except Exception:
            full_response = None
        webpage = self._download_webpage(url, display_id, headers)
        info_dict = {
            'id': display_id,
            'title': self._generic_title('', webpage, default='video'),
            'thumbnail': self._og_search_thumbnail(webpage, default=None),
            # 'timestamp': timestamp,
        }
        embeds = list(
            self._extract_generic_embeds(original_url, webpage, urlh=full_response, info_dict=info_dict))
        if len(embeds) == 1:
            return merge_dicts(info_dict, embeds[0])
        elif embeds:
            return self.playlist_result(embeds, **info_dict)
        raise UnsupportedError(url)

    @classmethod
    def _match_valid_url(cls, url):
        # DEBUG
        # re.compile(r'https?://.*\.amplifyapp\.com.*/embed/(?P<id>[a-f0-9\-]+)?.*', re.UNICODE).match(url), url
        if cls._VALID_URL is False:
            return None
        # This does not use has/getattr intentionally - we want to know whether
        # we have cached the regexp for *this* class, whereas getattr would also
        # match the superclass
        if '_VALID_URL_RE' not in cls.__dict__:
            cls._VALID_URL_RE = tuple(map(re.compile, variadic(cls._VALID_URL)))
        return next(filter(None, (regex.match(url) for regex in cls._VALID_URL_RE)), None)
