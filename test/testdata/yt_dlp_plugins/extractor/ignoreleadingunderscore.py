from yt_dlp.extractor.common import InfoExtractor


class _IgnoreUnderscorePluginIE(InfoExtractor):
    _WORKING = False
    IE_DESC = False
    _VALID_URL = r'^ignoreunderscoreplugin:'

    def _real_extract(self, url):
        self.to_screen('URL "%s" successfully captured' % url)
