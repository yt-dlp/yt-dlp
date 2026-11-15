import { useEffect, useMemo, useRef, useState } from 'preact/hooks';
import { formatBytes } from '../../shared/output';
import type { LogFile } from '../../shared/types';
import { api, set, toast, useStore } from '../state';
import { Btn, Empty, Search, when } from '../ui';

export function LogsView({ searchRef }: { searchRef: { current: HTMLInputElement | null } }) {
  const s = useStore();
  const [files, setFiles] = useState<LogFile[]>([]);
  const [sel, setSel] = useState<string>('');
  const [text, setText] = useState('');
  const [query, setQuery] = useState('');
  const [only, setOnly] = useState(false);
  const view = useRef<HTMLDivElement>(null);

  const titles = useMemo(() => {
    const m = new Map<string, string>();
    for (const j of [...s.history, ...s.jobs]) m.set(`${j.id}.log`, j.title);
    return m;
  }, [s.history, s.jobs]);

  const refresh = async () => {
    const list = await api.listLogs();
    setFiles(list);
    return list;
  };
  useEffect(() => {
    void api.listHistory().then((history) => set({ history }));
    void refresh().then((list) => {
      const target = s.logTarget ? list.find((f) => f.name === `${s.logTarget}.log`) : undefined;
      setSel((target ?? list.find((f) => f.kind === 'app') ?? list[0])?.path ?? '');
      if (s.logTarget) set({ logTarget: null });
    });
  }, [s.logTarget]);
  useEffect(() => {
    if (!sel) { setText(''); return; }
    let live = true;
    const load = () => api.readLog(sel).then((t) => { if (live) setText(t); });
    void load();
    const timer = setInterval(load, 2500);
    return () => { live = false; clearInterval(timer); };
  }, [sel]);
  useEffect(() => { if (view.current) view.current.scrollTop = view.current.scrollHeight; }, [sel, text.length > 0]);

  const q = query.trim().toLowerCase();
  const lines = text.split('\n');
  const shown = q && only ? lines.filter((l) => l.toLowerCase().includes(q)) : lines;
  const hits = q ? lines.filter((l) => l.toLowerCase().includes(q)).length : 0;
  const current = files.find((f) => f.path === sel);

  return (
    <div class="main">
      <div class="bar">
        <h1>Logs</h1>
        <div class="grow" />
        <Search value={query} onChange={setQuery} placeholder="Find in this log" inputRef={searchRef} />
        {q ? <label class="check small"><input type="checkbox" checked={only} onChange={(e) => setOnly((e.target as HTMLInputElement).checked)} /><span>Only matching lines ({hits})</span></label> : null}
        <div class="sep" />
        <Btn kind="quiet" icon="copy" disabled={!text} onClick={() => { void api.copyText(text); toast('Log copied.'); }}>Copy</Btn>
        <Btn kind="quiet" icon="folder-open" onClick={() => api.openLogsFolder()}>Open folder</Btn>
      </div>
      {!files.length ? <Empty title="No logs yet"><p>The app keeps a log of what it does, and one log for each download. They are stored on this computer only.</p></Empty> : (
        <div class="split">
          <div class="listcol" role="listbox" aria-label="Log files">
            {files.map((f) => (
              <button type="button" class="item" role="option" aria-selected={f.path === sel} onClick={() => setSel(f.path)}>
                <span class="ellipsis" style={{ fontWeight: 500 }}>{f.kind === 'app' ? (f.name === 'app.log' ? 'Application' : 'Application (older)') : titles.get(f.name) ?? f.name}</span>
                <span class="s">{when(f.modified)} · {formatBytes(f.size)}</span>
              </button>
            ))}
          </div>
          <div class="col">
            <div class="logview" ref={view} tabIndex={0} aria-label={current ? `Contents of ${current.name}` : 'Log'}>
              <pre class="pre">
                {shown.map((l) => <span class={`log-line${q && !only && l.toLowerCase().includes(q) ? ' hit' : ''} ${/ERROR|error:/.test(l) ? 'err' : /WARN/.test(l) ? 'wrn' : ''}`}>{l}{'\n'}</span>)}
              </pre>
            </div>
            <div class="status"><span class="mono ellipsis selectable">{current?.path}</span><div class="grow" /><span class="faint">Passwords and your user name are removed before writing.</span></div>
          </div>
        </div>
      )}
    </div>
  );
}
