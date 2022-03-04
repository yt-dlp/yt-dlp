# flake8: noqa: F401

from ..utils import load_plugins

from .common import PostProcessor
from .embedthumbnail import EmbedThumbnailPP
from .exec import ExecPP, ExecAfterDownloadPP
from .ffmpeg import (
    FFmpegPostProcessor,
    FFmpegCopyStreamPP,
    FFmpegConcatPP,
    FFmpegEmbedSubtitlePP,
    FFmpegExtractAudioPP,
    FFmpegFixupDuplicateMoovPP,
    FFmpegFixupDurationPP,
    FFmpegFixupStretchedPP,
    FFmpegFixupTimestampPP,
    FFmpegFixupM3u8PP,
    FFmpegFixupM4aPP,
    FFmpegMergerPP,
    FFmpegMetadataPP,
    FFmpegSubtitlesConvertorPP,
    FFmpegThumbnailsConvertorPP,
    FFmpegSplitChaptersPP,
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

_PLUGIN_CLASSES = load_plugins('postprocessor', 'PP', globals())


def get_postprocessor(key):
    return globals()[key + 'PP']


__all__ = [name for name in globals().keys() if name.endswith('PP')]
__all__.extend(('PostProcessor', 'FFmpegPostProcessor'))
