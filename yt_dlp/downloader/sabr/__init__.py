from __future__ import annotations

from yt_dlp.dependencies import protobug
from ._base import SabrFDBase
from yt_dlp.utils import DownloadError

if not protobug:
    class SabrFD(SabrFDBase):
        def real_download(self, filename, info_dict):
            raise DownloadError(
                'A supported version of protobug is required to be installed to download SABR formats')

else:
    from ._fd import SabrFD  # noqa: F401
