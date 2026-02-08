from yt_dlp.extractor.common import InfoExtractor


class NormalPluginIE(InfoExtractor):
    _VALID_URL = 'normalpluginie'
    REPLACED = False


class _IgnoreUnderscorePluginIE(InfoExtractor):
    _VALID_URL = 'ignoreunderscorepluginie'
    pass
