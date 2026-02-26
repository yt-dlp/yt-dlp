from __future__ import annotations

import abc
import enum
import functools

from yt_dlp.extractor.common import InfoExtractor
from yt_dlp.utils import NO_DEFAULT, bug_reports_message, classproperty, traverse_obj
from yt_dlp.version import __version__

# xxx: these could be generalized outside YoutubeIE eventually


class IEContentProviderLogger(abc.ABC):

    class LogLevel(enum.IntEnum):
        TRACE = 0
        DEBUG = 10
        INFO = 20
        WARNING = 30
        ERROR = 40

        @classmethod
        def _missing_(cls, value):
            if isinstance(value, str):
                value = value.upper()
                if value in dir(cls):
                    return cls[value]

            return cls.INFO

    log_level = LogLevel.INFO

    @abc.abstractmethod
    def trace(self, message: str):
        pass

    @abc.abstractmethod
    def debug(self, message: str, *, once=False):
        pass

    @abc.abstractmethod
    def info(self, message: str):
        pass

    @abc.abstractmethod
    def warning(self, message: str, *, once=False):
        pass

    @abc.abstractmethod
    def error(self, message: str, cause=None):
        pass


class IEContentProviderError(Exception):
    def __init__(self, msg=None, expected=False):
        super().__init__(msg)
        self.expected = expected


class IEContentProvider(abc.ABC):
    PROVIDER_VERSION: str = '0.0.0'
    BUG_REPORT_LOCATION: str = '(developer has not provided a bug report location)'

    def __init__(
        self,
        ie: InfoExtractor,
        logger: IEContentProviderLogger,
        settings: dict[str, list[str]], *_, **__,
    ):
        self.ie = ie
        self.settings = settings or {}
        self.logger = logger
        super().__init__()

    @classmethod
    def __init_subclass__(cls, *, suffix=None, **kwargs):
        if suffix:
            cls._PROVIDER_KEY_SUFFIX = suffix
        return super().__init_subclass__(**kwargs)

    @classproperty
    def PROVIDER_NAME(cls) -> str:
        return cls.__name__[:-len(cls._PROVIDER_KEY_SUFFIX)]

    @classproperty
    def BUG_REPORT_MESSAGE(cls):
        return f'please report this issue to the provider developer at  {cls.BUG_REPORT_LOCATION}  .'

    @classproperty
    def PROVIDER_KEY(cls) -> str:
        assert hasattr(cls, '_PROVIDER_KEY_SUFFIX'), 'Content Provider implementation must define a suffix for the provider key'
        assert cls.__name__.endswith(cls._PROVIDER_KEY_SUFFIX), f'Class name must end with "{cls._PROVIDER_KEY_SUFFIX}"'
        return cls.__name__[:-len(cls._PROVIDER_KEY_SUFFIX)]

    @abc.abstractmethod
    def is_available(self) -> bool:
        """
        Check if the provider is available (e.g. all required dependencies are available)
        This is used to determine if the provider should be used and to provide debug information.

        IMPORTANT: This method should not make any network requests or perform any expensive operations.
         It is called multiple times.
        """
        raise NotImplementedError

    def close(self):  # noqa: B027
        pass

    def _configuration_arg(self, key, default=NO_DEFAULT, *, casesense=False):
        """
        @returns            A list of values for the setting given by "key"
                            or "default" if no such key is present
        @param default      The default value to return when the key is not present (default: [])
        @param casesense    When false, the values are converted to lower case
        """
        return configuration_arg(self.settings, key, default=default, casesense=casesense)


class BuiltinIEContentProvider(IEContentProvider, abc.ABC):
    PROVIDER_VERSION = __version__
    BUG_REPORT_MESSAGE = bug_reports_message(before='')


def configuration_arg(config, key, default=NO_DEFAULT, *, casesense=False):
    """
    @returns            A list of values for the setting given by "key"
                        or "default" if no such key is present
    @param config       The configuration dictionary
    @param default      The default value to return when the key is not present (default: [])
    @param casesense    When false, the values are converted to lower case
    """
    val = traverse_obj(config, key)
    if val is None:
        return [] if default is NO_DEFAULT else default
    return list(val) if casesense else [x.lower() for x in val]


def register_provider_generic(
    provider,
    base_class,
    registry,
):
    """Generic function to register a provider class"""
    assert issubclass(provider, base_class), f'{provider} must be a subclass of {base_class.__name__}'
    assert provider.PROVIDER_KEY not in registry, f'{base_class.__name__} {provider.PROVIDER_KEY} already registered'
    registry[provider.PROVIDER_KEY] = provider
    return provider


def register_preference_generic(
    base_class,
    registry,
    *providers,
):
    """Generic function to register a preference for a provider"""
    assert all(issubclass(provider, base_class) for provider in providers)

    def outer(preference):
        @functools.wraps(preference)
        def inner(provider, *args, **kwargs):
            if not providers or isinstance(provider, providers):
                return preference(provider, *args, **kwargs)
            return 0
        registry.add(inner)
        return preference
    return outer
