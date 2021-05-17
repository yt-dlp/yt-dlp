from __future__ import unicode_literals
import sys

try:
    import yt_dlp
    #print("Imported yt_dlp", file=sys.stderr)
except ImportError as e:
    print(e, file=sys.stderr)

# ⚠ Don't use relative imports
from yt_dlp.extractor.common import InfoExtractor


# See https://github.com/ytdl-org/youtube-dl#adding-support-for-a-new-site
# for instuctions on making extractors

class SamplePluginIE(InfoExtractor):
    _WORKING = False
    IE_DESC = False
    _VALID_URL = r'^sampleplugin:'

    def _real_extract(self, url):
        self.to_screen('URL "%s" sucessfully captured' % url)
