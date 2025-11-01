from yt_dlp.dependencies import protobug


class CompressionAlgorithm(protobug.Enum, strict=False):
    COMPRESSION_ALGORITHM_UNKNOWN = 0
    COMPRESSION_ALGORITHM_NONE = 1
    COMPRESSION_ALGORITHM_GZIP = 2
