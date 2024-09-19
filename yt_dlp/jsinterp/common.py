from __future__ import annotations

import abc
import typing

from ..utils import classproperty


DEFAULT_TIMEOUT = 10000
_JSI_HANDLERS: dict[str, type[JSI]] = {}
_JSI_PREFERENCES: set[JSIPreference] = set()
_ALL_FEATURES = {
    'js',
    'wasm',
    'dom',
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


class JSIExec(typing.Protocol):
    @abc.abstractmethod
    def execute(self, jscode: str) -> str:
        """Execute JS code and return console.log contents, using `html` requires `dom` feature"""


class JSIDirector(JSIExec):
    """JSIDirector class

    Helper class to forward JS interpretation need to a JSI that supports it.

    @param downloader: downloader instance.
    @param features: list of features that JSI must support.
    @param only_include: list of JSI to choose from.
    @param exclude: list of JSI to avoid using.
    @param jsi_params: extra parameters to pass to `JSI.__init__()`.
    @param preferred_order: list of JSI to use. First in list is tested first.
    @param fallback_jsi: list of JSI that may fail and should act non-fatal and fallback to other JSI. Pass `"all"` to always fallback
    @param timeout: timeout in miliseconds for JS interpretation
    """
    def __init__(
        self,
        downloader: YoutubeDL,
        features: typing.Iterable[str] = [],
        only_include: typing.Iterable[str | type[JSI]] = [],
        exclude: typing.Iterable[str | type[JSI]] = [],
        jsi_params: dict[str, dict] = {},
        preferred_order: typing.Iterable[str | type[JSI]] = [],
        fallback_jsi: typing.Iterable[str | type[JSI]] | typing.Literal['all'] = [],
        timeout: float | None = None,
        verbose=False,
    ):
        self._downloader = downloader
        self._verbose = verbose

        jsi_keys = set(get_jsi_keys(only_include or _JSI_HANDLERS)) - set(get_jsi_keys(exclude))
        handler_classes = [_JSI_HANDLERS[key] for key in jsi_keys
                           if _JSI_HANDLERS[key]._SUPPORTED_FEATURES.issuperset(features)]
        if not handler_classes:
            raise Exception(f'No JSI can be selected for features: {features}, '
                            f'included: {get_jsi_keys(only_include) or "all"}, excluded: {get_jsi_keys(exclude)}')

        self._handler_dict = {cls.JSI_KEY: cls(downloader, timeout, **jsi_params.get(cls.JSI_KEY, {}))
                              for cls in handler_classes}
        self.preferences: set[JSIPreference] = {order_to_pref(preferred_order, 100)} | _JSI_PREFERENCES
        self._fallback_jsi = get_jsi_keys(handler_classes) if fallback_jsi == 'all' else get_jsi_keys(fallback_jsi)

    def add_handler(self, handler: JSI):
        """Add a handler. If a handler of the same JSI_KEY exists, it will overwrite it"""
        assert isinstance(handler, JSI), 'handler must be a JSI instance'
        self._handler_dict[handler.JSI_KEY] = handler

    @property
    def write_debug(self):
        return self._downloader.write_debug

    @property
    def report_warning(self):
        return self._downloader.report_warning

    def _get_handlers(self, method: str, *args, **kwargs) -> list[JSI]:
        handlers = [h for h in self._handler_dict.values() if getattr(h, method, None)]
        self.write_debug(f'JSIDirector has handlers for `{method}`: {handlers}')
        if not handlers:
            raise Exception(f'No JSI supports method `{method}`, '
                            f'included handlers: {[handler.JSI_KEY for handler in self._handler_dict.values()]}')

        preferences = {
            handler: sum(pref_func(handler, method, args, kwargs) for pref_func in self.preferences)
            for handler in handlers
        }
        self._downloader.write_debug('JSI preferences for this request: {}'.format(', '.join(
            f'{jsi.JSI_NAME}={pref}' for jsi, pref in preferences.items())))

        return sorted(self._handler_dict.values(), key=preferences.get, reverse=True)

    # def _send(self, request: JSIRequest):
    #     unavailable_handlers = []
    #     exec_errors = []
    #     for handler in self._get_handlers(request):
    #         if not handler.is_available:
    #             unavailable_handlers.append(handler)
    #             continue
    #         try:
    #             return handler.handle(request)
    #         except Exception as e:
    #             exec_errors.append(e)
    #             if not request.fallback:
    #                 raise
    #     raise EvaluationError

    def _get_handler_method(method_name: str):
        def handler(self: JSIDirector, *args, **kwargs):
            unavailable: list[JSI] = []
            exceptions: list[tuple[JSI, Exception]] = []
            is_test = self._downloader.params.get('test', False)
            results: list[tuple[JSI, typing.Any]] = []

            for handler in self._get_handlers(method_name, *args, **kwargs):
                if not handler.is_available:
                    if is_test:
                        raise Exception(f'{handler.JSI_NAME} is not available for testing, '
                                        f'add "{handler.JSI_KEY}" in `exclude` if it should not be used')
                    self.write_debug(f'{handler.JSI_NAME} is not available')
                    unavailable.append(handler)
                    continue
                try:
                    self.write_debug(f'Dispatching `{method_name}` task to {handler.JSI_NAME}')
                    result = getattr(handler, method_name)(*args, **kwargs)
                    if is_test:
                        results.append((handler, result))
                    else:
                        return result
                except Exception as e:
                    if handler.JSI_KEY not in self._fallback_jsi:
                        raise
                    else:
                        exceptions.append((handler, e))
                        self.write_debug(f'{handler.JSI_NAME} encountered error, fallback to next handler: {e}')

            if not is_test or not results:
                if not exceptions:
                    msg = f'No available JSI installed, please install one of: {join_jsi_name(unavailable)}'
                else:
                    msg = f'Failed to perform {method_name}, total {len(exceptions)} errors'
                    if unavailable:
                        msg = f'{msg}. You can try installing one of unavailable JSI: {join_jsi_name(unavailable)}'
                raise Exception(msg)

            if is_test:
                ref_handler, ref_result = results[0]
                for handler, result in results[1:]:
                    if result != ref_result:
                        self.report_warning(
                            f'Different JSI results produced from {ref_handler.JSI_NAME} and {handler.JSI_NAME}')
                return ref_result

        return handler

    execute = _get_handler_method('execute')
    evaluate = _get_handler_method('evaluate')


class JSI(abc.ABC):
    _SUPPORTED_FEATURES: set[str] = set()
    _BASE_PREFERENCE: int = 0

    def __init__(self, downloader: YoutubeDL, timeout: float | int | None = None):
        self._downloader = downloader
        self.timeout = float(timeout or DEFAULT_TIMEOUT)

    @property
    @abc.abstractmethod
    def is_available(self) -> bool:
        raise NotImplementedError

    @classproperty
    def JSI_NAME(cls) -> str:
        return cls.__name__[:-3]

    @classproperty
    def JSI_KEY(cls) -> str:
        assert cls.__name__.endswith('JSI'), 'JSI class names must end with "JSI"'
        return cls.__name__[:-3]


def register_jsi(handler_cls: TYPE_JSI) -> TYPE_JSI:
    """Register a JS interpreter class"""
    assert issubclass(handler_cls, JSI), f'{handler_cls} must be a subclass of JSI'
    assert handler_cls.JSI_KEY not in _JSI_HANDLERS, f'JSI {handler_cls.JSI_KEY} already registered'
    assert handler_cls._SUPPORTED_FEATURES.issubset(_ALL_FEATURES), f'{handler_cls._SUPPORTED_FEATURES - _ALL_FEATURES} is not declared in `_All_FEATURES`'
    _JSI_HANDLERS[handler_cls.JSI_KEY] = handler_cls
    return handler_cls


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
    JSIPreference = typing.Callable[[JSI, str, list, dict], int]
    TYPE_JSI = typing.TypeVar('TYPE_JSI')
