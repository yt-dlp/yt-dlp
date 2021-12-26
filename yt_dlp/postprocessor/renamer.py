from __future__ import unicode_literals

import os
import re
import shutil

from .common import PostProcessor
from ..utils import PostProcessingError


class RenamePP(PostProcessor):

    def __init__(self, downloader=None, group='ytdlP'):
        try:
            global MediaInfo
            from pymediainfo import MediaInfo
        except ModuleNotFoundError:
            raise PostProcessingError('Run: python3 -m pip install -U pymediainfo')
        PostProcessor.__init__(self, downloader)
        self.group = group

    _SCENE_NAME = {
        'Youtube': 'YT',
        'Hotstar': 'HS',
        'SonyLiv': 'SONY',
        'Zee5': 'ZEE',
        'DiscoveryPlusIndia': 'DSCP',
    }

    def run(self, info):
        file = info['filepath']
        dir_path = os.path.dirname(file)
        ext = file.split('.')[-1]
        media_info = MediaInfo.parse(file)
        languages = []
        langs = 0
        source = self._SCENE_NAME.get(info['extractor_key'], info['extractor_key'])
        for track in media_info.tracks:
            if track.track_type == 'Video':
                if int(track.width) == 1280 or int(track.height) == 720:
                    resolution = '720p'
                elif int(track.width) == 1920 or int(track.height) == 1080:
                    resolution = '1080p'
                else:
                    resolution = '{}p'.format(track.height)

                if track.format == 'AVC':
                    codec = 'H.264'
                elif track.format == 'HEVC':
                    codec = 'H.265'
                else:
                    codec = track.format

                hdr = track.hdr_format_commercial or 'SDR'

            if track.track_type == 'Audio':
                langs += 1
                if track.language:
                    languages.append(track.other_language[0].upper())
                if track.format == 'E-AC-3':
                    audioCodec = 'DD+'
                elif track.format == 'AC-3':
                    audioCodec = 'DD'
                elif track.format == 'AAC':
                    audioCodec = 'AAC'
                else:
                    audioCodec = track.format

                if track.channel_s == 6:
                    channels = '5.1'
                elif track.channel_s == 2:
                    channels = '2.0'
                elif track.channel_s == 1:
                    channels = '1.0'
                else:
                    channels = track.channel_s

        suffix = f'{resolution}.{source}.WEB-DL.{hdr}.{audioCodec}{channels}.{codec}-{self.group}.{ext}'
        if langs > 1:
            suffix = f'MULTi.{suffix}'
        elif languages and not languages[0].startswith('EN'):
            suffix = f'{languages[0]}.{suffix}'

        if info.get('series'):
            prefix = f'{info["series"]}.S{info["season_number"]:02d}E{info["episode_number"]:02d}.{info["title"]}'
        else:
            prefix = f'{info["title"]}.{info["upload_date"][0:4]}'
        prefix = prefix.replace(' ', '.').replace('\'', '').replace(',', '')

        newfile = re.sub(r'\.{2,}', '.', f'{dir_path}/{prefix}.{suffix}')
        self.to_screen('Renaming file "%s" to "%s"' % (file, newfile))
        shutil.move(file, newfile)
        info['filepath'] = newfile
        return [], info
