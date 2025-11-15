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
        try:
            lib = cdll.LoadLibrary(self.runtime_info.path)
            self.lib = lib
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
        except (OSError, AttributeError):
            self.lib = None

    def _run_js_runtime(self, stdin: str, /) -> str:
        ctx = self.JSGlobalContextCreate(None)

        def jsstring_to_str(jsstr):
            size = self.JSStringGetLength(jsstr) * 2
            ptr = self.JSStringGetCharactersPtr(jsstr)
            return string_at(ptr, size).decode('utf-16')

        def jsvalue_to_json(jsval):
            err = c_voidp()
            string = self.JSValueCreateJSONString(ctx, jsval, 0, byref(err))
            if string:
                res = jsstring_to_str(string)
                self.JSStringRelease(string)
                return res
            else:
                raise JavaScriptCoreError(err)

        def eval_js(code):
            jscode = self.JSStringCreateWithUTF8CString(code)
            try:
                err = c_voidp()
                res = self.JSEvaluateScript(ctx, jscode, None, None, 0, byref(err))
                if res:
                    return res
                raise JavaScriptCoreError(err)
            finally:
                self.JSStringRelease(jscode)

        try:
            eval_js(self._get_init_script().encode('utf-8'))
            return jsvalue_to_json(eval_js(stdin.encode('utf-8')))
        except JavaScriptCoreError as err:
            jsstr = self.JSValueToStringCopy(ctx, err.value, None)
            if jsstr:
                msg = jsstring_to_str(jsstr)
                self.JSStringRelease(jsstr)
            else:
                msg = 'Failed to stringify exception!'
            raise JsChallengeProviderError(f'JavaScriptCore threw an exception: {msg}')
        finally:
            self.JSGlobalContextRelease(ctx)

    def _construct_stdin(self, player: str, preprocessed: bool, requests: list[JsChallengeRequest], /) -> str:
        return f'jsc({json.dumps(self._construct_request_object(player, preprocessed, requests))})'

    def is_available(self):
        return self.lib and super().is_available()


@register_preference(JavaScriptCoreJCP)
def preference(provider: JsChallengeProvider, requests: list[JsChallengeRequest]) -> int:
    return 800
