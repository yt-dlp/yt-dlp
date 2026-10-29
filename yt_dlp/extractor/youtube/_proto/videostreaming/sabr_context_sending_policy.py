from yt_dlp.dependencies import protobug


@protobug.message
class SabrContextSendingPolicy:
    # Start sending the SabrContextUpdates of this type
    start_policy: list[protobug.Int32] = protobug.field(1, default_factory=list)

    # Stop sending the SabrContextUpdates of this type
    stop_policy: list[protobug.Int32] = protobug.field(2, default_factory=list)

    # Stop and discard the SabrContextUpdates of this type
    discard_policy: list[protobug.Int32] = protobug.field(3, default_factory=list)
