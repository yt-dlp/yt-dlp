"""
yt-dlp Desktop Application — Python API
Exposes yt-dlp functionality to the pywebview JavaScript bridge.
"""

import json
import os
import threading
import time
import uuid

import webview

import yt_dlp

from . import bootstrap


class DownloadItem:
    """Tracks a single download's state."""

    def __init__(self, download_id, url, title='', thumbnail=''):
        self.id = download_id
        self.url = url
        self.title = title
        self.thumbnail = thumbnail
        self.status = 'pending'  # pending, downloading, finished, error, cancelled
        self.progress = 0.0
        self.speed = ''
        self.eta = ''
        self.filesize = ''
        self.filename = ''
        self.error = ''
        self.cancel_event = threading.Event()

    def to_dict(self):
        return {
            'id': self.id,
            'url': self.url,
            'title': self.title,
            'thumbnail': self.thumbnail,
            'status': self.status,
            'progress': self.progress,
            'speed': self.speed,
            'eta': self.eta,
            'filesize': self.filesize,
            'filename': self.filename,
            'error': self.error,
        }


class Api:
    """API class exposed to JavaScript via pywebview bridge."""

    def __init__(self):
        self._downloads = {}
        self._config = {
            'output_dir': os.path.join(os.path.expanduser('~'), 'Downloads', 'yt-dlp'),
            'default_format': 'best',
            'audio_only': False,
            'embed_thumbnail': True,
            'embed_metadata': True,
            'write_subtitles': False,
            'subtitle_lang': 'en',
        }
        self._window = None

        # Ensure output directory exists
        os.makedirs(self._config['output_dir'], exist_ok=True)

    def set_window(self, window):
        self._window = window

    def extract_info(self, url):
        """Extract video info without downloading."""
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'skip_download': True,
                'simulate': True,
                'ignoreerrors': True,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

            if info is None:
                return json.dumps({'error': 'Could not extract video information. Check the URL.'})

            # Handle playlists
            if info.get('_type') == 'playlist':
                entries = info.get('entries', [])
                items = []
                for entry in entries:
                    if entry is None:
                        continue
                    items.append({
                        'id': entry.get('id', ''),
                        'title': entry.get('title', 'Unknown'),
                        'url': entry.get('webpage_url', entry.get('url', '')),
                        'duration': entry.get('duration', 0),
                        'thumbnail': entry.get('thumbnail', ''),
                    })
                return json.dumps({
                    'type': 'playlist',
                    'title': info.get('title', 'Playlist'),
                    'count': len(items),
                    'entries': items[:50],  # Limit for UI performance
                })

            # Single video
            formats = []
            for f in info.get('formats', []):
                format_entry = {
                    'format_id': f.get('format_id', ''),
                    'ext': f.get('ext', ''),
                    'resolution': f.get('resolution', 'audio only'),
                    'fps': f.get('fps'),
                    'vcodec': f.get('vcodec', 'none'),
                    'acodec': f.get('acodec', 'none'),
                    'filesize': f.get('filesize') or f.get('filesize_approx') or 0,
                    'tbr': f.get('tbr', 0),
                    'format_note': f.get('format_note', ''),
                    'has_video': f.get('vcodec', 'none') != 'none',
                    'has_audio': f.get('acodec', 'none') != 'none',
                    'width': f.get('width'),
                    'height': f.get('height'),
                }
                formats.append(format_entry)

            # Sort: video+audio first, then video-only, then audio-only; highest quality first
            formats.sort(key=lambda x: (
                x['has_video'] and x['has_audio'],
                x['has_video'],
                x.get('height') or 0,
                x.get('tbr') or 0,
            ), reverse=True)

            result = {
                'type': 'video',
                'id': info.get('id', ''),
                'title': info.get('title', 'Unknown'),
                'thumbnail': info.get('thumbnail', ''),
                'duration': info.get('duration', 0),
                'uploader': info.get('uploader', info.get('channel', '')),
                'view_count': info.get('view_count', 0),
                'upload_date': info.get('upload_date', ''),
                'description': (info.get('description', '') or '')[:500],
                'webpage_url': info.get('webpage_url', url),
                'formats': formats,
            }

            return json.dumps(result)

        except Exception as e:
            return json.dumps({'error': str(e)})

    def start_download(self, url, format_id='best', title='', thumbnail=''):
        """Start a download in a background thread."""
        download_id = str(uuid.uuid4())[:8]
        item = DownloadItem(download_id, url, title, thumbnail)
        self._downloads[download_id] = item

        thread = threading.Thread(
            target=self._download_worker,
            args=(item, format_id),
            daemon=True,
        )
        thread.start()

        return json.dumps({'id': download_id, 'status': 'started'})

    def _download_worker(self, item, format_id):
        """Background download worker."""
        item.status = 'downloading'

        def progress_hook(d):
            if item.cancel_event.is_set():
                raise yt_dlp.utils.DownloadCancelled('Cancelled by user')

            status = d.get('status', '')
            if status == 'downloading':
                total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
                downloaded = d.get('downloaded_bytes', 0)
                if total > 0:
                    item.progress = round((downloaded / total) * 100, 1)
                item.speed = self._format_speed(d.get('speed'))
                item.eta = self._format_eta(d.get('eta'))
                item.filesize = self._format_bytes(total)
                item.filename = d.get('filename', '')

            elif status == 'finished':
                item.progress = 100.0
                item.filename = d.get('filename', '')

        output_dir = self._config['output_dir']
        os.makedirs(output_dir, exist_ok=True)

        ydl_opts = {
            'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
            'progress_hooks': [progress_hook],
            'quiet': True,
            'no_warnings': True,
            'overwrites': True,
        }

        ffmpeg_dir = bootstrap.find_ffmpeg()

        if ffmpeg_dir:
            ydl_opts['ffmpeg_location'] = ffmpeg_dir
            ydl_opts['merge_output_format'] = 'mp4'

            # With FFmpeg: download best video + best audio separately, merge
            if self._config.get('audio_only'):
                ydl_opts['format'] = 'ba/b'
                ydl_opts.setdefault('postprocessors', []).append({
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                })
            elif format_id and format_id not in ('best', 'bestvideo+bestaudio/best', 'bv*+ba/b'):
                ydl_opts['format'] = format_id
            else:
                ydl_opts['format'] = 'bv*+ba/b'

            if self._config.get('embed_thumbnail'):
                ydl_opts.setdefault('postprocessors', []).append({
                    'key': 'EmbedThumbnail',
                    'already_have_thumbnail': False,
                })
                ydl_opts['writethumbnail'] = True

            if self._config.get('embed_metadata'):
                ydl_opts.setdefault('postprocessors', []).append({
                    'key': 'FFmpegMetadata',
                    'add_metadata': True,
                })
        else:
            # No FFmpeg: can only download pre-merged single streams
            ydl_opts['format'] = 'b'  # Best pre-merged stream

            if self._config.get('audio_only'):
                ydl_opts['format'] = 'ba/b'

        if self._config.get('write_subtitles'):
            ydl_opts['writesubtitles'] = True
            ydl_opts['subtitleslangs'] = [self._config.get('subtitle_lang', 'en')]

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(item.url, download=True)
                if info:
                    item.title = item.title or info.get('title', 'Unknown')
                    item.thumbnail = item.thumbnail or info.get('thumbnail', '')
            item.status = 'finished'
            item.progress = 100.0
        except yt_dlp.utils.DownloadCancelled:
            item.status = 'cancelled'
        except Exception as e:
            item.status = 'error'
            item.error = str(e)

    def get_downloads(self):
        """Return all downloads as JSON array."""
        items = [d.to_dict() for d in reversed(self._downloads.values())]
        return json.dumps(items)

    def get_progress(self):
        """Return progress for active downloads."""
        active = [
            d.to_dict() for d in self._downloads.values()
            if d.status in ('pending', 'downloading')
        ]
        return json.dumps(active)

    def cancel_download(self, download_id):
        """Cancel an active download."""
        item = self._downloads.get(download_id)
        if item and item.status in ('pending', 'downloading'):
            item.cancel_event.set()
            item.status = 'cancelled'
            return json.dumps({'success': True})
        return json.dumps({'success': False, 'error': 'Download not found or already finished'})

    def remove_download(self, download_id):
        """Remove a download from history."""
        if download_id in self._downloads:
            del self._downloads[download_id]
            return json.dumps({'success': True})
        return json.dumps({'success': False})

    def clear_history(self):
        """Clear completed/errored/cancelled downloads."""
        to_remove = [
            k for k, v in self._downloads.items()
            if v.status in ('finished', 'error', 'cancelled')
        ]
        for k in to_remove:
            del self._downloads[k]
        return json.dumps({'success': True, 'removed': len(to_remove)})

    def get_config(self):
        """Return current configuration."""
        return json.dumps(self._config)

    def update_config(self, config_json):
        """Update configuration."""
        try:
            new_config = json.loads(config_json)
            self._config.update(new_config)
            os.makedirs(self._config['output_dir'], exist_ok=True)
            return json.dumps({'success': True})
        except Exception as e:
            return json.dumps({'success': False, 'error': str(e)})

    def browse_folder(self):
        """Open native folder picker dialog."""
        if self._window:
            result = self._window.create_file_dialog(
                webview.FOLDER_DIALOG,
                directory=self._config['output_dir'],
            )
            if result and len(result) > 0:
                folder = result[0]
                self._config['output_dir'] = folder
                return json.dumps({'path': folder})
        return json.dumps({'path': None})

    def open_file(self, filepath):
        """Open a file with the default system application."""
        try:
            os.startfile(filepath)
            return json.dumps({'success': True})
        except Exception as e:
            return json.dumps({'success': False, 'error': str(e)})

    def open_folder(self, folderpath=None):
        """Open folder in file explorer."""
        try:
            path = folderpath or self._config['output_dir']
            os.startfile(path)
            return json.dumps({'success': True})
        except Exception as e:
            return json.dumps({'success': False, 'error': str(e)})

    # ==========================================
    # Update & Dependency Management
    # ==========================================

    def check_update(self):
        """Check if a yt-dlp update is available."""
        try:
            info = bootstrap.check_update_available()
            return json.dumps(info)
        except Exception as e:
            return json.dumps({'available': False, 'error': str(e)})

    def do_update(self):
        """Update yt-dlp to the latest version."""
        try:
            success = bootstrap.update_ytdlp()
            new_version = bootstrap.get_current_version() if success else None
            return json.dumps({'success': success, 'version': new_version})
        except Exception as e:
            return json.dumps({'success': False, 'error': str(e)})

    def install_ffmpeg_dep(self):
        """Download and install FFmpeg if not present."""
        try:
            if bootstrap.find_ffmpeg():
                return json.dumps({'success': True, 'message': 'FFmpeg already installed'})
            success = bootstrap.install_ffmpeg()
            return json.dumps({'success': success})
        except Exception as e:
            return json.dumps({'success': False, 'error': str(e)})

    def get_app_info(self):
        """Get application info (versions, FFmpeg status)."""
        ffmpeg_dir = bootstrap.find_ffmpeg()
        return json.dumps({
            'ytdlp_version': bootstrap.get_current_version(),
            'ffmpeg_available': ffmpeg_dir is not None,
            'ffmpeg_path': ffmpeg_dir or '',
        })

    @staticmethod
    def _format_speed(speed):
        if speed is None:
            return ''
        if speed < 1024:
            return f'{speed:.0f} B/s'
        elif speed < 1024 * 1024:
            return f'{speed / 1024:.1f} KB/s'
        else:
            return f'{speed / (1024 * 1024):.1f} MB/s'

    @staticmethod
    def _format_eta(eta):
        if eta is None:
            return ''
        if eta < 60:
            return f'{eta}s'
        elif eta < 3600:
            return f'{eta // 60}m {eta % 60}s'
        else:
            return f'{eta // 3600}h {(eta % 3600) // 60}m'

    @staticmethod
    def _format_bytes(size):
        if not size:
            return ''
        if size < 1024:
            return f'{size} B'
        elif size < 1024 * 1024:
            return f'{size / 1024:.1f} KB'
        elif size < 1024 * 1024 * 1024:
            return f'{size / (1024 * 1024):.1f} MB'
        else:
            return f'{size / (1024 * 1024 * 1024):.2f} GB'
