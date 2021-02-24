#!/usr/bin/python3

import argparse
import ctypes
import functools
import shutil
import subprocess
import sys
import tempfile
import threading
import traceback
import os.path

sys.path.insert(0, os.path.dirname(os.path.dirname((os.path.abspath(__file__)))))
from yt_dlp.compat import (
    compat_input,
    compat_http_server,
    compat_str,
    compat_urlparse,
)

# These are not used outside of buildserver.py thus not in compat.py

try:
    import winreg as compat_winreg
except ImportError:  # Python 2
    import _winreg as compat_winreg

try:
    import socketserver as compat_socketserver
except ImportError:  # Python 2
    import SocketServer as compat_socketserver


class BuildHTTPServer(compat_socketserver.ThreadingMixIn, compat_http_server.HTTPServer):
    allow_reuse_address = True


advapi32 = ctypes.windll.advapi32

SC_MANAGER_ALL_ACCESS = 0xf003f
SC_MANAGER_CREATE_SERVICE = 0x02
SERVICE_WIN32_OWN_PROCESS = 0x10
SERVICE_AUTO_START = 0x2
SERVICE_ERROR_NORMAL = 0x1
DELETE = 0x00010000
SERVICE_STATUS_START_PENDING = 0x00000002
SERVICE_STATUS_RUNNING = 0x00000004
SERVICE_ACCEPT_STOP = 0x1

SVCNAME = 'youtubedl_builder'

LPTSTR = ctypes.c_wchar_p
START_CALLBACK = ctypes.WINFUNCTYPE(None, ctypes.c_int, ctypes.POINTER(LPTSTR))


class SERVICE_TABLE_ENTRY(ctypes.Structure):
    _fields_ = [
        ('lpServiceName', LPTSTR),
        ('lpServiceProc', START_CALLBACK)
    ]


HandlerEx = ctypes.WINFUNCTYPE(
    ctypes.c_int,     # return
    ctypes.c_int,     # dwControl
    ctypes.c_int,     # dwEventType
    ctypes.c_void_p,  # lpEventData,
    ctypes.c_void_p,  # lpContext,
)


def _ctypes_array(c_type, py_array):
    ar = (c_type * len(py_array))()
    ar[:] = py_array
    return ar


def win_OpenSCManager():
    res = advapi32.OpenSCManagerW(None, None, SC_MANAGER_ALL_ACCESS)
    if not res:
        raise Exception('Opening service manager failed - '
                        'are you running this as administrator?')
    return res


def win_install_service(service_name, cmdline):
    manager = win_OpenSCManager()
    try:
        h = advapi32.CreateServiceW(
            manager, service_name, None,
            SC_MANAGER_CREATE_SERVICE, SERVICE_WIN32_OWN_PROCESS,
            SERVICE_AUTO_START, SERVICE_ERROR_NORMAL,
            cmdline, None, None, None, None, None)
        if not h:
            raise OSError('Service creation failed: %s' % ctypes.FormatError())

        advapi32.CloseServiceHandle(h)
    finally:
        advapi32.CloseServiceHandle(manager)


def win_uninstall_service(service_name):
    manager = win_OpenSCManager()
    try:
        h = advapi32.OpenServiceW(manager, service_name, DELETE)
        if not h:
            raise OSError('Could not find service %s: %s' % (
                service_name, ctypes.FormatError()))

        try:
            if not advapi32.DeleteService(h):
                raise OSError('Deletion failed: %s' % ctypes.FormatError())
        finally:
            advapi32.CloseServiceHandle(h)
    finally:
        advapi32.CloseServiceHandle(manager)


def win_service_report_event(service_name, msg, is_error=True):
    with open('C:/sshkeys/log', 'a', encoding='utf-8') as f:
        f.write(msg + '\n')

    event_log = advapi32.RegisterEventSourceW(None, service_name)
    if not event_log:
        raise OSError('Could not report event: %s' % ctypes.FormatError())

    try:
        type_id = 0x0001 if is_error else 0x0004
        event_id = 0xc0000000 if is_error else 0x40000000
        lines = _ctypes_array(LPTSTR, [msg])

        if not advapi32.ReportEventW(
                event_log, type_id, 0, event_id, None, len(lines), 0,
                lines, None):
            raise OSError('Event reporting failed: %s' % ctypes.FormatError())
    finally:
        advapi32.DeregisterEventSource(event_log)


def win_service_handler(stop_event, *args):
    try:
        raise ValueError('Handler called with args ' + repr(args))
        TODO
    except Exception as e:
        tb = traceback.format_exc()
        msg = str(e) + '\n' + tb
        win_service_report_event(service_name, msg, is_error=True)
        raise


def win_service_set_status(handle, status_code):
    svcStatus = SERVICE_STATUS()
    svcStatus.dwServiceType = SERVICE_WIN32_OWN_PROCESS
    svcStatus.dwCurrentState = status_code
    svcStatus.dwControlsAccepted = SERVICE_ACCEPT_STOP

    svcStatus.dwServiceSpecificExitCode = 0

    if not advapi32.SetServiceStatus(handle, ctypes.byref(svcStatus)):
        raise OSError('SetServiceStatus failed: %r' % ctypes.FormatError())


def win_service_main(service_name, real_main, argc, argv_raw):
    try:
        # args = [argv_raw[i].value for i in range(argc)]
        stop_event = threading.Event()
        handler = HandlerEx(functools.partial(stop_event, win_service_handler))
        h = advapi32.RegisterServiceCtrlHandlerExW(service_name, handler, None)
        if not h:
            raise OSError('Handler registration failed: %s' %
                          ctypes.FormatError())

        TODO
    except Exception as e:
        tb = traceback.format_exc()
        msg = str(e) + '\n' + tb
        win_service_report_event(service_name, msg, is_error=True)
        raise


def win_service_start(service_name, real_main):
    try:
        cb = START_CALLBACK(
            functools.partial(win_service_main, service_name, real_main))
        dispatch_table = _ctypes_array(SERVICE_TABLE_ENTRY, [
            SERVICE_TABLE_ENTRY(
                service_name,
                cb
            ),
            SERVICE_TABLE_ENTRY(None, ctypes.cast(None, START_CALLBACK))
        ])

        if not advapi32.StartServiceCtrlDispatcherW(dispatch_table):
            raise OSError('ctypes start failed: %s' % ctypes.FormatError())
    except Exception as e:
        tb = traceback.format_exc()
        msg = str(e) + '\n' + tb
        win_service_report_event(service_name, msg, is_error=True)
        raise


def main(args=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--install',
                        action='store_const', dest='action', const='install',
                        help='Launch at Windows startup')
    parser.add_argument('-u', '--uninstall',
                        action='store_const', dest='action', const='uninstall',
                        help='Remove Windows service')
    parser.add_argument('-s', '--service',
                        action='store_const', dest='action', const='service',
                        help='Run as a Windows service')
    parser.add_argument('-b', '--bind', metavar='<host:port>',
                        action='store', default='0.0.0.0:8142',
                        help='Bind to host:port (default %default)')
    options = parser.parse_args(args=args)

    if options.action == 'install':
        fn = os.path.abspath(__file__).replace('v:', '\\\\vboxsrv\\vbox')
        cmdline = '%s %s -s -b %s' % (sys.executable, fn, options.bind)
        win_install_service(SVCNAME, cmdline)
        return

    if options.action == 'uninstall':
        win_uninstall_service(SVCNAME)
        return

    if options.action == 'service':
        win_service_start(SVCNAME, main)
        return

    host, port_str = options.bind.split(':')
    port = int(port_str)

    print('Listening on %s:%d' % (host, port))
    srv = BuildHTTPServer((host, port), BuildHTTPRequestHandler)
    thr = threading.Thread(target=srv.serve_forever)
    thr.start()
    compat_input('Press ENTER to shut down')
    srv.shutdown()
    thr.join()


def rmtree(path):
    for name in os.listdir(path):
        fname = os.path.join(path, name)
        if os.path.isdir(fname):
            rmtree(fname)
        else:
            os.chmod(fname, 0o666)
            os.remove(fname)
    os.rmdir(path)


class BuildError(Exception):
    def __init__(self, output, code=500):
        self.output = output
        self.code = code

    def __str__(self):
        return self.output


class HTTPError(BuildError):
    pass


class PythonBuilder(object):
    def __init__(self, **kwargs):
        python_version = kwargs.pop('python', '3.4')
        python_path = None
        for node in ('Wow6432Node\\', ''):
            try:
                key = compat_winreg.OpenKey(
                    compat_winreg.HKEY_LOCAL_MACHINE,
                    r'SOFTWARE\%sPython\PythonCore\%s\InstallPath' % (node, python_version))
                try:
                    python_path, _ = compat_winreg.QueryValueEx(key, '')
                finally:
                    compat_winreg.CloseKey(key)
                break
            except Exception:
                pass

        if not python_path:
            raise BuildError('No such Python version: %s' % python_version)

        self.pythonPath = python_path

        super(PythonBuilder, self).__init__(**kwargs)


class GITInfoBuilder(object):
    def __init__(self, **kwargs):
        try:
            self.user, self.repoName = kwargs['path'][:2]
            self.rev = kwargs.pop('rev')
        except ValueError:
            raise BuildError('Invalid path')
        except KeyError as e:
            raise BuildError('Missing mandatory parameter "%s"' % e.args[0])

        path = os.path.join(os.environ['APPDATA'], 'Build archive', self.repoName, self.user)
        if not os.path.exists(path):
            os.makedirs(path)
        self.basePath = tempfile.mkdtemp(dir=path)
        self.buildPath = os.path.join(self.basePath, 'build')

        super(GITInfoBuilder, self).__init__(**kwargs)


class GITBuilder(GITInfoBuilder):
    def build(self):
        try:
            subprocess.check_output(['git', 'clone', 'git://github.com/%s/%s.git' % (self.user, self.repoName), self.buildPath])
            subprocess.check_output(['git', 'checkout', self.rev], cwd=self.buildPath)
        except subprocess.CalledProcessError as e:
            raise BuildError(e.output)

        super(GITBuilder, self).build()


class YoutubeDLBuilder(object):
    authorizedUsers = ['fraca7', 'phihag', 'rg3', 'FiloSottile', 'ytdl-org']

    def __init__(self, **kwargs):
        if self.repoName != 'yt-dlp':
            raise BuildError('Invalid repository "%s"' % self.repoName)
        if self.user not in self.authorizedUsers:
            raise HTTPError('Unauthorized user "%s"' % self.user, 401)

        super(YoutubeDLBuilder, self).__init__(**kwargs)

    def build(self):
        try:
            proc = subprocess.Popen([os.path.join(self.pythonPath, 'python.exe'), 'setup.py', 'py2exe'], stdin=subprocess.PIPE, cwd=self.buildPath)
            proc.wait()
            #subprocess.check_output([os.path.join(self.pythonPath, 'python.exe'), 'setup.py', 'py2exe'],
            #                        cwd=self.buildPath)
        except subprocess.CalledProcessError as e:
            raise BuildError(e.output)

        super(YoutubeDLBuilder, self).build()


class DownloadBuilder(object):
    def __init__(self, **kwargs):
        self.handler = kwargs.pop('handler')
        self.srcPath = os.path.join(self.buildPath, *tuple(kwargs['path'][2:]))
        self.srcPath = os.path.abspath(os.path.normpath(self.srcPath))
        if not self.srcPath.startswith(self.buildPath):
            raise HTTPError(self.srcPath, 401)

        super(DownloadBuilder, self).__init__(**kwargs)

    def build(self):
        if not os.path.exists(self.srcPath):
            raise HTTPError('No such file', 404)
        if os.path.isdir(self.srcPath):
            raise HTTPError('Is a directory: %s' % self.srcPath, 401)

        self.handler.send_response(200)
        self.handler.send_header('Content-Type', 'application/octet-stream')
        self.handler.send_header('Content-Disposition', 'attachment; filename=%s' % os.path.split(self.srcPath)[-1])
        self.handler.send_header('Content-Length', str(os.stat(self.srcPath).st_size))
        self.handler.end_headers()

        with open(self.srcPath, 'rb') as src:
            shutil.copyfileobj(src, self.handler.wfile)

        super(DownloadBuilder, self).build()


class CleanupTempDir(object):
    def build(self):
        try:
            rmtree(self.basePath)
        except Exception as e:
            print('WARNING deleting "%s": %s' % (self.basePath, e))

        super(CleanupTempDir, self).build()


class Null(object):
    def __init__(self, **kwargs):
        pass

    def start(self):
        pass

    def close(self):
        pass

    def build(self):
        pass


class Builder(PythonBuilder, GITBuilder, YoutubeDLBuilder, DownloadBuilder, CleanupTempDir, Null):
    pass


class BuildHTTPRequestHandler(compat_http_server.BaseHTTPRequestHandler):
    actionDict = {'build': Builder, 'download': Builder}  # They're the same, no more caching.

    def do_GET(self):
        path = compat_urlparse.urlparse(self.path)
        paramDict = dict([(key, value[0]) for key, value in compat_urlparse.parse_qs(path.query).items()])
        action, _, path = path.path.strip('/').partition('/')
        if path:
            path = path.split('/')
            if action in self.actionDict:
                try:
                    builder = self.actionDict[action](path=path, handler=self, **paramDict)
                    builder.start()
                    try:
                        builder.build()
                    finally:
                        builder.close()
                except BuildError as e:
                    self.send_response(e.code)
                    msg = compat_str(e).encode('UTF-8')
                    self.send_header('Content-Type', 'text/plain; charset=UTF-8')
                    self.send_header('Content-Length', len(msg))
                    self.end_headers()
                    self.wfile.write(msg)
            else:
                self.send_response(500, 'Unknown build method "%s"' % action)
        else:
            self.send_response(500, 'Malformed URL')

if __name__ == '__main__':
    main()
