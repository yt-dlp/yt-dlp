from __future__ import annotations

import contextlib
import http.cookiejar
import json
import subprocess
import typing
import urllib.parse


from ..utils import (
    ExtractorError,
    Popen,
    filter_dict,
    int_or_none,
    is_outdated_version,
    shell_quote,
)
from ._helper import TempFileWrapper, random_string
from .common import ExternalJSI, register_jsi


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
            JSON.parse(fs.read({cookies_fn}, read)).forEach(function(x) {{
                phantom.addCookie(x);
            }});
            {jscode}
          }}
        }};
        page.open("");
    '''

    def _save_cookies(self, url, cookiejar: YoutubeDLCookieJar | None):
        def _cookie_to_dict(cookie: http.cookiejar.Cookie):
            cookie_dict = {
                'name': cookie.name,
                'value': cookie.value,
                'port': cookie.port,
                'domain': cookie.domain,
                'path': cookie.path or '/',
                'expires': int_or_none(cookie.expires, invscale=1000),
                'secure': cookie.secure,
                'discard': cookie.discard,
            }
            if not cookie_dict['domain']:
                cookie_dict['domain'] = urllib.parse.urlparse(url).hostname
                cookie_dict['port'] = urllib.parse.urlparse(url).port
            with contextlib.suppress(TypeError):
                if (cookie.has_nonstandard_attr('httpOnly')
                        or cookie.has_nonstandard_attr('httponly')
                        or cookie.has_nonstandard_attr('HttpOnly')):
                    cookie_dict['httponly'] = True
            return filter_dict(cookie_dict)

        cookies = cookiejar.get_cookies_for_url(url) if cookiejar else []
        return json.dumps([_cookie_to_dict(cookie) for cookie in cookies])

    def _load_cookies(self, cookies_json: str, cookiejar: YoutubeDLCookieJar | None):
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
                {'httpOnly': None} if cookie.get('httponly') is True else {},
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

        jscode = self._TEMPLATE.format_map({
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
            jscode = '''console.log(page.evaluate(function() {
                var %(std_var)s = [];
                console.log = function() {
                    var values = '';
                    for (var i = 0; i < arguments.length; i++) {
                        values += arguments[i] + ' ';
                    }
                    %(std_var)s.push(values);
                }
                %(jscode)s;
                return %(std_var)s.join('\\n');

            }));
            saveAndExit();''' % {
                'std_var': f'__stdout__values_{random_string()}',
                'jscode': jscode,
            }
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
    from ..extractor.common import InfoExtractor
    from ..cookies import YoutubeDLCookieJar
