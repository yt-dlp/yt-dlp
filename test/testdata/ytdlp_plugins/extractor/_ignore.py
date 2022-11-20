from yt_dlp.extractor.common import InfoExtractor


class IgnorePluginIE(InfoExtractor):
    _WORKING = False
    IE_DESC = False
    _VALID_URL = r'^ignoreplugin:'

    def _real_extract(self, url):
        self.to_screen('URL "%s" successfully captured' % url)
