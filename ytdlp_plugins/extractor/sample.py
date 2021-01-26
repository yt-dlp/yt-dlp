from __future__ import unicode_literals

from youtube_dlc.extractor.common import InfoExtractor


class SamplePluginIE(InfoExtractor):
    _WORKING = False
    IE_DESC = False
    _VALID_URL = r'^sampleplugin:'

    def _real_extract(self, url):
        self.to_screen('URL "%s" sucessfully captured' % url)
