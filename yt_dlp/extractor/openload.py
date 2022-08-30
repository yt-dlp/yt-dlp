import collections
import contextlib
import json
import os
import subprocess
import tempfile

from ..compat import compat_urlparse
from ..utils import (
    ExtractorError,
    Popen,
    check_executable,
    format_field,
    get_exe_version,
    is_outdated_version,
    shell_quote,
)


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


class PhantomJSwrapper:
    """PhantomJS wrapper class

    This class is experimental.
    """

    INSTALL_HINT = 'Please download it from https://phantomjs.org/download.html'

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

    @staticmethod
    def _version():
        return get_exe_version('phantomjs', version_re=r'([0-9.]+)')

    def __init__(self, extractor, required_version=None, timeout=10000):
        self._TMP_FILES = {}

        self.exe = check_executable('phantomjs', ['-v'])
        if not self.exe:
            raise ExtractorError(f'PhantomJS not found, {self.INSTALL_HINT}', expected=True)

        self.extractor = extractor

        if required_version:
            version = self._version()
            if is_outdated_version(version, required_version):
                self.extractor._downloader.report_warning(
                    'Your copy of PhantomJS is outdated, update it to version '
                    '%s or newer if you encounter any errors.' % required_version)

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
                cookie['domain'] = compat_urlparse.urlparse(url).netloc
        with open(self._TMP_FILES['cookies'].name, 'wb') as f:
            f.write(json.dumps(cookies).encode('utf-8'))

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
            f.write(html.encode('utf-8'))

        self._save_cookies(url)

        user_agent = headers.get('User-Agent') or self.extractor.get_param('http_headers')['User-Agent']
        jscode = self._TEMPLATE.format_map(self.options.new_child({
            'url': url,
            'ua': user_agent.replace('"', '\\"'),
            'jscode': jscode,
        }))

        stdout = self.execute(jscode, video_id, note2)

        with open(self._TMP_FILES['html'].name, 'rb') as f:
            html = f.read().decode('utf-8')
        self._load_cookies()

        return html, stdout

    def execute(self, jscode, video_id=None, *, note='Executing JS'):
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
