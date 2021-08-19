# coding: utf-8

from __future__ import unicode_literals

# ⚠ Don't use relative imports
from yt_dlp.extractor.common import InfoExtractor


# ℹ️ Instructions on making extractors can be found at:
# 🔗 https://github.com/ytdl-org/youtube-dl#adding-support-for-a-new-site

class SamplePluginIE(InfoExtractor):
    _WORKING = False
    IE_DESC = False
    _VALID_URL = r'^sampleplugin:'

    def _real_extract(self, url):
        self.to_screen('URL "%s" sucessfully captured' % url)
