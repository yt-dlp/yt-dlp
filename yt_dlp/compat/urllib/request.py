# flake8: noqa: F405
from urllib.request import *  # noqa: F403
from urllib.request import getproxies_environment
from .. import compat_os_name
from ..compat_utils import passthrough_module
import re

passthrough_module(__name__, 'urllib.request')
del passthrough_module


if compat_os_name == 'nt':
    """
    Code from https://github.com/python/cpython/blob/main/Lib/urllib/request.py
    https://github.com/python/cpython/pull/26307
    """
    def getproxies_registry():
        """Return a dictionary of scheme -> proxy server URL mappings.
        Win32 uses the registry to store proxies.
        """
        proxies = {}
        try:
            import winreg
        except ImportError:
            # Std module, so should be around - but you never know!
            return proxies
        try:
            internetSettings = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                              r'Software\Microsoft\Windows\CurrentVersion\Internet Settings')
            proxyEnable = winreg.QueryValueEx(internetSettings,
                                              'ProxyEnable')[0]
            if proxyEnable:
                # Returned as Unicode but problems if not converted to ASCII
                proxyServer = str(winreg.QueryValueEx(internetSettings,
                                                      'ProxyServer')[0])
                if '=' not in proxyServer and ';' not in proxyServer:
                    # Use one setting for all protocols.
                    proxyServer = 'http={0};https={0};ftp={0}'.format(proxyServer)
                for p in proxyServer.split(';'):
                    protocol, address = p.split('=', 1)
                    # See if address has a type:// prefix
                    if not re.match('(?:[^/:]+)://', address):
                        # Add type:// prefix to address without specifying type
                        if protocol in ('http', 'https', 'ftp'):
                            # The default proxy type of Windows is HTTP
                            address = 'http://' + address
                        elif protocol == 'socks':
                            address = 'socks://' + address
                    proxies[protocol] = address
                # Use SOCKS proxy for HTTP(S) protocols
                if proxies.get('socks'):
                    # The default SOCKS proxy type of Windows is SOCKS4
                    address = re.sub(r'^socks://', 'socks4://', proxies['socks'])
                    proxies['http'] = proxies.get('http') or address
                    proxies['https'] = proxies.get('https') or address
            internetSettings.Close()
        except (OSError, ValueError, TypeError):
            # Either registry key not found etc, or the value in an
            # unexpected format.
            # proxies already set up to be empty so nothing to do
            pass
        return proxies

    def getproxies():
        return getproxies_environment() or getproxies_registry()
