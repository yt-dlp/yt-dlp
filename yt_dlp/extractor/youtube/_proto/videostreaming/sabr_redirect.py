from __future__ import annotations

from yt_dlp.dependencies import protobug


@protobug.message
class SabrRedirect:
    redirect_url: protobug.String | None = protobug.field(1, default=None)
