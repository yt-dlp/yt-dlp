import time

from yt_dlp.utils import filter_dict, unsmuggle_url, unified_timestamp, UnsupportedError

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
    def _download_webpage(self, url_or_request, display_id, headers=None, *_args, **_kwargs):
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions
        from selenium.common.exceptions import SessionNotCreatedException

        for _r in range(3):
            driver = None
            try:
                chrome_options = Options()
                for arq in DEFAULT_CONFIGURATION.get('chrome_options'):
                    chrome_options.add_argument(arq)
                driver = webdriver.Chrome(options=chrome_options)
                driver.execute_cdp_cmd('Network.enable', {})
                if headers:
                    driver.execute_cdp_cmd(
                        'Network.setExtraHTTPHeaders', {'headers': headers}
                    )
                driver.get(url_or_request)

                driver.implicitly_wait(DEFAULT_CONFIGURATION.get('implicitly_wait') or 10)
                # Wait for the page to render and the video to appear
                src = 'UnsupportedError'
                for _ in range(3):
                    try:
                        wait = WebDriverWait(driver, 5)
                        src = wait.until(
                            expected_conditions.visibility_of_element_located(
                                (By.CSS_SELECTOR, 'video')
                            )
                        ).find_element(By.CSS_SELECTOR, 'source').get_attribute('src')
                        if display_id not in src:
                            raise UnsupportedError(url)
                        break
                    except Exception:
                        pass
                if display_id not in src:
                    raise UnsupportedError(url_or_request)
                return driver.page_source
            except SessionNotCreatedException:
                time.sleep()
            finally:
                try:
                    if driver:
                        driver.quit()
                except Exception:
                    pass
        raise UnsupportedError(url_or_request)


    def _og_search_thumbnail(self, html, **kargs):
        if not 'data-poster="' in html:
            return kargs.get('default')
        return html.split('data-poster="')[1].split('"')[0]

    def _get_headers(self, url):
        headers = DEFAULT_CONFIGURATION.get('headers')
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
        full_response = self._request_webpage(url, display_id, headers=headers)
        webpage = self._download_webpage(url, display_id, headers)
        info_dict = {
            'id': display_id,
            'title': self._generic_title('', webpage, default='video'),
            'thumbnail': self._og_search_thumbnail(webpage, default=None),
            'timestamp': unified_timestamp(full_response.headers.get('Last-Modified')),
        }
        embeds = list(
            self._extract_generic_embeds(original_url, webpage, urlh=full_response, info_dict=info_dict))
        if len(embeds) == 1:
            return merge_dicts(info_dict, embeds[0])
        elif embeds:
            return self.playlist_result(embeds, **info_dict)
        raise UnsupportedError(url)
