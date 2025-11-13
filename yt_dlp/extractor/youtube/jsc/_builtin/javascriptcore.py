from __future__ import annotations

import json
from ctypes import (
    byref,
    c_char_p,
    c_int,
    c_size_t,
    c_uint,
    c_voidp,
    cdll,
    string_at,
)

from yt_dlp.extractor.youtube.jsc._builtin.ejs import EJSBaseJCP
from yt_dlp.extractor.youtube.jsc.provider import (
    JsChallengeProvider,
    JsChallengeProviderError,
    JsChallengeRequest,
    register_preference,
    register_provider,
)
from yt_dlp.extractor.youtube.pot._provider import BuiltinIEContentProvider


class JavaScriptCoreError(Exception):
    def __init__(self, value):
        self.value = value


def _set_signature(fn, restype, *args):
    fn.restype = restype
    fn.argtypes = args
    return fn


@register_provider
class JavaScriptCoreJCP(EJSBaseJCP, BuiltinIEContentProvider):
    PROVIDER_NAME = 'javascriptcore'
    JS_RUNTIME_NAME = 'javascriptcore'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        lib = cdll.LoadLibrary(self.runtime_info.path)
        self.JSGlobalContextCreate = _set_signature(lib.JSGlobalContextCreate, c_voidp, c_voidp)
        self.JSGlobalContextRelease = _set_signature(lib.JSGlobalContextRelease, None, c_voidp)
        self.JSStringCreateWithUTF8CString = _set_signature(lib.JSStringCreateWithUTF8CString, c_voidp, c_char_p)
        self.JSStringRelease = _set_signature(lib.JSStringRelease, None, c_voidp)
        self.JSStringGetLength = _set_signature(lib.JSStringGetLength, c_size_t, c_voidp)
        self.JSStringGetCharactersPtr = _set_signature(lib.JSStringGetCharactersPtr, c_voidp, c_voidp)
        self.JSEvaluateScript = _set_signature(lib.JSEvaluateScript, c_voidp, c_voidp, c_voidp, c_voidp, c_voidp, c_int, c_voidp)
        self.JSValueToStringCopy = _set_signature(lib.JSValueToStringCopy, c_voidp, c_voidp, c_voidp, c_voidp)
        self.JSValueCreateJSONString = _set_signature(lib.JSValueCreateJSONString, c_voidp, c_voidp, c_voidp, c_uint, c_voidp)
        self.JSGarbageCollect = _set_signature(lib.JSGarbageCollect, None, c_voidp)
        self.ctx = None

    def _jsstring_to_str(self, jsstr):
        size = self.JSStringGetLength(jsstr) * 2
        ptr = self.JSStringGetCharactersPtr(jsstr)
        return string_at(ptr, size).decode('utf-16')

    def _jsvalue_to_json(self, jsval):
        err = c_voidp()
        string = self.JSValueCreateJSONString(self.ctx, jsval, 0, byref(err))
        if string:
            res = self._jsstring_to_str(string)
            self.JSStringRelease(string)
            return res
        else:
            raise JavaScriptCoreError(err)

    def _jsvalue_to_json(self, jsval):
        err = c_voidp()
        string = self.JSValueCreateJSONString(self.ctx, jsval, 0, byref(err))
        if string:
            res = self._jsstring_to_str(string)
            self.JSStringRelease(string)
            return res
        else:
            raise JavaScriptCoreError(err)

    def _eval_js(self, code):
        jscode = self.JSStringCreateWithUTF8CString(code)
        try:
            err = c_voidp()
            res = self.JSEvaluateScript(self.ctx, jscode, None, None, 0, byref(err))
            if res:
                return res
            raise JavaScriptCoreError(err)
        finally:
            self.JSStringRelease(jscode)

    def _run_js_runtime(self, stdin: str, /) -> str:
        res = self._jsvalue_to_json(self._eval_js(stdin.encode('utf-8')))
        self.JSGarbageCollect(self.ctx)
        return res

    def _real_bulk_solve(self, /, requests: list[JsChallengeRequest]):
        self.ctx = self.JSGlobalContextCreate(None)
        try:
            self._eval_js(self._get_init_script().encode('utf-8'))
            yield from super()._real_bulk_solve(requests=requests)
        except JavaScriptCoreError as err:
            jsstr = self.JSValueToStringCopy(self.ctx, err.value, None)
            if jsstr:
                msg = self._jsstring_to_str(jsstr)
                self.JSStringRelease(jsstr)
            else:
                msg = 'Failed to stringify exception!'
            raise JsChallengeProviderError(f'JavaScriptCore threw an exception: {msg}')
        finally:
            self.JSGlobalContextRelease(self.ctx)
            self.ctx = None

    def _construct_stdin(self, player: str, preprocessed: bool, requests: list[JsChallengeRequest], /) -> str:
        return f'jsc({json.dumps(self._construct_request_object(player, preprocessed, requests))})'


@register_preference(JavaScriptCoreJCP)
def preference(provider: JsChallengeProvider, requests: list[JsChallengeRequest]) -> int:
    return 800
