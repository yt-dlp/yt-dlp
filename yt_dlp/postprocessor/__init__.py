from __future__ import unicode_literals

from .embedthumbnail import EmbedThumbnailPP
from .ffmpeg import (
    FFmpegPostProcessor,
    FFmpegEmbedSubtitlePP,
    FFmpegExtractAudioPP,
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
from .xattrpp import XAttrMetadataPP
from .exec import ExecPP, ExecAfterDownloadPP
from .metadataparser import (
    MetadataFromFieldPP,
    MetadataFromTitlePP,
    MetadataParserPP,
)
from .movefilesafterdownload import MoveFilesAfterDownloadPP
from .sponsorblock import SponsorBlockPP
from .sponskrub import SponSkrubPP
from .modify_chapters import ModifyChaptersPP


def get_postprocessor(key):
    return globals()[key + 'PP']


__all__ = [
    'FFmpegPostProcessor',
    'EmbedThumbnailPP',
    'ExecPP',
    'ExecAfterDownloadPP',
    'FFmpegEmbedSubtitlePP',
    'FFmpegExtractAudioPP',
    'FFmpegSplitChaptersPP',
    'FFmpegFixupDurationPP',
    'FFmpegFixupM3u8PP',
    'FFmpegFixupM4aPP',
    'FFmpegFixupStretchedPP',
    'FFmpegFixupTimestampPP',
    'FFmpegMergerPP',
    'FFmpegMetadataPP',
    'FFmpegSubtitlesConvertorPP',
    'FFmpegThumbnailsConvertorPP',
    'FFmpegVideoConvertorPP',
    'FFmpegVideoRemuxerPP',
    'MetadataParserPP',
    'MetadataFromFieldPP',
    'MetadataFromTitlePP',
    'MoveFilesAfterDownloadPP',
    'SponsorBlockPP',
    'SponSkrubPP',
    'ModifyChaptersPP',
    'XAttrMetadataPP',
]
