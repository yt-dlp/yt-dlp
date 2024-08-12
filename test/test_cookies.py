import datetime as dt
import unittest

from yt_dlp import cookies
from yt_dlp.cookies import (
    LenientSimpleCookie,
    LinuxChromeCookieDecryptor,
    MacChromeCookieDecryptor,
    WindowsChromeCookieDecryptor,
    _get_linux_desktop_environment,
    _LinuxDesktopEnvironment,
    parse_safari_cookies,
    pbkdf2_sha1,
)


class Logger:
    def debug(self, message, *args, **kwargs):
        print(f'[verbose] {message}')

    def info(self, message, *args, **kwargs):
        print(message)

    def warning(self, message, *args, **kwargs):
        self.error(message)

    def error(self, message, *args, **kwargs):
        raise Exception(message)


class MonkeyPatch:
    def __init__(self, module, temporary_values):
        self._module = module
        self._temporary_values = temporary_values
        self._backup_values = {}

    def __enter__(self):
        for name, temp_value in self._temporary_values.items():
            self._backup_values[name] = getattr(self._module, name)
            setattr(self._module, name, temp_value)

    def __exit__(self, exc_type, exc_val, exc_tb):
        for name, backup_value in self._backup_values.items():
            setattr(self._module, name, backup_value)


class TestCookies(unittest.TestCase):
    def test_get_desktop_environment(self):
        """ based on https://chromium.googlesource.com/chromium/src/+/refs/heads/main/base/nix/xdg_util_unittest.cc """
        test_cases = [
            ({}, _LinuxDesktopEnvironment.OTHER),
            ({'DESKTOP_SESSION': 'my_custom_de'}, _LinuxDesktopEnvironment.OTHER),
            ({'XDG_CURRENT_DESKTOP': 'my_custom_de'}, _LinuxDesktopEnvironment.OTHER),

            ({'DESKTOP_SESSION': 'gnome'}, _LinuxDesktopEnvironment.GNOME),
            ({'DESKTOP_SESSION': 'mate'}, _LinuxDesktopEnvironment.GNOME),
            ({'DESKTOP_SESSION': 'kde4'}, _LinuxDesktopEnvironment.KDE4),
            ({'DESKTOP_SESSION': 'kde'}, _LinuxDesktopEnvironment.KDE3),
            ({'DESKTOP_SESSION': 'xfce'}, _LinuxDesktopEnvironment.XFCE),

            ({'GNOME_DESKTOP_SESSION_ID': 1}, _LinuxDesktopEnvironment.GNOME),
            ({'KDE_FULL_SESSION': 1}, _LinuxDesktopEnvironment.KDE3),
            ({'KDE_FULL_SESSION': 1, 'DESKTOP_SESSION': 'kde4'}, _LinuxDesktopEnvironment.KDE4),

            ({'XDG_CURRENT_DESKTOP': 'X-Cinnamon'}, _LinuxDesktopEnvironment.CINNAMON),
            ({'XDG_CURRENT_DESKTOP': 'Deepin'}, _LinuxDesktopEnvironment.DEEPIN),
            ({'XDG_CURRENT_DESKTOP': 'GNOME'}, _LinuxDesktopEnvironment.GNOME),
            ({'XDG_CURRENT_DESKTOP': 'GNOME:GNOME-Classic'}, _LinuxDesktopEnvironment.GNOME),
            ({'XDG_CURRENT_DESKTOP': 'GNOME : GNOME-Classic'}, _LinuxDesktopEnvironment.GNOME),
            ({'XDG_CURRENT_DESKTOP': 'ubuntu:GNOME'}, _LinuxDesktopEnvironment.GNOME),

            ({'XDG_CURRENT_DESKTOP': 'Unity', 'DESKTOP_SESSION': 'gnome-fallback'}, _LinuxDesktopEnvironment.GNOME),
            ({'XDG_CURRENT_DESKTOP': 'KDE', 'KDE_SESSION_VERSION': '5'}, _LinuxDesktopEnvironment.KDE5),
            ({'XDG_CURRENT_DESKTOP': 'KDE', 'KDE_SESSION_VERSION': '6'}, _LinuxDesktopEnvironment.KDE6),
            ({'XDG_CURRENT_DESKTOP': 'KDE'}, _LinuxDesktopEnvironment.KDE4),
            ({'XDG_CURRENT_DESKTOP': 'Pantheon'}, _LinuxDesktopEnvironment.PANTHEON),
            ({'XDG_CURRENT_DESKTOP': 'UKUI'}, _LinuxDesktopEnvironment.UKUI),
            ({'XDG_CURRENT_DESKTOP': 'Unity'}, _LinuxDesktopEnvironment.UNITY),
            ({'XDG_CURRENT_DESKTOP': 'Unity:Unity7'}, _LinuxDesktopEnvironment.UNITY),
            ({'XDG_CURRENT_DESKTOP': 'Unity:Unity8'}, _LinuxDesktopEnvironment.UNITY),
        ]

        for env, expected_desktop_environment in test_cases:
            self.assertEqual(_get_linux_desktop_environment(env, Logger()), expected_desktop_environment)

    def test_chrome_cookie_decryptor_linux_derive_key(self):
        key = LinuxChromeCookieDecryptor.derive_key(b'abc')
        self.assertEqual(key, b'7\xa1\xec\xd4m\xfcA\xc7\xb19Z\xd0\x19\xdcM\x17')

    def test_chrome_cookie_decryptor_mac_derive_key(self):
        key = MacChromeCookieDecryptor.derive_key(b'abc')
        self.assertEqual(key, b'Y\xe2\xc0\xd0P\xf6\xf4\xe1l\xc1\x8cQ\xcb|\xcdY')

    def test_chrome_cookie_decryptor_linux_v10(self):
        with MonkeyPatch(cookies, {'_get_linux_keyring_password': lambda *args, **kwargs: b''}):
            encrypted_value = b'v10\xccW%\xcd\xe6\xe6\x9fM" \xa7\xb0\xca\xe4\x07\xd6'
            value = 'USD'
            decryptor = LinuxChromeCookieDecryptor('Chrome', Logger())
            self.assertEqual(decryptor.decrypt(encrypted_value), value)

    def test_chrome_cookie_decryptor_linux_v11(self):
        with MonkeyPatch(cookies, {'_get_linux_keyring_password': lambda *args, **kwargs: b''}):
            encrypted_value = b'v11#\x81\x10>`w\x8f)\xc0\xb2\xc1\r\xf4\x1al\xdd\x93\xfd\xf8\xf8N\xf2\xa9\x83\xf1\xe9o\x0elVQd'
            value = 'tz=Europe.London'
            decryptor = LinuxChromeCookieDecryptor('Chrome', Logger())
            self.assertEqual(decryptor.decrypt(encrypted_value), value)

    def test_chrome_cookie_decryptor_windows_v10(self):
        with MonkeyPatch(cookies, {
            '_get_windows_v10_key': lambda *args, **kwargs: b'Y\xef\xad\xad\xeerp\xf0Y\xe6\x9b\x12\xc2<z\x16]\n\xbb\xb8\xcb\xd7\x9bA\xc3\x14e\x99{\xd6\xf4&',
        }):
            encrypted_value = b'v10T\xb8\xf3\xb8\x01\xa7TtcV\xfc\x88\xb8\xb8\xef\x05\xb5\xfd\x18\xc90\x009\xab\xb1\x893\x85)\x87\xe1\xa9-\xa3\xad='
            value = '32101439'
            decryptor = WindowsChromeCookieDecryptor('', Logger())
            self.assertEqual(decryptor.decrypt(encrypted_value), value)

    def test_chrome_cookie_decryptor_mac_v10(self):
        with MonkeyPatch(cookies, {'_get_mac_keyring_password': lambda *args, **kwargs: b'6eIDUdtKAacvlHwBVwvg/Q=='}):
            encrypted_value = b'v10\xb3\xbe\xad\xa1[\x9fC\xa1\x98\xe0\x9a\x01\xd9\xcf\xbfc'
            value = '2021-06-01-22'
            decryptor = MacChromeCookieDecryptor('', Logger())
            self.assertEqual(decryptor.decrypt(encrypted_value), value)

    def test_safari_cookie_parsing(self):
        cookies = (
            b'cook\x00\x00\x00\x01\x00\x00\x00i\x00\x00\x01\x00\x01\x00\x00\x00\x10\x00\x00\x00\x00\x00\x00\x00Y'
            b'\x00\x00\x00\x00\x00\x00\x00 \x00\x00\x00\x00\x00\x00\x008\x00\x00\x00B\x00\x00\x00F\x00\x00\x00H'
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x80\x03\xa5>\xc3A\x00\x00\x80\xc3\x07:\xc3A'
            b'localhost\x00foo\x00/\x00test%20%3Bcookie\x00\x00\x00\x054\x07\x17 \x05\x00\x00\x00Kbplist00\xd1\x01'
            b'\x02_\x10\x18NSHTTPCookieAcceptPolicy\x10\x02\x08\x0b&\x00\x00\x00\x00\x00\x00\x01\x01\x00\x00\x00'
            b'\x00\x00\x00\x00\x03\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00(')

        jar = parse_safari_cookies(cookies)
        self.assertEqual(len(jar), 1)
        cookie = next(iter(jar))
        self.assertEqual(cookie.domain, 'localhost')
        self.assertEqual(cookie.port, None)
        self.assertEqual(cookie.path, '/')
        self.assertEqual(cookie.name, 'foo')
        self.assertEqual(cookie.value, 'test%20%3Bcookie')
        self.assertFalse(cookie.secure)
        expected_expiration = dt.datetime(2021, 6, 18, 21, 39, 19, tzinfo=dt.timezone.utc)
        self.assertEqual(cookie.expires, int(expected_expiration.timestamp()))

    def test_pbkdf2_sha1(self):
        key = pbkdf2_sha1(b'peanuts', b' ' * 16, 1, 16)
        self.assertEqual(key, b'g\xe1\x8e\x0fQ\x1c\x9b\xf3\xc9`!\xaa\x90\xd9\xd34')


class TestLenientSimpleCookie(unittest.TestCase):
    def _run_tests(self, *cases):
        for message, raw_cookie, expected in cases:
            cookie = LenientSimpleCookie(raw_cookie)

            with self.subTest(message, expected=expected):
                self.assertEqual(cookie.keys(), expected.keys(), message)

                for key, expected_value in expected.items():
                    morsel = cookie[key]
                    if isinstance(expected_value, tuple):
                        expected_value, expected_attributes = expected_value
                    else:
                        expected_attributes = {}

                    attributes = {
                        key: value
                        for key, value in dict(morsel).items()
                        if value != ''
                    }
                    self.assertEqual(attributes, expected_attributes, message)

                    self.assertEqual(morsel.value, expected_value, message)

    def test_parsing(self):
        self._run_tests(
            # Copied from https://github.com/python/cpython/blob/v3.10.7/Lib/test/test_http_cookies.py
            (
                'Test basic cookie',
                'chips=ahoy; vienna=finger',
                {'chips': 'ahoy', 'vienna': 'finger'},
            ),
            (
                'Test quoted cookie',
                'keebler="E=mc2; L=\\"Loves\\"; fudge=\\012;"',
                {'keebler': 'E=mc2; L="Loves"; fudge=\012;'},
            ),
            (
                "Allow '=' in an unquoted value",
                'keebler=E=mc2',
                {'keebler': 'E=mc2'},
            ),
            (
                "Allow cookies with ':' in their name",
                'key:term=value:term',
                {'key:term': 'value:term'},
            ),
            (
                "Allow '[' and ']' in cookie values",
                'a=b; c=[; d=r; f=h',
                {'a': 'b', 'c': '[', 'd': 'r', 'f': 'h'},
            ),
            (
                'Test basic cookie attributes',
                'Customer="WILE_E_COYOTE"; Version=1; Path=/acme',
                {'Customer': ('WILE_E_COYOTE', {'version': '1', 'path': '/acme'})},
            ),
            (
                'Test flag only cookie attributes',
                'Customer="WILE_E_COYOTE"; HttpOnly; Secure',
                {'Customer': ('WILE_E_COYOTE', {'httponly': True, 'secure': True})},
            ),
            (
                'Test flag only attribute with values',
                'eggs=scrambled; httponly=foo; secure=bar; Path=/bacon',
                {'eggs': ('scrambled', {'httponly': 'foo', 'secure': 'bar', 'path': '/bacon'})},
            ),
            (
                "Test special case for 'expires' attribute, 4 digit year",
                'Customer="W"; expires=Wed, 01 Jan 2010 00:00:00 GMT',
                {'Customer': ('W', {'expires': 'Wed, 01 Jan 2010 00:00:00 GMT'})},
            ),
            (
                "Test special case for 'expires' attribute, 2 digit year",
                'Customer="W"; expires=Wed, 01 Jan 98 00:00:00 GMT',
                {'Customer': ('W', {'expires': 'Wed, 01 Jan 98 00:00:00 GMT'})},
            ),
            (
                'Test extra spaces in keys and values',
                'eggs  =  scrambled  ;  secure  ;  path  =  bar   ; foo=foo   ',
                {'eggs': ('scrambled', {'secure': True, 'path': 'bar'}), 'foo': 'foo'},
            ),
            (
                'Test quoted attributes',
                'Customer="WILE_E_COYOTE"; Version="1"; Path="/acme"',
                {'Customer': ('WILE_E_COYOTE', {'version': '1', 'path': '/acme'})},
            ),
            # Our own tests that CPython passes
            (
                "Allow ';' in quoted value",
                'chips="a;hoy"; vienna=finger',
                {'chips': 'a;hoy', 'vienna': 'finger'},
            ),
            (
                'Keep only the last set value',
                'a=c; a=b',
                {'a': 'b'},
            ),
        )

    def test_lenient_parsing(self):
        self._run_tests(
            (
                'Ignore and try to skip invalid cookies',
                'chips={"ahoy;": 1}; vienna="finger;"',
                {'vienna': 'finger;'},
            ),
            (
                'Ignore cookies without a name',
                'a=b; unnamed; c=d',
                {'a': 'b', 'c': 'd'},
            ),
            (
                "Ignore '\"' cookie without name",
                'a=b; "; c=d',
                {'a': 'b', 'c': 'd'},
            ),
            (
                'Skip all space separated values',
                'x a=b c=d x; e=f',
                {'a': 'b', 'c': 'd', 'e': 'f'},
            ),
            (
                'Skip all space separated values',
                'x a=b; data={"complex": "json", "with": "key=value"}; x c=d x',
                {'a': 'b', 'c': 'd'},
            ),
            (
                'Expect quote mending',
                'a=b; invalid="; c=d',
                {'a': 'b', 'c': 'd'},
            ),
            (
                'Reset morsel after invalid to not capture attributes',
                'a=b; invalid; Version=1; c=d',
                {'a': 'b', 'c': 'd'},
            ),
            (
                'Reset morsel after invalid to not capture attributes',
                'a=b; $invalid; $Version=1; c=d',
                {'a': 'b', 'c': 'd'},
            ),
            (
                'Continue after non-flag attribute without value',
                'a=b; path; Version=1; c=d',
                {'a': 'b', 'c': 'd'},
            ),
            (
                'Allow cookie attributes with `$` prefix',
                'Customer="WILE_E_COYOTE"; $Version=1; $Secure; $Path=/acme',
                {'Customer': ('WILE_E_COYOTE', {'version': '1', 'secure': True, 'path': '/acme'})},
            ),
            (
                'Invalid Morsel keys should not result in an error',
                'Key=Value; [Invalid]=Value; Another=Value',
                {'Key': 'Value', 'Another': 'Value'},
            ),
        )
