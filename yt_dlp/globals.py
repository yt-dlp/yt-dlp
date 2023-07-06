from contextvars import ContextVar


class UNSET:
    pass


class GlobalVar:
    def __init__(self, name, default=UNSET):
        self.name, self.value = name, default

    def __repr__(self):
        if self.value is UNSET:
            return f'{type(self).__name__}({self.name!r})'
        return f'{type(self).__name__}({self.name!r}, {self.value!r})'

    def get(self):
        if self.value is UNSET:
            raise ValueError(f'{self} is unset')
        return self.value

    def set(self, value):
        self.value = value


_IN_CLI = GlobalVar('_IN_CLI', default=False)

# `True`=enabled, `None`=disabled, `False`=force disabled
LAZY_EXTRACTORS = GlobalVar('LAZY_EXTRACTORS')
ALL_IES = GlobalVar('ALL_IES')
PLUGIN_IES = GlobalVar('PLUGIN_IES')

ALL_PPS = GlobalVar('ALL_PPS')
PLUGIN_PPS = GlobalVar('PLUGIN_PPS')


# Intended to be changed by users
ffmpeg_location = ContextVar('ffmpeg_location', default=None)
