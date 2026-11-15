import { useEffect, useMemo, useRef, useState } from 'preact/hooks';
import { buildArgs } from '../../shared/command';
import { formatBytes, formatDuration } from '../../shared/output';
import { redactArgs } from '../../shared/redact';
import type { OptionValues } from '../../shared/schema';
import { quote } from '../../shared/shlex';
import { audioFormats, audioQualities, describeSimple, effectiveValues, simpleToValues, videoContainers, videoQualities, type SimpleChoices } from '../../shared/simple';
import { preflight } from '../../shared/preflight';
import type { FormatInfo, JobSpec, ProbeResult } from '../../shared/types';
import { Advanced, extraProblems } from '../Advanced';
import { api, applyPreset, blankDraft, get, go, parseLinks, saveSettings, set, setDraft, toast, useStore, type Draft } from '../state';
import { ask, Btn, Check, Icon, Seg, Select, Tabs, Thumb } from '../ui';

function compressItems(count: number, skip: number[]): string {
  const skipSet = new Set(skip);
  const parts: string[] = [];
  let start = 0;
  for (let i = 1; i <= count + 1; i++) {
    const keep = i <= count && !skipSet.has(i);
    if (keep && !start) start = i;
    if (!keep && start) { parts.push(start === i - 1 ? `${start}` : `${start}-${i - 1}`); start = 0; }
  }
  return parts.join(',');
}

export function draftValues(d: Draft, base: OptionValues): OptionValues {
  return effectiveValues(d.simple, d.advanced, base);
}

function lookup(url: string, values: OptionValues): void {
  set((s) => ({ previews: { ...s.previews, [url]: 'loading' } }));
  void api.probe(url, values, '').then((r) => {
    if (get().previews[url] === 'loading') set((s) => ({ previews: { ...s.previews, [url]: r } }));
  });
}

function Formats({ url, formats }: { url: string; formats: FormatInfo[] }) {
  const s = useStore();
  const picked = s.draft.overrides[url]?.format ?? '';
  const [v, a] = picked.includes('+') ? picked.split('+') : [picked, ''];
  const pick = (f: FormatInfo) => {
    let next: string;
    if (f.kind === 'video+audio') next = picked === f.id ? '' : f.id;
    else if (f.kind === 'video') next = v === f.id && !picked.includes('+') ? '' : [f.id, a || (formats.some((x) => x.id === v && x.kind === 'audio') ? v : '')].filter(Boolean).join('+');
    else {
      const video = formats.find((x) => x.id === v && x.kind === 'video');
      next = video ? (a === f.id ? video.id : `${video.id}+${f.id}`) : picked === f.id ? '' : f.id;
    }
    setDraft({ overrides: { ...s.draft.overrides, [url]: { ...s.draft.overrides[url], format: next || undefined } } });
  };
  const groups: [string, FormatInfo[]][] = [
    ['Video with audio', formats.filter((f) => f.kind === 'video+audio')],
    ['Video only', formats.filter((f) => f.kind === 'video')],
    ['Audio only', formats.filter((f) => f.kind === 'audio')],
  ];
  const ids = new Set(picked.split('+'));
  return (
    <div>
      <div class="fmt" role="listbox" aria-label="Available formats" aria-multiselectable="true">
        <div class="frow h"><span /><span>ID</span><span>Type</span><span>Resolution</span><span>FPS</span><span>Codec</span><span class="right">Size</span></div>
        {groups.filter(([, list]) => list.length).map(([name, list]) => (
          <>
            <div class="grp">{name}</div>
            {list.map((f) => (
              <div class="frow num" role="option" tabIndex={0} aria-checked={ids.has(f.id)} aria-selected={ids.has(f.id)} onClick={() => pick(f)}
                onKeyDown={(e) => { if (e.key === ' ' || e.key === 'Enter') { e.preventDefault(); pick(f); } }} title={f.note}>
                <span class="radio" /><span class="ellipsis">{f.id}</span><span>{f.ext}</span><span class="ellipsis">{f.resolution}</span><span>{f.fps ? Math.round(f.fps) : ''}</span>
                <span class="ellipsis">{[[f.vcodec, f.acodec].filter(Boolean).join(' + '), f.note].filter(Boolean).join(' · ')}</span>
                <span class="right">{f.size ? `${f.sizeApprox ? '~' : ''}${formatBytes(f.size)}` : ''}</span>
              </div>
            ))}
          </>
        ))}
      </div>
      <p class="small faint" style={{ marginTop: 4 }}>
        {picked ? <>This link will use format <span class="mono">{picked}</span> instead of the quality chosen on the right. <a onClick={() => pick({ id: picked, kind: 'video+audio' } as FormatInfo)}>Clear</a></>
          : 'Pick a row to use that exact format for this link. A video-only row can be combined with an audio-only row.'}
      </p>
    </div>
  );
}

function Preview({ url, values }: { url: string; values: OptionValues }) {
  const s = useStore();
  const p = s.previews[url];
  const [open, setOpen] = useState<'formats' | 'items' | 'log' | null>(null);
  const remove = () => {
    setDraft({ text: s.draft.text.split(/\r?\n/).filter((l) => !l.includes(url.replace(/^https:\/\//, ''))).join('\n') });
  };
  if (!p || p === 'loading') {
    return (
      <div class="pv" aria-busy="true">
        <div class="head">
          <div class="thumb lg skel" />
          <div class="grow col" style={{ gap: 6 }}>
            <div class="skel" style={{ height: 14, width: '70%' }} />
            <div class="skel" style={{ height: 10, width: '40%' }} />
            <div class="small faint ellipsis">{p ? 'Looking up' : 'Waiting'} {url}</div>
          </div>
          {p ? <Btn icon="x" small kind="quiet" label="Stop looking up" onClick={() => { void api.cancelProbe(url); set((st) => ({ previews: { ...st.previews, [url]: { ok: false, url } } })); }} /> : null}
        </div>
      </div>
    );
  }
  if (!p.ok) {
    return (
      <div class="pv bad">
        <div class="head">
          <div class="thumb lg"><Icon name="alert-circle" /></div>
          <div class="grow">
            <div class="t">{p.error?.title ?? 'Preview was cancelled'}</div>
            <div class="meta selectable ellipsis">{url}</div>
            {p.error ? <div class="meta">{p.error.what} {p.error.tryThis[0]}</div> : <div class="meta">You can still add this link. It will be looked up when the download starts.</div>}
            <div class="tools">
              <Btn small icon="refresh" onClick={() => lookup(url, values)}>Look up again</Btn>
              {p.log ? <Btn small kind="quiet" onClick={() => setOpen(open === 'log' ? null : 'log')}>{open === 'log' ? 'Hide details' : 'Show details'}</Btn> : null}
              <Btn small kind="quiet" icon="x" onClick={remove}>Remove link</Btn>
            </div>
          </div>
        </div>
        {open === 'log' ? <pre class="pre">{p.log}</pre> : null}
      </div>
    );
  }
  const skip = s.draft.overrides[url]?.skip ?? [];
  const setSkip = (next: number[]) => setDraft({ overrides: { ...s.draft.overrides, [url]: { ...s.draft.overrides[url], skip: next } } });
  const entries = p.entries ?? [];
  return (
    <div class="pv">
      <div class="head">
        <Thumb src={p.thumbnail} large />
        <div class="grow">
          <div class="t">{p.title}</div>
          <div class="meta">
            {[p.uploader, p.kind === 'playlist' ? `${p.count ?? entries.length} items` : formatDuration(p.duration), p.live ? 'Live' : null, p.extractor].filter(Boolean).join(' · ')}
          </div>
          <div class="tools">
            {p.kind === 'video' && p.formats?.length ? (
              <Btn small icon={open === 'formats' ? 'chevron-down' : 'chevron-right'} onClick={() => setOpen(open === 'formats' ? null : 'formats')}>
                {p.formats.length} formats{s.draft.overrides[url]?.format ? ' · 1 picked' : ''}
              </Btn>
            ) : null}
            {p.kind === 'playlist' && entries.length ? (
              <Btn small icon={open === 'items' ? 'chevron-down' : 'chevron-right'} onClick={() => setOpen(open === 'items' ? null : 'items')}>
                {skip.length ? `${entries.length - skip.length} of ${entries.length} selected` : 'Choose items'}
              </Btn>
            ) : null}
            {p.subtitles?.length ? <span class="tag" title={p.subtitles.join(', ')}>{p.subtitles.length} subtitle {p.subtitles.length === 1 ? 'language' : 'languages'}</span> : null}
            <Btn small kind="quiet" icon="x" label="Remove link" onClick={remove} />
          </div>
        </div>
      </div>
      {open === 'formats' && p.formats ? <Formats url={url} formats={p.formats} /> : null}
      {open === 'items' ? (
        <div>
          <div class="row small" style={{ marginBottom: 4 }}>
            <a onClick={() => setSkip([])}>Select all</a><a onClick={() => setSkip(entries.map((e) => e.index))}>Select none</a>
          </div>
          <div class="entries">
            {entries.slice(0, 500).map((e) => (
              <label>
                <input type="checkbox" checked={!skip.includes(e.index)} onChange={(ev) => setSkip((ev.target as HTMLInputElement).checked ? skip.filter((x) => x !== e.index) : [...skip, e.index])} />
                <span class="num faint">{e.index}</span><span class="ellipsis">{e.title}</span><span class="num faint right">{formatDuration(e.duration)}</span>
              </label>
            ))}
          </div>
          {entries.length > 500 ? <p class="small faint" style={{ marginTop: 4 }}>Showing the first 500. To pick from the rest, use “Items” under Playlists and filters in the advanced options.</p> : null}
        </div>
      ) : null}
    </div>
  );
}

function SimplePanel({ simple, advanced, onChange }: { simple: SimpleChoices; advanced: OptionValues; onChange: (p: Partial<SimpleChoices>) => void }) {
  const owned = simpleToValues(simple);
  const overridden = Object.keys(owned).filter((k) => k in advanced);
  const pickFolder = async () => { const f = await api.pickFolder(simple.folder); if (f) onChange({ folder: f }); };
  return (
    <div class="simple">
      <div class="field">
        <span class="label">Download</span>
        <div><Seg label="What to download" value={simple.kind} options={[['video', 'Video'], ['audio', 'Audio only']] as const} onChange={(kind) => onChange({ kind, thumbnail: kind === 'audio' ? true : simple.thumbnail })} /></div>
      </div>
      {simple.kind === 'video' ? (
        <>
          <div class="field"><label for="s-q">Quality</label><Select label="Quality" value={simple.quality} options={videoQualities} onChange={(quality) => onChange({ quality })} /></div>
          <div class="field">
            <label>File type</label><Select label="File type" value={simple.container} options={videoContainers} onChange={(container) => onChange({ container })} />
            <span class="hint">{simple.container === 'mp4' ? 'Prefers H.264 and AAC so the file plays on phones, TVs and editors.' : simple.container === 'auto' ? 'Keeps the best streams the site has. The result is often WebM or MKV.' : simple.container === 'mkv' ? 'Holds any combination of streams without converting.' : 'Prefers VP9 or AV1 with Opus.'}</span>
          </div>
          <div class="field">
            <span class="label">Subtitles</span>
            <div class="row">
              <Check checked={simple.subtitles} onChange={(subtitles) => onChange({ subtitles })}>Include</Check>
              <input class="input mono grow" disabled={!simple.subtitles} value={simple.subtitleLangs} aria-label="Subtitle languages" placeholder="en.*,de" onInput={(e) => onChange({ subtitleLangs: (e.target as HTMLInputElement).value })} />
            </div>
            {simple.subtitles ? <span class="hint">Language codes separated by commas. en.* covers every kind of English.</span> : null}
          </div>
        </>
      ) : (
        <>
          <div class="field"><label>Format</label><Select label="Audio format" value={simple.audioFormat} options={audioFormats} onChange={(audioFormat) => onChange({ audioFormat })} /></div>
          {['mp3', 'm4a', 'opus'].includes(simple.audioFormat) ? (
            <div class="field"><label>Quality</label><Select label="Audio quality" value={simple.audioQuality} options={audioQualities} onChange={(audioQuality) => onChange({ audioQuality })} /></div>
          ) : null}
        </>
      )}
      <div class="field">
        <span class="label">Extras</span>
        <div class="row" style={{ gap: 16 }}>
          <Check checked={simple.metadata} onChange={(metadata) => onChange({ metadata })}>Tags and chapters</Check>
          <Check checked={simple.thumbnail} onChange={(thumbnail) => onChange({ thumbnail })}>Cover image</Check>
        </div>
      </div>
      <div class="field">
        <label>Playlist links</label>
        <Select label="Playlist links" value={simple.playlist} onChange={(playlist) => onChange({ playlist: playlist as SimpleChoices['playlist'] })}
          options={[['default', 'Let the link decide'], ['all', 'Always take the whole playlist'], ['single', 'Only the one video']] as const} />
      </div>
      <div class="field">
        <label>Save to</label>
        <div class="row" style={{ gap: 4 }}>
          <input class="input grow" value={simple.folder} aria-label="Folder to save to" onInput={(e) => onChange({ folder: (e.target as HTMLInputElement).value })} />
          <Btn icon="folder" onClick={pickFolder}>Choose</Btn>
        </div>
      </div>
      {overridden.length ? <p class="over"><Icon name="info-circle" small /> {overridden.length === 1 ? 'One of these choices is' : `${overridden.length} of these choices are`} overridden in Advanced: <span class="mono">{overridden.join(' ')}</span></p> : null}
    </div>
  );
}

export function NewView() {
  const s = useStore();
  const d = s.draft;
  const base = s.settings.baseValues;
  const values = useMemo(() => draftValues(d, base), [d.simple, d.advanced, base]);
  const { links, rejected } = useMemo(() => parseLinks(d.text), [d.text]);
  const textRef = useRef<HTMLTextAreaElement>(null);
  const editing = d.editJobId ? s.jobs.find((j) => j.id === d.editJobId) : undefined;

  useEffect(() => { textRef.current?.focus(); }, []);

  // look up new links a moment after typing stops
  useEffect(() => {
    if (d.editPresetId) return;
    const t = setTimeout(() => {
      for (const url of links) if (!(url in get().previews)) lookup(url, values);
    }, 500);
    return () => clearTimeout(t);
  }, [links.join('\n')]);

  const noLinkNeeded = '--batch-file' in values || '--load-info-json' in values;
  const problem = extraProblems(d.extraArgs);
  const args = buildArgs({ values, extraArgs: problem ? '' : d.extraArgs, urls: links });
  const shown = redactArgs(args);
  const changed = Object.keys(d.advanced).length + (d.extraArgs.trim() ? 1 : 0);

  const specFor = (url: string): JobSpec => {
    const p = s.previews[url];
    const info = p && p !== 'loading' && p.ok ? p : undefined;
    const v: OptionValues = { ...values };
    const o = d.overrides[url];
    let summary = describeSimple(d.simple) + (changed ? ` + ${changed} advanced` : '');
    if (o?.format && info?.kind === 'video') { v['--format'] = o.format; delete v['--format-sort']; summary = `Format ${o.format}`; }
    if (o?.skip?.length && info?.kind === 'playlist' && !('--playlist-items' in d.advanced)) {
      v['--playlist-items'] = compressItems(info.entries?.length ?? 0, o.skip);
      summary += `, ${(info.entries?.length ?? 0) - o.skip.length} items`;
    }
    return {
      url, title: info?.title, thumbnail: info?.thumbnail, uploader: info?.uploader, duration: info?.duration, summary, values: v,
      extraArgs: d.extraArgs, scheduledFor: d.scheduleAt ? new Date(d.scheduleAt).getTime() : undefined,
    };
  };

  const submit = async () => {
    if (problem) { toast('Fix the extra arguments first.'); setDraft({ tab: 'advanced' }); return; }
    const blockers = preflight(values);
    if (blockers.length && !d.editPresetId) { ask({ title: 'Check the options first', body: blockers.join('\n'), confirm: 'Edit options', onConfirm: () => setDraft({ tab: 'advanced' }) }); return; }
    if (d.editPresetId) {
      const p = s.presets.find((x) => x.id === d.editPresetId);
      if (p) {
        const { folder: _f, ...simple } = d.simple;
        set({ presets: await api.savePreset({ ...p, simple, advanced: d.advanced, extraArgs: d.extraArgs }), draft: blankDraft(s.settings), view: 'presets' });
        toast(`Preset “${p.name}” updated.`);
      }
      return;
    }
    if (editing) {
      await api.updateJob(editing.id, { values, extraArgs: d.extraArgs, url: links[0] ?? editing.url }, true);
      set({ draft: blankDraft(s.settings), view: 'queue', selected: [editing.id] });
      return;
    }
    const urls = links.length ? links : noLinkNeeded ? [''] : [];
    if (!urls.length) { textRef.current?.focus(); return; }
    await api.addJobs(urls.map(specFor));
    const { folder, ...rest } = d.simple;
    void saveSettings({ simple: { ...rest, folder: '' }, downloadFolder: folder || s.settings.downloadFolder, lastPresetId: d.presetId });
    set({ draft: blankDraft({ ...s.settings, simple: { ...rest, folder: '' }, downloadFolder: folder || s.settings.downloadFolder }), view: 'queue' });
    if (d.presetId) applyPresetQuiet(d.presetId);
  };
  const applyPresetQuiet = (id: string) => { const keepView = get().view; applyPreset(id); set({ view: keepView }); };

  const savePreset = () => ask({
    title: 'Save as preset',
    body: 'A preset remembers every choice on this screen except the links and the folder.',
    input: { label: 'Name', value: '', placeholder: 'Podcast MP3' },
    confirm: 'Save',
    onConfirm: async (name) => {
      if (!name.trim()) return;
      const { folder: _f, ...simple } = d.simple;
      const id = `user-${Date.now().toString(36)}`;
      set({ presets: await api.savePreset({ id, name: name.trim(), simple, advanced: d.advanced, extraArgs: d.extraArgs }) });
      setDraft({ presetId: id });
      toast(`Preset “${name.trim()}” saved.`);
    },
  });

  const paste = async () => {
    const text = (await api.readClipboard()).trim();
    if (!text) { toast('The clipboard is empty.'); return; }
    setDraft({ text: d.text.trim() ? `${d.text.trim()}\n${text}` : text });
  };

  const title = d.editPresetId ? `Edit preset: ${s.presets.find((p) => p.id === d.editPresetId)?.name ?? ''}` : editing ? 'Edit download' : 'New download';
  const canSubmit = d.editPresetId || editing || links.length > 0 || noLinkNeeded;

  return (
    <div class="main" onKeyDown={(e) => { if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') { e.preventDefault(); void submit(); } }}>
      <div class="bar">
        <h1>{title}</h1>
        <div class="grow" />
        <span class="dim small">Preset</span>
        <Select label="Preset" value={d.presetId} onChange={(id) => applyPreset(id)} style={{ width: 200 }}
          options={[['', 'None'], ...s.presets.map((p) => [p.id, p.name] as const)]} />
        {!d.editPresetId ? <Btn icon="bookmark" onClick={savePreset}>Save as preset</Btn> : null}
        <div class="sep" />
        <Btn kind="quiet" onClick={() => { set({ draft: blankDraft(s.settings) }); go(d.editPresetId ? 'presets' : 'queue'); }}>Cancel</Btn>
      </div>
      <div class="new">
        <div class="col">
          {d.editPresetId ? (
            <div class="pad dim">Links are not part of a preset. Change the options on the right, then save.</div>
          ) : (
            <>
              <div class="links">
                <div class="row">
                  <h3 class="grow">Links</h3>
                  <Btn small icon="clipboard" onClick={paste}>Paste</Btn>
                </div>
                <textarea ref={textRef} class="input" spellcheck={false} rows={3} value={d.text} aria-label="Links, one per line"
                  placeholder={'Paste one link per line.\nVideos, playlists and channels all work.'} onInput={(e) => setDraft({ text: (e.target as HTMLTextAreaElement).value })} />
                {rejected.length ? <p class="small state-warn"><Icon name="alert-triangle" small /> Not a link, so it will be left out: <span class="mono">{rejected.slice(0, 3).join(', ')}</span>{rejected.length > 3 ? ` and ${rejected.length - 3} more` : ''}</p> : null}
              </div>
              <div class="scroll grow">
                {links.map((url) => <Preview key={url} url={url} values={values} />)}
                {!links.length ? (
                  <div class="pad dim" style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                    <p>A preview of each link shows up here: title, length, and the formats on offer.</p>
                    <p>You can also drop links anywhere on the window.</p>
                  </div>
                ) : null}
              </div>
            </>
          )}
        </div>
        <div class="col">
          <Tabs value={d.tab} onChange={(tab) => setDraft({ tab })} options={[['simple', 'Simple'], ['advanced', changed ? `Advanced · ${changed} changed` : 'Advanced']] as const} />
          {d.tab === 'simple' ? (
            <div class="scroll grow">
              <SimplePanel simple={d.simple} advanced={d.advanced} onChange={(p) => setDraft({ simple: { ...d.simple, ...p } })} />
            </div>
          ) : (
            <Advanced values={d.advanced} inherited={{ ...base, ...simpleToValues(d.simple) }} inheritedFrom="Simple or your defaults" extraArgs={d.extraArgs}
              onChange={(advanced) => setDraft({ advanced })} onExtra={(extraArgs) => setDraft({ extraArgs })} />
          )}
        </div>
      </div>
      <div class="cmd">
        <span class="lbl" title="This is the exact command the app runs for you. You never need to type it.">Command</span>
        <div class="text" tabIndex={0} aria-label="Equivalent command">
          <b>yt-dlp</b> {shown.map((a, i) => <>{a.startsWith('-') && !links.includes(args[i]) ? <b>{a}</b> : quote(a)} </>)}
        </div>
        <Btn icon="copy" kind="quiet" label="Copy command" onClick={() => { void api.copyText(['yt-dlp', ...shown].map(quote).join(' ')); toast('Command copied. Passwords are left out.'); }} />
        {!d.editPresetId && !editing ? (
          <Btn icon="clock" title="Choose when the download starts" onClick={() => ask({
            title: 'Start later', body: 'The download waits in the queue and starts at this time. The app needs to be open then. Leave the box empty to start straight away.',
            input: { label: 'Start at', value: d.scheduleAt, type: 'datetime-local' }, confirm: 'Set',
            onConfirm: (v) => setDraft({ scheduleAt: v && new Date(v).getTime() > Date.now() ? v : '' }),
          })}>{d.scheduleAt ? new Date(d.scheduleAt).toLocaleString([], { weekday: 'short', hour: '2-digit', minute: '2-digit' }) : 'Start now'}</Btn>
        ) : null}
        <Btn kind="primary" icon={d.editPresetId ? 'check' : 'download'} disabled={!canSubmit} onClick={submit} title="Ctrl+Enter">
          {d.editPresetId ? 'Save preset' : editing ? 'Save and retry' : d.scheduleAt ? 'Schedule' : links.length > 1 ? `Download ${links.length}` : 'Download'}
        </Btn>
      </div>
    </div>
  );
}
