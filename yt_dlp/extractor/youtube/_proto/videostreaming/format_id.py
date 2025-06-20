from __future__ import annotations

from yt_dlp.dependencies import protobug


@protobug.message
class FormatId:
    itag: protobug.Int32 | None = protobug.field(1)
    lmt: protobug.UInt64 | None = protobug.field(2, default=None)
    xtags: protobug.String | None = protobug.field(3, default=None)
