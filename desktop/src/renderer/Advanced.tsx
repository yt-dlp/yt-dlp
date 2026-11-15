// The full option editor. Every control is generated from the engine's own
// option list, so it always covers everything the command line accepts.
import { useMemo, useRef, useState } from 'preact/hooks';
import { parseArgs } from '../shared/command';
import { categories, fallbackLabel, meta, type Meta } from '../shared/meta';
import { schema, type Control, type OptionValues, type Value } from '../shared/schema';
import { split } from '../shared/shlex';
import { api } from './state';
import { Btn, Icon, Search } from './ui';

const visibleCategories = categories.filter((c) => c.id !== 'tools');
const controlsByCategory = new Map<string, Control[]>();
for (const c of schema.controls) {
  const cat = meta[c.id]?.category ?? 'config';
  if (!controlsByCategory.has(cat)) controlsByCategory.set(cat, []);
  controlsByCategory.get(cat)!.push(c);
}
export const optionCount = schema.controls.filter((c) => !meta[c.id]?.tool).length;

function metaFor(c: Control): Meta {
  return meta[c.id] ?? { category: 'config', label: fallbackLabel(c.id), tip: c.option?.help ?? c.members.map((m) => m.help).join(' ') };
}

function flagsOf(c: Control): string {
  return c.kind === 'value' ? c.option!.flags.join(', ') + (c.option!.metavar ? ` ${c.option!.metavar}` : '') : c.members.map((m) => m.id).join(' / ');
}

function isSet(v: Value | undefined): boolean {
  return v !== undefined && v !== null;
}

interface RowProps {
  control: Control;
  own: Value | undefined;
  inherited: Value | undefined;
  inheritedFrom: string;
  onChange: (v: Value | undefined) => void;
  onHelp: (c: Control | null) => void;
}

function Row({ control: c, own, inherited, inheritedFrom, onChange, onHelp }: RowProps) {
  const m = metaFor(c);
  const [open, setOpen] = useState(false);
  const value = own !== undefined ? own : inherited;
  const fromElsewhere = own === undefined && inherited !== undefined;
  const listId = `dl-${c.id.replace(/\W/g, '')}`;

  const browse = async (apply: (p: string) => void) => {
    const p = m.widget === 'folder' ? await api.pickFolder() : await api.pickFile();
    if (p) apply(p);
  };

  let ctl;
  if (c.kind === 'switch') {
    const chosen = typeof value === 'string' ? value : '';
    if (c.onFlag && c.offFlag) {
      const on = chosen ? chosen === c.onFlag : !!c.defaultOn;
      ctl = (
        <label class="check" style={{ minHeight: 28 }}>
          <input type="checkbox" class={chosen ? '' : 'default'} checked={on} aria-label={m.label} onChange={(e) => onChange((e.target as HTMLInputElement).checked ? c.onFlag! : c.offFlag!)} />
          <span class={chosen ? '' : 'faint'}>{chosen ? (on ? 'On' : 'Off') : `Default (${c.defaultOn ? 'on' : 'off'})`}</span>
        </label>
      );
    } else if (c.members.length === 1) {
      ctl = (
        <label class="check" style={{ minHeight: 28 }}>
          <input type="checkbox" checked={chosen === c.members[0].id} aria-label={m.label} onChange={(e) => onChange((e.target as HTMLInputElement).checked ? c.members[0].id : undefined)} />
          <span class={chosen ? '' : 'faint'}>{chosen ? 'On' : 'Off'}</span>
        </label>
      );
    } else {
      ctl = (
        <select class="select" aria-label={m.label} value={chosen} onChange={(e) => onChange((e.target as HTMLSelectElement).value || undefined)}>
          <option value="">Default</option>
          {c.members.map((mem) => <option value={mem.id}>{m.memberLabels?.[mem.id] ?? fallbackLabel(mem.id)}</option>)}
        </select>
      );
    }
  } else if (c.nargs > 1) {
    const rows = (Array.isArray(value) ? value : []) as string[][];
    const setRow = (i: number, j: number, v: string) => onChange(rows.map((r, k) => (k === i ? r.map((x, l) => (l === j ? v : x)) : r)));
    ctl = (
      <>
        {rows.map((r, i) => (
          <div class="multi" key={i}>
            {Array.from({ length: c.nargs }, (_, j) => (
              <input class="input mono" value={r[j] ?? ''} placeholder={m.parts?.[j]} aria-label={`${m.label}: ${m.parts?.[j] ?? j + 1}`} onInput={(e) => setRow(i, j, (e.target as HTMLInputElement).value)} />
            ))}
            <Btn icon="minus" small kind="quiet" label="Remove" onClick={() => onChange(rows.filter((_, k) => k !== i))} />
          </div>
        ))}
        <div><Btn icon="plus" small label="Add" onClick={() => onChange([...rows, Array(c.nargs).fill('')])}>Add</Btn></div>
      </>
    );
  } else if (c.multiple) {
    const rows = (Array.isArray(value) ? value : value ? [value] : []) as string[];
    ctl = (
      <>
        {rows.map((r, i) => (
          <div class="multi" key={i}>
            <input class="input mono" value={r} list={m.suggest ? listId : undefined} placeholder={m.placeholder ?? ''} aria-label={`${m.label} ${i + 1}`}
              onInput={(e) => onChange(rows.map((x, k) => (k === i ? (e.target as HTMLInputElement).value : x)))} />
            {m.widget === 'folder' || m.widget === 'file' ? <Btn icon="folder" small kind="quiet" label="Browse" onClick={() => browse((p) => onChange(rows.map((x, k) => (k === i ? (x.includes(':') && !/^[a-zA-Z]:[\\/]/.test(x) ? `${x.split(':')[0]}:${p}` : p) : x))))} /> : null}
            <Btn icon="minus" small kind="quiet" label="Remove" onClick={() => onChange(rows.filter((_, k) => k !== i))} />
          </div>
        ))}
        <div><Btn icon="plus" small label="Add" onClick={() => onChange([...rows, ''])}>Add</Btn></div>
      </>
    );
  } else {
    const text = typeof value === 'string' ? value : '';
    const choices = m.choices ?? c.option!.choices;
    if (m.widget === 'select' && choices) {
      ctl = (
        <select class="select" aria-label={m.label} value={text} onChange={(e) => onChange((e.target as HTMLSelectElement).value || undefined)}>
          <option value="">Default{c.option!.default ? ` (${String(c.option!.default)})` : ''}</option>
          {choices.map((ch) => <option value={ch}>{ch}</option>)}
        </select>
      );
    } else {
      const numeric = m.widget === 'number';
      const input = (
        <input class={`input${m.widget === 'password' ? '' : ' mono'}`} type={m.widget === 'password' ? 'password' : 'text'} inputMode={numeric ? 'decimal' : undefined}
          autocomplete="off" value={text} list={m.suggest ? listId : undefined} aria-label={m.label}
          placeholder={m.placeholder ?? (c.option!.default != null && c.option!.default !== '' && typeof c.option!.default !== 'object' ? String(c.option!.default) : '')}
          onInput={(e) => onChange((e.target as HTMLInputElement).value)} />
      );
      ctl = m.widget === 'file' || m.widget === 'folder'
        ? <div class="row" style={{ gap: 4 }}>{input}<Btn icon="folder" small label="Browse" onClick={() => browse((p) => onChange(p))} /></div>
        : input;
    }
  }

  return (
    <div class={`opt${own !== undefined ? ' set' : ''}`} onMouseEnter={() => onHelp(c)} onFocusCapture={() => onHelp(c)}>
      <button type="button" class="name" title={m.tip} aria-expanded={open} onClick={() => setOpen(!open)}>
        <span class="l">{m.label}{own !== undefined ? <span class="sr"> (changed)</span> : null}</span>
        <span class="f">{flagsOf(c)}</span>
      </button>
      <div class="ctl">
        {ctl}
        {m.suggest ? <datalist id={listId}>{m.suggest.map((s) => <option value={s} />)}</datalist> : null}
        {fromElsewhere ? <span class="from">Set by {inheritedFrom}</span> : null}
      </div>
      {own !== undefined ? <Btn icon="arrow-back-up" small kind="quiet" label={`Reset ${m.label}`} title="Reset to default" onClick={() => onChange(undefined)} /> : <span />}
      {open ? <div class="tip">{m.tip}</div> : null}
    </div>
  );
}

export function extraProblems(extraArgs: string): string | null {
  if (!extraArgs.trim()) return null;
  try {
    const p = parseArgs(split(extraArgs, false));
    if (p.unknown.length) return `The engine does not have ${p.unknown.length === 1 ? 'an option' : 'options'} called ${p.unknown.join(', ')}.`;
    if (p.urls.length) return `Links go in the Links box, not here: ${p.urls.slice(0, 2).join(', ')}`;
    return null;
  } catch (e) {
    return `${(e as Error).message}.`;
  }
}

interface Props {
  values: OptionValues;
  inherited?: OptionValues;
  inheritedFrom?: string;
  extraArgs: string;
  onChange: (values: OptionValues) => void;
  onExtra: (text: string) => void;
}

export function Advanced({ values, inherited = {}, inheritedFrom = 'Simple options', extraArgs, onChange, onExtra }: Props) {
  const [cat, setCat] = useState('formats');
  const [query, setQuery] = useState('');
  const [help, setHelp] = useState<Control | null>(null);
  const listRef = useRef<HTMLDivElement>(null);

  const update = (id: string, v: Value | undefined) => {
    const next = { ...values };
    if (v === undefined) delete next[id]; else next[id] = v;
    onChange(next);
  };

  const q = query.trim().toLowerCase();
  const matches = useMemo(() => {
    if (!q) return null;
    return schema.controls.filter((c) => {
      const m = metaFor(c);
      if (m.tool) return false;
      return `${m.label} ${flagsOf(c)} ${m.tip}`.toLowerCase().includes(q);
    });
  }, [q]);

  const counts = useMemo(() => {
    const n: Record<string, number> = {};
    for (const id of Object.keys(values)) {
      const c = meta[id]?.category;
      if (c) n[c] = (n[c] ?? 0) + 1;
    }
    return n;
  }, [values]);

  const shown = matches ?? (cat === 'extra' ? [] : controlsByCategory.get(cat) ?? []);
  const current = visibleCategories.find((c) => c.id === cat);
  const problem = extraProblems(extraArgs);
  const helpMeta = help ? metaFor(help) : null;

  return (
    <div class="col grow">
      <div class="adv">
        <nav class="cats" aria-label="Option categories">
          <div class="filter" style={{ padding: '0 0 6px' }}>
            <Search value={query} onChange={setQuery} placeholder="Find an option" />
          </div>
          {visibleCategories.map((c) => (
            <button type="button" class="nav" aria-current={!q && cat === c.id ? 'page' : undefined} onClick={() => { setQuery(''); setCat(c.id); listRef.current?.scrollTo(0, 0); }}>
              <span class="ellipsis">{c.label}</span>
              {counts[c.id] ? <span class="dot" title={`${counts[c.id]} changed`}>{counts[c.id]}</span> : null}
            </button>
          ))}
          <button type="button" class="nav" aria-current={!q && cat === 'extra' ? 'page' : undefined} onClick={() => { setQuery(''); setCat('extra'); }}>
            <span class="ellipsis">Extra arguments</span>
            {extraArgs.trim() ? <span class="dot">1</span> : null}
          </button>
        </nav>
        <div class="list" ref={listRef}>
          {matches ? (
            <div class="cat-head"><h2>{matches.length} {matches.length === 1 ? 'option matches' : 'options match'} “{query.trim()}”</h2></div>
          ) : cat === 'extra' ? (
            <div class="cat-head">
              <h2>Extra arguments</h2>
              <p>Anything typed here is passed to the engine exactly as written, after the options above. Use it for old or hidden flags that have no control, or for aliases you defined.</p>
            </div>
          ) : (
            <div class="cat-head"><h2>{current?.label}</h2><p>{current?.blurb}</p></div>
          )}
          {shown.filter((c) => !metaFor(c).tool).map((c) => (
            <Row key={c.id} control={c} own={values[c.id]} inherited={inherited[c.id]} inheritedFrom={inheritedFrom} onChange={(v) => update(c.id, v)} onHelp={setHelp} />
          ))}
          {matches && !matches.length ? <p class="dim" style={{ padding: '4px 16px' }}>Nothing matches. Try the flag name, such as “--embed” or “proxy”.</p> : null}
          {!matches && cat === 'extra' ? (
            <div style={{ padding: '4px 16px 16px', display: 'flex', flexDirection: 'column', gap: 8 }}>
              <textarea class={`input mono${problem ? ' bad' : ''}`} rows={5} spellcheck={false} value={extraArgs} aria-label="Extra arguments"
                placeholder={'--prefer-free-formats --my-alias'} onInput={(e) => onExtra((e.target as HTMLTextAreaElement).value)} />
              {problem ? <p class="small state-error"><Icon name="alert-triangle" small /> {problem}</p> : <p class="small faint">Quote values that contain spaces, the same way you would in a terminal.</p>}
            </div>
          ) : null}
        </div>
      </div>
      <div class="helpline" aria-live="polite">
        {helpMeta && help
          ? <><b>{helpMeta.label}</b> <span class="mono faint">{help.kind === 'value' ? help.id : help.members.map((x) => x.id).join(' / ')}</span><br />{helpMeta.tip}</>
          : <span class="faint">Point at an option to read what it does, or click its name to keep the explanation open. A dot marks options you have changed.</span>}
      </div>
    </div>
  );
}
