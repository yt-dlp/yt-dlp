from __future__ import annotations

from yt_dlp.downloader import FileDownloader


class SabrFDBase(FileDownloader):
    @classmethod
    def can_download(cls, info_dict):
        requested_formats = info_dict.get('requested_formats') or [info_dict]
        return all(format_info.get('protocol') == 'sabr' for format_info in requested_formats)
