from .common import InfoExtractor
from ..utils.lazy import lazy_ie, lazy_fields


@lazy_ie
class LazyExtractorIE(InfoExtractor):
    IE_NAME = 'lazy'
    _VALID_URL = r"lazy://(?P<id>.*)"

    def _lazy_webpage(self, storage):
        return self._download_webpage(storage.url, storage.id)

    @lazy_fields("creator")
    def _extract_other(self, storage):
        self.to_screen("Extracting something else from webpage")
        return {
            "creator": storage.webpage.partition(" - ")[0],
        }

    @lazy_fields("title", "description")
    def _extract_website(self, storage):
        self.to_screen("Extracting title and description from webpage")
        title, _, description = storage.webpage.partition("\n")

        return {
            "title": title,
            "description": description,
        }

    # Fake downloading the webpage for testing purposes
    def _download_webpage(self, url_or_request, video_id, *args, **kwargs):
        self.to_screen(f"[{video_id}] Downloaded webpage ({url_or_request})")
        return "<creator> - Fake Webpage title\nThis is the description.\n..."
