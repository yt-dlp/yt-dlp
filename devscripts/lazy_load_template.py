#!/usr/bin/env python3
# coding: utf-8
from __future__ import unicode_literals

import re


class LazyLoadExtractor(object):
    _module = None

    @classmethod
    def ie_key(cls):
        return cls.__name__[:-2]

    def __new__(cls, *args, **kwargs):
        mod = __import__(cls._module, fromlist=(cls.__name__,))
        real_cls = getattr(mod, cls.__name__)
        instance = real_cls.__new__(real_cls)
        instance.__init__(*args, **kwargs)
        return instance
