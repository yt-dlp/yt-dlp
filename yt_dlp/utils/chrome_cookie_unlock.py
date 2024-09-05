import sys

import yt_dlp.cookies

original_func = yt_dlp.cookies._open_database_copy

def unlock_chrome(database_path, tmpdir):
    try:
        return original_func(database_path, tmpdir)
    except PermissionError:
        print('Attempting to unlock cookies', file=sys.stderr)
        unlock_cookies(database_path)
        return original_func(database_path, tmpdir)

yt_dlp.cookies._open_database_copy = unlock_chrome


# Adapted from https://gist.github.com/csm10495/e89e660ffee0030e8ef410b793ad6a7e
# By Charles Machalow under the MIT License

from ctypes import windll, byref, create_unicode_buffer, pointer, WINFUNCTYPE
from ctypes.wintypes import DWORD, WCHAR, UINT

ERROR_SUCCESS = 0
ERROR_MORE_DATA  = 234
RmForceShutdown = 1

@WINFUNCTYPE(None, UINT)
def callback(percent_complete: UINT) -> None:
    pass

rstrtmgr = windll.LoadLibrary("Rstrtmgr")

def unlock_cookies(cookies_path):
    session_handle = DWORD(0)
    session_flags = DWORD(0)
    session_key = (WCHAR * 256)()

    result = DWORD(rstrtmgr.RmStartSession(byref(session_handle), session_flags, session_key)).value

    if result != ERROR_SUCCESS:
        raise RuntimeError(f"RmStartSession returned non-zero result: {result}")

    try:
        result = DWORD(rstrtmgr.RmRegisterResources(session_handle, 1, byref(pointer(create_unicode_buffer(cookies_path))), 0, None, 0, None)).value

        if result != ERROR_SUCCESS:
            raise RuntimeError(f"RmRegisterResources returned non-zero result: {result}")

        proc_info_needed = DWORD(0)
        proc_info = DWORD(0)
        reboot_reasons = DWORD(0)

        result = DWORD(rstrtmgr.RmGetList(session_handle, byref(proc_info_needed), byref(proc_info), None, byref(reboot_reasons))).value

        if result not in (ERROR_SUCCESS, ERROR_MORE_DATA):
            raise RuntimeError(f"RmGetList returned non-successful result: {result}")

        if proc_info_needed.value:
            result = DWORD(rstrtmgr.RmShutdown(session_handle, RmForceShutdown, callback)).value

            if result != ERROR_SUCCESS:
                raise RuntimeError(f"RmShutdown returned non-successful result: {result}")
        else:
            print("File is not locked")
    finally:
        result = DWORD(rstrtmgr.RmEndSession(session_handle)).value

        if result != ERROR_SUCCESS:
            raise RuntimeError(f"RmEndSession returned non-successful result: {result}")
