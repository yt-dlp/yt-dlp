from __future__ import annotations

from yt_dlp.dependencies import protobug


@protobug.message
class StreamProtectionStatus:

    class Status(protobug.Enum, strict=False):
        OK = 1
        ATTESTATION_PENDING = 2
        ATTESTATION_REQUIRED = 3

    status: Status | None = protobug.field(1, default=None)
    max_retries: protobug.Int32 | None = protobug.field(2, default=None)
