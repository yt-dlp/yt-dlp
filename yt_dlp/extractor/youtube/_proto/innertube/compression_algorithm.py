from yt_dlp.dependencies import protobug


class CompressionAlgorithm(protobug.Enum, strict=False):
    UNKNOWN = 0
    NONE = 1
    GZIP = 2
