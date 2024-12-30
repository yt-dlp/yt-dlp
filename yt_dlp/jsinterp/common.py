from __future__ import annotations

import abc
import typing
import functools

from ..utils import classproperty, format_field, variadic, ExtractorError
from ..extractor.common import InfoExtractor


_JSI_HANDLERS: dict[str, type[JSI]] = {}
_JSI_PREFERENCES: set[JSIPreference] = set()
_ALL_FEATURES = {
    'js',
    'wasm',
    'location',
    'dom',
    'cookies',
}


def get_jsi_keys(jsi_or_keys: typing.Iterable[str | type[JSI] | JSI]) -> list[str]:
    return [jok if isinstance(jok, str) else jok.JSI_KEY for jok in jsi_or_keys]


def order_to_pref(jsi_order: typing.Iterable[str | type[JSI] | JSI], multiplier: int) -> JSIPreference:
    jsi_order = reversed(get_jsi_keys(jsi_order))
    pref_score = {jsi_cls: (i + 1) * multiplier for i, jsi_cls in enumerate(jsi_order)}

    def _pref(jsi: JSI, *args):
        return pref_score.get(jsi.JSI_KEY, 0)
    return _pref


def join_jsi_name(jsi_list: typing.Iterable[str | type[JSI] | JSI], sep=', '):
    return sep.join(get_jsi_keys(jok if isinstance(jok, str) else jok.JSI_NAME for jok in jsi_list))


def require_features(param_features: dict[str, str | typing.Iterable[str]]):
    assert all(_ALL_FEATURES.issuperset(variadic(kw_feature)) for kw_feature in param_features.values())

    def outer(func):
        @functools.wraps(func)
        def inner(self: JSInterp, *args, **kwargs):
            for kw_name, kw_feature in param_features.items():
                if kw_name in kwargs and not self._features.issuperset(variadic(kw_feature)):
                    raise ExtractorError(f'feature {kw_feature} is required for `{kw_name}` param but not declared')
            return func(self, *args, **kwargs)
        return inner
    return outer


class JSInterp:
    """
    Helper class to forward JS interp request to a concrete JSI that supports it.

    @param dl_or_ie: `YoutubeDL` or `InfoExtractor` instance.
    @param features: list of features that JSI must support.
    @param only_include: limit JSI to choose from.
    @param exclude: JSI to avoid using.
    @param jsi_params: extra kwargs to pass to `JSI.__init__()` for each JSI, using jsi key as dict key.
    @param preferred_order: list of JSI to use. First in list is tested first.
    @param fallback_jsi: list of JSI that may fail and should act non-fatal and fallback to other JSI. Pass `"all"` to always fallback
    @param timeout: timeout parameter for all chosen JSI
    """

    def __init__(
        self,
        dl_or_ie: YoutubeDL | InfoExtractor,
        features: typing.Iterable[str] = [],
        only_include: typing.Iterable[str | type[JSI]] = [],
        exclude: typing.Iterable[str | type[JSI]] = [],
        jsi_params: dict[str, dict] = {},
        preferred_order: typing.Iterable[str | type[JSI]] = [],
        fallback_jsi: typing.Iterable[str | type[JSI]] | typing.Literal['all'] = [],
        timeout: float | int = 10,
    ):
        self._downloader: YoutubeDL = dl_or_ie._downloader if isinstance(dl_or_ie, InfoExtractor) else dl_or_ie
        self._features = set(features)

        if unsupported_features := self._features - _ALL_FEATURES:
            raise ExtractorError(f'Unsupported features: {unsupported_features}, allowed features: {_ALL_FEATURES}')

        jsi_keys = [key for key in get_jsi_keys(only_include or _JSI_HANDLERS) if key not in get_jsi_keys(exclude)]
        self.write_debug(f'Allowed JSI keys: {jsi_keys}')
        handler_classes = [_JSI_HANDLERS[key] for key in jsi_keys
                           if _JSI_HANDLERS[key]._SUPPORT_FEATURES.issuperset(self._features)]
        self.write_debug(f'Selected JSI classes for given features: {get_jsi_keys(handler_classes)}, '
                         f'included: {get_jsi_keys(only_include) or "all"}, excluded: {get_jsi_keys(exclude)}')

        self._handler_dict = {cls.JSI_KEY: cls(self._downloader, timeout=timeout, **jsi_params.get(cls.JSI_KEY, {}))
                              for cls in handler_classes}
        self.preferences: set[JSIPreference] = {order_to_pref(preferred_order, 100)} | _JSI_PREFERENCES
        self._fallback_jsi = get_jsi_keys(handler_classes) if fallback_jsi == 'all' else get_jsi_keys(fallback_jsi)
        self._is_test = self._downloader.params.get('test', False)

    def add_handler(self, handler: JSI):
        """Add a handler. If a handler of the same JSI_KEY exists, it will overwrite it"""
        assert isinstance(handler, JSI), 'handler must be a JSI instance'
        if not handler._SUPPORT_FEATURES.issuperset(self._features):
            raise ExtractorError(f'{handler.JSI_NAME} does not support all required features: {self._features}')
        self._handler_dict[handler.JSI_KEY] = handler

    def write_debug(self, message, only_once=False):
        return self._downloader.write_debug(f'[JSIDirector] {message}', only_once=only_once)

    def report_warning(self, message, only_once=False):
        return self._downloader.report_warning(f'[JSIDirector] {message}', only_once=only_once)

    def _get_handlers(self, method_name: str, *args, **kwargs) -> list[JSI]:
        handlers = [h for h in self._handler_dict.values() if callable(getattr(h, method_name, None))]
        self.write_debug(f'Choosing handlers for method `{method_name}`: {get_jsi_keys(handlers)}')
        if not handlers:
            raise ExtractorError(f'No JSI supports method `{method_name}`, '
                                 f'included handlers: {get_jsi_keys(self._handler_dict.values())}')

        preferences = {
            handler.JSI_KEY: sum(pref_func(handler, method_name, args, kwargs) for pref_func in self.preferences)
            for handler in handlers
        }
        self.write_debug('JSI preferences for `{}` request: {}'.format(
            method_name, ', '.join(f'{key}={pref}' for key, pref in preferences.items())))

        return sorted(handlers, key=lambda h: preferences[h.JSI_KEY], reverse=True)

    def _dispatch_request(self, method_name: str, *args, **kwargs):
        handlers = self._get_handlers(method_name, *args, **kwargs)

        unavailable: list[JSI] = []
        exceptions: list[tuple[JSI, Exception]] = []
        test_results: list[tuple[JSI, typing.Any]] = []

        for handler in handlers:
            if not handler.is_available():
                if self._is_test:
                    raise Exception(f'{handler.JSI_NAME} is not available for testing, '
                                    f'add "{handler.JSI_KEY}" in `exclude` if it should not be used')
                self.write_debug(f'{handler.JSI_NAME} is not available')
                unavailable.append(handler)
                continue
            try:
                self.write_debug(f'Dispatching `{method_name}` task to {handler.JSI_NAME}')
                result = getattr(handler, method_name)(*args, **kwargs)
                if self._is_test:
                    test_results.append((handler, result))
                else:
                    return result
            except Exception as e:
                if handler.JSI_KEY not in self._fallback_jsi:
                    raise
                else:
                    exceptions.append((handler, e))
                    self.write_debug(f'{handler.JSI_NAME} encountered error, fallback to next handler: {e}')

        if self._is_test and test_results:
            ref_handler, ref_result = test_results[0]
            for handler, result in test_results[1:]:
                if result != ref_result:
                    self.report_warning(
                        f'Different JSI results produced from {ref_handler.JSI_NAME} and {handler.JSI_NAME}')
            return ref_result

        if not exceptions:
            msg = f'No available JSI installed, please install one of: {join_jsi_name(unavailable)}'
        else:
            msg = f'Failed to perform {method_name}, total {len(exceptions)} errors'
            if unavailable:
                msg = f'{msg}. You can try installing one of unavailable JSI: {join_jsi_name(unavailable)}'
        raise ExtractorError(msg)

    @require_features({'location': 'location', 'html': 'dom', 'cookiejar': 'cookies'})
    def execute(self, jscode: str, video_id: str | None, **kwargs) -> str:
        """
        Execute JS code and return stdout from console.log

        @param {str} jscode: JS code to execute
        @param video_id: video id
        @param note: note
        @param {str} location: url to configure window.location, requires `location` feature
        @param {str} html: html to load as document, requires `dom` feature
        @param {YoutubeDLCookieJar} cookiejar: cookiejar to set cookies, requires url and `cookies` feature
        """
        return self._dispatch_request('execute', jscode, video_id, **kwargs)


class JSI(abc.ABC):
    _SUPPORT_FEATURES: set[str] = set()
    _BASE_PREFERENCE: int = 0

    def __init__(self, downloader: YoutubeDL, timeout: float | int):
        self._downloader = downloader
        self.timeout = timeout

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


def register_jsi(jsi_cls: JsiClass) -> JsiClass:
    """Register a JS interpreter class"""
    assert issubclass(jsi_cls, JSI), f'{jsi_cls} must be a subclass of JSI'
    assert jsi_cls.JSI_KEY not in _JSI_HANDLERS, f'JSI {jsi_cls.JSI_KEY} already registered'
    assert jsi_cls._SUPPORT_FEATURES.issubset(_ALL_FEATURES), f'{jsi_cls._SUPPORT_FEATURES - _ALL_FEATURES}  not declared in `_All_FEATURES`'
    _JSI_HANDLERS[jsi_cls.JSI_KEY] = jsi_cls
    return jsi_cls


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
    return getattr(handler, '_BASE_PREFERENCE', 0)


if typing.TYPE_CHECKING:
    from ..YoutubeDL import YoutubeDL
    JsiClass = typing.TypeVar('JsiClass', bound=type[JSI])

    class JSIPreference(typing.Protocol):
        def __call__(self, handler: JSI, method_name: str, *args, **kwargs) -> int:
            ...
