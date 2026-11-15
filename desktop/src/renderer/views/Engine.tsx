import { useEffect, useState } from 'preact/hooks';
import { meta } from '../../shared/meta';
import { schema } from '../../shared/schema';
import { split } from '../../shared/shlex';
import { api, saveSettings, set, toast, useStore } from '../state';
import { ask, Btn, Select } from '../ui';

const tools = schema.controls.filter((c) => meta[c.id]?.tool && !['--update', '--update-to', '--version'].includes(c.id));
const CHANNELS = [
  ['stable', 'Stable releases (yt-dlp/yt-dlp)'], ['nightly', 'Nightly builds'], ['master', 'Master builds (newest, least tested)'],
  ['fork', 'This fork (Nardi05/yt-dlp)'], ['custom', 'Another repository'],
] as const;

export function EngineView() {
  const s = useStore();
  const [output, setOutput] = useState<{ title: string; text: string; code: number | null } | null>(null);
  const [busy, setBusy] = useState('');
  const [ffPct, setFfPct] = useState<number | null>(null);
  const [custom, setCustom] = useState('');
  const e = s.engine;
  const u = s.engineUpdate;

  const reload = async () => set({ engine: await api.engineInfo() });
  useEffect(() => { void reload(); return api.on('ffmpeg-progress', setFfPct); }, []);

  const run = async (title: string, args: string[]) => {
    setBusy(title);
    setOutput({ title, text: 'Running…', code: null });
    const r = await api.engineTool(args);
    setOutput({ title, text: r.output.trim() || '(no output)', code: r.code });
    setBusy('');
    void reload();
  };
  const update = async () => {
    setBusy('update');
    const r = await api.engineUpdate();
    setBusy('');
    await reload();
    if (r.state === 'installed') toast(`Engine updated to ${r.current}.`);
  };
  const sourceText = e?.source === 'updated' ? 'Updated copy, downloaded by the app' : e?.source === 'bundled' ? 'The copy that came with the app' : e?.source === 'source' ? 'Running from source code (development)' : 'Not found';

  return (
    <div class="main">
      <div class="bar"><h1>Engine</h1></div>
      <div class="scroll grow">
        <div class="page">
          <p class="dim" style={{ maxWidth: 620 }}>The engine is yt-dlp, the program that does the downloading. Sites change often, so it is updated far more frequently than the app around it. If a site stops working, updating the engine is the first thing to try.</p>
          <div class="section">
            <h3>yt-dlp</h3>
            <div class="field"><span class="label">Version</span><span class="mono selectable">{e ? e.version || 'not found' : 'Checking…'}</span></div>
            <div class="field"><span class="label">In use</span><span>{sourceText}</span></div>
            <div class="field"><span class="label">Location</span><span class="mono ellipsis selectable small" title={e?.path}>{e?.path}</span></div>
            <div class="field">
              <label>Update from</label>
              <Select label="Update channel" value={s.settings.engineChannel} options={CHANNELS} onChange={(v) => saveSettings({ engineChannel: v as never })} style={{ maxWidth: 320 }} />
              {s.settings.engineChannel === 'custom' ? <input class="input mono" style={{ gridColumn: 2, maxWidth: 320 }} placeholder="owner/repository or owner/repository@tag" aria-label="Custom update source" value={s.settings.engineCustomSource} onInput={(ev) => saveSettings({ engineCustomSource: (ev.target as HTMLInputElement).value })} /> : null}
              <span class="hint">{s.settings.engineChannel === 'fork' ? 'Uses releases published on the fork. If there are none, pick Stable.' : s.settings.engineChannel === 'stable' ? 'The official builds. Recommended, because site fixes land here first.' : s.settings.engineChannel === 'custom' ? 'Any GitHub repository that publishes yt-dlp builds with a SHA2-256SUMS file.' : 'Newer than stable. Useful when a fix has not been released yet.'}</span>
            </div>
            <div class="row" style={{ marginTop: 4, flexWrap: 'wrap' }}>
              <Btn icon="refresh" busy={u.state === 'checking'} onClick={() => api.engineCheck()}>Check for updates</Btn>
              <Btn kind={u.state === 'available' ? 'primary' : undefined} icon="download" busy={busy === 'update'} onClick={update}>{u.state === 'available' ? `Update to ${u.latest ?? 'latest'}` : 'Download latest'}</Btn>
              {e?.source === 'updated' ? <Btn onClick={() => ask({ title: 'Go back to the built-in engine', body: 'This removes the updated copy and uses the engine that came with the app.', confirm: 'Use built-in engine', onConfirm: async () => { set({ engine: await api.engineRevert(), engineUpdate: { state: 'idle' } }); } })}>Use built-in engine</Btn> : null}
              <span class={`small ${u.state === 'error' ? 'state-error' : 'dim'}`} role="status">
                {u.state === 'current' ? `Up to date${u.latest ? ` (latest is ${u.latest})` : ''}.` : u.state === 'available' ? `Version ${u.latest ?? ''} is available.` : u.state === 'downloading' ? `Downloading… ${u.percent ?? 0}%` : u.state === 'installed' ? `Now on ${u.current}.` : u.state === 'error' ? u.message : ''}
              </span>
            </div>
            <div class="field" style={{ marginTop: 8 }}>
              <label>Specific version</label>
              <div class="row" style={{ gap: 4 }}>
                <input class="input mono grow" placeholder="stable@2025.01.15 or nightly@latest" aria-label="Channel and tag for --update-to" value={custom} list="update-to" onInput={(ev) => setCustom((ev.target as HTMLInputElement).value)} />
                <datalist id="update-to"><option value="stable@latest" /><option value="nightly@latest" /><option value="master@latest" /></datalist>
                <Btn disabled={!custom.trim() || !!busy} onClick={() => run(`--update-to ${custom.trim()}`, ['--update-to', custom.trim()])}>Run --update-to</Btn>
                <Btn disabled={!!busy} onClick={() => run('--update', ['--update'])} title="Ask the engine to update itself in place">Run --update</Btn>
              </div>
              <span class="hint">These run the engine’s own updater. It only works on an engine binary, not when running from source.</span>
            </div>
          </div>

          <div class="section">
            <h3>ffmpeg</h3>
            <div class="field"><span class="label">Version</span><span class={`mono ${e?.ffmpeg.version ? '' : 'state-error'}`}>{e ? e.ffmpeg.version || 'not found' : 'Checking…'}</span></div>
            <div class="field"><span class="label">In use</span><span>{e?.ffmpeg.source === 'bundled' ? 'The copy that came with the app' : e?.ffmpeg.source === 'installed' ? 'Installed by the app' : e?.ffmpeg.source === 'system' ? 'The copy installed on this computer' : 'None. Merging and converting will fail until it is installed.'}</span></div>
            <div class="row">
              <Btn icon="download" busy={busy === 'ffmpeg'} kind={e && !e.ffmpeg.version ? 'primary' : undefined} onClick={async () => {
                setBusy('ffmpeg'); setFfPct(0);
                const r = await api.installFfmpeg();
                setBusy(''); setFfPct(null); await reload();
                toast(r.ok ? 'ffmpeg installed.' : r.message ?? 'ffmpeg could not be installed.');
              }}>{e?.ffmpeg.source === 'installed' ? 'Reinstall ffmpeg' : 'Install ffmpeg'}</Btn>
              {ffPct !== null ? <span class="small dim num">{ffPct}%</span> : <span class="small faint">About 80 MB. Stored in the app’s own folder; nothing else on the computer changes.</span>}
            </div>
          </div>

          <div class="section">
            <h3>JavaScript runtime</h3>
            <p class="dim">Some sites need a JavaScript runtime to work out video addresses. The app lends the engine its own ({e?.jsRuntime ?? 'node'}), so nothing needs installing. To use a different one, set “JavaScript runtimes” under Sites and plugins.</p>
          </div>

          <div class="section">
            <h3>Engine commands</h3>
            <p class="dim">One-off commands that print information. Nothing is downloaded.</p>
            <div class="row" style={{ flexWrap: 'wrap', marginTop: 4 }}>
              {tools.map((c) => <Btn busy={busy === meta[c.id].label} disabled={!!busy} title={`${c.id}: ${meta[c.id].tip}`} onClick={() => run(meta[c.id].label, [c.id])}>{meta[c.id].label}</Btn>)}
              <Btn disabled={!!busy} title="Run the engine with any arguments and see what it prints" onClick={() => ask({
                title: 'Run a custom engine command', body: 'Type engine arguments the way you would after “yt-dlp” in a terminal. The result is shown below.',
                input: { label: 'Arguments', value: '', placeholder: '--dump-user-agent' }, confirm: 'Run',
                onConfirm: (v) => { try { void run(v, split(v, false)); } catch (err) { toast(`${(err as Error).message}.`); } },
              })}>Custom command…</Btn>
            </div>
            {output ? (
              <div style={{ marginTop: 8 }}>
                <div class="row" style={{ marginBottom: 4 }}>
                  <h2 class="grow">{output.title}{output.code ? <span class="tag bad" style={{ marginLeft: 8 }}>exit code {output.code}</span> : null}</h2>
                  <Btn small kind="quiet" icon="copy" onClick={() => { void api.copyText(output.text); toast('Copied.'); }}>Copy</Btn>
                  <Btn small kind="quiet" icon="x" label="Close output" onClick={() => setOutput(null)} />
                </div>
                <pre class="pre" style={{ maxHeight: 320, overflow: 'auto', border: '1px solid var(--line)', borderRadius: 4, padding: '8px 10px', background: 'var(--surface)' }}>{output.text}</pre>
              </div>
            ) : null}
          </div>
        </div>
      </div>
    </div>
  );
}
