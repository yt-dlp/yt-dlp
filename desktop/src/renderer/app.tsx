import { render } from 'preact';
import { useEffect, useRef, useState } from 'preact/hooks';
import './styles.css';
import { api, get, go, parseLinks, saveSettings, set, startNew, toast, useStore, type View } from './state';
import { Dialog, Icon } from './ui';
import type { IconName } from './icons.generated';
import { EngineView } from './views/Engine';
import { HelpView, Welcome } from './views/Help';
import { HistoryView } from './views/History';
import { LogsView } from './views/Logs';
import { NewView } from './views/New';
import { importConfigAsPreset, PresetsView } from './views/Presets';
import { QueueView } from './views/Queue';
import { SettingsView } from './views/Settings';

const NAV: [View, string, IconName][] = [
  ['queue', 'Downloads', 'download'], ['history', 'History', 'history'], ['presets', 'Presets', 'bookmark'], ['logs', 'Logs', 'file-text'], ['engine', 'Engine', 'engine'],
];

function Mark() {
  return (
    <svg viewBox="0 0 64 64" aria-hidden="true">
      <rect x="2" y="2" width="60" height="60" rx="13" fill="var(--ink)" />
      <rect x="13" y="14" width="8" height="36" rx="2" fill="var(--paper)" />
      <circle cx="37" cy="32" r="14" fill="none" stroke="var(--paper)" stroke-width="8" />
      <circle cx="37" cy="32" r="4" fill="var(--accent)" />
    </svg>
  );
}

function isEditable(el: EventTarget | null): boolean {
  const e = el as HTMLElement | null;
  return !!e && (e.tagName === 'INPUT' || e.tagName === 'TEXTAREA' || e.tagName === 'SELECT' || e.isContentEditable);
}

function App() {
  const s = useStore();
  const [dragging, setDragging] = useState(false);
  const searchRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    void (async () => {
      const [settings, presets, jobs, appVersion] = await Promise.all([api.getSettings(), api.listPresets(), api.listJobs(), api.appVersion()]);
      set({ settings, presets, jobs, appVersion, ready: true, welcome: !settings.welcomed, draft: { ...get().draft, simple: { ...get().draft.simple, ...settings.simple, folder: settings.downloadFolder } } });
      set({ engine: await api.engineInfo() });
    })();
    const offs = [
      api.on('jobs', (jobs) => set({ jobs })),
      api.on('engine-update', (engineUpdate) => set({ engineUpdate })),
      api.on('app-update', (appUpdate) => set({ appUpdate })),
      api.on('command', (cmd, arg) => {
        const jobs = get().jobs;
        if (cmd.startsWith('view:')) go(cmd.slice(5) as View);
        else if (cmd === 'new') startNew();
        else if (cmd === 'paste') void api.readClipboard().then((t) => startNew(t.trim()));
        else if (cmd === 'add-links' && arg) startNew(arg);
        else if (cmd === 'import-config') void importConfigAsPreset();
        else if (cmd === 'open-folder') void api.openPath(get().settings.downloadFolder);
        else if (cmd === 'pause-all') void api.jobAction(jobs.filter((j) => j.state === 'running' || j.state === 'queued').map((j) => j.id), 'pause');
        else if (cmd === 'resume-all') void api.jobAction(jobs.filter((j) => j.state === 'paused').map((j) => j.id), 'resume');
        else if (cmd === 'retry-failed') void api.jobAction(jobs.filter((j) => j.state === 'error').map((j) => j.id), 'retry');
        else if (cmd === 'clear-finished') void api.clearFinished();
        else if (cmd === 'welcome') set({ welcome: true });
        else if (cmd === 'find') searchRef.current?.focus();
        else if (cmd === 'check-updates') { go('settings'); void api.appUpdateCheck(); void api.engineCheck(); }
      }),
    ];
    const onPaste = (e: ClipboardEvent) => {
      if (isEditable(e.target) || get().dialog) return;
      const text = e.clipboardData?.getData('text/plain')?.trim();
      if (text && parseLinks(text).links.length) { e.preventDefault(); startNew(text); }
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && get().view === 'new' && !get().dialog && !isEditable(e.target)) go('queue');
    };
    window.addEventListener('paste', onPaste);
    window.addEventListener('keydown', onKey);
    return () => { offs.forEach((o) => o()); window.removeEventListener('paste', onPaste); window.removeEventListener('keydown', onKey); };
  }, []);

  const onDrop = (e: DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const dt = e.dataTransfer;
    if (!dt) return;
    const text = dt.getData('text/uri-list') || dt.getData('text/plain');
    const fromFiles = Array.from(dt.files ?? []).map((f) => api.pathForFile?.(f) ?? '').filter(Boolean);
    if (text.trim()) {
      const { links } = parseLinks(text.split('\n').filter((l) => !l.startsWith('#')).join('\n'));
      if (links.length) startNew(links.join('\n')); else toast('That does not look like a link.');
    } else if (fromFiles.length) {
      toast('To read links from a file, set “Read links from file” under Files and naming in the advanced options.');
    }
  };

  if (!s.ready) return <div class="shell"><aside class="sidebar" /><div class="main" /></div>;
  const active = s.jobs.filter((j) => ['running', 'queued', 'paused', 'scheduled'].includes(j.state)).length;
  const eu = s.engineUpdate;
  const view = s.view;

  return (
    <div class={`shell${api.platform === 'darwin' ? ' mac' : ''}`}
      onDragOver={(e) => { if (e.dataTransfer?.types.some((t) => t === 'text/uri-list' || t === 'text/plain' || t === 'Files')) { e.preventDefault(); setDragging(true); } }}
      onDragLeave={(e) => { if (!e.relatedTarget) setDragging(false); }} onDrop={onDrop}>
      <aside class="sidebar">
        <div class="brand"><Mark />Dubdeck</div>
        <nav class="col" style={{ gap: 2 }} aria-label="Main">
          {NAV.map(([id, label, icon]) => (
            <button type="button" class="nav" aria-current={view === id || (id === 'queue' && view === 'new') ? 'page' : undefined} onClick={() => go(id)}>
              <Icon name={icon} />{label}{id === 'queue' && active ? <span class="count" aria-label={`${active} active`}>{active}</span> : null}
            </button>
          ))}
          <div class="side-gap" />
          <button type="button" class="nav" aria-current={view === 'settings' ? 'page' : undefined} onClick={() => go('settings')}><Icon name="settings" />Settings</button>
          <button type="button" class="nav" aria-current={view === 'help' ? 'page' : undefined} onClick={() => go('help')}><Icon name="lifebuoy" />Help</button>
        </nav>
        <div class="side-foot">
          <button type="button" onClick={() => go('engine')} title="Open the Engine screen">
            Engine {s.engine?.version || (s.engine ? 'missing' : '…')}<br />
            {eu.state === 'available' ? <span class="flag">{eu.latest ? `Update available: ${eu.latest}` : 'Engine update available'}</span>
              : s.engine && !s.engine.ffmpeg.version ? <span class="flag">ffmpeg is missing</span>
              : s.engine?.source === 'missing' ? <span class="flag">Engine is missing</span>
              : eu.state === 'downloading' ? `Updating… ${eu.percent ?? 0}%` : eu.state === 'current' ? 'Up to date' : `Dubdeck ${s.appVersion}`}
          </button>
        </div>
      </aside>
      {view === 'queue' ? <QueueView searchRef={searchRef} /> : view === 'new' ? <NewView /> : view === 'history' ? <HistoryView searchRef={searchRef} />
        : view === 'presets' ? <PresetsView /> : view === 'logs' ? <LogsView searchRef={searchRef} /> : view === 'engine' ? <EngineView />
        : view === 'settings' ? <SettingsView /> : <HelpView />}
      {dragging ? <div class="drop-hint">Drop to add the link</div> : null}
      <Dialog />
      {s.welcome ? <Welcome onClose={() => { set({ welcome: false }); void saveSettings({ welcomed: true }); }} /> : null}
      <div class="toasts" role="status" aria-live="polite">
        {s.toasts.map((t) => <div class="toast" key={t.id}>{t.text}{t.action ? <button onClick={t.action.run}>{t.action.label}</button> : null}</div>)}
      </div>
    </div>
  );
}

render(<App />, document.getElementById('app')!);
