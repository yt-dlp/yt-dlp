from __future__ import annotations

from yt_dlp.dependencies import protobug


@protobug.message
class ReloadPlaybackParams:
    token: protobug.String | None = protobug.field(1, default=None)


@protobug.message
class ReloadPlayerResponse:
    reload_playback_params: ReloadPlaybackParams | None = protobug.field(1, default=None)
