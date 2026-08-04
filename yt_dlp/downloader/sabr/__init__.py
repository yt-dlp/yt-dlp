from __future__ import annotations

from yt_dlp.dependencies import protobug
from yt_dlp.utils import DownloadError
from yt_dlp.downloader import FileDownloader

if not protobug:
    class SabrFD(FileDownloader):

        @classmethod
        def can_download(cls, info_dict):
            is_sabr = (
                info_dict.get('requested_formats')
                and all(
                    format_info.get('protocol') == 'sabr'
                    for format_info in info_dict['requested_formats']))

            if is_sabr:
                raise DownloadError('SABRFD requires protobug to be installed')

            return is_sabr

else:
    from ._fd import SabrFD  # noqa: F401
