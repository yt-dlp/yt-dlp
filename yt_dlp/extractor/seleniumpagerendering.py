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
    def _download_webpage(self, url_or_request, display_id, *_args, **_kwargs):
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions

        chrome_options = Options()
        for arq in DEFAULT_CONFIGURATION.get('chrome_options'):
            chrome_options.add_argument(arq)
        driver = webdriver.Chrome(options=chrome_options)
        driver.execute_cdp_cmd('Network.enable', {})
        if DEFAULT_CONFIGURATION.get('headers'):
            driver.execute_cdp_cmd(
                'Network.setExtraHTTPHeaders', {'headers': DEFAULT_CONFIGURATION.get('headers')}
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
            raise UnsupportedError(url)
        html_modificado = driver.page_source
        driver.quit()
        return html_modificado

    def _real_extract(self, url):
        original_url = url
        display_id = self._match_id(url)
        video_id = self._generic_id(url)
        url, smuggled_data = unsmuggle_url(url, {})
        full_response = self._request_webpage(url, display_id, headers=filter_dict({
            'Accept-Encoding': 'identity',
            'Referer': smuggled_data.get('referer'),
        }))
        for _ in range(3):
            webpage = self._download_webpage(url, display_id)
            info_dict = {
                'id': display_id,
                'title': self._generic_title(url),
                'timestamp': unified_timestamp(full_response.headers.get('Last-Modified')),
            }

            info_dict.update({
                'id': display_id,
                'display_id': display_id,
                'title': self._generic_title('', webpage, default='video'),
                'description': self._og_search_description(webpage, default=None),
                'thumbnail': self._og_search_thumbnail(webpage, default=None),
                'age_limit': self._rta_search(webpage),
            })

            embeds = list(
                self._extract_generic_embeds(original_url, webpage, urlh=full_response, info_dict=info_dict))
            if len(embeds) == 1:
                return merge_dicts(embeds[0], info_dict)
            elif embeds:
                return self.playlist_result(embeds, **info_dict)
        raise UnsupportedError(url)
