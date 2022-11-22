from yt_dlp.extractor.common import InfoExtractor


class IgnoreNotInAllPluginIE(InfoExtractor):
    _WORKING = False
    IE_DESC = False
    _VALID_URL = r'^ignorenotinallplugin:'

    def _real_extract(self, url):
        self.to_screen('URL "%s" successfully captured' % url)


class InAllPluginIE(InfoExtractor):
    _WORKING = False
    IE_DESC = False
    _VALID_URL = r'^inallplugin:'

    def _real_extract(self, url):
        self.to_screen('URL "%s" successfully captured' % url)


__all__ = ['InAllPluginIE']
