from __future__ import annotations

import http.cookiejar
import json
import subprocess
import typing
import urllib.parse


from ..utils import (
    ExtractorError,
    Popen,
    classproperty,
    int_or_none,
    shell_quote,
    unified_timestamp,
)
from ._helper import TempFileWrapper, random_string, override_navigator_js, extract_script_tags
from .common import ExternalJSI, register_jsi


@register_jsi
class DenoJSI(ExternalJSI):
    """JS interpreter class using Deno binary"""
    _SUPPORTED_FEATURES = {'js', 'wasm', 'location'}
    _BASE_PREFERENCE = 5
    _EXE_NAME = 'deno'
    _DENO_FLAGS = ['--cached-only', '--no-prompt', '--no-check']
    _INIT_SCRIPT = 'localStorage.clear(); delete window.Deno; global = window;\n'

    def __init__(self, *args, flags=[], replace_flags=False, init_script=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._flags = flags if replace_flags else [*self._DENO_FLAGS, *flags]
        self._init_script = self._INIT_SCRIPT if init_script is None else init_script

    @property
    def _override_navigator_js(self):
        return override_navigator_js(self.user_agent)

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

    def execute(self, jscode, video_id=None, note='Executing JS in Deno'):
        self.report_note(video_id, note)
        location_args = ['--location', self._url] if self._url else []
        with TempFileWrapper(f'{self._init_script};\n{self._override_navigator_js}\n{jscode}', suffix='.js') as js_file:
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
    _JSDOM_URL = 'https://cdn.esm.sh/jsdom'

    @staticmethod
    def serialize_cookie(cookiejar: YoutubeDLCookieJar | None, url: str):
        """serialize netscape-compatible fields from cookiejar for tough-cookie loading"""
        # JSDOM use tough-cookie as its CookieJar https://github.com/jsdom/jsdom/blob/main/lib/api.js
        # tough-cookie use Cookie.fromJSON and Cookie.toJSON for cookie serialization
        # https://github.com/salesforce/tough-cookie/blob/master/lib/cookie/cookie.ts
        if not cookiejar:
            return json.dumps({'cookies': []})
        cookies: list[http.cookiejar.Cookie] = list(cookiejar.get_cookies_for_url(url))
        return json.dumps({'cookies': [{
            'key': cookie.name,
            'value': cookie.value,
            # leading dot of domain must be removed, otherwise will fail to match
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
        with TempFileWrapper(f'import jsdom from "{self._JSDOM_URL}"', suffix='.js') as js_file:
            cmd = [self.exe, 'run', js_file.name]
            self._run_deno(cmd)
        self._JSDOM_IMPORT_CHECKED = True

    def execute(self, jscode, video_id=None, note='Executing JS in Deno', html='', cookiejar=None):
        self.report_note(video_id, note)
        self._ensure_jsdom()

        if cookiejar and not self._url:
            self.report_warning('No valid url scope provided, cookiejar is not applied')
            cookiejar = None

        html, inline_scripts = extract_script_tags(html)
        wrapper_scripts = '\n'.join(['try { %s } catch (e) {}' % script for script in inline_scripts])

        callback_varname = f'__callback_{random_string()}'
        script = f'''{self._init_script};
        {self._override_navigator_js};
        import jsdom from "{self._JSDOM_URL}";
        let {callback_varname} = (() => {{
            const jar = jsdom.CookieJar.deserializeSync({json.dumps(self.serialize_cookie(cookiejar, self._url))});
            const dom = new jsdom.JSDOM({json.dumps(str(html))}, {{
                {'url: %s,' % json.dumps(str(self._url)) if self._url else ''}
                cookieJar: jar,
            }});
            Object.keys(dom.window).forEach((key) => {{try {{window[key] = dom.window[key]}} catch (e) {{}}}});
            delete window.jsdom;
            const origLog = console.log;
            console.log = () => {{}};
            console.info = () => {{}};
            return () => {{
                const stdout = [];
                console.log = (...msg) => stdout.push(msg.map(m => m.toString()).join(' '));
                return () => {{ origLog(JSON.stringify({{
                    stdout: stdout.join('\\n'), cookies: jar.serializeSync().cookies}})); }}
            }}
        }})();
        {wrapper_scripts}
        {callback_varname} = {callback_varname}(); // begin to capture console.log
        try {{
            {jscode}
        }} finally {{
            {callback_varname}();
        }}
        '''

        location_args = ['--location', self._url] if self._url else []
        with TempFileWrapper(script, suffix='.js') as js_file:
            cmd = [self.exe, 'run', *self._flags, *location_args, js_file.name]
            result = self._run_deno(cmd)
            try:
                data = json.loads(result)
            except json.JSONDecodeError as e:
                raise ExtractorError(f'Failed to parse JSON output from Deno: {result}', cause=e)
        self.apply_cookies(cookiejar, data['cookies'])
        return data['stdout']


if typing.TYPE_CHECKING:
    from ..cookies import YoutubeDLCookieJar
