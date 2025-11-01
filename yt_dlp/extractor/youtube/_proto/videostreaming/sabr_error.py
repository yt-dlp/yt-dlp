from __future__ import annotations

from yt_dlp.dependencies import protobug


@protobug.message
class Error:
    status_code: protobug.Int32 | None = protobug.field(1, default=None)
    type: protobug.Int32 | None = protobug.field(4, default=None)


@protobug.message
class SabrError:
    type: protobug.String | None = protobug.field(1, default=None)
    action: protobug.Int32 | None = protobug.field(2, default=None)
    error: Error | None = protobug.field(3, default=None)
