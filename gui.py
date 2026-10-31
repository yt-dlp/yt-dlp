import os
import queue
import re
import shutil
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from urllib.parse import parse_qs, unquote, urljoin, urlparse
from urllib.request import Request, urlopen

from yt_dlp import DownloadCancelled, YoutubeDL


ANSI_ESCAPE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')


def clean_text(value):
    return ANSI_ESCAPE.sub('', str(value)).strip()


class GuiLogger:
    def __init__(self, report):
        self.report = report

    def debug(self, message):
        message = clean_text(message)
        if message and not message.startswith('[debug]'):
            self.report(message)

    info = debug

    def warning(self, message):
        self.report(f'Warnung: {clean_text(message)}')

    def error(self, message):
        self.report(f'Fehler: {clean_text(message)}')


def bundled_path(name):
    base = Path(getattr(sys, '_MEIPASS', Path(__file__).parent))
    return base / name


def resolve_video_page(url):
    try:
        request = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urlopen(request, timeout=20) as response:
            content_type = response.headers.get('Content-Type', '')
            if content_type.startswith('video/'):
                return url
            page = response.read(2 * 1024 * 1024).decode('utf-8', 'replace')
    except Exception:
        return url

    patterns = (
        r"(?:var\s+source\s*=|['\"](?:content|src)['\"]\s*:)\s*['\"]([^'\"]+)['\"]",
        r'<source[^>]+src=[\'\"]([^\'\"]+)',
        r'<meta[^>]+property=[\'\"]og:video(?::url)?[\'\"][^>]+content=[\'\"]([^\'\"]+)',
    )
    for pattern in patterns:
        match = re.search(pattern, page, re.IGNORECASE)
        if match:
            candidate = urljoin(url, match.group(1))
            if (urlparse(url).hostname or '').lower().endswith('shanelocaldog.com') \
                    and 'test-videos.co.uk' in (urlparse(candidate).hostname or '').lower():
                continue
            if candidate.startswith(('http://', 'https://')):
                return candidate
    return url


def is_voe_mirror(url):
    hostname = (urlparse(url).hostname or '').lower()
    return hostname == 'shanelocaldog.com' or hostname.endswith('.shanelocaldog.com')


def direct_filename(url):
    parsed = urlparse(url)
    filename = parse_qs(parsed.query).get('n', [None])[0]
    filename = Path(unquote(filename or Path(parsed.path).name)).name
    filename = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', filename).strip('. ')
    return filename if Path(filename).suffix else None


class YtDlpGui(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('yt-dlp Downloader')
        self.geometry('1000x600')
        self.minsize(700, 500)
        self.configure(background='#f3f4f6')
        self.style = ttk.Style(self)
        self.style.theme_use('vista' if 'vista' in self.style.theme_names() else 'clam')
        self.style.configure('Card.TFrame', background='white')
        self.style.configure('Title.TLabel', background='#f3f4f6', foreground='#172033',
                             font=('Segoe UI', 20, 'bold'))
        self.style.configure('Subtitle.TLabel', background='#f3f4f6', foreground='#667085',
                             font=('Segoe UI', 10))
        self.style.configure('Card.TLabel', background='white', foreground='#172033',
                             font=('Segoe UI', 10))
        self.style.configure('Hint.TLabel', background='white', foreground='#667085',
                             font=('Segoe UI', 9))
        self.style.configure('Primary.TButton', font=('Segoe UI', 10, 'bold'))
        self.events = queue.Queue()
        self.cancel_event = threading.Event()
        self.download_thread = None
        self.output_dir = tk.StringVar(value=str(Path.home() / 'Downloads'))
        self.format_choice = tk.StringVar(value='Bestes Video')
        self.playlist = tk.BooleanVar(value=True)
        self.subtitles = tk.BooleanVar(value=False)
        self.subtitle_language = tk.StringVar(value='Alle Sprachen')
        self.thumbnail = tk.BooleanVar(value=False)
        self.metadata = tk.BooleanVar(value=False)
        self.info_json = tk.BooleanVar(value=False)
        self.chapters = tk.BooleanVar(value=False)
        self.description = tk.BooleanVar(value=False)
        self.comments = tk.BooleanVar(value=False)
        self.audio_quality = tk.StringVar(value='192 kbps')
        self.fragment_count = tk.IntVar(value=1)
        self.status = tk.StringVar(value='Bereit')
        self.detail = tk.StringVar(value='Noch kein Download gestartet')
        self.progress = tk.DoubleVar()
        self.create_widgets()
        self.after(100, self.process_events)

    def create_widgets(self):
        outer = ttk.Frame(self, padding=(20, 12))
        outer.pack(fill='both', expand=True)
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(2, weight=1)

        ttk.Label(outer, text='yt-dlp Downloader', style='Title.TLabel').grid(
            row=0, column=0, sticky='w')
        ttk.Label(outer, text='Videos und Audios unkompliziert herunterladen', style='Subtitle.TLabel').grid(
            row=1, column=0, sticky='w', pady=(2, 8))

        frame = ttk.Frame(outer, style='Card.TFrame', padding=14)
        frame.grid(row=2, column=0, sticky='nsew')
        frame.columnconfigure(1, weight=1)
        frame.columnconfigure(3, weight=1)
        frame.rowconfigure(12, weight=1)

        ttk.Label(frame, text='Video- oder Playlist-URL', style='Card.TLabel',
                  font=('Segoe UI', 11, 'bold')).grid(row=0, column=0, columnspan=4,
                                                       sticky='w', pady=(0, 5))
        self.url = tk.Text(frame, height=2, wrap='word', relief='solid', borderwidth=1,
                           font=('Segoe UI', 10))
        self.url.grid(row=1, column=0, columnspan=4, sticky='ew')
        ttk.Label(frame, text='Video-, Audio- und Playlist-Links werden unterstützt.',
                  style='Hint.TLabel').grid(row=2, column=0, columnspan=4, sticky='w', pady=(3, 8))

        ttk.Label(frame, text='Format:', style='Card.TLabel').grid(row=3, column=0, sticky='w', padx=(0, 12), pady=5)
        formats = ('Bestes Video', 'Nur Audio (MP3)', 'Bestes Video ohne Zusammenführen')
        ttk.Combobox(frame, textvariable=self.format_choice, values=formats, state='readonly', width=42).grid(
            row=3, column=1, columnspan=2, sticky='w', pady=5)

        ttk.Label(frame, text='Speicherort:', style='Card.TLabel').grid(row=4, column=0, sticky='w', padx=(0, 12), pady=5)
        ttk.Entry(frame, textvariable=self.output_dir, width=42).grid(row=4, column=1, sticky='w', pady=5)
        ttk.Button(frame, text='Durchsuchen …', command=self.choose_directory).grid(row=4, column=2, padx=(8, 0), pady=5)
        ttk.Checkbutton(frame, text='Playlists herunterladen', variable=self.playlist).grid(
            row=5, column=1, columnspan=2, sticky='w', pady=(4, 10))

        options = ttk.LabelFrame(frame, text='Weitere Optionen', padding=(10, 5))
        options.grid(row=3, column=3, rowspan=5, sticky='nsew', padx=(18, 0), pady=(0, 5))
        options.columnconfigure(0, weight=1)
        options.columnconfigure(1, weight=1)
        ttk.Checkbutton(options, text='Untertitel herunterladen', variable=self.subtitles).grid(
            row=0, column=0, sticky='w', padx=4, pady=(2, 0))
        ttk.Combobox(options, textvariable=self.subtitle_language,
                     values=('Alle Sprachen', 'Deutsch', 'Englisch', 'Deutsch und Englisch'),
                     state='readonly', width=22).grid(row=0, column=1, sticky='w', padx=4, pady=2)
        ttk.Label(options, text='Untertitel werden als separate Dateien gespeichert.', style='Hint.TLabel').grid(
            row=1, column=0, columnspan=2, sticky='w', padx=4)
        ttk.Checkbutton(options, text='Vorschaubild speichern', variable=self.thumbnail).grid(
            row=2, column=0, sticky='w', padx=4, pady=(5, 0))
        ttk.Checkbutton(options, text='Metadaten in Datei schreiben', variable=self.metadata).grid(
            row=2, column=1, sticky='w', padx=4, pady=(5, 0))
        ttk.Label(options, text='Titel, Künstler und weitere Informationen ergänzen.', style='Hint.TLabel').grid(
            row=3, column=0, columnspan=2, sticky='w', padx=4)
        ttk.Checkbutton(options, text='Info-Datei (.json) speichern', variable=self.info_json).grid(
            row=4, column=0, sticky='w', padx=4, pady=(5, 0))
        ttk.Checkbutton(options, text='Kapitelinformationen übernehmen', variable=self.chapters).grid(
            row=4, column=1, sticky='w', padx=4, pady=(5, 0))
        ttk.Label(options, text='Technische Zusatzinformationen für spätere Verarbeitung.', style='Hint.TLabel').grid(
            row=5, column=0, columnspan=2, sticky='w', padx=4)
        ttk.Checkbutton(options, text='Beschreibung als .txt speichern', variable=self.description).grid(
            row=6, column=0, sticky='w', padx=4, pady=(5, 0))
        ttk.Checkbutton(options, text='Kommentare speichern', variable=self.comments).grid(
            row=6, column=1, sticky='w', padx=4, pady=(5, 0))
        ttk.Label(options, text='Speichert zusätzliche Textinformationen neben dem Video.', style='Hint.TLabel').grid(
            row=7, column=0, columnspan=2, sticky='w', padx=4)
        ttk.Label(options, text='MP3-Qualität:', style='Card.TLabel').grid(
            row=8, column=0, sticky='w', padx=4, pady=(5, 2))
        ttk.Combobox(options, textvariable=self.audio_quality,
                     values=('128 kbps', '192 kbps', '256 kbps', '320 kbps'),
                     state='readonly', width=22).grid(row=8, column=1, sticky='w', padx=4, pady=2)
        ttk.Label(options, text='Gleichzeitige Fragmente:', style='Card.TLabel').grid(
            row=9, column=0, sticky='w', padx=4, pady=(8, 2))
        ttk.Spinbox(options, from_=1, to=10, textvariable=self.fragment_count,
                    width=20).grid(row=9, column=1, sticky='w', padx=4, pady=(8, 2))
        ttk.Label(options, text='Mehrere Stream-Teile parallel laden (max. 10).', style='Hint.TLabel').grid(
            row=10, column=0, columnspan=2, sticky='w', padx=4)

        buttons = ttk.Frame(frame)
        buttons.grid(row=8, column=0, columnspan=4, sticky='ew', pady=(8, 10))
        self.download_button = ttk.Button(buttons, text='▶  Download starten', style='Primary.TButton', command=self.start_download)
        self.download_button.pack(side='left')
        self.cancel_button = ttk.Button(buttons, text='Abbrechen', command=self.cancel_download, state='disabled')
        self.cancel_button.pack(side='left', padx=8)

        ttk.Label(frame, textvariable=self.status, style='Card.TLabel', font=('Segoe UI', 10, 'bold')).grid(
            row=9, column=0, columnspan=4, sticky='w', pady=(0, 5))
        ttk.Progressbar(frame, variable=self.progress, maximum=100).grid(
            row=10, column=0, columnspan=4, sticky='ew', pady=(0, 3))
        ttk.Label(frame, textvariable=self.detail, style='Hint.TLabel').grid(
            row=11, column=0, columnspan=4, sticky='w')

        self.log = tk.Text(frame, height=5, state='disabled', wrap='word')
        self.log.grid(row=12, column=0, columnspan=4, sticky='nsew', pady=(12, 0))
        frame.rowconfigure(12, weight=1)

    def choose_directory(self):
        directory = filedialog.askdirectory(initialdir=self.output_dir.get())
        if directory:
            self.output_dir.set(directory)

    def write_log(self, message):
        message = clean_text(message)
        self.log.configure(state='normal')
        self.log.insert('end', message + '\n')
        self.log.see('end')
        self.log.configure(state='disabled')

    def start_download(self):
        url = self.url.get('1.0', 'end').strip()
        if not url:
            messagebox.showwarning('URL fehlt', 'Bitte eine Video- oder Playlist-URL eingeben.')
            return
        output_dir = Path(self.output_dir.get()).expanduser()
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            messagebox.showerror('Speicherort', str(error))
            return

        self.cancel_event.clear()
        self.progress.set(0)
        self.status.set('Download wird vorbereitet …')
        self.download_button.configure(state='disabled')
        self.cancel_button.configure(state='normal')
        self.download_thread = threading.Thread(target=self.download, args=(url, output_dir), daemon=True)
        self.download_thread.start()

    def cancel_download(self):
        self.cancel_event.set()
        self.status.set('Abbruch wird angefordert …')

    def download(self, url, output_dir):
        choice = self.format_choice.get()
        try:
            fragments = max(1, min(int(self.fragment_count.get()), 10))
        except (TypeError, ValueError):
            fragments = 1
        source_url = resolve_video_page(url)
        if is_voe_mirror(url) and source_url == url:
            self.events.put(('error', 'Diese neue VOE-Domain benötigt noch einen eigenen VOE-Resolver. '
                                      'Das Testvideo der Seite wird absichtlich nicht heruntergeladen.'))
            return
        if source_url != url:
            self.events.put(('log', f'Videoquelle erkannt: {source_url}'))
        postprocessors = []
        options = {
            'outtmpl': str(output_dir / '%(title)s [%(id)s].%(ext)s'),
            'logger': GuiLogger(lambda message: self.events.put(('log', message))),
            'progress_hooks': [self.progress_hook],
            'noplaylist': not self.playlist.get(),
            'quiet': True,
            'no_warnings': False,
            'concurrent_fragment_downloads': fragments,
        }
        if self.subtitles.get():
            languages = {
                'Alle Sprachen': ['all'],
                'Deutsch': ['de'],
                'Englisch': ['en'],
                'Deutsch und Englisch': ['de', 'en'],
            }
            options.update(writesubtitles=True, subtitleslangs=languages[self.subtitle_language.get()])
        if self.thumbnail.get():
            options['writethumbnail'] = True
            postprocessors.append({'key': 'EmbedThumbnail'})
        if self.metadata.get():
            postprocessors.append({'key': 'FFmpegMetadata'})
        if self.info_json.get():
            options['writeinfojson'] = True
        if self.chapters.get():
            options['embedchapters'] = True
        if self.description.get():
            options['writedescription'] = True
        if self.comments.get():
            options['writecomments'] = True
        filename = direct_filename(source_url)
        if filename:
            options['outtmpl'] = str(output_dir / filename)
        if choice == 'Nur Audio (MP3)':
            options['format'] = 'ba/b'
            postprocessors.append({
                'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3',
                'preferredquality': self.audio_quality.get().split()[0],
            })
        elif choice == 'Bestes Video ohne Zusammenführen':
            options['format'] = 'bv*'
        else:
            options['format'] = 'bv*+ba/b'
        if postprocessors:
            options['postprocessors'] = postprocessors

        ffmpeg = bundled_path('ffmpeg.exe')
        if ffmpeg.exists():
            options['ffmpeg_location'] = str(ffmpeg.parent)
        elif choice == 'Nur Audio (MP3)':
            self.events.put(('error', 'ffmpeg.exe ist nicht eingebettet. Diese Auswahl benötigt ffmpeg.'))
            return

        try:
            with YoutubeDL(options) as downloader:
                downloader.download([source_url])
            self.events.put(('done', 'Download abgeschlossen.'))
        except DownloadCancelled:
            self.events.put(('done', 'Download abgebrochen.'))
        except Exception as error:
            self.events.put(('error', str(error)))

    def progress_hook(self, data):
        if self.cancel_event.is_set():
            raise DownloadCancelled()
        if data.get('status') == 'downloading':
            percent = clean_text(data.get('_percent_str', ''))
            speed = clean_text(data.get('_speed_str', ''))
            eta = clean_text(data.get('_eta_str', ''))
            try:
                value = float(data.get('downloaded_bytes', 0)) / max(float(data.get('total_bytes') or data.get('total_bytes_estimate') or 1), 1) * 100
                self.events.put(('progress', (value, f'{percent}  {speed}  ETA {eta}')))
            except (TypeError, ValueError):
                pass
        elif data.get('status') == 'finished':
            self.events.put(('progress', (100, 'Verarbeitung …')))

    def process_events(self):
        try:
            while True:
                event, value = self.events.get_nowait()
                if event == 'log':
                    self.write_log(value)
                elif event == 'progress':
                    self.progress.set(value[0])
                    self.status.set(f'{value[0]:.1f} %')
                    self.detail.set(value[1])
                elif event == 'done':
                    self.progress.set(100 if 'abgeschlossen' in value else 0)
                    self.status.set(value)
                    self.detail.set('')
                    self.download_button.configure(state='normal')
                    self.cancel_button.configure(state='disabled')
                    self.write_log(value)
                elif event == 'error':
                    self.status.set('Fehler')
                    self.detail.set('')
                    self.write_log(value)
                    self.download_button.configure(state='normal')
                    self.cancel_button.configure(state='disabled')
                    messagebox.showerror('Download fehlgeschlagen', value)
        except queue.Empty:
            pass
        self.after(100, self.process_events)


if __name__ == '__main__':
    YtDlpGui().mainloop()
