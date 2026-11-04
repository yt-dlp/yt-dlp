from __future__ import annotations

from yt_dlp.dependencies import protobug


@protobug.message
class VideoFormatCapability:

    class VideoCodec(protobug.Enum, strict=False):
        UNKNOWN_CODEC = 0
        H263 = 1
        H264 = 2
        VP8 = 3
        VP9 = 4
        H262 = 5
        VP6 = 6
        MPEG4 = 7
        AV1 = 8
        H265 = 9
        FLV1 = 10

    video_codec: VideoCodec | None = protobug.field(1, default=None)
    efficient: protobug.Bool | None = protobug.field(2, default=None)
    is_10_bit_supported: protobug.Bool | None = protobug.field(15, default=None)


@protobug.message
class AudioFormatCapability:

    class AudioCodec(protobug.Enum, strict=False):
        UNKNOWN_CODEC = 0
        AAC = 1
        VORBIS = 2
        OPUS = 3
        DTSHD = 4
        EAC3 = 5
        PCM = 6
        AC3 = 7
        SPEEX = 8
        MP3 = 9
        MP2 = 10
        AMR = 11
        IAMF = 12
        XHEAAC = 13

    audio_codec: AudioCodec | None = protobug.field(1, default=None)


@protobug.message
class MediaCapabilities:
    video_format_capabilities: list[VideoFormatCapability] = protobug.field(1, default_factory=list)
    audio_format_capabilities: list[AudioFormatCapability] = protobug.field(2, default_factory=list)
    hdr_mode_bitmask: protobug.Int32 | None = protobug.field(5, default=None)
