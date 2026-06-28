from __future__ import annotations

from yt_dlp.dependencies import protobug


@protobug.message
class Tag:
    name: protobug.String = protobug.field(1)
    value: protobug.String = protobug.field(2)


@protobug.message
class XTags:
    tags: list[Tag] = protobug.field(1, default=list)
