from __future__ import annotations

import abc
import typing
import inspect

from ..globals import jsi_runtimes
from ..extractor.common import InfoExtractor
from ..utils import (
    classproperty,
    format_field,
    filter_dict,
    get_exe_version,
    url_or_none,
    sanitize_url,
    ExtractorError,
)

_JSI_PREFERENCES: set[JSIPreference] = set()


def all_handlers() -> dict[str, type[JSI]]:
    return {jsi.JSI_KEY: jsi for jsi in jsi_runtimes.value.values()}


def to_jsi_keys(jsi_or_keys: typing.Iterable[str | type[JSI] | JSI]) -> list[str]:
    return [jok if isinstance(jok, str) else jok.JSI_KEY for jok in jsi_or_keys]


def get_included_jsi(only_include=None, exclude=None):
    return {
        key: value for key, value in all_handlers().items()
        if (not only_include or key in to_jsi_keys(only_include))
        and (not exclude or key not in to_jsi_keys(exclude))
    }


def order_to_pref(jsi_order: typing.Iterable[str | type[JSI] | JSI], multiplier: int) -> JSIPreference:
    jsi_order = reversed(to_jsi_keys(jsi_order))
    pref_score = {jsi_cls: (i + 1) * multiplier for i, jsi_cls in enumerate(jsi_order)}

    def _pref(jsi: JSI, *args):
        return pref_score.get(jsi.JSI_KEY, 0)
    return _pref


class JSIWrapper:
    """
    Helper class to forward JS interp request to a JSI that supports it.

    Usage:
    ```
    def _real_extract(self, url):
        ...
        jsi = JSIWrapper(self, url)
        result = jsi.execute(jscode, video_id)
        ...
    ```

    @param dl_or_ie: `YoutubeDL` or `InfoExtractor` instance.
    @param url: setting url context
    @param only_include: limit JSI to choose from.
    @param exclude: JSI to avoid using.
    @param jsi_params: extra kwargs to pass to `JSI.__init__()` for each JSI, using jsi key as dict key.
    @param preferred_order: list of JSI to use. First in list is tested first.
    @param timeout: timeout parameter for all chosen JSI
    @param user_agent: override user-agent to use for supported JSI
    """

    def __init__(
        self,
        dl_or_ie: YoutubeDL | InfoExtractor,
        url: str = '',
        only_include: typing.Iterable[str | type[JSI]] = [],
        exclude: typing.Iterable[str | type[JSI]] = [],
        jsi_params: dict[str, dict] = {},
        preferred_order: typing.Iterable[str | type[JSI]] = [],
        timeout: float | int = 10,
        user_agent: str | None = None,
    ):
        if isinstance(dl_or_ie, InfoExtractor):
            self._downloader = dl_or_ie._downloader
            self._ie_key = dl_or_ie.ie_key()
        else:
            self._downloader = dl_or_ie
            self._ie_key = None

        self._url = self._sanitize_url(url)
        self.preferences: set[JSIPreference] = {
            order_to_pref(self._load_pref_from_option(), 10000),
            order_to_pref(preferred_order, 100),
        } | _JSI_PREFERENCES

        handler_classes = self._load_allowed_jsi_cls(only_include, exclude)
        if not handler_classes:
            raise ExtractorError('No JSI is allowed to use')

        self._handler_dict = {cls.JSI_KEY: cls(
            self._downloader, url=self._url, timeout=timeout,
            user_agent=user_agent, **jsi_params.get(cls.JSI_KEY, {}),
        ) for cls in handler_classes.values()}

        self._is_test = self._downloader.params.get('test', False)

    def _sanitize_url(self, url):
        sanitized = sanitize_url(url_or_none(url)) or ''
        if url and not sanitized:
            self.report_warning(f'Invalid URL: "{url}", using empty string instead')
        return sanitized

    def _load_pref_from_option(self):
        user_prefs = self._downloader.params.get('jsi_preference', [])
        valid_handlers = list(all_handlers())
        for invalid_key in [jsi_key for jsi_key in user_prefs if jsi_key not in valid_handlers]:
            self.report_warning(f'`{invalid_key}` is not a valid JSI, ignoring preference setting')
            user_prefs.remove(invalid_key)
        return user_prefs

    def _load_allowed_jsi_cls(self, only_include, exclude):
        handler_classes = get_included_jsi(only_include, exclude)
        self.write_debug(f'Select JSI: {to_jsi_keys(handler_classes)}, '
                         f'included: {to_jsi_keys(only_include) or "all"}, excluded: {to_jsi_keys(exclude)}')
        return handler_classes

    def write_debug(self, message, only_once=False):
        return self._downloader.write_debug(f'[JSIDirector] {message}', only_once=only_once)

    def report_warning(self, message, only_once=False):
        return self._downloader.report_warning(f'[JSIDirector] {message}', only_once=only_once)

    def _get_handlers(self, method_name: str, *args, **kwargs) -> list[JSI]:
        def _supports(jsi: JSI):
            if not callable(method := getattr(jsi, method_name, None)):
                return False
            method_params = inspect.signature(method).parameters
            return all(key in method_params for key in kwargs)

        handlers = [h for h in self._handler_dict.values() if _supports(h)]
        self.write_debug(f'Choosing handlers for method `{method_name}` with kwargs {list(kwargs)}'
                         f': {to_jsi_keys(handlers)}')

        if not handlers:
            raise ExtractorError(f'No JSI supports method `{method_name}` with kwargs {list(kwargs)}, '
                                 f'included handlers: {to_jsi_keys(self._handler_dict.values())}')

        preferences = {
            handler.JSI_KEY: sum(pref_func(handler, method_name, args, kwargs) for pref_func in self.preferences)
            for handler in handlers
        }
        self.write_debug('JSI preferences for `{}` request: {}'.format(
            method_name, ', '.join(f'{key}={pref}' for key, pref in preferences.items())))

        return sorted(handlers, key=lambda h: preferences[h.JSI_KEY], reverse=True)

    def _dispatch_request(self, method_name: str, *args, **kwargs):
        handlers = self._get_handlers(method_name, *args, **kwargs)

        unavailable: list[str] = []
        exceptions: list[tuple[JSI, Exception]] = []

        for handler in handlers:
            if not handler.is_available():
                if self._is_test:
                    raise ExtractorError(f'{handler.JSI_NAME} is not available for testing, '
                                         f'add "{handler.JSI_KEY}" in `exclude` if it should not be used')
                self.write_debug(f'{handler.JSI_KEY} is not available')
                unavailable.append(handler.JSI_NAME)
                continue

            try:
                self.write_debug(f'Dispatching `{method_name}` task to {handler.JSI_NAME}')
                return getattr(handler, method_name)(*args, **kwargs)
            except ExtractorError as e:
                if self._is_test:
                    raise ExtractorError(f'{handler.JSI_NAME} got error while evaluating js, '
                                         f'add "{handler.JSI_KEY}" in `exclude` if it should not be used')
                exceptions.append((handler, e))
                self.write_debug(f'{handler.JSI_NAME} encountered error, fallback to next handler: {e}')

        if not exceptions:
            msg = f'No available JSI installed, please install one of: {", ".join(unavailable)}'
        else:
            msg = f'Failed to perform {method_name}, total {len(exceptions)} errors'
            if unavailable:
                msg = f'{msg}. You may try installing one of unavailable JSI: {", ".join(unavailable)}'
        raise ExtractorError(msg)

    def execute(self, jscode: str, video_id: str | None, note: str | None = None,
                html: str | None = None, cookiejar: YoutubeDLCookieJar | None = None) -> str:
        """
        Execute JS code and return stdout from console.log

        @param jscode: JS code to execute
        @param video_id
        @param note
        @param html: html to load as document
        @param cookiejar: cookiejar to read and set cookies, pass `InfoExtractor.cookiejar` if you want to read and write cookies
        """
        return self._dispatch_request('execute', jscode, video_id, **filter_dict({
            'note': note, 'html': html, 'cookiejar': cookiejar}))


class JSI(abc.ABC):
    _BASE_PREFERENCE: int = 0

    def __init__(self, downloader: YoutubeDL, url: str, timeout: float | int, user_agent=None):
        self._downloader = downloader
        self._url = url
        self.timeout = timeout
        self.user_agent: str = user_agent or self._downloader.params['http_headers']['User-Agent']

    @abc.abstractmethod
    def is_available(self) -> bool:
        raise NotImplementedError

    def write_debug(self, message, *args, **kwargs):
        self._downloader.write_debug(f'[{self.JSI_KEY}] {message}', *args, **kwargs)

    def report_warning(self, message, *args, **kwargs):
        self._downloader.report_warning(f'[{self.JSI_KEY}] {message}', *args, **kwargs)

    def to_screen(self, msg, *args, **kwargs):
        self._downloader.to_screen(f'[{self.JSI_KEY}] {msg}', *args, **kwargs)

    def report_note(self, video_id, note):
        self.to_screen(f'{format_field(video_id, None, "%s: ")}{note}')

    @classproperty
    def JSI_NAME(cls) -> str:
        return cls.__name__[:-3]

    @classproperty
    def JSI_KEY(cls) -> str:
        assert cls.__name__.endswith('JSI'), 'JSI class names must end with "JSI"'
        return cls.__name__[:-3]


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


def register_jsi_preference(*handlers: type[JSI]):
    assert all(issubclass(handler, JSI) for handler in handlers), f'{handlers} must all be a subclass of JSI'

    def outer(pref_func: JSIPreference) -> JSIPreference:
        def inner(handler: JSI, *args):
            if not handlers or isinstance(handler, handlers):
                return pref_func(handler, *args)
            return 0
        _JSI_PREFERENCES.add(inner)
        return inner
    return outer


@register_jsi_preference()
def _base_preference(handler: JSI, *args):
    return min(10, getattr(handler, '_BASE_PREFERENCE', 0))


if typing.TYPE_CHECKING:
    from ..YoutubeDL import YoutubeDL
    from ..cookies import YoutubeDLCookieJar

    class JSIPreference(typing.Protocol):
        def __call__(self, handler: JSI, method_name: str, *args, **kwargs) -> int:
            ...
