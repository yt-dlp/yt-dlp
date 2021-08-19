#!/usr/bin/env python3

#from ..utils import load_plugins

#try:
#    from .lazy_extractors import *
#    from .lazy_extractors import _ALL_CLASSES
#    _LAZY_LOADER = True
#    _PLUGIN_CLASSES = []
#except ImportError:
#    _LAZY_LOADER = False
#
#if not _LAZY_LOADER:
if True:
    from .youtube import (
        YoutubeIE,
        YoutubeFavouritesIE,
        YoutubeHistoryIE,
        YoutubeTabIE,
        YoutubePlaylistIE,
        YoutubeRecommendedIE,
        YoutubeSearchDateIE,
        YoutubeSearchIE,
        YoutubeSearchURLIE,
        YoutubeSubscriptionsIE,
        YoutubeTruncatedIDIE,
        YoutubeTruncatedURLIE,
        YoutubeYtBeIE,
        YoutubeYtUserIE,
        YoutubeWatchLaterIE,
    )
    from .dailymotion import (
        DailymotionIE,
        DailymotionPlaylistIE,
        DailymotionUserIE,
    )
    from .line import (
        LineTVIE,
        LineLiveIE,
        LineLiveChannelIE,
    )
    from .ustream import (
        UstreamIE,
        UstreamChannelIE,
    )
    from .niconico import (
        NiconicoIE,
        NiconicoPlaylistIE,
        NiconicoUserIE,
    )
    from .youku import (
        YoukuIE,
        YoukuShowIE,
    )
    from .fc2 import (
        FC2IE,
        FC2EmbedIE,
    )
    from .twitter import (
        TwitterCardIE,
        TwitterIE,
        TwitterAmplifyIE,
        TwitterBroadcastIE,
        TwitterShortenerIE,
    )
    from .pornhub import (
        PornHubIE,
        PornHubUserIE,
        PornHubPlaylistIE,
        PornHubPagedVideoListIE,
        PornHubUserVideosUploadIE,
    )
    from .vimeo import (
        VimeoIE,
        VimeoAlbumIE,
        VimeoChannelIE,
        VimeoGroupsIE,
        VimeoLikesIE,
        VimeoOndemandIE,
        VimeoReviewIE,
        VimeoUserIE,
        VimeoWatchLaterIE,
        VHXEmbedIE,
    )
    from .viki import (
        VikiIE,
        VikiChannelIE,
    )
    from .youporn import YouPornIE
    from .xvideos import XVideosIE
    from .generic import GenericIE

    _ALL_CLASSES = [
        klass
        for name, klass in globals().items()
        if name.endswith('IE') and name != 'GenericIE'
    ]
    _ALL_CLASSES.append(GenericIE)

    #import pprint
    #for x in _ALL_CLASSES:
    #    print(x.__name__)

    #_PLUGIN_CLASSES = load_plugins('extractor', 'IE', globals())
    #_ALL_CLASSES = _PLUGIN_CLASSES + _ALL_CLASSES


def gen_extractor_classes():
    """ Return a list of supported extractors.
    The order does matter; the first extractor matched is the one handling the URL.
    """
    return _ALL_CLASSES


def gen_extractors():
    """ Return a list of an instance of every supported extractor.
    The order does matter; the first extractor matched is the one handling the URL.
    """
    return [klass() for klass in gen_extractor_classes()]


def list_extractors(age_limit):
    """
    Return a list of extractors that are suitable for the given age,
    sorted by extractor ID.
    """
    return sorted(
        filter(lambda ie: ie.is_suitable(age_limit), gen_extractors()),
        key=lambda ie: ie.IE_NAME.lower())


def get_info_extractor(ie_name):
    """Returns the info extractor class with the given ie_name"""
    return globals()[ie_name + 'IE']
