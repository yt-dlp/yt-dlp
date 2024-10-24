from .common import InfoExtractor


class ShareVideosEmbedIE(InfoExtractor):
    _VALID_URL = False
    _EMBED_REGEX = [r'<iframe[^>]+?\bsrc\s*=\s*(["\'])(?P<url>(?:https?:)?//embed\.share-videos\.se/auto/embed/\d+\?.*?\buid=\d+.*?)\1']
