import { useEffect, useState } from 'preact/hooks';
import type { Job } from '../../shared/types';
import { jobMenu, redownload } from '../actions';
import { api, set, startNew, useStore } from '../state';
import { ask, Btn, Empty, Search, Seg, Thumb, when } from '../ui';
import { Detail } from './Queue';

export function HistoryView({ searchRef }: { searchRef: { current: HTMLInputElement | null } }) {
  const s = useStore();
  const [query, setQuery] = useState('');
  const [filter, setFilter] = useState<'all' | 'done' | 'error'>('all');
  const [sel, setSel] = useState<string | null>(null);
  useEffect(() => { void api.listHistory().then((history) => set({ history })); }, [s.jobs.filter((j) => j.finishedAt).length]);

  const q = query.trim().toLowerCase();
  const shown = s.history.filter((j) => (filter === 'all' || (filter === 'done' ? j.state === 'done' : j.state !== 'done'))
    && (!q || `${j.title} ${j.url} ${j.uploader ?? ''} ${j.summary} ${j.files.join(' ')}`.toLowerCase().includes(q)));
  const job = shown.find((j) => j.id === sel);
  const label = (j: Job) => (j.state === 'done' ? (j.note ?? 'Saved') : j.state === 'cancelled' ? 'Cancelled' : j.error?.title ?? 'Failed');

  return (
    <div class="main">
      <div class="bar">
        <h1>History</h1>
        <Seg label="Show" value={filter} onChange={setFilter} options={[['all', 'All'], ['done', 'Finished'], ['error', 'Failed']] as const} />
        <div class="grow" />
        <Search value={query} onChange={setQuery} placeholder="Search history" inputRef={searchRef} />
        <div class="sep" />
        <Btn kind="quiet" icon="trash" disabled={!s.history.length} onClick={() => ask({
          title: 'Clear history', body: 'This forgets the list of past downloads. The downloaded files stay where they are.', confirm: 'Clear history', danger: true,
          onConfirm: async () => set({ history: await api.clearHistory() }),
        })}>Clear</Btn>
      </div>
      {!s.history.length ? (
        <Empty title="No history yet">
          <p>Every download that finishes, fails or is cancelled is listed here, so you can find the file again or run it once more.</p>
          <div class="row"><Btn icon="plus" onClick={() => startNew()}>New download</Btn></div>
        </Empty>
      ) : (
        <div class="table" role="grid" aria-label="History">
          <div class="thead history-cols" role="row"><span>When</span><span>Name</span><span>Result</span><span>Options</span><span /></div>
          <div class="scroll grow">
            {shown.map((j) => (
              <div class="tr history-cols" role="row" tabIndex={0} aria-selected={sel === j.id} onClick={() => setSel(j.id)}
                onKeyDown={(e) => { if (e.key === 'Enter') setSel(j.id); }} onContextMenu={(e) => { e.preventDefault(); setSel(j.id); void jobMenu(j, true); }}
                onDblClick={() => { if (j.files[0]) void api.openPath(j.files[0]); }}>
                <span class="num dim">{when(j.finishedAt ?? j.createdAt)}</span>
                <div class="row" style={{ minWidth: 0, gap: 10 }}>
                  <Thumb src={j.thumbnail} audio={j.values['--extract-audio'] !== undefined} />
                  <div class="title2"><span class="t ellipsis">{j.title}</span><span class="s ellipsis">{j.uploader ?? j.url}</span></div>
                </div>
                <span class={`ellipsis ${j.state === 'done' ? 'state-done' : j.state === 'error' ? 'state-error' : 'dim'}`}>{label(j)}</span>
                <span class="ellipsis dim small">{j.summary}</span>
                <div class="acts">
                  <Btn small kind="quiet" icon="refresh" label="Download again" onClick={(e) => { e.stopPropagation(); void redownload(j); }} />
                  {j.files[0] ? <Btn small kind="quiet" icon="folder-open" label="Show in folder" onClick={(e) => { e.stopPropagation(); void api.showItem(j.files[0]); }} /> : null}
                  <Btn small kind="quiet" icon="trash" label="Remove from history" onClick={async (e) => { e.stopPropagation(); set({ history: await api.removeHistory([j.id]) }); }} />
                </div>
              </div>
            ))}
            {!shown.length ? <p class="dim pad">Nothing in your history matches{q ? ` “${query.trim()}”` : ' this filter'}.</p> : null}
          </div>
        </div>
      )}
      {job ? <Detail job={job} onClose={() => setSel(null)} /> : null}
      <div class="status"><span>{s.history.length} {s.history.length === 1 ? 'entry' : 'entries'}</span><span class="faint">The newest 2,000 are kept.</span></div>
    </div>
  );
}
