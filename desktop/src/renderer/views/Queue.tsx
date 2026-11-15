import { useEffect, useMemo, useRef, useState } from 'preact/hooks';
import { fixLabels, stageLabels, type Stage } from '../../shared/errors';
import { formatBytes, formatDuration } from '../../shared/output';
import type { Job } from '../../shared/types';
import { copyReport, editJob, jobMenu, runFix } from '../actions';
import { api, get, set, startNew, toast, useStore } from '../state';
import { Btn, Empty, Icon, Search, Seg, Tabs, Thumb, when } from '../ui';

type Filter = 'all' | 'active' | 'done' | 'failed';
const STAGES: Stage[] = ['info', 'format', 'download', 'merge', 'post', 'write'];

function statusText(j: Job): string {
  switch (j.state) {
    case 'queued': return 'Waiting for a free slot';
    case 'scheduled': return j.note ?? `Starts ${when(j.scheduledFor).toLowerCase()}`;
    case 'paused': return 'Paused';
    case 'cancelled': return 'Cancelled';
    case 'error': return j.error?.title ?? 'Failed';
    case 'done': return j.note ?? (j.printOnly ? 'Output ready' : j.files.length > 1 ? `${j.files.length} files saved` : 'Saved');
    case 'running': {
      const item = j.item ? `Item ${j.item.index} of ${j.item.count}` : '';
      const label = j.stage === 'download' ? '' : (j.stageLabel ?? stageLabels[j.stage]);
      return [item, label].filter(Boolean).join(' · ') || 'Downloading';
    }
  }
}

function Row({ job, selected, onSelect }: { job: Job; selected: boolean; onSelect: (e: MouseEvent | KeyboardEvent) => void }) {
  const p = job.progress;
  const running = job.state === 'running';
  const pct = p.percent;
  const meterClass = job.state === 'done' ? 'done' : running && (pct === undefined || job.stage !== 'download') ? 'busy' : running ? '' : 'idle';
  const audio = job.values['--extract-audio'] !== undefined;
  return (
    <div class="tr queue-cols" role="row" tabIndex={0} aria-selected={selected} data-id={job.id} onClick={onSelect}
      onContextMenu={(e) => { e.preventDefault(); onSelect(e); void jobMenu(job); }}
      onDblClick={() => { if (job.files[0]) void api.openPath(job.files[0]); }}>
      <Thumb src={job.thumbnail} audio={audio} />
      <div class="title2" role="gridcell">
        <span class="t ellipsis">{job.item?.title && running ? job.item.title : job.title}</span>
        <span class="s ellipsis">{[job.item?.title && running ? job.title : job.uploader, job.summary].filter(Boolean).join(' · ')}</span>
      </div>
      <div class="prog" role="gridcell">
        <div class="line">
          <span class={`ellipsis ${job.state === 'error' ? 'state-error' : job.state === 'done' ? 'state-done' : ''}`}>{statusText(job)}</span>
          {running && pct !== undefined && job.stage === 'download' ? <span class="num">{pct.toFixed(pct >= 99.95 ? 0 : 1)}%</span> : null}
        </div>
        {job.state === 'error' || job.state === 'cancelled' ? null : (
          <div class={`meter ${meterClass}`} role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={pct !== undefined ? Math.round(pct) : undefined} aria-label="Progress">
            <i style={{ width: `${job.state === 'done' ? 100 : pct ?? 0}%` }} />
          </div>
        )}
      </div>
      <span class="num right" role="gridcell">{p.total ? `${p.estimated ? '~' : ''}${formatBytes(p.total)}` : p.downloaded ? formatBytes(p.downloaded) : ''}</span>
      <span class="num right" role="gridcell">{running && p.speed ? `${formatBytes(p.speed)}/s` : ''}</span>
      <span class="num right" role="gridcell">{running && p.eta !== undefined ? formatDuration(p.eta) : ''}</span>
      <div class="acts">
        {running || job.state === 'queued' ? <Btn small kind="quiet" icon="player-pause" label="Pause" onClick={(e) => { e.stopPropagation(); void api.jobAction([job.id], 'pause'); }} /> : null}
        {job.state === 'paused' || job.state === 'scheduled' ? <Btn small kind="quiet" icon="player-play" label={job.state === 'scheduled' ? 'Start now' : 'Resume'} onClick={(e) => { e.stopPropagation(); void api.jobAction([job.id], 'resume'); }} /> : null}
        {job.state === 'error' || job.state === 'cancelled' ? <Btn small kind="quiet" icon="refresh" label="Retry" onClick={(e) => { e.stopPropagation(); void api.jobAction([job.id], 'retry'); }} /> : null}
        {job.state === 'done' && job.files[0] ? <Btn small kind="quiet" icon="folder-open" label="Show in folder" onClick={(e) => { e.stopPropagation(); void api.showItem(job.files[0]); }} /> : null}
        {['running', 'queued', 'paused', 'scheduled'].includes(job.state)
          ? <Btn small kind="quiet" icon="x" label="Cancel" onClick={(e) => { e.stopPropagation(); void api.jobAction([job.id], 'cancel'); }} />
          : <Btn small kind="quiet" icon="trash" label="Remove from list" onClick={(e) => { e.stopPropagation(); void api.jobAction([job.id], 'remove'); }} />}
      </div>
    </div>
  );
}

export function LogText({ text }: { text: string }) {
  return (
    <pre class="pre">
      {text.split('\n').map((l) => <span class={/^ERROR|error:/.test(l) ? 'err' : /^WARNING/.test(l) ? 'wrn' : ''}>{l}{'\n'}</span>)}
    </pre>
  );
}

export function Detail({ job, onClose }: { job: Job; onClose?: () => void }) {
  type Tab = 'summary' | 'output' | 'log' | 'command';
  const [tab, setTab] = useState<Tab>('summary');
  const [text, setText] = useState('');
  const [details, setDetails] = useState(false);
  const [internal, setInternal] = useState(false);
  const [busyFix, setBusyFix] = useState('');
  const body = useRef<HTMLDivElement>(null);

  useEffect(() => { setTab(job.printOnly && job.state === 'done' ? 'output' : 'summary'); setDetails(false); }, [job.id]);
  useEffect(() => { if (job.printOnly && job.state === 'done' && tab === 'summary') setTab('output'); }, [job.state]);
  useEffect(() => {
    let live = true;
    const load = async () => {
      const t = tab === 'log' || (tab === 'summary' && details) ? await api.jobLog(job.id) : tab === 'output' ? await api.jobOutput(job.id) : tab === 'command' ? await api.jobCommand(job.id, internal) : '';
      if (!live) return;
      const el = body.current;
      const atEnd = !el || el.scrollHeight - el.scrollTop - el.clientHeight < 40;
      setText(t);
      if (tab === 'log' && atEnd) requestAnimationFrame(() => { if (body.current) body.current.scrollTop = body.current.scrollHeight; });
    };
    void load();
    const timer = job.state === 'running' && (tab === 'log' || tab === 'output') ? setInterval(load, 1000) : null;
    return () => { live = false; if (timer) clearInterval(timer); };
  }, [job.id, tab, details, internal, job.state, job.attempts]);

  const err = job.error;
  const stageNow = err?.stage ?? job.stage;
  const idx = STAGES.indexOf(stageNow);
  const fix = async (f: string) => { setBusyFix(f); try { await runFix(job, f as never); } finally { setBusyFix(''); } };

  return (
    <section class="detail" aria-label={`Details for ${job.title}`}>
      <Tabs value={tab} onChange={setTab} options={[['summary', err ? 'Problem' : 'Summary'], ['output', 'Output'], ['log', 'Log'], ['command', 'Command']] as const}>
        <div class="grow" />
        {tab === 'log' || tab === 'output' || tab === 'command' ? <Btn small kind="quiet" icon="copy" onClick={() => { void api.copyText(text); toast('Copied.'); }}>Copy</Btn> : null}
        {tab === 'output' && text ? <Btn small kind="quiet" icon="file-export" onClick={() => void api.saveText(`${job.title.slice(0, 40) || 'output'}.txt`, text)}>Save</Btn> : null}
        {onClose ? <Btn small kind="quiet" icon="x" label="Close details" onClick={onClose} /> : null}
      </Tabs>
      <div class="body" ref={body}>
        {tab === 'summary' && err ? (
          <div class="problem">
            <div>
              <h2><Icon name="alert-triangle" /> {err.title}</h2>
              <p>{err.what} {err.why}</p>
              <ul>{err.tryThis.map((t) => <li>{t}</li>)}</ul>
              {job.note ? <p class="small faint">{job.note}</p> : null}
              <div class="fixes">
                {err.fixes.map((f, i) => <Btn kind={i === 0 ? 'primary' : undefined} busy={busyFix === f} disabled={!!busyFix && busyFix !== f} onClick={() => fix(f)}>{fixLabels[f]}</Btn>)}
                <Btn kind="quiet" icon={details ? 'chevron-down' : 'chevron-right'} onClick={() => setDetails(!details)}>{details ? 'Hide details' : 'Show details'}</Btn>
                <Btn kind="quiet" icon="copy" onClick={() => copyReport(job)}>Copy report</Btn>
              </div>
              {details ? (
                <div style={{ marginTop: 12 }}>
                  <h3>What the engine said</h3>
                  <pre class="pre" style={{ margin: '4px 0 12px' }}><span class="err">{err.raw}</span></pre>
                  <h3>Full log</h3>
                  <div style={{ marginTop: 4 }}><LogText text={text} /></div>
                </div>
              ) : null}
            </div>
            <div>
              <h3 style={{ marginBottom: 6 }}>Where it stopped</h3>
              <ol class="stages">
                {STAGES.map((st, i) => <li class={st === stageNow ? 'failed' : idx === -1 || i < idx ? 'past' : ''}>{stageLabels[st]}{st === stageNow ? ' (failed here)' : ''}</li>)}
              </ol>
              {stageNow === 'starting' ? <p class="small state-error" style={{ marginTop: 6 }}>Failed before the download began.</p> : null}
            </div>
          </div>
        ) : null}
        {tab === 'summary' && !err ? (
          <div class="problem">
            <div class="col" style={{ gap: 12 }}>
              <dl class="kv">
                <dt>Link</dt><dd>{job.url || <span class="faint">From a file</span>}</dd>
                <dt>Options</dt><dd>{job.summary}</dd>
                {job.uploader ? <><dt>By</dt><dd>{job.uploader}</dd></> : null}
                {job.duration ? <><dt>Length</dt><dd>{formatDuration(job.duration)}</dd></> : null}
                <dt>Added</dt><dd>{when(job.createdAt)}</dd>
                {job.finishedAt ? <><dt>Finished</dt><dd>{when(job.finishedAt)}{job.startedAt ? `, took ${formatDuration((job.finishedAt - job.startedAt) / 1000)}` : ''}</dd></> : null}
                {job.note ? <><dt>Note</dt><dd>{job.note}</dd></> : null}
              </dl>
              {job.files.length ? (
                <div>
                  <h3 style={{ marginBottom: 4 }}>{job.files.length === 1 ? 'File' : `${job.files.length} files`}</h3>
                  <div class="files">
                    {job.files.slice(0, 50).map((f) => (
                      <div class="file">
                        <span class="mono grow ellipsis selectable" title={f}>{f}</span>
                        <Btn small onClick={async () => { if (await api.openPath(f)) toast('The file is no longer where it was saved.'); }}>Open</Btn>
                        <Btn small icon="folder-open" label="Show in folder" onClick={() => api.showItem(f)} />
                      </div>
                    ))}
                  </div>
                </div>
              ) : null}
              {job.warnings.length ? (
                <div>
                  <h3 style={{ marginBottom: 4 }}>{job.warnings.length === 1 ? 'One warning' : `${job.warnings.length} warnings`}</h3>
                  <pre class="pre">{job.warnings.map((w) => <span class="wrn">{w}{'\n'}</span>)}</pre>
                </div>
              ) : null}
              {!['running', 'done'].includes(job.state) ? <div><Btn icon="pencil" onClick={() => editJob(job)}>Edit options</Btn></div> : null}
            </div>
            <div>
              <h3 style={{ marginBottom: 6 }}>Progress</h3>
              <ol class="stages">
                {STAGES.map((st, i) => <li class={job.state === 'done' ? 'past' : st === job.stage && job.state === 'running' ? 'now' : idx > i ? 'past' : ''}>{stageLabels[st]}</li>)}
              </ol>
            </div>
          </div>
        ) : null}
        {tab === 'output' ? (text ? <pre class="pre">{text}</pre> : <p class="dim">Nothing was printed. Output appears here when you use options such as Print fields, Print JSON or List formats.</p>) : null}
        {tab === 'log' ? (text ? <LogText text={text} /> : <p class="dim">The log is empty until the download starts.</p>) : null}
        {tab === 'command' ? (
          <div class="col" style={{ gap: 8 }}>
            <pre class="pre">{text}</pre>
            <label class="check small"><input type="checkbox" checked={internal} onChange={(e) => setInternal((e.target as HTMLInputElement).checked)} /><span>Also show the flags the app adds to follow progress</span></label>
          </div>
        ) : null}
      </div>
    </section>
  );
}

export function QueueView({ searchRef }: { searchRef: { current: HTMLInputElement | null } }) {
  const s = useStore();
  const [filter, setFilter] = useState<Filter>('all');
  const [query, setQuery] = useState('');
  const jobs = s.jobs;
  const counts = useMemo(() => ({
    all: jobs.length,
    active: jobs.filter((j) => ['running', 'queued', 'paused', 'scheduled'].includes(j.state)).length,
    done: jobs.filter((j) => j.state === 'done').length,
    failed: jobs.filter((j) => j.state === 'error' || j.state === 'cancelled').length,
  }), [jobs]);
  const q = query.trim().toLowerCase();
  const shown = jobs.filter((j) => (filter === 'all' || (filter === 'active' ? ['running', 'queued', 'paused', 'scheduled'].includes(j.state) : filter === 'done' ? j.state === 'done' : j.state === 'error' || j.state === 'cancelled'))
    && (!q || `${j.title} ${j.url} ${j.uploader ?? ''} ${j.summary}`.toLowerCase().includes(q))).slice().reverse();
  const selected = s.selected.filter((id) => jobs.some((j) => j.id === id));
  const focusJob = selected.length === 1 ? jobs.find((j) => j.id === selected[0]) : undefined;
  const running = jobs.filter((j) => j.state === 'running');
  const speed = running.reduce((a, j) => a + (j.progress.speed ?? 0), 0);

  const select = (job: Job, e: MouseEvent | KeyboardEvent) => {
    if (e.shiftKey && selected.length) {
      const a = shown.findIndex((j) => j.id === selected[selected.length - 1]);
      const b = shown.findIndex((j) => j.id === job.id);
      set({ selected: shown.slice(Math.min(a, b), Math.max(a, b) + 1).map((j) => j.id) });
    } else if (e.ctrlKey || e.metaKey) {
      set({ selected: selected.includes(job.id) ? selected.filter((x) => x !== job.id) : [...selected, job.id] });
    } else set({ selected: [job.id] });
  };

  const onKey = (e: KeyboardEvent) => {
    if ((e.target as HTMLElement).closest('input, textarea, select, .detail')) return;
    const i = shown.findIndex((j) => j.id === selected[selected.length - 1]);
    const focusRow = (id: string) => requestAnimationFrame(() => document.querySelector<HTMLElement>(`.tr[data-id="${id}"]`)?.focus());
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault();
      const next = shown[Math.max(0, Math.min(shown.length - 1, i + (e.key === 'ArrowDown' ? 1 : -1)))];
      if (next) { set({ selected: [next.id] }); focusRow(next.id); }
    } else if ((e.key === 'a' || e.key === 'A') && (e.ctrlKey || e.metaKey)) { e.preventDefault(); set({ selected: shown.map((j) => j.id) }); }
    else if (!selected.length) return;
    else if (e.key === 'Delete' || e.key === 'Backspace') {
      const sel = jobs.filter((j) => selected.includes(j.id));
      const live = sel.filter((j) => ['running', 'queued', 'paused', 'scheduled'].includes(j.state)).map((j) => j.id);
      void api.jobAction(live, 'cancel');
      void api.jobAction(sel.filter((j) => !live.includes(j.id)).map((j) => j.id), 'remove');
    } else if (e.key === ' ') {
      e.preventDefault();
      const sel = jobs.filter((j) => selected.includes(j.id));
      const toPause = sel.filter((j) => j.state === 'running' || j.state === 'queued').map((j) => j.id);
      if (toPause.length) void api.jobAction(toPause, 'pause'); else void api.jobAction(sel.map((j) => j.id), 'resume');
    } else if (e.key === 'Enter' && focusJob?.files[0]) void api.openPath(focusJob.files[0]);
    else if (e.key === 'Escape') set({ selected: [] });
  };

  return (
    <div class="main" onKeyDown={onKey}>
      <div class="bar">
        <Btn kind="primary" icon="plus" onClick={() => startNew()} title="Ctrl+N">New download</Btn>
        <div class="sep" />
        <Seg label="Show" value={filter} onChange={setFilter} options={[['all', `All ${counts.all}`], ['active', `Active ${counts.active}`], ['done', `Done ${counts.done}`], ['failed', `Failed ${counts.failed}`]] as const} />
        <div class="grow" />
        <Search value={query} onChange={setQuery} placeholder="Find in downloads" inputRef={searchRef} />
        <div class="sep" />
        <Btn kind="quiet" icon="player-pause" label="Pause all" disabled={!jobs.some((j) => j.state === 'running' || j.state === 'queued')} onClick={() => api.jobAction(jobs.filter((j) => j.state === 'running' || j.state === 'queued').map((j) => j.id), 'pause')} />
        <Btn kind="quiet" icon="player-play" label="Resume all" disabled={!jobs.some((j) => j.state === 'paused')} onClick={() => api.jobAction(jobs.filter((j) => j.state === 'paused').map((j) => j.id), 'resume')} />
        <Btn kind="quiet" icon="trash" label="Clear finished" disabled={!counts.done && !counts.failed} onClick={() => api.clearFinished()} />
      </div>
      {jobs.length === 0 ? (
        <Empty title="Nothing in the queue">
          <p>Paste a link to a video, playlist or channel and Dubdeck fetches it. You can also drop links onto this window.</p>
          <div class="row">
            <Btn kind="primary" icon="plus" onClick={() => startNew()}>New download</Btn>
            <Btn icon="clipboard" onClick={async () => { const t = (await api.readClipboard()).trim(); if (t) startNew(t); else toast('The clipboard is empty.'); }}>Paste from clipboard</Btn>
          </div>
        </Empty>
      ) : (
        <div class="table" role="grid" aria-label="Downloads" aria-rowcount={shown.length}>
          <div class="thead queue-cols" role="row">
            <span /><span role="columnheader">Name</span><span role="columnheader">Status</span><span class="right" role="columnheader">Size</span>
            <span class="right" role="columnheader">Speed</span><span class="right" role="columnheader">Time left</span><span />
          </div>
          <div class="scroll grow" onClick={(e) => { if (e.target === e.currentTarget) set({ selected: [] }); }}>
            {shown.map((j) => <Row key={j.id} job={j} selected={selected.includes(j.id)} onSelect={(e) => select(j, e)} />)}
            {!shown.length ? <p class="dim pad">{q ? `No downloads match “${query.trim()}”.` : 'Nothing here right now.'}</p> : null}
          </div>
        </div>
      )}
      {focusJob ? <Detail job={focusJob} onClose={() => set({ selected: [] })} /> : null}
      <div class="status">
        <span>{running.length ? `${running.length} downloading` : counts.active ? `${counts.active} waiting` : 'Idle'}</span>
        {speed ? <span class="num">{formatBytes(speed)}/s</span> : null}
        {selected.length > 1 ? <span>{selected.length} selected</span> : null}
        <div class="grow" />
        <button class="path ellipsis" title="Open the download folder" onClick={() => api.openPath(get().settings.downloadFolder)}>{s.settings.downloadFolder}</button>
      </div>
    </div>
  );
}
