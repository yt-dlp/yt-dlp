from __future__ import annotations

from yt_dlp.dependencies import protobug

from ..innertube import ClientInfo


@protobug.message
class SabrContext:
    # Type and Value from a SabrContextUpdate
    type: protobug.Int32 | None = protobug.field(1, default=None)
    value: protobug.Bytes | None = protobug.field(2, default=None)


@protobug.message
class StreamerContext:
    client_info: ClientInfo | None = protobug.field(1, default=None)
    po_token: protobug.Bytes | None = protobug.field(2, default=None)
    playback_cookie: protobug.Bytes | None = protobug.field(3, default=None)
    sabr_contexts: list[SabrContext] = protobug.field(5, default_factory=list)
    unsent_sabr_contexts: list[protobug.Int32] = protobug.field(6, default_factory=list)
