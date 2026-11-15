import { app, BrowserWindow, clipboard, dialog, ipcMain, Menu, nativeTheme, net, Notification, shell } from 'electron';
import { existsSync, readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { parseConfigText } from '../shared/command';
import { defaultSettings, type Api, type AppUpdateStatus, type Job, type MenuItemSpec, type Preset, type Settings } from '../shared/types';
import { Engine, type AppPaths } from './engine';
import { JobManager } from './jobs';
import { Logs } from './logs';
import { buildMenu } from './menu';
import { builtinPresets, mergePresets } from './presets';
import { Prober } from './probe';
import { JsonStore } from './store';

const dev = !app.isPackaged;
if (process.env.DUBDECK_USER_DATA) app.setPath('userData', process.env.DUBDECK_USER_DATA);
app.setName('Dubdeck');

if (!app.requestSingleInstanceLock()) {
  app.quit();
} else {
  void main();
}

async function main(): Promise<void> {
  await app.whenReady();

  const userData = app.getPath('userData');
  const appRoot = app.getAppPath();
  const vendor = path.join(appRoot, 'vendor');
  const paths: AppPaths = {
    userData,
    logs: path.join(userData, 'logs'),
    resources: dev ? (existsSync(vendor) ? vendor : null) : process.resourcesPath,
    repoRoot: dev ? path.resolve(appRoot, '..') : null,
  };
  const logs = new Logs(paths.logs);
  logs.app('info', `Dubdeck ${app.getVersion()} starting on ${process.platform} ${process.arch}`);
  process.on('uncaughtException', (e) => logs.app('error', `uncaught: ${e.stack ?? e.message}`));
  process.on('unhandledRejection', (e) => logs.app('error', `unhandled rejection: ${e instanceof Error ? e.stack : String(e)}`));

  const settingsStore = new JsonStore<Settings>(path.join(userData, 'settings.json'), defaultSettings, (loaded, fallback) => {
    const l = loaded as Partial<Settings>;
    return { ...fallback, ...l, simple: { ...fallback.simple, ...(l.simple ?? {}) }, baseValues: l.baseValues ?? fallback.baseValues };
  });
  if (!settingsStore.get().downloadFolder) {
    settingsStore.set({ ...settingsStore.get(), downloadFolder: app.getPath('downloads') });
  }
  const presetStore = new JsonStore<Preset[]>(path.join(userData, 'presets.json'), builtinPresets, (l) => mergePresets(l as Preset[]));
  const windowStore = new JsonStore<{ width: number; height: number; x?: number; y?: number; maximized?: boolean }>(
    path.join(userData, 'window.json'), { width: 1180, height: 760 });
  nativeTheme.themeSource = settingsStore.get().theme;

  const engine = new Engine(paths);
  engine.fetchImpl = ((input: string | URL | Request, init?: RequestInit) => net.fetch(String(input), init as never)) as typeof fetch;
  const prober = new Prober(engine);

  let win: BrowserWindow | null = null;
  const send = (channel: string, ...args: unknown[]) => { if (win && !win.isDestroyed()) win.webContents.send(channel, ...args); };

  const jobs = new JobManager({
    engine, logs, appVersion: app.getVersion(),
    settings: () => settingsStore.get(),
    queue: new JsonStore<Job[]>(path.join(userData, 'queue.json'), []),
    history: new JsonStore<Job[]>(path.join(userData, 'history.json'), []),
    onChange: (list) => {
      send('jobs', list);
      const active = list.filter((j) => j.state === 'running');
      if (win && !win.isDestroyed()) {
        const known = active.filter((j) => j.progress.percent !== undefined);
        win.setProgressBar(active.length ? (known.length ? known.reduce((a, j) => a + j.progress.percent!, 0) / known.length / 100 : 2) : -1);
      }
    },
    onFinished: (job) => {
      const s = settingsStore.get();
      if (!s.notifyOnFinish || !Notification.isSupported() || win?.isFocused()) return;
      if (job.state === 'done') new Notification({ title: 'Download finished', body: job.title, silent: true }).show();
      if (job.state === 'error') new Notification({ title: job.error?.title ?? 'Download failed', body: job.title, silent: true }).show();
    },
  });
  logs.prune(settingsStore.get().logRetentionDays);

  // ---- app updates ----------------------------------------------------------
  let appUpdate: AppUpdateStatus = { state: dev ? 'unsupported' : 'idle', message: dev ? 'Updates are checked in installed copies of the app, not when running from source.' : undefined };
  const setAppUpdate = (s: AppUpdateStatus) => { appUpdate = s; send('app-update', s); };
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  let updater: any = null;
  if (!dev) {
    try {
      // eslint-disable-next-line @typescript-eslint/no-require-imports
      updater = require('electron-updater').autoUpdater;
      updater.autoDownload = false;
      updater.autoInstallOnAppQuit = true;
      updater.logger = { info: (m: string) => logs.app('info', `updater: ${m}`), warn: (m: string) => logs.app('warn', `updater: ${m}`), error: (m: string) => logs.app('error', `updater: ${m}`), debug: () => {} };
      updater.on('checking-for-update', () => setAppUpdate({ state: 'checking' }));
      updater.on('update-available', (i: { version: string }) => { setAppUpdate({ state: 'available', version: i.version }); if (settingsStore.get().autoUpdateApp) void updater.downloadUpdate(); });
      updater.on('update-not-available', () => setAppUpdate({ state: 'current', version: app.getVersion() }));
      updater.on('download-progress', (p: { percent: number }) => setAppUpdate({ ...appUpdate, state: 'downloading', percent: Math.round(p.percent) }));
      updater.on('update-downloaded', (i: { version: string }) => setAppUpdate({ state: 'ready', version: i.version }));
      updater.on('error', (e: Error) => setAppUpdate({ state: 'error', message: /ENOTFOUND|ERR_INTERNET|ERR_NAME|net::/i.test(e.message) ? 'Could not reach the update server.' : /404|latest.*yml|No published versions/i.test(e.message) ? 'No app release has been published yet.' : 'The update check failed. Details are in the app log.' }));
    } catch (e) {
      appUpdate = { state: 'unsupported', message: 'This copy of the app cannot update itself. Download the new version from the releases page.' };
      logs.app('warn', `updater unavailable: ${(e as Error).message}`);
    }
  }

  // ---- the window's API -----------------------------------------------------
  const handlers: Omit<Api, 'platform' | 'on'> = {
    getSettings: async () => settingsStore.get(),
    setSettings: async (patch) => {
      const next = { ...settingsStore.get(), ...patch };
      settingsStore.set(next);
      if (patch.theme) nativeTheme.themeSource = patch.theme;
      return next;
    },
    listPresets: async () => presetStore.get(),
    savePreset: async (p) => {
      const list = presetStore.get().filter((x) => x.id !== p.id || x.builtin);
      presetStore.set(mergePresets([...list, { ...p, builtin: false }]));
      return presetStore.get();
    },
    removePreset: async (id) => {
      presetStore.set(presetStore.get().filter((p) => p.id !== id || p.builtin));
      return presetStore.get();
    },
    probe: (url, values) => prober.probe(url, values),
    cancelProbe: async (url) => prober.cancel(url),
    listJobs: async () => jobs.list(),
    addJobs: async (specs) => jobs.add(specs),
    jobAction: async (ids, action) => jobs.action(ids, action),
    updateJob: async (id, patch, retry) => jobs.update(id, patch, retry),
    applyFix: (id, fix) => jobs.applyFix(id, fix),
    clearFinished: async () => jobs.clearFinished(),
    listHistory: async () => jobs.history(),
    removeHistory: async (ids) => jobs.removeHistory(ids),
    clearHistory: async () => jobs.clearHistory(),
    jobLog: async (id) => logs.readJob(id),
    jobOutput: async (id) => jobs.output(id),
    jobReport: (id) => jobs.report(id),
    jobCommand: async (id, internal) => jobs.command(id, internal),
    listLogs: async () => logs.list(),
    readLog: async (file) => logs.read(file),
    openLogsFolder: async () => { await shell.openPath(paths.logs); },
    engineInfo: () => engine.info(),
    engineCheck: async () => {
      const s = settingsStore.get();
      send('engine-update', { state: 'checking' });
      const r = await engine.checkUpdate(s.engineChannel, s.engineCustomSource);
      send('engine-update', r);
      return r;
    },
    engineUpdate: async () => {
      const s = settingsStore.get();
      const r = await engine.update(s.engineChannel, s.engineCustomSource, (st) => send('engine-update', st), true);
      logs.app(r.state === 'error' ? 'warn' : 'info', `engine update: ${r.state} ${r.message ?? r.current ?? ''}`);
      send('engine-update', r);
      return r;
    },
    engineRevert: async () => { await engine.revert(); return engine.info(); },
    engineTool: async (args) => {
      const r = await engine.run(args.map(String), { timeoutMs: 300_000 });
      return { code: r.code, output: [r.stdout, r.stderr].filter((x) => x.trim()).join('\n') };
    },
    installFfmpeg: async () => {
      const r = await engine.installFfmpeg((p) => send('ffmpeg-progress', p));
      logs.app(r.ok ? 'info' : 'warn', `ffmpeg install: ${r.ok ? 'ok' : r.message}`);
      return r;
    },
    appVersion: async () => app.getVersion(),
    appUpdateCheck: async () => {
      if (!updater) return appUpdate;
      try { await updater.checkForUpdates(); } catch { /* reported through the error event */ }
      return appUpdate;
    },
    appUpdateInstall: async () => {
      if (!updater) return;
      if (appUpdate.state === 'ready') { jobs.shutdown(); updater.quitAndInstall(); } else if (appUpdate.state === 'available') void updater.downloadUpdate();
    },
    pickFolder: async (current) => {
      const r = await dialog.showOpenDialog(win!, { properties: ['openDirectory', 'createDirectory'], defaultPath: current || settingsStore.get().downloadFolder });
      return r.canceled ? null : r.filePaths[0];
    },
    pickFile: async (opts) => {
      const r = await dialog.showOpenDialog(win!, { properties: ['openFile'], title: opts?.title, filters: opts?.filters });
      return r.canceled ? null : r.filePaths[0];
    },
    saveText: async (defaultName, text) => {
      const r = await dialog.showSaveDialog(win!, { defaultPath: path.join(app.getPath('documents'), defaultName) });
      if (r.canceled || !r.filePath) return null;
      writeFileSync(r.filePath, text);
      return r.filePath;
    },
    importConfig: async () => {
      const r = await dialog.showOpenDialog(win!, { title: 'Import a yt-dlp config file', properties: ['openFile', 'showHiddenFiles'], filters: [{ name: 'Config files', extensions: ['conf', 'txt', 'config'] }, { name: 'All files', extensions: ['*'] }] });
      if (r.canceled) return null;
      return { path: r.filePaths[0], parsed: parseConfigText(readFileSync(r.filePaths[0], 'utf8')) };
    },
    showItem: async (p) => { if (existsSync(p)) shell.showItemInFolder(p); else await shell.openPath(path.dirname(p)); },
    openPath: (p) => shell.openPath(p),
    openExternal: async (url) => { if (/^(https?:|mailto:)/i.test(url)) await shell.openExternal(url); },
    copyText: async (text) => clipboard.writeText(text),
    readClipboard: async () => clipboard.readText(),
    popupMenu: (items: MenuItemSpec[]) => new Promise<string | null>((resolve) => {
      let picked: string | null = null;
      const menu = Menu.buildFromTemplate(items.map((i) => i.type === 'separator'
        ? { type: 'separator' as const }
        : { label: i.label, enabled: i.enabled !== false, type: i.checked !== undefined ? 'checkbox' as const : 'normal' as const, checked: i.checked, click: () => { picked = i.id ?? null; } }));
      menu.popup({ window: win!, callback: () => setImmediate(() => resolve(picked)) });
    }),
  };

  ipcMain.handle('api', async (event, method: keyof typeof handlers, ...args: unknown[]) => {
    if (!win || event.sender !== win.webContents) throw new Error('unknown sender');
    const fn = handlers[method] as ((...a: unknown[]) => unknown) | undefined;
    if (typeof fn !== 'function') throw new Error(`unknown method ${String(method)}`);
    try {
      return await fn(...args);
    } catch (e) {
      logs.app('error', `${String(method)} failed: ${e instanceof Error ? e.stack : String(e)}`);
      throw e;
    }
  });

  // ---- window ---------------------------------------------------------------
  const createWindow = () => {
    const state = windowStore.get();
    const dark = nativeTheme.shouldUseDarkColors;
    win = new BrowserWindow({
      width: state.width, height: state.height, x: state.x, y: state.y, minWidth: 900, minHeight: 560,
      show: false, backgroundColor: dark ? '#1c1b19' : '#f3f1ec', title: 'Dubdeck',
      titleBarStyle: process.platform === 'darwin' ? 'hiddenInset' : 'default',
      icon: process.platform === 'linux' ? path.join(appRoot, 'assets', 'icon.png') : undefined,
      webPreferences: { preload: path.join(appRoot, 'dist', 'preload', 'preload.js'), contextIsolation: true, nodeIntegration: false, sandbox: true, spellcheck: false },
    });
    if (state.maximized) win.maximize();
    win.once('ready-to-show', () => win?.show());
    win.webContents.setWindowOpenHandler(({ url }) => { void handlers.openExternal(url); return { action: 'deny' }; });
    win.webContents.on('will-navigate', (e, url) => { if (url !== win?.webContents.getURL()) { e.preventDefault(); void handlers.openExternal(url); } });
    const save = () => {
      if (!win || win.isDestroyed()) return;
      const b = win.getNormalBounds();
      windowStore.set({ width: b.width, height: b.height, x: b.x, y: b.y, maximized: win.isMaximized() });
    };
    win.on('resize', save);
    win.on('move', save);
    win.on('close', (e) => {
      if (quitting || process.platform === 'darwin' || !jobs.activeCount()) return;
      e.preventDefault();
      confirmQuit();
    });
    win.on('closed', () => { win = null; });
    void win.loadFile(path.join(appRoot, 'dist', 'renderer', 'index.html'));
  };

  let quitting = false;
  const confirmQuit = () => {
    const n = jobs.activeCount();
    if (n && win) {
      const choice = dialog.showMessageBoxSync(win, {
        type: 'question', buttons: ['Quit', 'Keep Downloading'], defaultId: 1, cancelId: 1,
        message: n === 1 ? 'A download is still running.' : `${n} downloads are still running.`,
        detail: 'If you quit now they stop, and pick up where they left off the next time you open Dubdeck.',
      });
      if (choice === 1) return;
    }
    quitting = true;
    app.quit();
  };
  app.on('before-quit', (e) => {
    if (!quitting && jobs.activeCount()) { e.preventDefault(); confirmQuit(); return; }
    quitting = true;
    jobs.shutdown();
    settingsStore.flush(); presetStore.flush(); windowStore.flush();
  });

  Menu.setApplicationMenu(buildMenu(() => win, dev));
  app.setAboutPanelOptions({
    applicationName: 'Dubdeck', applicationVersion: app.getVersion(),
    copyright: 'A desktop app for yt-dlp. Released into the public domain (Unlicense).',
    website: 'https://github.com/Nardi05/yt-dlp',
  });
  createWindow();

  const linksFrom = (argv: string[]) => argv.filter((a) => /^https?:\/\//i.test(a));
  app.on('second-instance', (_e, argv) => {
    if (!win) return;
    if (win.isMinimized()) win.restore();
    win.focus();
    const links = linksFrom(argv);
    if (links.length) send('command', 'add-links', links.join('\n'));
  });
  app.on('activate', () => { if (!win) createWindow(); });
  app.on('window-all-closed', () => { if (process.platform !== 'darwin') app.quit(); });

  win!.webContents.once('did-finish-load', () => {
    const links = linksFrom(process.argv.slice(1));
    if (links.length) send('command', 'add-links', links.join('\n'));
    const s = settingsStore.get();
    if (updater && s.autoUpdateApp) setTimeout(() => { void handlers.appUpdateCheck(); }, 8000);
    if (s.autoCheckEngine) setTimeout(() => { void handlers.engineCheck(); }, 3000);
  });
}
