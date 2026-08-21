"""Persistent settings of the graphical interface"""

from __future__ import annotations

import dataclasses
import json
import os

from ..utils import get_user_config_dirs, parse_bytes

SETTINGS_FILENAME = 'gui-settings.json'
DEFAULT_OUTPUT_TEMPLATE = '%(title)s [%(id)s].%(ext)s'

QUALITY_CHOICES = ('best', '2160', '1440', '1080', '720', '480', '360')
VIDEO_CONTAINERS = ('mp4', 'mkv', 'webm', 'best')
AUDIO_FORMATS = ('mp3', 'm4a', 'opus', 'flac', 'wav', 'best')
BROWSER_CHOICES = ('', 'brave', 'chrome', 'chromium', 'edge', 'firefox', 'opera', 'safari', 'vivaldi')
SPONSORBLOCK_CATEGORIES = ('sponsor', 'selfpromo', 'interaction')

MODE_VIDEO = 'video'
MODE_AUDIO = 'audio'


def default_download_dir():
    """@returns the user download directory, falling back to the current one"""
    downloads = os.path.join(os.path.expanduser('~'), 'Downloads')
    return downloads if os.path.isdir(downloads) else os.getcwd()


def settings_file():
    """@returns the path the interface reads and writes its settings to"""
    return os.path.join(next(iter(get_user_config_dirs('yt-dlp'))), SETTINGS_FILENAME)


@dataclasses.dataclass
class Settings:
    """User selectable options, mapped to `YoutubeDL` parameters by `to_params`"""

    output_dir: str = dataclasses.field(default_factory=default_download_dir)
    output_template: str = DEFAULT_OUTPUT_TEMPLATE
    mode: str = MODE_VIDEO
    quality: str = 'best'
    container: str = 'mp4'
    audio_format: str = 'mp3'
    audio_quality: str = '0'
    custom_format: str = ''
    download_playlist: bool = False
    restrict_filenames: bool = False
    overwrite: bool = False
    use_archive: bool = False
    embed_subtitles: bool = False
    subtitle_langs: str = 'en'
    auto_subtitles: bool = False
    embed_thumbnail: bool = False
    embed_metadata: bool = True
    embed_chapters: bool = False
    remove_sponsor: bool = False
    cookies_from_browser: str = ''
    proxy: str = ''
    rate_limit: str = ''
    concurrency: int = 2
    verbose: bool = False

    @classmethod
    def load(cls, path=None):
        """Read the settings file, falling back to the defaults on any error"""
        path = path or settings_file()
        try:
            with open(path, encoding='utf-8') as file:
                stored = json.load(file)
        except (OSError, ValueError):
            return cls()

        known = {field.name for field in dataclasses.fields(cls)}
        return cls(**{key: value for key, value in stored.items() if key in known})

    def save(self, path=None):
        """Write the settings file, ignoring failures since they are not fatal"""
        path = path or settings_file()
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w', encoding='utf-8') as file:
                json.dump(dataclasses.asdict(self), file, indent=4, sort_keys=True)
        except OSError:
            return False
        return True

    @property
    def is_audio_only(self):
        return self.mode == MODE_AUDIO

    def format_selector(self):
        """@returns the format selection expression for the current settings"""
        if self.custom_format.strip():
            return self.custom_format.strip()
        if self.is_audio_only:
            return 'bestaudio/best'

        height = '' if self.quality == 'best' else f'[height<=?{self.quality}]'
        selectors = []
        if self.container == 'mp4':
            selectors.append(f'bv*{height}[ext=mp4]+ba[ext=m4a]')
        selectors.extend((f'bv*{height}+ba', f'b{height}', 'b'))
        return '/'.join(dict.fromkeys(selectors))

    def _postprocessors(self):
        """Yield the postprocessors in the order expected by `YoutubeDL`"""
        sponsor_categories = list(SPONSORBLOCK_CATEGORIES) if self.remove_sponsor else []
        if sponsor_categories:
            yield {
                'key': 'SponsorBlock',
                'categories': sponsor_categories,
                'when': 'after_filter',
            }
        if self.is_audio_only:
            yield {
                'key': 'FFmpegExtractAudio',
                'preferredcodec': self.audio_format,
                'preferredquality': self.audio_quality,
            }
        if self.embed_subtitles and not self.is_audio_only:
            yield {
                'key': 'FFmpegEmbedSubtitle',
                'already_have_subtitle': False,
            }
        if sponsor_categories:
            yield {
                'key': 'ModifyChapters',
                'remove_sponsor_segments': sponsor_categories,
            }
        if self.embed_metadata or self.embed_chapters:
            yield {
                'key': 'FFmpegMetadata',
                'add_metadata': self.embed_metadata,
                'add_chapters': self.embed_chapters,
            }
        if self.embed_thumbnail:
            yield {
                'key': 'EmbedThumbnail',
                'already_have_thumbnail': False,
            }

    def to_params(self):
        """@returns the `YoutubeDL` parameters described by these settings"""
        params = {
            'format': self.format_selector(),
            'outtmpl': {'default': os.path.join(self.output_dir, self.output_template)},
            'postprocessors': list(self._postprocessors()),
            'noplaylist': not self.download_playlist,
            'restrictfilenames': self.restrict_filenames,
            'overwrites': self.overwrite or None,
            'continuedl': True,
            'ignoreerrors': False,
            'verbose': self.verbose,
            'quiet': True,
            'noprogress': True,
            'no_color': True,
            'consoletitle': False,
        }

        if not self.is_audio_only and self.container != 'best':
            params['merge_output_format'] = self.container
        if self.embed_subtitles and not self.is_audio_only:
            params['writesubtitles'] = True
            params['writeautomaticsub'] = self.auto_subtitles
            params['subtitleslangs'] = [
                lang.strip() for lang in self.subtitle_langs.split(',') if lang.strip()] or ['en']
        if self.embed_thumbnail:
            params['writethumbnail'] = True
        if self.cookies_from_browser:
            params['cookiesfrombrowser'] = (self.cookies_from_browser, None, None, None)
        if self.proxy.strip():
            params['proxy'] = self.proxy.strip()
        if self.use_archive:
            params['download_archive'] = os.path.join(self.output_dir, 'yt-dlp-archive.txt')

        rate_limit = parse_bytes(self.rate_limit) if self.rate_limit.strip() else None
        if rate_limit:
            params['ratelimit'] = rate_limit

        return params
