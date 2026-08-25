from yt_dlp.dependencies import selenium
from yt_dlp.utils import ExtractorError

if selenium is None:
    raise ExtractorError(
        'This feature requires selenium. '
        'Install it with: pip install "yt-dlp[selenium]" '
        '(or pip install selenium)',
        expected=True,
    )

from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.proxy import Proxy, ProxyType
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import WebDriverException
from pathlib import Path
from time import sleep
import re


class GenerateCookies:
    def __init__(self , proxy_string : str = None):
        self.NETSCAPE_HEADER = (
    "# Netscape HTTP Cookie File\n"
    "# https://curl.se/docs/http-cookies.html\n"
    "# This is a generated file! Do not edit.\n"
)
        self.proxy = self._prepare_proxy(proxy_string) if proxy_string else None

    def _prepare_proxy(self, proxy_str: str) -> Proxy:
        """Parses '<proxy-type>://<host>:<port>' and returns a Selenium Proxy object."""
        if not isinstance(proxy_str, str):
            raise ValueError("Proxy must be a string.")

        pattern = r"^(?P<scheme>[a-zA-Z0-9]+)://(?P<host>[^:]+):(?P<port>\d+)$"
        match = re.match(pattern, proxy_str.strip())

        if not match:
            raise ValueError(
                f"Invalid proxy format '{proxy_str}'. "
                "Expected format: '<proxy-type>://<host>:<port>'"
            )

        scheme = match.group("scheme").lower()
        host = match.group("host")
        port = int(match.group("port"))

        if not (1 <= port <= 65535):
            raise ValueError(
                f"Invalid port '{port}'. Port must be between 1 and 65535."
            )

        supported_schemes = {
            "http",
            "https",
            "ssl",
            "socks4",
            "socks5",
            "socks",
        }
        if scheme not in supported_schemes:
            raise ValueError(
                f"Unsupported proxy type '{scheme}'. "
                f"Supported types are: {', '.join(sorted(supported_schemes))}"
            )

        proxy = Proxy()
        proxy.proxy_type = ProxyType.MANUAL
        endpoint = f"{host}:{port}"

        if scheme == "http":
            proxy.http_proxy = endpoint
            proxy.ssl_proxy = endpoint
        elif scheme in ("https", "ssl"):
            proxy.ssl_proxy = endpoint
        elif scheme == "socks4":
            proxy.socks_proxy = endpoint
            proxy.socks_version = 4
        elif scheme in ("socks5", "socks"):
            proxy.socks_proxy = endpoint
            proxy.socks_version = 5

        return proxy
    def _get_chrome_options(self , headless : bool = False) -> ChromeOptions:
        options = ChromeOptions()
        options.add_argument("--incognito")
        if headless:
            options.add_argument("--headless")
        options.add_argument("--disable-infobars")
        options.add_argument("--disable-extensions")
        options.add_argument(
            "--disable-blink-features=AutomationControlled"
        ) 
        options.add_experimental_option(
            "excludeSwitches", ["enable-automation"]
        )
        options.add_experimental_option(
            "useAutomationExtension", False
        ) 
        
        if self.proxy:
            options.proxy = self.proxy

        return options
    def _init_driver(self , browser_name: str = "chrome" , headless : bool = False):
        browser_name = browser_name.lower()

        if browser_name == "chrome":
            return webdriver.Chrome(options=self._get_chrome_options(headless=headless))
        # no firefox support currently
        # elif browser_name == "firefox":
        #     return webdriver.Firefox(options=_get_firefox_options())
        else:
            raise ValueError(f"Unknown Browser: {browser_name}")
    def _is_chrome_installed(self) -> bool:
        driver = self._init_driver(browser_name="chrome" , headless=True)
        try:
            driver.get("https://www.google.com")
            return True
        except:
            return False
        finally:
            driver.quit()


    def _get_youtube_cookies(self , driver):
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        driver.get("https://www.youtube.com/")
        accept_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable(
            (By.XPATH, "//button[.//span[text()='Accept all']]")
        )
        )
        accept_button.click()
        WebDriverWait(driver, 10).until(EC.staleness_of(accept_button))
        signin_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable(
        (By.CSS_SELECTOR, "a[aria-label='Sign in']")
        )
        )
        signin_button.click()
        print("[+] Log in using your Google Account in the opened browser window...\n[+] Cookies will be generated automatically after login.")
        while True:
            if "https://www.youtube.com/" == driver.current_url:
                print("Logged into YouTube , Exporting cookies for YTDLP")
                return driver.get_cookies()
            sleep(1)

    def _to_netscape(self , cookies):
        seen = set()
        lines = [self.NETSCAPE_HEADER]
        for c in sorted(cookies, key=lambda x: (x["name"], x["domain"])):
            if not c["domain"].endswith("youtube.com"):
                continue
            key = (c["domain"], c["path"], c["name"])
            if key in seen:
                continue
            seen.add(key)
            domain = c["domain"]
            subdomains = "TRUE" if domain.startswith(".") else "FALSE"
            secure = "TRUE" if c.get("secure") else "FALSE"
            expiry = int(c.get("expiry", 0))
            lines.append(
                "\t".join([domain, subdomains, c.get("path", "/"), secure, str(expiry), c["name"], c.get("value", "")])
            )
        return "\n".join(lines) + "\n"
    
    def start(self):
        if not self._is_chrome_installed():
            raise RuntimeError("Error : Please install Google Chrome.")
        driver = self._init_driver(browser_name= "chrome")
        youtube_cookies = None
        try:
            youtube_cookies = self._get_youtube_cookies(driver)
        except WebDriverException as e:
            if "Reached error page" in str(e) or "about:neterror" in str(e):
                raise ConnectionError("Network/Connection failure: Unable to reach the target URL.")
        finally:
            driver.quit()
        
        try:
            Path("cookies.txt").write_text(self._to_netscape(youtube_cookies))
            print('[+] Cookies saved to "cookies.txt"\n[+] Usage: yt_dlp --cookies cookies.txt')
        except Exception as e:
            print(e)
