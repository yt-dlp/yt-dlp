# flake8: noqa: F405
from urllib.request import *  # noqa: F403

from ..compat_utils import passthrough_module

passthrough_module(__name__, 'urllib.request')
del passthrough_module


from .. import compat_os_name

if compat_os_name == 'nt':
    # On older python versions, proxies are extracted from Windows registry erroneously. [1]
    # If the https proxy in the registry does not have a scheme, urllib will incorrectly add https:// to it. [2]
    # It is unlikely that the user has actually set it to be https, so we should be fine to safely downgrade
    # it to http on these older python versions to avoid issues
    # This also applies for ftp proxy type, as ftp:// proxy scheme is not supported.
    # 1: https://github.com/python/cpython/issues/86793
    # 2: https://github.com/python/cpython/blob/51f1ae5ceb0673316c4e4b0175384e892e33cc6e/Lib/urllib/request.py#L2683-L2698
    import sys
    from urllib.request import getproxies_environment, getproxies_registry

    def getproxies_registry_patched():
        proxies = getproxies_registry()
        if (
            sys.version_info >= (3, 10, 5)  # https://docs.python.org/3.10/whatsnew/changelog.html#python-3-10-5-final
            or (3, 9, 13) <= sys.version_info < (3, 10)  # https://docs.python.org/3.9/whatsnew/changelog.html#python-3-9-13-final
        ):
            return proxies

        for scheme in ('https', 'ftp'):
            if scheme in proxies and proxies[scheme].startswith(f'{scheme}://'):
                proxies[scheme] = 'http' + proxies[scheme][len(scheme):]

        return proxies

    def getproxies():
        return getproxies_environment() or getproxies_registry_patched()

del compat_os_name
