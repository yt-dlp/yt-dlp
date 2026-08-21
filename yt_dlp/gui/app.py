"""tkinter based interface for yt-dlp"""

from __future__ import annotations

import dataclasses
import os
import queue
import subprocess
import sys
import tkinter as tk
import webbrowser
from tkinter import filedialog, messagebox, ttk

from . import config
from .manager import DownloadManager, Status
from ..version import __version__

DOCUMENTATION_URL = 'https://github.com/yt-dlp/yt-dlp#readme'
EVENT_INTERVAL = 120
EVENT_BUDGET = 400
LOG_LIMIT = 2000
PROGRESS_WIDTH = 14

ENTRY, COMBO, EDITABLE, CHECK, SPIN = 'entry', 'combo', 'editable', 'check', 'spin'

FORMAT_FIELDS = (
    (COMBO, 'quality', 'Maximum height', config.QUALITY_CHOICES),
    (COMBO, 'container', 'Video container', config.VIDEO_CONTAINERS),
    (COMBO, 'audio_format', 'Audio format', config.AUDIO_FORMATS),
    (ENTRY, 'custom_format', 'Custom format selector'),
    (ENTRY, 'output_template', 'Output template'),
)

PROCESSING_FIELDS = (
    (CHECK, 'embed_metadata', 'Embed metadata'),
    (CHECK, 'embed_chapters', 'Embed chapters'),
    (CHECK, 'embed_thumbnail', 'Embed thumbnail'),
    (CHECK, 'embed_subtitles', 'Embed subtitles'),
    (CHECK, 'auto_subtitles', 'Include automatically generated subtitles'),
    (ENTRY, 'subtitle_langs', 'Subtitle languages'),
    (CHECK, 'remove_sponsor', 'Remove sponsor segments (SponsorBlock)'),
)

ADVANCED_FIELDS = (
    (CHECK, 'download_playlist', 'Download complete playlists'),
    (CHECK, 'restrict_filenames', 'Restrict filenames to ASCII'),
    (CHECK, 'overwrite', 'Overwrite existing files'),
    (CHECK, 'use_archive', 'Keep a download archive'),
    (CHECK, 'verbose', 'Show debug messages in the log'),
    (EDITABLE, 'cookies_from_browser', 'Cookies from browser', config.BROWSER_CHOICES),
    (ENTRY, 'proxy', 'Proxy'),
    (ENTRY, 'rate_limit', 'Rate limit'),
    (SPIN, 'concurrency', 'Simultaneous downloads', (1, 8)),
)

QUEUE_COLUMNS = (
    ('title', 'Title', 340, 'w', True),
    ('status', 'Status', 110, 'w', False),
    ('progress', 'Progress', 180, 'w', False),
    ('speed', 'Speed', 95, 'e', False),
    ('eta', 'ETA', 70, 'e', False),
    ('size', 'Size', 95, 'e', False),
)

STATUS_COLOURS = {
    Status.FINISHED: '#1e8449',
    Status.ERROR: '#c0392b',
    Status.CANCELLED: '#7f8c8d',
}

LOG_COLOURS = {
    'debug': '#7f8c8d',
    'info': '#2c3e50',
    'warning': '#b9770e',
    'error': '#c0392b',
}


def reveal(path):
    """Show `path` in the file manager of the current platform"""
    if not path or not os.path.exists(path):
        return False
    if sys.platform == 'win32':
        os.startfile(path)
    elif sys.platform == 'darwin':
        subprocess.Popen(['open', path])
    else:
        subprocess.Popen(['xdg-open', path])
    return True


class SettingsBinder:
    """Two way binding between the `Settings` fields and tkinter variables"""

    _FACTORIES = {'bool': tk.BooleanVar, 'int': tk.IntVar}

    def __init__(self, settings):
        self._settings = settings
        self._variables = {
            field.name: self._FACTORIES.get(field.type, tk.StringVar)(
                value=getattr(settings, field.name))
            for field in dataclasses.fields(settings)
        }

    def __getitem__(self, name):
        return self._variables[name]

    def collect(self):
        """Copy the widget values into the settings and @returns them"""
        for name, variable in self._variables.items():
            setattr(self._settings, name, variable.get())
        return self._settings


class YtDlpGUI:
    """Main window of the graphical interface"""

    def __init__(self, urls=()):
        self.settings = config.Settings.load()
        self.events = queue.Queue()
        self.manager = DownloadManager(self.events, workers=self.settings.concurrency)

        self.root = tk.Tk()
        self.root.title(f'yt-dlp {__version__}')
        self.root.geometry('1000x700')
        self.root.minsize(780, 580)
        self.root.protocol('WM_DELETE_WINDOW', self.close)

        self._binder = SettingsBinder(self.settings)
        self._url = tk.StringVar()
        self._summary = tk.StringVar()
        self._filepaths = {}

        self._use_native_theme()
        self._build_layout()

        for url in urls:
            self._enqueue(url)
        self.root.after(EVENT_INTERVAL, self._pump)

    def run(self):
        self.root.mainloop()
        return 0

    def close(self):
        _, running, _ = self.manager.counts()
        if running and not messagebox.askokcancel(
                'yt-dlp', 'Some downloads are still running. Quit anyway?'):
            return
        self._read_settings().save()
        self.manager.shutdown()
        self.root.destroy()

    def _use_native_theme(self):
        style = ttk.Style(self.root)
        available = style.theme_names()
        for theme in ('vista', 'aqua', 'clam'):
            if theme in available:
                style.theme_use(theme)
                return

    def _build_layout(self):
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(3, weight=1)

        self._build_menu()
        self._build_source().grid(row=0, column=0, sticky='ew', padx=8, pady=(8, 4))
        self._build_options().grid(row=1, column=0, sticky='ew', padx=8, pady=4)
        self._build_actions().grid(row=2, column=0, sticky='ew', padx=8, pady=4)
        self._build_panes().grid(row=3, column=0, sticky='nsew', padx=8, pady=4)
        ttk.Label(self.root, textvariable=self._summary, anchor='w', relief='sunken').grid(
            row=4, column=0, sticky='ew', padx=8, pady=(4, 8))

    def _build_menu(self):
        menubar = tk.Menu(self.root)
        file_menu = tk.Menu(menubar, tearoff=False)
        file_menu.add_command(label='Add URLs from file...', command=self._import_urls)
        file_menu.add_command(label='Open download folder', command=self._open_download_folder)
        file_menu.add_separator()
        file_menu.add_command(label='Quit', command=self.close)
        menubar.add_cascade(label='File', menu=file_menu)

        help_menu = tk.Menu(menubar, tearoff=False)
        help_menu.add_command(
            label='Documentation', command=lambda: webbrowser.open(DOCUMENTATION_URL))
        help_menu.add_command(label='About', command=self._show_about)
        menubar.add_cascade(label='Help', menu=help_menu)
        self.root.configure(menu=menubar)

    def _build_source(self):
        frame = ttk.LabelFrame(self.root, text='Source')
        frame.columnconfigure(0, weight=1)

        entry = ttk.Entry(frame, textvariable=self._url)
        entry.grid(row=0, column=0, sticky='ew', padx=(8, 4), pady=8)
        entry.bind('<Return>', lambda _: self._add_from_entry())
        entry.focus_set()

        ttk.Button(frame, text='Add to queue', command=self._add_from_entry).grid(
            row=0, column=1, padx=(4, 8), pady=8)

        ttk.Label(frame, text='Folder').grid(row=1, column=0, sticky='w', padx=8)
        destination = ttk.Frame(frame)
        destination.grid(row=2, column=0, columnspan=2, sticky='ew', padx=8, pady=(0, 8))
        destination.columnconfigure(0, weight=1)
        ttk.Entry(destination, textvariable=self._binder['output_dir']).grid(
            row=0, column=0, sticky='ew')
        ttk.Button(destination, text='Browse...', command=self._choose_folder).grid(
            row=0, column=1, padx=(4, 0))
        return frame

    def _build_options(self):
        notebook = ttk.Notebook(self.root)
        tabs = (
            ('Format', FORMAT_FIELDS, True),
            ('Processing', PROCESSING_FIELDS, False),
            ('Advanced', ADVANCED_FIELDS, False),
        )
        for title, fields, with_mode in tabs:
            tab = ttk.Frame(notebook, padding=8)
            offset = 0
            if with_mode:
                offset = 1
                modes = ttk.Frame(tab)
                modes.grid(row=0, column=0, columnspan=2, sticky='w', pady=(0, 6))
                for value, label in ((config.MODE_VIDEO, 'Video'), (config.MODE_AUDIO, 'Audio only')):
                    ttk.Radiobutton(
                        modes, text=label, value=value, variable=self._binder['mode'],
                    ).pack(side='left', padx=(0, 16))
            self._build_form(tab, fields, offset)
            notebook.add(tab, text=title)
        return notebook

    def _build_form(self, parent, fields, offset=0):
        parent.columnconfigure(1, weight=1)
        for index, (kind, name, label, *extra) in enumerate(fields):
            row, variable = index + offset, self._binder[name]
            if kind == CHECK:
                ttk.Checkbutton(parent, text=label, variable=variable).grid(
                    row=row, column=0, columnspan=2, sticky='w', pady=1)
                continue

            ttk.Label(parent, text=label).grid(row=row, column=0, sticky='w', padx=(0, 8), pady=2)
            if kind in (COMBO, EDITABLE):
                widget = ttk.Combobox(
                    parent, textvariable=variable, values=list(extra[0]),
                    state='readonly' if kind == COMBO else 'normal')
            elif kind == SPIN:
                minimum, maximum = extra[0]
                widget = ttk.Spinbox(parent, textvariable=variable, from_=minimum, to=maximum, width=6)
            else:
                widget = ttk.Entry(parent, textvariable=variable)
            widget.grid(row=row, column=1, sticky='ew', pady=2)

    def _build_actions(self):
        frame = ttk.Frame(self.root)
        actions = (
            ('Cancel selected', self._cancel_selected),
            ('Cancel all', self.manager.cancel_all),
            ('Remove finished', self._remove_finished),
            ('Open download folder', self._open_download_folder),
            ('Clear log', self._clear_log),
        )
        for text, command in actions:
            ttk.Button(frame, text=text, command=command).pack(side='left', padx=(0, 6))
        return frame

    def _build_panes(self):
        panes = ttk.PanedWindow(self.root, orient='vertical')
        panes.add(self._build_queue(panes), weight=3)
        panes.add(self._build_log(panes), weight=1)
        return panes

    def _build_queue(self, parent):
        frame = ttk.LabelFrame(parent, text='Queue')
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)

        self._tree = ttk.Treeview(
            frame, columns=[column[0] for column in QUEUE_COLUMNS],
            show='headings', selectmode='extended')
        for name, heading, width, anchor, stretch in QUEUE_COLUMNS:
            self._tree.heading(name, text=heading)
            self._tree.column(name, width=width, anchor=anchor, stretch=stretch)
        for status, colour in STATUS_COLOURS.items():
            self._tree.tag_configure(status, foreground=colour)
        self._tree.bind('<Double-1>', lambda _: self._reveal_selected())
        self._tree.grid(row=0, column=0, sticky='nsew')

        scrollbar = ttk.Scrollbar(frame, orient='vertical', command=self._tree.yview)
        scrollbar.grid(row=0, column=1, sticky='ns')
        self._tree.configure(yscrollcommand=scrollbar.set)
        return frame

    def _build_log(self, parent):
        frame = ttk.LabelFrame(parent, text='Log')
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)

        self._log = tk.Text(frame, height=8, wrap='none', state='disabled')
        for level, colour in LOG_COLOURS.items():
            self._log.tag_configure(level, foreground=colour)
        self._log.grid(row=0, column=0, sticky='nsew')

        scrollbar = ttk.Scrollbar(frame, orient='vertical', command=self._log.yview)
        scrollbar.grid(row=0, column=1, sticky='ns')
        self._log.configure(yscrollcommand=scrollbar.set)
        return frame

    def _read_settings(self):
        try:
            return self._binder.collect()
        except tk.TclError:
            messagebox.showerror('yt-dlp', 'Some option holds an invalid value')
            raise

    def _add_from_entry(self):
        urls = self._url.get().split()
        if not urls:
            return
        for url in urls:
            if not self._enqueue(url):
                return
        self._url.set('')

    def _enqueue(self, url):
        try:
            settings = self._read_settings()
        except tk.TclError:
            return False
        if not os.path.isdir(settings.output_dir):
            messagebox.showerror('yt-dlp', f'The download folder does not exist:\n{settings.output_dir}')
            return False

        try:
            params = settings.to_params()
        except ValueError as error:
            messagebox.showerror('yt-dlp', str(error))
            return False

        self.manager.set_concurrency(settings.concurrency)
        self.manager.submit(url, params)
        return True

    def _import_urls(self):
        path = filedialog.askopenfilename(
            title='Add URLs from file', filetypes=[('Text files', '*.txt'), ('All files', '*.*')])
        if not path:
            return
        try:
            with open(path, encoding='utf-8') as file:
                urls = [line.strip() for line in file if line.strip() and not line.startswith('#')]
        except OSError as error:
            messagebox.showerror('yt-dlp', str(error))
            return
        for url in urls:
            if not self._enqueue(url):
                return

    def _choose_folder(self):
        chosen = filedialog.askdirectory(
            initialdir=self._binder['output_dir'].get() or os.getcwd())
        if chosen:
            self._binder['output_dir'].set(chosen)

    def _selected_ids(self):
        return [int(item) for item in self._tree.selection()]

    def _cancel_selected(self):
        for task_id in self._selected_ids():
            self.manager.cancel(task_id)

    def _remove_finished(self):
        for task in self.manager.tasks:
            if self.manager.forget(task.task_id):
                self._filepaths.pop(task.task_id, None)
                self._tree.delete(str(task.task_id))

    def _reveal_selected(self):
        for task_id in self._selected_ids():
            if reveal(os.path.dirname(self._filepaths.get(task_id) or '')):
                return
        self._open_download_folder()

    def _open_download_folder(self):
        folder = self._binder['output_dir'].get()
        if not reveal(folder):
            messagebox.showerror('yt-dlp', f'The download folder does not exist:\n{folder}')

    def _clear_log(self):
        self._log.configure(state='normal')
        self._log.delete('1.0', 'end')
        self._log.configure(state='disabled')

    def _show_about(self):
        messagebox.showinfo('About yt-dlp', '\n'.join((
            f'yt-dlp {__version__}',
            '',
            'A feature-rich audio/video downloader.',
            DOCUMENTATION_URL,
        )))

    def _pump(self):
        handlers = {'state': self._render_task, 'log': self._handle_log}
        for _ in range(EVENT_BUDGET):
            try:
                event = self.events.get_nowait()
            except queue.Empty:
                break
            handlers[event['type']](event)
        queued, running, done = self.manager.counts()
        self._summary.set(f'Queued: {queued}    Running: {running}    Finished: {done}')
        self.root.after(EVENT_INTERVAL, self._pump)

    def _render_task(self, event):
        item = str(event['task_id'])
        values = (
            event['title'] or event['url'],
            event['status'],
            self._progress_cell(event['progress']),
            event['speed'],
            event['eta'],
            event['size'],
        )
        if self._tree.exists(item):
            self._tree.item(item, values=values, tags=(event['status'],))
        else:
            self._tree.insert('', 'end', iid=item, values=values, tags=(event['status'],))
            self._tree.see(item)

        if event['filepath']:
            self._filepaths[event['task_id']] = event['filepath']

    def _handle_log(self, event):
        if event['level'] == 'debug' and not self.settings.verbose:
            return
        self._write_log(event['level'], event['message'])

    def _write_log(self, level, message):
        self._log.configure(state='normal')
        self._log.insert('end', f'{message.rstrip()}\n', level)
        excess = int(self._log.index('end-1c').split('.')[0]) - LOG_LIMIT
        if excess > 0:
            self._log.delete('1.0', f'{excess + 1}.0')
        self._log.see('end')
        self._log.configure(state='disabled')

    @staticmethod
    def _progress_cell(progress):
        percent = min(100.0, max(0.0, progress))
        filled = int(percent / 100 * PROGRESS_WIDTH)
        return f'{"=" * filled}{"." * (PROGRESS_WIDTH - filled)} {percent:5.1f}%'
