from __future__ import annotations

import abc
import collections
import contextlib
import json
import os
import subprocess
import tempfile
import urllib.parse
import typing


from ..utils import (
    ExtractorError,
    Popen,
    classproperty,
    format_field,
    get_exe_version,
    is_outdated_version,
    shell_quote,
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
    _EXE_NAME = 'deno'
    _SUPPORTED_FEATURES = {'js', 'wasm', 'location'}
    _DENO_FLAGS = ['--cached-only', '--no-prompt', '--no-check']
    _INIT_SCRIPT = 'localStorage.clear(); delete window.Deno; global = window;\n'

    def __init__(self, downloader: YoutubeDL, timeout=None, flags=[], replace_flags=False, init_script=None):
        super().__init__(downloader, timeout)
        self._flags = flags if replace_flags else [*self._DENO_FLAGS, *flags]
        self._init_script = self._INIT_SCRIPT if init_script is None else init_script

    def _run_deno(self, cmd, video_id=None):
        self.write_debug(f'Deno command line: {shell_quote(cmd)}')
        try:
            stdout, stderr, returncode = Popen.run(
                cmd, timeout=self.timeout, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except Exception as e:
            raise ExtractorError('Unable to run Deno binary', cause=e)
        if returncode:
            raise ExtractorError(f'Failed with returncode {returncode}:\n{stderr}')
        elif stderr:
            self.report_warning(f'JS console error msg:\n{stderr.strip()}', video_id=video_id)
        return stdout.strip()

    def execute(self, jscode, video_id=None, note='Executing JS in Deno', url=None):
        self.report_note(video_id, note)
        js_file = TempFileWrapper(f'{self._init_script};\n{jscode}', suffix='.js')
        location_args = ['--location', url] if url else []
        cmd = [self.exe, 'run', *self._flags, *location_args, js_file.name]
        return self._run_deno(cmd, video_id=video_id)


@register_jsi
class DenoJITlessJSI(DenoJSI):
    _EXE_NAME = DenoJSI._EXE_NAME
    _SUPPORTED_FEATURES = {'js', 'location'}
    _DENO_FLAGS = ['--cached-only', '--no-prompt', '--no-check', '--v8-flags=--jitless,--noexpose-wasm']

    @classproperty
    def exe_version(cls):
        return DenoJSI.exe_version


class DenoJSDomJSI(DenoJSI):
    _SUPPORTED_FEATURES = {'js', 'wasm', 'dom'}
    _DENO_FLAGS = ['--cached-only', '--no-prompt', '--no-check']
    _JSDOM_IMPORT = False

    def _ensure_jsdom(self):
        if self._JSDOM_IMPORT:
            return
        js_file = TempFileWrapper('import { JSDOM } from "https://cdn.esm.sh/jsdom"', suffix='.js')
        cmd = [self.exe, 'run', js_file.name]
        self._run_deno(cmd)
        self._JSDOM_IMPORT = True

    def execute(self, jscode, video_id=None, note='Executing JS in Deno', url=None, html=None):
        self.report_note(video_id, note)
        if html:
            self._ensure_jsdom()
            init_script = '''%s;
            import { JSDOM } from "https://cdn.esm.sh/jsdom";
            const dom = new JSDOM(%s);
            Object.keys(dom.window).forEach((key) => {try {window[key] = dom.window[key]} catch (e) {}});
            ''' % (self._init_script, json.dumps(html))
        else:
            init_script = self._init_script
        js_file = TempFileWrapper(f'{init_script};\n{jscode}', suffix='.js')

        location_args = ['--location', url] if url else []
        cmd = [self.exe, 'run', *self._flags, *location_args, js_file.name]
        return self._run_deno(cmd, video_id=video_id)


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


class PhantomJSwrapper(ExternalJSI):
    """PhantomJS wrapper class

    This class is experimental.
    """
    _EXE_NAME = 'phantomjs'
    INSTALL_HINT = 'Please download PhantomJS from https://phantomjs.org/download.html'

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
        JSON.parse(fs.read("{cookies}", read)).forEach(function(x) {{
          phantom.addCookie(x);
        }});
        page.settings.resourceTimeout = {timeout};
        page.settings.userAgent = "{ua}";
        page.onLoadStarted = function() {{
          page.evaluate(function() {{
            delete window._phantom;
            delete window.callPhantom;
          }});
        }};
        var saveAndExit = function() {{
          fs.write("{html}", page.content, write);
          fs.write("{cookies}", JSON.stringify(phantom.cookies), write);
          phantom.exit();
        }};
        page.onLoadFinished = function(status) {{
          if(page.url === "") {{
            page.setContent(fs.read("{html}", read), "{url}");
          }}
          else {{
            {jscode}
          }}
        }};
        page.open("");
    '''

    _TMP_FILE_NAMES = ['script', 'html', 'cookies']

    @classmethod
    def _version(cls):
        return cls.exe_version

    def __init__(self, extractor: InfoExtractor, required_version=None, timeout=10000):
        self._TMP_FILES = {}

        if not self.exe:
            raise ExtractorError(f'PhantomJS not found, {self.INSTALL_HINT}', expected=True)

        self.extractor = extractor

        if required_version:
            if is_outdated_version(self.exe_version, required_version):
                self.extractor._downloader.report_warning(
                    'Your copy of PhantomJS is outdated, update it to version '
                    f'{required_version} or newer if you encounter any errors.')

        for name in self._TMP_FILE_NAMES:
            tmp = tempfile.NamedTemporaryFile(delete=False)
            tmp.close()
            self._TMP_FILES[name] = tmp

        self.options = collections.ChainMap({
            'timeout': timeout,
        }, {
            x: self._TMP_FILES[x].name.replace('\\', '\\\\').replace('"', '\\"')
            for x in self._TMP_FILE_NAMES
        })

    def __del__(self):
        for name in self._TMP_FILE_NAMES:
            with contextlib.suppress(OSError, KeyError):
                os.remove(self._TMP_FILES[name].name)

    def _save_cookies(self, url):
        cookies = cookie_jar_to_list(self.extractor.cookiejar)
        for cookie in cookies:
            if 'path' not in cookie:
                cookie['path'] = '/'
            if 'domain' not in cookie:
                cookie['domain'] = urllib.parse.urlparse(url).netloc
        with open(self._TMP_FILES['cookies'].name, 'wb') as f:
            f.write(json.dumps(cookies).encode())

    def _load_cookies(self):
        with open(self._TMP_FILES['cookies'].name, 'rb') as f:
            cookies = json.loads(f.read().decode('utf-8'))
        for cookie in cookies:
            if cookie['httponly'] is True:
                cookie['rest'] = {'httpOnly': None}
            if 'expiry' in cookie:
                cookie['expire_time'] = cookie['expiry']
            self.extractor._set_cookie(**cookie)

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
        with open(self._TMP_FILES['html'].name, 'wb') as f:
            f.write(html.encode())

        self._save_cookies(url)

        user_agent = headers.get('User-Agent') or self.extractor.get_param('http_headers')['User-Agent']
        jscode = self._TEMPLATE.format_map(self.options.new_child({
            'url': url,
            'ua': user_agent.replace('"', '\\"'),
            'jscode': jscode,
        }))

        stdout = self.execute(jscode, video_id, note=note2)

        with open(self._TMP_FILES['html'].name, 'rb') as f:
            html = f.read().decode('utf-8')
        self._load_cookies()

        return html, stdout

    def execute(self, jscode, video_id=None, *, note='Executing JS in PhantomJS'):
        """Execute JS and return stdout"""
        if 'phantom.exit();' not in jscode:
            jscode += ';\nphantom.exit();'
        jscode = self._BASE_JS + jscode

        with open(self._TMP_FILES['script'].name, 'w', encoding='utf-8') as f:
            f.write(jscode)
        self.extractor.to_screen(f'{format_field(video_id, None, "%s: ")}{note}')

        cmd = [self.exe, '--ssl-protocol=any', self._TMP_FILES['script'].name]
        self.extractor.write_debug(f'PhantomJS command line: {shell_quote(cmd)}')
        try:
            stdout, stderr, returncode = Popen.run(cmd, timeout=self.options['timeout'] / 1000,
                                                   text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except Exception as e:
            raise ExtractorError(f'{note} failed: Unable to run PhantomJS binary', cause=e)
        if returncode:
            raise ExtractorError(f'{note} failed with returncode {returncode}:\n{stderr.strip()}')

        return stdout


if typing.TYPE_CHECKING:
    from ..YoutubeDL import YoutubeDL
    from ..extractor.common import InfoExtractor
