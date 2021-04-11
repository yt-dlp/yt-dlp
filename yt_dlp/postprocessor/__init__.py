from __future__ import unicode_literals

from .embedthumbnail import EmbedThumbnailPP
from .ffmpeg import (
    FFmpegPostProcessor,
    FFmpegEmbedSubtitlePP,
    FFmpegExtractAudioPP,
    FFmpegFixupStretchedPP,
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
from .execafterdownload import ExecAfterDownloadPP
from .metadatafromfield import MetadataFromFieldPP
from .metadatafromfield import MetadataFromTitlePP
from .movefilesafterdownload import MoveFilesAfterDownloadPP
from .sponskrub import SponSkrubPP


def get_postprocessor(key):
    return globals()[key + 'PP']


__all__ = [
    'FFmpegPostProcessor',
    'EmbedThumbnailPP',
    'ExecAfterDownloadPP',
    'FFmpegEmbedSubtitlePP',
    'FFmpegExtractAudioPP',
    'FFmpegSplitChaptersPP',
    'FFmpegFixupM3u8PP',
    'FFmpegFixupM4aPP',
    'FFmpegFixupStretchedPP',
    'FFmpegMergerPP',
    'FFmpegMetadataPP',
    'FFmpegSubtitlesConvertorPP',
    'FFmpegThumbnailsConvertorPP',
    'FFmpegVideoConvertorPP',
    'FFmpegVideoRemuxerPP',
    'MetadataFromFieldPP',
    'MetadataFromTitlePP',
    'MoveFilesAfterDownloadPP',
    'SponSkrubPP',
    'XAttrMetadataPP',
]
