import { useState } from 'preact/hooks';
import { buildOptionArgs, toConfigText } from '../../shared/command';
import type { OptionValues } from '../../shared/schema';
import { join } from '../../shared/shlex';
import { defaultSimple, describeSimple, simpleToValues } from '../../shared/simple';
import type { Preset } from '../../shared/types';
import { api, blankDraft, set, startNew, toast, useStore } from '../state';
import { ask, Btn, Empty } from '../ui';

export function presetArgs(p: Preset): string {
  const values: OptionValues = { ...simpleToValues({ ...p.simple, folder: '' }), ...p.advanced };
  return join(buildOptionArgs(values)) + (p.extraArgs.trim() ? ` ${p.extraArgs.trim()}` : '');
}

export async function importConfigAsPreset(): Promise<void> {
  const r = await api.importConfig();
  if (!r) return;
  const { parsed } = r;
  const name = r.path.split(/[\\/]/).pop()!.replace(/\.(conf|txt|config)$/i, '') || 'Imported';
  const { folder: _f, ...base } = defaultSimple;
  // Imported options are kept exactly as written; the simple choices are set to add nothing of their own.
  const preset: Preset = {
    id: `user-${Date.now().toString(36)}`, name: `${name} (imported)`, note: `Imported from ${r.path}`,
    simple: { ...base, container: 'auto', metadata: false }, advanced: parsed.values, extraArgs: join(parsed.extra),
  };
  set({ presets: await api.savePreset(preset), view: 'presets' });
  const notes = [
    parsed.unknown.length ? `${parsed.unknown.length} unknown ${parsed.unknown.length === 1 ? 'option was' : 'options were'} left out: ${parsed.unknown.join(' ')}` : '',
    parsed.urls.length ? `${parsed.urls.length} ${parsed.urls.length === 1 ? 'link was' : 'links were'} ignored` : '',
  ].filter(Boolean);
  toast(`Imported ${Object.keys(parsed.values).length} options as a preset.${notes.length ? ` ${notes.join('. ')}.` : ''}`);
}

export function PresetsView() {
  const s = useStore();
  const [sel, setSel] = useState(s.presets[0]?.id ?? '');
  const p = s.presets.find((x) => x.id === sel) ?? s.presets[0];

  const edit = (preset: Preset) => set({
    view: 'new',
    draft: { ...blankDraft(s.settings), simple: { ...preset.simple, folder: s.settings.downloadFolder }, advanced: { ...preset.advanced }, extraArgs: preset.extraArgs, presetId: preset.id, editPresetId: preset.id, tab: Object.keys(preset.advanced).length ? 'advanced' : 'simple' },
  });
  const duplicate = async (preset: Preset) => {
    const id = `user-${Date.now().toString(36)}`;
    set({ presets: await api.savePreset({ ...preset, id, name: `${preset.name} copy`, builtin: false }) });
    setSel(id);
  };

  return (
    <div class="main">
      <div class="bar">
        <h1>Presets</h1>
        <div class="grow" />
        <Btn icon="file-import" onClick={importConfigAsPreset}>Import config file</Btn>
      </div>
      {!p ? <Empty title="No presets"><p>Save the options of a download as a preset from the New download screen.</p></Empty> : (
        <div class="split">
          <div class="listcol" role="listbox" aria-label="Presets">
            {s.presets.map((x) => (
              <button type="button" class="item" role="option" aria-selected={x.id === p.id} onClick={() => setSel(x.id)}>
                <span class="ellipsis" style={{ fontWeight: 500 }}>{x.name}</span>
                <span class="s ellipsis">{describeSimple({ ...x.simple, folder: '' })}{Object.keys(x.advanced).length ? ` + ${Object.keys(x.advanced).length} advanced` : ''}{x.builtin ? ' · built in' : ''}</span>
              </button>
            ))}
          </div>
          <div class="scroll">
            <div class="page">
              <div class="section">
                <div class="row"><h1 class="grow">{p.name}</h1>{p.builtin ? <span class="tag">Built in</span> : null}</div>
                {p.note ? <p class="dim">{p.note}</p> : null}
                <div class="row" style={{ marginTop: 4, flexWrap: 'wrap' }}>
                  <Btn kind="primary" icon="download" onClick={() => startNew('', p.id)}>Use for a new download</Btn>
                  {!p.builtin ? <Btn icon="pencil" onClick={() => edit(p)}>Edit</Btn> : null}
                  {!p.builtin ? <Btn onClick={() => ask({ title: 'Rename preset', input: { label: 'Name', value: p.name }, confirm: 'Rename', onConfirm: async (name) => { if (name.trim()) set({ presets: await api.savePreset({ ...p, name: name.trim() }) }); } })}>Rename</Btn> : null}
                  <Btn icon="copy" onClick={() => duplicate(p)}>Duplicate</Btn>
                  <Btn icon="file-export" onClick={async () => {
                    const text = toConfigText({ values: { ...simpleToValues({ ...p.simple, folder: '' }), ...p.advanced }, extraArgs: p.extraArgs }, `${p.name}\nExported from Dubdeck. Use with: yt-dlp --config-locations THIS_FILE URL`);
                    const saved = await api.saveText(`${p.name.replace(/[^\w.-]+/g, '-')}.conf`, text);
                    if (saved) toast('Config file saved.');
                  }}>Export as config file</Btn>
                  {!p.builtin ? <Btn kind="danger" icon="trash" onClick={() => ask({ title: `Delete “${p.name}”`, body: 'Downloads already in the queue keep their options.', confirm: 'Delete', danger: true, onConfirm: async () => set({ presets: await api.removePreset(p.id) }) })}>Delete</Btn> : null}
                </div>
              </div>
              <div class="section">
                <h3>What it sets</h3>
                <dl class="kv" style={{ gridTemplateColumns: '120px 1fr', fontSize: 13 }}>
                  <dt>Download</dt><dd>{describeSimple({ ...p.simple, folder: '' })}</dd>
                  <dt>Subtitles</dt><dd>{p.simple.kind === 'video' && p.simple.subtitles ? `Yes, ${p.simple.subtitleLangs}` : 'No'}</dd>
                  <dt>Tags and chapters</dt><dd>{p.simple.metadata ? 'Yes' : 'No'}</dd>
                  <dt>Cover image</dt><dd>{p.simple.thumbnail ? 'Yes' : 'No'}</dd>
                  <dt>Advanced</dt><dd>{Object.keys(p.advanced).length ? `${Object.keys(p.advanced).length} options` : 'None'}{p.extraArgs.trim() ? ', plus extra arguments' : ''}</dd>
                </dl>
              </div>
              <div class="section">
                <h3>As engine options</h3>
                <pre class="pre">{presetArgs(p) || '(engine defaults)'}</pre>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
