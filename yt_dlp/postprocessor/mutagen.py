from __future__ import annotations
import collections
from functools import singledispatchmethod
import os
import re
from typing import TypedDict

from yt_dlp.compat import imghdr
from yt_dlp.utils._utils import PostProcessingError, variadic
from ..dependencies import mutagen

if mutagen:
    import mutagen
    from mutagen import (
        FileType,
        aiff,
        dsdiff,
        dsf,
        flac,
        id3,
        mp3,
        mp4,
        oggopus,
        oggspeex,
        oggtheora,
        oggvorbis,
        trueaudio,
        wave,
    )

from yt_dlp.postprocessor.common import PostProcessor


class MutagenPPError(PostProcessingError):
    pass


class MutagenPP(PostProcessor):
    def __init__(self, downloader=None):
        PostProcessor.__init__(self, downloader)

    class MetadataInfo(TypedDict):
        title: str | None
        date: str | None
        description: str | None
        synopsis: str | None
        purl: str | None
        comment: str | None
        track: str | None
        artist: str | None
        composer: str | None
        genre: str | None
        album: str | None
        album_artist: str | None
        disc: str | None
        show: str | None
        season_number: str | None
        episode_id: str | None
        episode_sort: str | None

    @singledispatchmethod
    @staticmethod
    def _assemble_metadata(file: FileType, meta: MetadataInfo) -> None:
        raise MutagenPPError(f'Filetype {file.__class__.__name__} is not currently supported')

    @staticmethod
    def _set_metadata(file: FileType, meta: MetadataInfo, file_name: str, meta_name: str):
        if meta[meta_name]:
            file[file_name] = meta[meta_name]

    @_assemble_metadata.register(oggvorbis.OggVorbis)
    @_assemble_metadata.register(oggtheora.OggTheora)
    @_assemble_metadata.register(oggspeex.OggSpeex)
    @_assemble_metadata.register(oggopus.OggOpus)
    @_assemble_metadata.register(flac.FLAC)
    @staticmethod
    def _(file: oggopus.OggOpus, meta: MetadataInfo) -> None:
        MutagenPP._set_metadata(file, meta, 'artist', 'artist')
        MutagenPP._set_metadata(file, meta, 'title', 'title')
        MutagenPP._set_metadata(file, meta, 'genre', 'genre')
        MutagenPP._set_metadata(file, meta, 'date', 'date')
        MutagenPP._set_metadata(file, meta, 'album', 'album')
        MutagenPP._set_metadata(file, meta, 'albumartist', 'album_artist')
        MutagenPP._set_metadata(file, meta, 'description', 'description')
        MutagenPP._set_metadata(file, meta, 'comment', 'comment')
        MutagenPP._set_metadata(file, meta, 'composer', 'composer')
        MutagenPP._set_metadata(file, meta, 'tracknumber', 'track')

        # https://getmusicbee.com/forum/index.php?topic=39759.0
        MutagenPP._set_metadata(file, meta, 'WWWAUDIOFILE', 'purl')

    @_assemble_metadata.register(trueaudio.TrueAudio)
    @_assemble_metadata.register(dsf.DSF)
    @_assemble_metadata.register(dsdiff.DSDIFF)
    @_assemble_metadata.register(aiff.AIFF)
    @_assemble_metadata.register(mp3.MP3)
    @_assemble_metadata.register(wave.WAVE)
    @staticmethod
    def _(file: wave.WAVE, meta: MetadataInfo) -> None:

        def _set_metadata(file_name: str, meta_name: str):
            if meta[meta_name]:
                id3_class = getattr(id3, file_name)
                file[file_name] = id3_class(encoding=id3.Encoding.UTF8, text=meta[meta_name])

        _set_metadata('TIT2', 'title')
        _set_metadata('TPE1', 'artist')
        _set_metadata('COMM', 'description')
        _set_metadata('TCON', 'genre')
        _set_metadata('WFED', 'purl')
        _set_metadata('WOAF', 'purl')
        _set_metadata('TDAT', 'date')
        _set_metadata('TALB', 'album')
        _set_metadata('TPE2', 'album_artist')
        _set_metadata('TRCK', 'track')
        _set_metadata('TCOM', 'composer')
        _set_metadata('TPOS', 'disc')

    @_assemble_metadata.register(mp4.MP4)
    @staticmethod
    def _(file: mp4.MP4, meta: MetadataInfo) -> None:
        MutagenPP._set_metadata(file, meta, '\251ART', 'artist')
        MutagenPP._set_metadata(file, meta, '\251nam', 'title')
        MutagenPP._set_metadata(file, meta, '\251gen', 'genre')
        MutagenPP._set_metadata(file, meta, '\251day', 'date')
        MutagenPP._set_metadata(file, meta, '\251alb', 'album')
        MutagenPP._set_metadata(file, meta, 'aART', 'album_artist')
        MutagenPP._set_metadata(file, meta, '\251cmt', 'description')
        MutagenPP._set_metadata(file, meta, '\251wrt', 'composer')
        MutagenPP._set_metadata(file, meta, 'disk', 'disc')
        MutagenPP._set_metadata(file, meta, 'tvsh', 'show')
        MutagenPP._set_metadata(file, meta, 'tvsn', 'season_number')
        MutagenPP._set_metadata(file, meta, 'egid', 'episode_id')
        MutagenPP._set_metadata(file, meta, 'tven', 'episode_sort')

        if meta['purl']:
            # https://getmusicbee.com/forum/index.php?topic=39759.0
            file['----:com.apple.iTunes:WWWAUDIOFILE'] = meta['purl'].encode()
            file['purl'] = meta['purl'].encode()

        if meta['track']:
            file['trkn'] = [(meta['track'], 0)]

    def _get_cover_art_file(self, info) -> str | None:
        idx = next((-i for i, t in enumerate(info['thumbnails'][::-1], 1) if t.get('filepath')), None)
        if idx is None:
            return None
        thumbnail_filename = info['thumbnails'][idx]['filepath']
        if not os.path.exists(thumbnail_filename):
            self.report_warning('Skipping embedding the cover art because the file is missing.')
            return None
        return thumbnail_filename

    def _get_metadata_from_info(self, info) -> MetadataInfo:
        meta_prefix = 'meta'
        metadata: dict[str, self.MetadataInfo] = collections.defaultdict(
            lambda: collections.defaultdict(lambda: None),
        )

        def add(meta_list, info_list=None):
            value = next((
                info[key] for key in [f'{meta_prefix}_', *variadic(info_list or meta_list)]
                if info.get(key) is not None), None)
            if value not in ('', None):
                value = ', '.join(map(str, variadic(value)))
                value = value.replace('\0', '')  # nul character cannot be passed in command line
                metadata['common'].update({meta_f: value for meta_f in variadic(meta_list)})

        add('title', ('track', 'title'))
        add('date', 'upload_date')
        add(('description', 'synopsis'), 'description')
        add(('purl', 'comment'), 'webpage_url')
        add('track', 'track_number')
        add('artist', ('artist', 'artists', 'creator', 'creators', 'uploader', 'uploader_id'))
        add('composer', ('composer', 'composers'))
        add('genre', ('genre', 'genres'))
        add('album')
        add('album_artist', ('album_artist', 'album_artists'))
        add('disc', 'disc_number')
        add('show', 'series')
        add('season_number')
        add('episode_id', ('episode', 'episode_id'))
        add('episode_sort', 'episode_number')
        if 'embed-metadata' in self.get_param('compat_opts', []):
            add('comment', 'description')
            metadata['common'].pop('synopsis', None)

        meta_regex = rf'{re.escape(meta_prefix)}(?P<i>\d+)?_(?P<key>.+)'
        for key, value in info.items():
            mobj = re.fullmatch(meta_regex, key)
            if value is not None and mobj:
                metadata[mobj.group('i') or 'common'][mobj.group('key')] = value.replace('\0', '')

        cover_art = self._get_cover_art_file(info)
        if cover_art:
            try:
                with open(cover_art, 'rb') as cover_file:
                    cover_data = cover_file.read()
                type_ = imghdr.what(h=cover_data)
                if not type_:
                    raise ValueError('could not determine image type')
                elif type_ not in ('jpeg', 'png'):
                    raise ValueError(f'incompatible image type: {type_}')
                metadata['common']['cover_art_data'] = cover_data
                metadata['common']['cover_art_type'] = type_
            except Exception as err:
                self.report_warning(f'Skipping embedding cover art due to error; {err}')

        return metadata['common']

    @PostProcessor._restrict_to(video=False, images=False)
    def run(self, info):
        if not mutagen:
            raise MutagenPPError('module mutagen was not found. Please install using `python3 -m pip install mutagen`')
        filename = info['filepath']
        metadata = self._get_metadata_from_info(info)
        if not metadata:
            self.to_screen('There isn\'t any metadata to add')
            return [], info

        self.to_screen(f'Adding metadata to "{filename}"')
        try:
            f = mutagen.File(filename)
            metadata = self._get_metadata_from_info(info)
            self._assemble_metadata(f, metadata)
            f.save()
        except Exception as err:
            raise MutagenPPError(f'Unable to embed metadata; {err}')

        return [], info
