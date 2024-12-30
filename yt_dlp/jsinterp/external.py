from __future__ import annotations

import abc
import contextlib
import json
import os
import subprocess
import tempfile
import urllib.parse
import typing
import http.cookiejar


from ..utils import (
    ExtractorError,
    Popen,
    classproperty,
    format_field,
    get_exe_version,
    is_outdated_version,
    shell_quote,
    int_or_none,
    unified_timestamp,
)
from .common import JSI, register_jsi


def cookie_to_dict(cookie):
    cookie_dict = {
        'name': cookie.name,
        'value': cookie.value,
    }
    if cookie.port_specified:
        cookie_dict['port'] = cookie.port
    if cookie.domain_specified:
        cookie_dict['domain'] = cookie.domain
    if cookie.path_specified:
        cookie_dict['path'] = cookie.path
    if cookie.expires is not None:
        cookie_dict['expires'] = cookie.expires
    if cookie.secure is not None:
        cookie_dict['secure'] = cookie.secure
    if cookie.discard is not None:
        cookie_dict['discard'] = cookie.discard
    with contextlib.suppress(TypeError):
        if (cookie.has_nonstandard_attr('httpOnly')
                or cookie.has_nonstandard_attr('httponly')
                or cookie.has_nonstandard_attr('HttpOnly')):
            cookie_dict['httponly'] = True
    return cookie_dict


def cookie_jar_to_list(cookie_jar):
    return [cookie_to_dict(cookie) for cookie in cookie_jar]


class TempFileWrapper:
    """Wrapper for NamedTemporaryFile, auto closes file after io and deletes file upon wrapper object gc"""

    def __init__(self, content: str | bytes | None = None, text: bool = True,
                 encoding='utf-8', suffix: str | None = None):
        self.encoding = None if not text else encoding
        self.text = text
        self._file = tempfile.NamedTemporaryFile('w' if text else 'wb', encoding=self.encoding,
                                                 suffix=suffix, delete=False)
        if content:
            self._file.write(content)
        self._file.close()

    @property
    def name(self):
        return self._file.name

    @contextlib.contextmanager
    def opened_file(self, mode, *, seek=None, seek_whence=0):
        mode = mode if (self.text or 'b' in mode) else mode + 'b'
        with open(self._file.name, mode, encoding=self.encoding) as f:
            if seek is not None:
                self._file.seek(seek, seek_whence)
            yield f

    def write(self, s, seek=None, seek_whence=0):
        with self.opened_file('w', seek=seek, seek_whence=seek_whence) as f:
            return f.write(s)

    def append_write(self, s, seek=None, seek_whence=0):
        with self.opened_file('a', seek=seek, seek_whence=seek_whence) as f:
            return f.write(s)

    def read(self, n=-1, seek=None, seek_whence=0):
        with self.opened_file('r', seek=seek, seek_whence=seek_whence) as f:
            return f.read(n)

    def cleanup(self):
        with contextlib.suppress(OSError):
            os.remove(self._file.name)

    def __del__(self):
        self.cleanup()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.cleanup()


class ExternalJSI(JSI, abc.ABC):
    _EXE_NAME: str

    @classproperty(cache=True)
    def exe_version(cls):
        return get_exe_version(cls._EXE_NAME, args=getattr(cls, 'V_ARGS', ['--version']), version_re=r'([0-9.]+)')

    @classproperty
    def exe(cls):
        return cls._EXE_NAME if cls.exe_version else None

    @classmethod
    def is_available(cls):
        return bool(cls.exe)


@register_jsi
class DenoJSI(ExternalJSI):
    """JS interpreter class using Deno binary"""
    _SUPPORTED_FEATURES = {'js', 'wasm', 'location'}
    _BASE_PREFERENCE = 5
    _EXE_NAME = 'deno'
    _DENO_FLAGS = ['--cached-only', '--no-prompt', '--no-check']
    _INIT_SCRIPT = 'localStorage.clear(); delete window.Deno; global = window;\n'

    def __init__(self, downloader: YoutubeDL, timeout=None, flags=[], replace_flags=False, init_script=None):
        super().__init__(downloader, timeout)
        self._flags = flags if replace_flags else [*self._DENO_FLAGS, *flags]
        self._init_script = self._INIT_SCRIPT if init_script is None else init_script

    def _run_deno(self, cmd):
        self.write_debug(f'Deno command line: {shell_quote(cmd)}')
        try:
            stdout, stderr, returncode = Popen.run(
                cmd, timeout=self.timeout, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except Exception as e:
            raise ExtractorError('Unable to run Deno binary', cause=e)
        if returncode:
            raise ExtractorError(f'Failed with returncode {returncode}:\n{stderr}')
        elif stderr:
            self.report_warning(f'JS console error msg:\n{stderr.strip()}')
        return stdout.strip()

    def execute(self, jscode, video_id=None, note='Executing JS in Deno', location=None):
        self.report_note(video_id, note)
        location_args = ['--location', location] if location else []
        with TempFileWrapper(f'{self._init_script};\n{jscode}', suffix='.js') as js_file:
            cmd = [self.exe, 'run', *self._flags, *location_args, js_file.name]
            return self._run_deno(cmd)


@register_jsi
class DenoJITlessJSI(DenoJSI):
    _SUPPORTED_FEATURES = {'js', 'location'}
    _BASE_PREFERENCE = 6
    _EXE_NAME = DenoJSI._EXE_NAME
    _DENO_FLAGS = ['--cached-only', '--no-prompt', '--no-check', '--v8-flags=--jitless,--noexpose-wasm']

    @classproperty
    def exe_version(cls):
        return DenoJSI.exe_version


class DenoJSDomJSI(DenoJSI):
    _SUPPORTED_FEATURES = {'js', 'wasm', 'location', 'dom', 'cookies'}
    _BASE_PREFERENCE = 4
    _DENO_FLAGS = ['--cached-only', '--no-prompt', '--no-check']
    _JSDOM_IMPORT_CHECKED = False

    @staticmethod
    def serialize_cookie(cookiejar: YoutubeDLCookieJar | None, url: str):
        """serialize netscape-compatible fields from cookiejar for tough-cookie loading"""
        # JSDOM use tough-cookie as its CookieJar https://github.com/jsdom/jsdom/blob/main/lib/api.js
        # tough-cookie use Cookie.fromJSON and Cookie.toJSON for cookie serialization
        # https://github.com/salesforce/tough-cookie/blob/master/lib/cookie/cookie.ts
        if not cookiejar:
            return json.dumps({'cookies': []})
        cookies: list[http.cookiejar.Cookie] = [cookie for cookie in cookiejar.get_cookies_for_url(url)]
        return json.dumps({'cookies': [{
            'key': cookie.name,
            'value': cookie.value,
            # leading dot must be removed, otherwise will fail to match
            'domain': cookie.domain.lstrip('.') or urllib.parse.urlparse(url).hostname,
            'expires': int_or_none(cookie.expires, invscale=1000),
            'hostOnly': not cookie.domain_initial_dot,
            'secure': bool(cookie.secure),
            'path': cookie.path,
        } for cookie in cookies if cookie.value]})

    @staticmethod
    def apply_cookies(cookiejar: YoutubeDLCookieJar | None, cookies: list[dict]):
        """apply cookies from serialized tough-cookie"""
        # see serialize_cookie
        if not cookiejar:
            return
        for cookie_dict in cookies:
            if not all(cookie_dict.get(k) for k in ('key', 'value', 'domain')):
                continue
            if cookie_dict.get('hostOnly'):
                cookie_dict['domain'] = cookie_dict['domain'].lstrip('.')
            else:
                cookie_dict['domain'] = '.' + cookie_dict['domain'].lstrip('.')

            cookiejar.set_cookie(http.cookiejar.Cookie(
                0, cookie_dict['key'], cookie_dict['value'],
                None, False,
                cookie_dict['domain'], True, not cookie_dict.get('hostOnly'),
                cookie_dict.get('path', '/'), True,
                bool(cookie_dict.get('secure')),
                unified_timestamp(cookie_dict.get('expires')),
                False, None, None, {}))

    def _ensure_jsdom(self):
        if self._JSDOM_IMPORT_CHECKED:
            return
        with TempFileWrapper('import jsdom from "https://cdn.esm.sh/jsdom"', suffix='.js') as js_file:
            cmd = [self.exe, 'run', js_file.name]
            self._run_deno(cmd)
        self._JSDOM_IMPORT_CHECKED = True

    def execute(self, jscode, video_id=None, note='Executing JS in Deno', location='', html='', cookiejar=None):
        self.report_note(video_id, note)
        self._ensure_jsdom()
        script = f'''{self._init_script};
        import jsdom from "https://cdn.esm.sh/jsdom";
        const callback = (() => {{
            const jar = jsdom.CookieJar.deserializeSync({json.dumps(self.serialize_cookie(cookiejar, location))});
            const dom = new jsdom.JSDOM({json.dumps(str(html))}, {{
                {'url: %s,' % json.dumps(str(location)) if location else ''}
                cookieJar: jar,
            }});
            Object.keys(dom.window).forEach((key) => {{try {{window[key] = dom.window[key]}} catch (e) {{}}}});
            delete window.jsdom;
            const stdout = [];
            const origLog = console.log;
            console.log = (...msg) => stdout.push(msg.map(m => m.toString()).join(' '));
            return () => {{ origLog(JSON.stringify({{
                stdout: stdout.join('\\n'), cookies: jar.serializeSync().cookies}})); }}
        }})();
        await (async () => {{
            {jscode}
        }})().finally(callback);
        '''

        location_args = ['--location', location] if location else []
        with TempFileWrapper(script, suffix='.js') as js_file:
            cmd = [self.exe, 'run', *self._flags, *location_args, js_file.name]
            data = json.loads(self._run_deno(cmd))
        self.apply_cookies(cookiejar, data['cookies'])
        return data['stdout']


class PuppeteerJSI(ExternalJSI):
    _PACKAGE_VERSION = '16.2.0'
    _HEADLESS = False
    _EXE_NAME = DenoJSI._EXE_NAME

    @classproperty
    def INSTALL_HINT(cls):
        msg = f'Run "deno run -A https://deno.land/x/puppeteer@{cls._PACKAGE_VERSION}/install.ts" to install puppeteer'
        if not DenoJSI.is_available:
            msg = f'{DenoJSI.INSTALL_HINT}. Then {msg}'
        return msg

    @classproperty(cache=True)
    def full_version(cls):
        if not DenoJSI.is_available:
            return
        try:
            browser_version = DenoJSI._execute(f'''
                import puppeteer from "https://deno.land/x/puppeteer@{cls._PACKAGE_VERSION}/mod.ts";
                const browser = await puppeteer.launch({{headless: {json.dumps(bool(cls._HEADLESS))}}});
                try {{
                    console.log(await browser.version())
                }} finally {{
                    await browser.close();
                }}''', flags=['--allow-all'])
            return f'puppeteer={cls._PACKAGE_VERSION} browser={browser_version}'
        except ExtractorError:
            return None

    @classproperty
    def exe_version(cls):
        return DenoJSI.exe_version if cls.full_version else None

    def __init__(self, downloader: YoutubeDL, timeout: float | int | None = None):
        super().__init__(downloader, timeout)
        self.deno = DenoJSI(downloader, timeout=(self.timeout + 30000))

    def _deno_execute(self, jscode, note=None):
        return self.deno.execute(f'''
            import puppeteer from "https://deno.land/x/puppeteer@{self._PACKAGE_VERSION}/mod.ts";
            const browser = await puppeteer.launch({{
                headless: {json.dumps(bool(self._HEADLESS))}, args: ["--disable-web-security"]}});
            try {{
                {jscode}
            }} finally {{
                await browser.close();
            }}''', note=note, flags=['--allow-all'], base_js='')

    def execute(self, jscode, video_id=None, note='Executing JS in Puppeteer', url='about:blank'):
        self._downloader.to_screen(f'{format_field(video_id, None, "%s: ")}{note}')
        return self._deno_execute(f'''
            const page = await browser.newPage();
            window.setTimeout(async () => {{
                console.error('Puppeteer execution timed out');
                await browser.close();
                Deno.exit(1);
            }}, {int(self.timeout)});
            page.resourceTimeout = {int(self.timeout)};

            // drop network requests
            await page.setRequestInterception(true);
            page.on("request", request => request.abort());
            // capture console output
            page.on("console", msg => {{
                msg.type() === 'log' && console.log(msg.text());
                msg.type() === 'error' && console.error(msg.text());
            }});

            const url = {json.dumps(str(url))};
            await page.evaluate(`window.history.replaceState('', '', ${{JSON.stringify(url)}})`);

            await page.evaluate({json.dumps(str(jscode))});
            await browser.close();
            Deno.exit(0);
        ''')


@register_jsi
class PhantomJSJSI(ExternalJSI):
    _EXE_NAME = 'phantomjs'
    _SUPPORTED_FEATURES = {'js', 'location', 'cookies'}
    _BASE_PREFERENCE = 3

    _BASE_JS = R'''
        phantom.onError = function(msg, trace) {{
          var msgStack = ['PHANTOM ERROR: ' + msg];
          if(trace && trace.length) {{
            msgStack.push('TRACE:');
            trace.forEach(function(t) {{
              msgStack.push(' -> ' + (t.file || t.sourceURL) + ': ' + t.line
                + (t.function ? ' (in function ' + t.function +')' : ''));
            }});
          }}
          console.error(msgStack.join('\n'));
          phantom.exit(1);
        }};
    '''

    _TEMPLATE = R'''
        var page = require('webpage').create();
        var fs = require('fs');
        var read = {{ mode: 'r', charset: 'utf-8' }};
        var write = {{ mode: 'w', charset: 'utf-8' }};
        JSON.parse(fs.read({cookies_fn}, read)).forEach(function(x) {{
          phantom.addCookie(x);
        }});
        page.settings.resourceTimeout = {timeout};
        page.settings.userAgent = {ua};
        page.onLoadStarted = function() {{
          page.evaluate(function() {{
            delete window._phantom;
            delete window.callPhantom;
          }});
        }};
        var saveAndExit = function() {{
          fs.write({html_fn}, page.content, write);
          fs.write({cookies_fn}, JSON.stringify(phantom.cookies), write);
          phantom.exit();
        }};
        page.onLoadFinished = function(status) {{
          if(page.url === "") {{
            page.setContent(fs.read({html_fn}, read), {url});
          }}
          else {{
            {jscode}
          }}
        }};
        page.open("");
    '''

    def _save_cookies(self, url, cookiejar):
        cookies = cookie_jar_to_list(cookiejar) if cookiejar else []
        for cookie in cookies:
            if 'path' not in cookie:
                cookie['path'] = '/'
            if 'domain' not in cookie:
                cookie['domain'] = urllib.parse.urlparse(url).netloc
        return json.dumps(cookies)

    def _load_cookies(self, cookies_json: str, cookiejar):
        if not cookiejar:
            return
        cookies = json.loads(cookies_json)
        for cookie in cookies:
            cookiejar.set_cookie(http.cookiejar.Cookie(
                0, cookie['name'], cookie['value'], cookie.get('port'), cookie.get('port') is not None,
                cookie['domain'], True, cookie['domain'].startswith('.'),
                cookie.get('path', '/'), True,
                cookie.get('secure', False), cookie.get('expiry'),
                cookie.get('discard', False), None, None,
                {'httpOnly': None} if cookie.get('httponly') is True else {}
            ))

    def _execute(self, jscode: str, video_id=None, *, note='Executing JS in PhantomJS'):
        """Execute JS and return stdout"""
        if 'phantom.exit();' not in jscode:
            jscode += ';\nphantom.exit();'
        jscode = self._BASE_JS + jscode

        self.report_note(video_id, note)
        with TempFileWrapper(jscode, suffix='.js') as js_file:
            cmd = [self.exe, '--ssl-protocol=any', js_file.name]
            self.write_debug(f'PhantomJS command line: {shell_quote(cmd)}')
            try:
                stdout, stderr, returncode = Popen.run(
                    cmd, timeout=self.timeout, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            except Exception as e:
                raise ExtractorError(f'{note} failed: Unable to run PhantomJS binary', cause=e)
            if returncode:
                raise ExtractorError(f'{note} failed with returncode {returncode}:\n{stderr.strip()}')
        return stdout

    def _execute_html(self, jscode: str, url: str, html: str, cookiejar, video_id=None, note='Executing JS on webpage'):
        if 'saveAndExit();' not in jscode:
            raise ExtractorError('`saveAndExit();` not found in `jscode`')

        html_file = TempFileWrapper(html, suffix='.html')
        cookie_file = TempFileWrapper(self._save_cookies(url, cookiejar), suffix='.json')

        jscode = self._TEMPLATE.format(**{
            'url': json.dumps(str(url)),
            'ua': json.dumps(str(self.user_agent)),
            'jscode': jscode,
            'html_fn': json.dumps(html_file.name),
            'cookies_fn': json.dumps(cookie_file.name),
            'timeout': int(self.timeout * 1000),
        })

        stdout = self._execute(jscode, video_id, note=note)
        self._load_cookies(cookie_file.read(), cookiejar)
        new_html = html_file.read()

        return new_html, stdout

    def execute(self, jscode, video_id=None,
                note='Executing JS in PhantomJS', location=None, html='', cookiejar=None):
        if location:
            return self._execute_html(jscode, location, html, cookiejar, video_id=video_id, note=note)[1]
        if html:
            self.report_warning('`location` is required to use `html`')
        if cookiejar:
            self.report_warning('`location` and `html` are required to use `cookiejar`')
        return self._execute(jscode, video_id, note=note)


class PhantomJSwrapper:
    """PhantomJS wrapper class

    This class is experimental.
    """
    INSTALL_HINT = 'Please download PhantomJS from https://phantomjs.org/download.html'

    @classmethod
    def _version(cls):
        return PhantomJSJSI.exe_version

    def __init__(self, extractor: InfoExtractor, required_version=None, timeout=10000):
        self._jsi = PhantomJSJSI(extractor._downloader, timeout=timeout / 1000)

        if not self._jsi.is_available():
            raise ExtractorError(f'PhantomJS not found, {self.INSTALL_HINT}', expected=True)

        self.extractor = extractor

        if required_version:
            if is_outdated_version(self._jsi.exe_version, required_version):
                self._jsi.report_warning(
                    'Your copy of PhantomJS is outdated, update it to version '
                    f'{required_version} or newer if you encounter any errors.')

    def get(self, url, html=None, video_id=None, note=None, note2='Executing JS on webpage', headers={}, jscode='saveAndExit();'):
        """
        Downloads webpage (if needed) and executes JS

        Params:
            url: website url
            html: optional, html code of website
            video_id: video id
            note: optional, displayed when downloading webpage
            note2: optional, displayed when executing JS
            headers: custom http headers
            jscode: code to be executed when page is loaded

        Returns tuple with:
            * downloaded website (after JS execution)
            * anything you print with `console.log` (but not inside `page.execute`!)

        In most cases you don't need to add any `jscode`.
        It is executed in `page.onLoadFinished`.
        `saveAndExit();` is mandatory, use it instead of `phantom.exit()`
        It is possible to wait for some element on the webpage, e.g.
            var check = function() {
              var elementFound = page.evaluate(function() {
                return document.querySelector('#b.done') !== null;
              });
              if(elementFound)
                saveAndExit();
              else
                window.setTimeout(check, 500);
            }

            page.evaluate(function(){
              document.querySelector('#a').click();
            });
            check();
        """
        if 'saveAndExit();' not in jscode:
            raise ExtractorError('`saveAndExit();` not found in `jscode`')
        if not html:
            html = self.extractor._download_webpage(url, video_id, note=note, headers=headers)

        self._jsi.user_agent = headers.get('User-Agent') or self.extractor.get_param('http_headers')['User-Agent']

        return self._jsi._execute_html(jscode, url, html, self.extractor.cookiejar, video_id=video_id, note=note2)

    def execute(self, jscode, video_id=None, *, note='Executing JS in PhantomJS'):
        """Execute JS and return stdout"""
        return self._jsi.execute(jscode, video_id=video_id, note=note)


if typing.TYPE_CHECKING:
    from ..YoutubeDL import YoutubeDL
    from ..extractor.common import InfoExtractor
    from ..cookies import YoutubeDLCookieJar
