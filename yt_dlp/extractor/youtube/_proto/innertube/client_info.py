from __future__ import annotations

from yt_dlp.dependencies import protobug


class ClientName(protobug.Enum, strict=False):
    UNKNOWN_INTERFACE = 0
    WEB = 1
    MWEB = 2
    ANDROID = 3
    IOS = 5
    TVHTML5 = 7
    TVLITE = 8
    TVANDROID = 10
    XBOX = 11
    CLIENTX = 12
    XBOXONEGUIDE = 13
    ANDROID_CREATOR = 14
    IOS_CREATOR = 15
    TVAPPLE = 16
    IOS_INSTANT = 17
    ANDROID_KIDS = 18
    IOS_KIDS = 19
    ANDROID_INSTANT = 20
    ANDROID_MUSIC = 21
    IOS_TABLOID = 22
    ANDROID_TV = 23
    ANDROID_GAMING = 24
    IOS_GAMING = 25
    IOS_MUSIC = 26
    MWEB_TIER_2 = 27
    ANDROID_VR = 28
    ANDROID_UNPLUGGED = 29
    ANDROID_TESTSUITE = 30
    WEB_MUSIC_ANALYTICS = 31
    WEB_GAMING = 32
    IOS_UNPLUGGED = 33
    ANDROID_WITNESS = 34
    IOS_WITNESS = 35
    ANDROID_SPORTS = 36
    IOS_SPORTS = 37
    ANDROID_LITE = 38
    IOS_EMBEDDED_PLAYER = 39
    IOS_DIRECTOR = 40
    WEB_UNPLUGGED = 41
    WEB_EXPERIMENTS = 42
    TVHTML5_CAST = 43
    WEB_EMBEDDED_PLAYER = 56
    TVHTML5_AUDIO = 57
    TV_UNPLUGGED_CAST = 58
    TVHTML5_KIDS = 59
    WEB_HEROES = 60
    WEB_MUSIC = 61
    WEB_CREATOR = 62
    TV_UNPLUGGED_ANDROID = 63
    IOS_LIVE_CREATION_EXTENSION = 64
    TVHTML5_UNPLUGGED = 65
    IOS_MESSAGES_EXTENSION = 66
    WEB_REMIX = 67
    IOS_UPTIME = 68
    WEB_UNPLUGGED_ONBOARDING = 69
    WEB_UNPLUGGED_OPS = 70
    WEB_UNPLUGGED_PUBLIC = 71
    TVHTML5_VR = 72
    WEB_LIVE_STREAMING = 73
    ANDROID_TV_KIDS = 74
    TVHTML5_SIMPLY = 75
    WEB_KIDS = 76
    MUSIC_INTEGRATIONS = 77
    TVHTML5_YONGLE = 80
    GOOGLE_ASSISTANT = 84
    TVHTML5_SIMPLY_EMBEDDED_PLAYER = 85
    WEB_MUSIC_EMBEDDED_PLAYER = 86
    WEB_INTERNAL_ANALYTICS = 87
    WEB_PARENT_TOOLS = 88
    GOOGLE_MEDIA_ACTIONS = 89
    WEB_PHONE_VERIFICATION = 90
    ANDROID_PRODUCER = 91
    IOS_PRODUCER = 92
    TVHTML5_FOR_KIDS = 93
    GOOGLE_LIST_RECS = 94
    MEDIA_CONNECT_FRONTEND = 95
    WEB_EFFECT_MAKER = 98
    WEB_SHOPPING_EXTENSION = 99
    WEB_PLAYABLES_PORTAL = 100
    VISIONOS = 101
    WEB_LIVE_APPS = 102
    WEB_MUSIC_INTEGRATIONS = 103
    ANDROID_MUSIC_AOSP = 104


@protobug.message
class ClientInfo:
    hl: protobug.String | None = protobug.field(1, default=None)
    gl: protobug.String | None = protobug.field(2, default=None)
    remote_host: protobug.String | None = protobug.field(4, default=None)

    device_make: protobug.String | None = protobug.field(12, default=None)
    device_model: protobug.String | None = protobug.field(13, default=None)
    visitor_data: protobug.String | None = protobug.field(14, default=None)
    user_agent: protobug.String | None = protobug.field(15, default=None)
    client_name: ClientName | None = protobug.field(16, default=None)
    client_version: protobug.String | None = protobug.field(17, default=None)
    os_name: protobug.String | None = protobug.field(18, default=None)
    os_version: protobug.String | None = protobug.field(19, default=None)
