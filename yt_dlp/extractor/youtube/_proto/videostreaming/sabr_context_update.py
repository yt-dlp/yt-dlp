from __future__ import annotations

from yt_dlp.dependencies import protobug


@protobug.message
class SabrContextUpdate:

    class SabrContextScope(protobug.Enum, strict=False):
        UNKNOWN = 0
        PLAYBACK = 1
        REQUEST = 2
        WATCH_ENDPOINT = 3
        CONTENT_ADS = 4

    class SabrContextWritePolicy(protobug.Enum, strict=False):
        UNSPECIFIED = 0
        OVERWRITE = 1
        KEEP_EXISTING = 2

    type: protobug.Int32 | None = protobug.field(1, default=None)
    scope: SabrContextScope | None = protobug.field(2, default=None)
    value: protobug.Bytes | None = protobug.field(3, default=None)
    send_by_default: protobug.Bool | None = protobug.field(4, default=None)
    write_policy: SabrContextWritePolicy | None = protobug.field(5, default=None)
