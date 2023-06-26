# flake8: noqa: F401
from ..globals import ALL_PPS, PLUGIN_PPS
from ..plugins import load_plugins

PLUGIN_PPS.set(load_plugins('postprocessor', 'PP'))
del load_plugins
globals().update(PLUGIN_PPS.get())

from .common import PostProcessor
from .embedthumbnail import EmbedThumbnailPP
from .exec import ExecAfterDownloadPP, ExecPP
from .ffmpeg import (
    FFmpegConcatPP,
    FFmpegCopyStreamPP,
    FFmpegEmbedSubtitlePP,
    FFmpegExtractAudioPP,
    FFmpegFixupDuplicateMoovPP,
    FFmpegFixupDurationPP,
    FFmpegFixupM3u8PP,
    FFmpegFixupM4aPP,
    FFmpegFixupStretchedPP,
    FFmpegFixupTimestampPP,
    FFmpegMergerPP,
    FFmpegMetadataPP,
    FFmpegPostProcessor,
    FFmpegSplitChaptersPP,
    FFmpegSubtitlesConvertorPP,
    FFmpegThumbnailsConvertorPP,
    FFmpegVideoConvertorPP,
    FFmpegVideoRemuxerPP,
)
from .metadataparser import (
    MetadataFromFieldPP,
    MetadataFromTitlePP,
    MetadataParserPP,
)
from .modify_chapters import ModifyChaptersPP
from .movefilesafterdownload import MoveFilesAfterDownloadPP
from .sponskrub import SponSkrubPP
from .sponsorblock import SponsorBlockPP
from .xattrpp import XAttrMetadataPP


ALL_PPS.set({name: klass for name, klass in globals().items() if name.endswith('PP')})
__all__ = ['PostProcessor', 'FFmpegPostProcessor', *ALL_PPS.get().keys()]
