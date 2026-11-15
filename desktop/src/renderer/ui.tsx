import type { ComponentChildren, JSX } from 'preact';
import { useEffect, useRef, useState } from 'preact/hooks';
import { icons, type IconName } from './icons.generated';
import { get, set, type DialogSpec } from './state';

export function Icon({ name, small, spin, label }: { name: IconName; small?: boolean; spin?: boolean; label?: string }) {
  return (
    <svg class={`icon${small ? ' s' : ''}${spin ? ' spin' : ''}`} viewBox="0 0 24 24" aria-hidden={label ? undefined : 'true'} role={label ? 'img' : undefined} aria-label={label}
      dangerouslySetInnerHTML={{ __html: icons[name] }} />
  );
}

type BtnProps = {
  icon?: IconName; label?: string; title?: string; kind?: 'primary' | 'quiet' | 'danger'; small?: boolean; disabled?: boolean; busy?: boolean;
  onClick?: (e: MouseEvent) => void; children?: ComponentChildren; autoFocus?: boolean;
};
export function Btn({ icon, label, title, kind, small, disabled, busy, onClick, children, autoFocus }: BtnProps) {
  const text = children;
  const ref = useRef<HTMLButtonElement>(null);
  useEffect(() => { if (autoFocus) ref.current?.focus(); }, []);
  return (
    <button ref={ref} type="button" class={`btn${kind ? ` ${kind}` : ''}${small ? ' sm' : ''}${text ? '' : ' icon-only'}`} title={title ?? (text ? undefined : label)}
      aria-label={text ? undefined : (title ?? label)} disabled={disabled || busy} onClick={onClick}>
      {busy ? <Icon name="loader-2" small={small} spin /> : icon ? <Icon name={icon} small={small} /> : null}
      {text}
    </button>
  );
}

export function Select({ value, options, onChange, label, disabled, style }: {
  value: string; options: readonly (readonly [string, string])[]; onChange: (v: string) => void; label?: string; disabled?: boolean; style?: JSX.CSSProperties;
}) {
  return (
    <select class="select" aria-label={label} value={value} disabled={disabled} style={style} onChange={(e) => onChange((e.target as HTMLSelectElement).value)}>
      {options.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
    </select>
  );
}

export function Check({ checked, onChange, children, disabled, dim }: { checked: boolean; onChange: (v: boolean) => void; children?: ComponentChildren; disabled?: boolean; dim?: boolean }) {
  return (
    <label class="check">
      <input type="checkbox" class={dim ? 'default' : ''} checked={checked} disabled={disabled} onChange={(e) => onChange((e.target as HTMLInputElement).checked)} />
      {children ? <span>{children}</span> : null}
    </label>
  );
}

export function Seg<T extends string>({ value, options, onChange, small, label }: { value: T; options: readonly (readonly [T, string])[]; onChange: (v: T) => void; small?: boolean; label: string }) {
  return (
    <div class={`seg${small ? ' sm' : ''}`} role="group" aria-label={label}>
      {options.map(([v, l]) => <button key={v} type="button" aria-pressed={value === v} onClick={() => onChange(v)}>{l}</button>)}
    </div>
  );
}

export function Tabs<T extends string>({ value, options, onChange, children }: { value: T; options: readonly (readonly [T, string])[]; onChange: (v: T) => void; children?: ComponentChildren }) {
  return (
    <div class="tabs" role="tablist">
      {options.map(([v, l]) => <button key={v} type="button" role="tab" aria-selected={value === v} onClick={() => onChange(v)}>{l}</button>)}
      {children}
    </div>
  );
}

export function Search({ value, onChange, placeholder, width, inputRef }: { value: string; onChange: (v: string) => void; placeholder: string; width?: number; inputRef?: { current: HTMLInputElement | null } }) {
  return (
    <div class="search">
      <Icon name="search" small />
      <input ref={inputRef} class="input" type="search" value={value} placeholder={placeholder} aria-label={placeholder} style={width ? { width } : undefined}
        onInput={(e) => onChange((e.target as HTMLInputElement).value)} onKeyDown={(e) => { if (e.key === 'Escape') { onChange(''); (e.target as HTMLInputElement).blur(); } }} />
    </div>
  );
}

export function Empty({ title, children }: { title: string; children?: ComponentChildren }) {
  return <div class="empty"><h2>{title}</h2>{children}</div>;
}

export function ask(spec: DialogSpec): void { set({ dialog: spec }); }

export function Dialog() {
  const spec = get().dialog;
  const [value, setValue] = useState('');
  const first = useRef<HTMLElement | null>(null);
  useEffect(() => {
    if (!spec) return;
    setValue(spec.input?.value ?? spec.choices?.[0]?.value ?? '');
    const prev = document.activeElement as HTMLElement | null;
    setTimeout(() => first.current?.focus(), 0);
    return () => prev?.focus?.();
  }, [spec]);
  if (!spec) return null;
  const close = () => set({ dialog: null });
  const confirm = () => { close(); spec.onConfirm(value); };
  return (
    <div class="scrim" onMouseDown={(e) => { if (e.target === e.currentTarget) close(); }}>
      <form class="dialog" role="dialog" aria-modal="true" aria-label={spec.title} onSubmit={(e) => { e.preventDefault(); confirm(); }}
        onKeyDown={(e) => { if (e.key === 'Escape') { e.stopPropagation(); close(); } }}>
        <header><h2>{spec.title}</h2></header>
        <div class="content">
          {spec.body ? spec.body.split('\n').map((p) => <p>{p}</p>) : null}
          {spec.input ? (
            <label class="col" style={{ gap: 4 }}>
              <span class="dim small">{spec.input.label}</span>
              <input ref={(el) => { first.current = el; }} class="input" type={spec.input.type ?? 'text'} value={value} placeholder={spec.input.placeholder}
                onInput={(e) => setValue((e.target as HTMLInputElement).value)} />
            </label>
          ) : null}
          {spec.choices ? (
            <select ref={(el) => { first.current = el; }} class="select" value={value} onChange={(e) => setValue((e.target as HTMLSelectElement).value)}>
              {spec.choices.map((c) => <option value={c.value}>{c.label}</option>)}
            </select>
          ) : null}
        </div>
        <footer>
          <button type="button" class="btn" onClick={close}>Cancel</button>
          <button type="submit" class={`btn ${spec.danger ? 'danger' : 'primary'}`} ref={(el) => { if (!spec.input && !spec.choices) first.current = el; }}>{spec.confirm}</button>
        </footer>
      </form>
    </div>
  );
}

export function when(ts?: number): string {
  if (!ts) return '';
  const d = new Date(ts);
  const now = new Date();
  const sameDay = d.toDateString() === now.toDateString();
  const time = d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  if (sameDay) return `Today ${time}`;
  const y = new Date(now.getTime() - 86_400_000);
  if (d.toDateString() === y.toDateString()) return `Yesterday ${time}`;
  return `${d.toLocaleDateString([], { day: 'numeric', month: 'short', year: d.getFullYear() === now.getFullYear() ? undefined : 'numeric' })} ${time}`;
}

export function Thumb({ src, large, audio }: { src?: string; large?: boolean; audio?: boolean }) {
  const [failed, setFailed] = useState(false);
  useEffect(() => setFailed(false), [src]);
  if (!src || failed) return <div class={`thumb${large ? ' lg' : ''}`}><Icon name={audio ? 'music' : 'movie'} /></div>;
  return <img class={`thumb${large ? ' lg' : ''}`} src={src} alt="" loading="lazy" referrerpolicy="no-referrer" onError={() => setFailed(true)} />;
}
