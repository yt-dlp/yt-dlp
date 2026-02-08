# flake8: noqa: F401
from ._base import YoutubeBaseInfoExtractor
from ._clip import YoutubeClipIE
from ._mistakes import YoutubeTruncatedIDIE, YoutubeTruncatedURLIE
from ._notifications import YoutubeNotificationsIE
from ._redirect import (
    YoutubeConsentRedirectIE,
    YoutubeFavouritesIE,
    YoutubeFeedsInfoExtractor,
    YoutubeHistoryIE,
    YoutubeLivestreamEmbedIE,
    YoutubeRecommendedIE,
    YoutubeShortsAudioPivotIE,
    YoutubeSubscriptionsIE,
    YoutubeWatchLaterIE,
    YoutubeYtBeIE,
    YoutubeYtUserIE,
)
from ._search import YoutubeMusicSearchURLIE, YoutubeSearchDateIE, YoutubeSearchIE, YoutubeSearchURLIE
from ._tab import YoutubePlaylistIE, YoutubeTabBaseInfoExtractor, YoutubeTabIE
from ._video import YoutubeIE

# Hack to allow plugin overrides work
for _cls in [
    YoutubeBaseInfoExtractor,
    YoutubeClipIE,
    YoutubeTruncatedIDIE,
    YoutubeTruncatedURLIE,
    YoutubeNotificationsIE,
    YoutubeConsentRedirectIE,
    YoutubeFavouritesIE,
    YoutubeFeedsInfoExtractor,
    YoutubeHistoryIE,
    YoutubeLivestreamEmbedIE,
    YoutubeRecommendedIE,
    YoutubeShortsAudioPivotIE,
    YoutubeSubscriptionsIE,
    YoutubeWatchLaterIE,
    YoutubeYtBeIE,
    YoutubeYtUserIE,
    YoutubeMusicSearchURLIE,
    YoutubeSearchDateIE,
    YoutubeSearchIE,
    YoutubeSearchURLIE,
    YoutubePlaylistIE,
    YoutubeTabBaseInfoExtractor,
    YoutubeTabIE,
    YoutubeIE,
]:
    _cls.__module__ = 'yt_dlp.extractor.youtube'
