# coding: utf-8
import re


class LazyLoadMetaClass(type):
    def __getattr__(cls, name):
        return getattr(cls._get_real_class(), name)


class LazyLoadExtractor(metaclass=LazyLoadMetaClass):
    _module = None
    _WORKING = True

    @classmethod
    def _get_real_class(cls):
        if '__real_class' not in cls.__dict__:
            mod = __import__(cls._module, fromlist=(cls.__name__,))
            cls.__real_class = getattr(mod, cls.__name__)
        return cls.__real_class

    def __new__(cls, *args, **kwargs):
        real_cls = cls._get_real_class()
        instance = real_cls.__new__(real_cls)
        instance.__init__(*args, **kwargs)
        return instance
