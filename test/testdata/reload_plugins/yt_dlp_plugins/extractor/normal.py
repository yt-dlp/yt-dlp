from yt_dlp.extractor.common import InfoExtractor


class NormalPluginIE(InfoExtractor):
    REPLACED = True


class _IgnoreUnderscorePluginIE(InfoExtractor):
    pass
