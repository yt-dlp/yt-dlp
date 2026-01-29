#!/usr/bin/env python3
"""
yt-dlp Local Web UI
A simple web interface for downloading videos from YouTube, Twitter/X, and other platforms.
"""

import json
import os
import sys
import threading
import time
import uuid
from pathlib import Path

from flask import Flask, render_template, request, jsonify, Response

# Add the parent directory to path to import yt_dlp
sys.path.insert(0, str(Path(__file__).parent.parent))

import yt_dlp

app = Flask(__name__)

# Store download tasks and their progress
downloads = {}
downloads_lock = threading.Lock()

# Default download directory
DOWNLOAD_DIR = Path(__file__).parent / 'downloads'
DOWNLOAD_DIR.mkdir(exist_ok=True)


class DownloadTask:
    """Represents a download task with progress tracking."""

    def __init__(self, task_id, url, options=None):
        self.task_id = task_id
        self.url = url
        self.options = options or {}
        self.status = 'pending'
        self.progress = 0
        self.speed = ''
        self.eta = ''
        self.filename = ''
        self.title = ''
        self.error = None
        self.thumbnail = ''
        self.filesize = ''
        self.downloaded_bytes = 0
        self.total_bytes = 0

    def to_dict(self):
        return {
            'task_id': self.task_id,
            'url': self.url,
            'status': self.status,
            'progress': self.progress,
            'speed': self.speed,
            'eta': self.eta,
            'filename': self.filename,
            'title': self.title,
            'error': self.error,
            'thumbnail': self.thumbnail,
            'filesize': self.filesize,
        }


def create_progress_hook(task):
    """Create a progress hook for a download task."""
    def progress_hook(d):
        if d['status'] == 'downloading':
            task.status = 'downloading'

            # Calculate progress
            downloaded = d.get('downloaded_bytes', 0)
            total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)

            if total > 0:
                task.progress = round((downloaded / total) * 100, 1)
                task.downloaded_bytes = downloaded
                task.total_bytes = total

            # Get speed and ETA
            task.speed = d.get('_speed_str', '')
            task.eta = d.get('_eta_str', '')
            task.filename = d.get('filename', '')

            # Get info from info_dict if available
            info = d.get('info_dict', {})
            if not task.title:
                task.title = info.get('title', '')
            if not task.thumbnail:
                task.thumbnail = info.get('thumbnail', '')

        elif d['status'] == 'finished':
            task.status = 'processing'
            task.progress = 100
            task.filename = d.get('filename', '')

        elif d['status'] == 'error':
            task.status = 'error'
            task.error = str(d.get('error', 'Unknown error'))

    return progress_hook


def create_postprocessor_hook(task):
    """Create a postprocessor hook for a download task."""
    def postprocessor_hook(d):
        if d['status'] == 'started':
            task.status = 'processing'
        elif d['status'] == 'finished':
            task.status = 'completed'

    return postprocessor_hook


def run_download(task):
    """Run the download in a background thread."""
    try:
        # Build yt-dlp options
        ydl_opts = {
            'format': task.options.get('format', 'best'),
            'outtmpl': str(DOWNLOAD_DIR / '%(title)s.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
            'noprogress': True,
            'noplaylist': task.options.get('noplaylist', True),
        }

        # Audio-only option
        if task.options.get('audio_only'):
            ydl_opts['format'] = 'bestaudio/best'
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]

        # Quality selection
        quality = task.options.get('quality', 'best')
        if quality == 'best':
            if not task.options.get('audio_only'):
                ydl_opts['format'] = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
        elif quality == '1080p':
            ydl_opts['format'] = 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best'
        elif quality == '720p':
            ydl_opts['format'] = 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best'
        elif quality == '480p':
            ydl_opts['format'] = 'bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480][ext=mp4]/best'

        task.status = 'starting'

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Add hooks
            ydl.add_progress_hook(create_progress_hook(task))
            ydl.add_postprocessor_hook(create_postprocessor_hook(task))

            # First extract info to get metadata
            try:
                info = ydl.extract_info(task.url, download=False)
                if info:
                    task.title = info.get('title', '')
                    task.thumbnail = info.get('thumbnail', '')

                    # Get filesize estimate
                    formats = info.get('formats', [])
                    if formats:
                        # Try to find the best format's filesize
                        for fmt in reversed(formats):
                            if fmt.get('filesize'):
                                task.filesize = format_bytes(fmt['filesize'])
                                break
            except Exception:
                pass  # Continue even if metadata extraction fails

            # Now download
            task.status = 'downloading'
            error_code = ydl.download([task.url])

            if error_code == 0:
                task.status = 'completed'
                task.progress = 100
            else:
                task.status = 'error'
                task.error = 'Download failed with error code: ' + str(error_code)

    except yt_dlp.utils.DownloadError as e:
        task.status = 'error'
        task.error = str(e)
    except Exception as e:
        task.status = 'error'
        task.error = str(e)


def format_bytes(size):
    """Format bytes to human-readable string."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} PB"


@app.route('/')
def index():
    """Serve the main page."""
    return render_template('index.html')


@app.route('/api/download', methods=['POST'])
def start_download():
    """Start a new download task."""
    data = request.get_json()
    url = data.get('url', '').strip()

    if not url:
        return jsonify({'error': 'URL is required'}), 400

    # Create a new task
    task_id = str(uuid.uuid4())[:8]
    options = {
        'quality': data.get('quality', 'best'),
        'audio_only': data.get('audio_only', False),
        'noplaylist': data.get('noplaylist', True),
    }

    task = DownloadTask(task_id, url, options)

    with downloads_lock:
        downloads[task_id] = task

    # Start download in background thread
    thread = threading.Thread(target=run_download, args=(task,), daemon=True)
    thread.start()

    return jsonify({'task_id': task_id, 'message': 'Download started'})


@app.route('/api/status/<task_id>')
def get_status(task_id):
    """Get the status of a download task."""
    with downloads_lock:
        task = downloads.get(task_id)

    if not task:
        return jsonify({'error': 'Task not found'}), 404

    return jsonify(task.to_dict())


@app.route('/api/status')
def get_all_status():
    """Get status of all download tasks."""
    with downloads_lock:
        tasks = [task.to_dict() for task in downloads.values()]

    return jsonify({'tasks': tasks})


@app.route('/api/stream/<task_id>')
def stream_status(task_id):
    """Stream status updates using Server-Sent Events."""
    def generate():
        last_status = None
        while True:
            with downloads_lock:
                task = downloads.get(task_id)

            if not task:
                yield f"data: {json.dumps({'error': 'Task not found'})}\n\n"
                break

            current = task.to_dict()
            if current != last_status:
                yield f"data: {json.dumps(current)}\n\n"
                last_status = current.copy()

            if task.status in ('completed', 'error'):
                break

            time.sleep(0.5)

    return Response(generate(), mimetype='text/event-stream')


@app.route('/api/cancel/<task_id>', methods=['POST'])
def cancel_download(task_id):
    """Cancel a download task."""
    with downloads_lock:
        task = downloads.get(task_id)

    if not task:
        return jsonify({'error': 'Task not found'}), 404

    task.status = 'cancelled'
    task.error = 'Download cancelled by user'

    return jsonify({'message': 'Download cancelled'})


@app.route('/api/clear', methods=['POST'])
def clear_completed():
    """Clear completed and errored downloads from the list."""
    with downloads_lock:
        to_remove = [
            task_id for task_id, task in downloads.items()
            if task.status in ('completed', 'error', 'cancelled')
        ]
        for task_id in to_remove:
            del downloads[task_id]

    return jsonify({'message': f'Cleared {len(to_remove)} tasks'})


if __name__ == '__main__':
    print(f"\n{'='*60}")
    print("  yt-dlp Local Web UI")
    print(f"{'='*60}")
    print(f"\n  Open your browser and go to: http://127.0.0.1:5000")
    print(f"\n  Downloads will be saved to: {DOWNLOAD_DIR}")
    print(f"\n  Press Ctrl+C to stop the server")
    print(f"{'='*60}\n")

    app.run(host='127.0.0.1', port=5000, debug=False, threaded=True)
