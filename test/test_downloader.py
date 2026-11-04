import pytest
from yt_dlp.utils import DownloadError
from yt_dlp import YoutubeDL
from yt_dlp.downloader import get_suitable_downloader
from yt_dlp.dependencies import protobug


class TestGetSuitableDownloader:
    @pytest.mark.skipif(protobug is None, reason='protobug not installed')
    def test_sabrfd_single_format_with_protobug(self):
        info_dict = {'protocol': 'sabr'}
        cls = get_suitable_downloader(info_dict)
        assert cls.__name__ == 'SabrFD'
        # ensure this is the real SabrFD
        assert cls.__module__ == 'yt_dlp.downloader.sabr._fd'

    @pytest.mark.skipif(protobug is None, reason='protobug not installed')
    def test_sabrfd_multi_format_with_protobug(self):
        info_dict = {'url': 'https://example.com/sabr', 'protocol': 'sabr+sabr', 'requested_formats': [{'protocol': 'sabr'}, {'protocol': 'sabr'}]}
        cls = get_suitable_downloader(info_dict)
        assert cls.__name__ == 'SabrFD'
        # ensure this is the real SabrFD
        assert cls.__module__ == 'yt_dlp.downloader.sabr._fd'

    @pytest.mark.skipif(protobug is not None, reason='protobug is installed')
    def test_sabrfd_without_protobug(self):
        info_dict = {'protocol': 'sabr'}
        cls = get_suitable_downloader(info_dict)
        assert cls.__name__ == 'SabrFD'
        # ensure this is the fake SabrFD
        assert cls.__module__ == 'yt_dlp.downloader.sabr'
        # should only fail when try to start a download
        fd = cls(YoutubeDL({}), {})
        with pytest.raises(DownloadError, match='A supported version of protobug is required to be installed to download SABR formats'):
            fd.download(filename='/invalid', info_dict=info_dict)
