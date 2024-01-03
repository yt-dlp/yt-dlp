from .common import PostProcessor
from ..dependencies import mutagen

if mutagen:
    from mutagen.easymp4 import EasyMP4
    from mutagen.flac import FLAC
    from mutagen.mp3 import EasyMP3
    from mutagen.musepack import Musepack
    from mutagen.oggopus import OggOpus
    from mutagen.oggvorbis import OggVorbis


class MutagenMetadataPP(PostProcessor):
    def __init__(self, downloader):
        PostProcessor.__init__(self, downloader)

    @PostProcessor._restrict_to(images=False)
    def run(self, information):
        extension = information['ext']
        ret = [], information
        if not mutagen:
            if extension in ['mp3', 'm4a', 'ogg', 'opus', 'flac', '.mpc']:
                self.report_warning('module mutagen was not found. Tags with multiple values (e.g. artist, album artist and genre) may be set incorrectly. Please install using `python -m pip install mutagen`')
            return ret
        tag_mapping = {
            'artist': 'artist_list',
            'albumartist': 'album_artist_list',
            'genre': 'genre_list',
            'composer': 'composer_list'
        }
        supported_formats = [EasyMP3, EasyMP4, OggVorbis, OggOpus, FLAC, Musepack]
        file = mutagen.File(information['filepath'], supported_formats)
        if not file:
            return ret
        if isinstance(file, EasyMP4):
            file.RegisterTextKey('composer', '\251wrt')
        for tag_key, info_key in tag_mapping.items():
            value = information.get(info_key)
            if value:
                file[tag_key] = value
        file.save()
        return ret
