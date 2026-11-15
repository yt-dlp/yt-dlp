// One small store for the whole window.
import { useEffect, useState } from 'preact/hooks';
import type { OptionValues } from '../shared/schema';
import { defaultSimple, type SimpleChoices } from '../shared/simple';
import type { Api, AppUpdateStatus, EngineInfo, EngineUpdateStatus, Job, Preset, ProbeResult, Settings } from '../shared/types';
import { defaultSettings } from '../shared/types';

export const api = (window as unknown as { api: Api & { pathForFile?: (f: File) => string } }).api;

export type View = 'queue' | 'new' | 'history' | 'presets' | 'logs' | 'engine' | 'settings' | 'help';

export interface Draft {
  text: string;
  simple: SimpleChoices;
  advanced: OptionValues;
  extraArgs: string;
  presetId: string;
  tab: 'simple' | 'advanced';
  overrides: Record<string, { format?: string; skip?: number[] }>;
  scheduleAt: string;
  /** set when the draft edits an existing download instead of creating new ones */
  editJobId?: string;
  editPresetId?: string;
}

export interface DialogSpec {
  title: string;
  body?: string;
  input?: { label: string; value: string; placeholder?: string; type?: string };
  choices?: { value: string; label: string }[];
  confirm: string;
  danger?: boolean;
  onConfirm: (value: string) => void;
}

export interface Toast { id: number; text: string; action?: { label: string; run: () => void } }

export interface State {
  ready: boolean;
  view: View;
  jobs: Job[];
  history: Job[];
  settings: Settings;
  presets: Preset[];
  engine: EngineInfo | null;
  engineUpdate: EngineUpdateStatus;
  appUpdate: AppUpdateStatus;
  appVersion: string;
  draft: Draft;
  previews: Record<string, ProbeResult | 'loading'>;
  selected: string[];
  dialog: DialogSpec | null;
  welcome: boolean;
  toasts: Toast[];
  logTarget: string | null;
  helpAnchor: string | null;
}

export function blankDraft(settings: Settings): Draft {
  return { text: '', simple: { ...defaultSimple, ...settings.simple, folder: settings.downloadFolder }, advanced: {}, extraArgs: '', presetId: '', tab: 'simple', overrides: {}, scheduleAt: '' };
}

let state: State = {
  ready: false, view: 'queue', jobs: [], history: [], settings: defaultSettings, presets: [], engine: null,
  engineUpdate: { state: 'idle' }, appUpdate: { state: 'idle' }, appVersion: '', draft: blankDraft(defaultSettings),
  previews: {}, selected: [], dialog: null, welcome: false, toasts: [], logTarget: null, helpAnchor: null,
};
const listeners = new Set<() => void>();

export const get = (): State => state;
export function set(patch: Partial<State> | ((s: State) => Partial<State>)): void {
  state = { ...state, ...(typeof patch === 'function' ? patch(state) : patch) };
  listeners.forEach((l) => l());
}
export function useStore(): State {
  const [, force] = useState(0);
  useEffect(() => {
    const l = () => force((n) => n + 1);
    listeners.add(l);
    return () => { listeners.delete(l); };
  }, []);
  return state;
}

export function setDraft(patch: Partial<Draft>): void { set((s) => ({ draft: { ...s.draft, ...patch } })); }

let toastId = 0;
export function toast(text: string, action?: Toast['action']): void {
  const id = ++toastId;
  set((s) => ({ toasts: [...s.toasts.slice(-2), { id, text, action }] }));
  setTimeout(() => set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })), action ? 8000 : 4000);
}

export async function saveSettings(patch: Partial<Settings>): Promise<void> {
  set({ settings: await api.setSettings(patch) });
}

export function go(view: View): void { set({ view }); }

/** Split pasted or typed text into links, and say which lines are not links. */
export function parseLinks(text: string): { links: string[]; rejected: string[] } {
  const links: string[] = [];
  const rejected: string[] = [];
  for (const raw of text.split(/[\r\n]+/)) {
    const line = raw.trim();
    if (!line || /^[#;\]]/.test(line)) continue;
    for (const part of /^[a-z][a-z0-9+.-]*:/i.test(line) && !/^https?:/i.test(line) ? [line] : line.split(/\s+/)) {
      if (/^https?:\/\/[^\s/]+\.[^\s]+|^https?:\/\/(localhost|\d+\.\d+\.\d+\.\d+)/i.test(part) || /^[a-z][a-z0-9]*(search)?\d*:.+/i.test(part)) {
        if (!links.includes(part)) links.push(part);
      } else if (/^([\w-]+\.)+[a-z]{2,}(\/\S*)?$/i.test(part)) {
        const fixed = `https://${part}`;
        if (!links.includes(fixed)) links.push(fixed);
      } else rejected.push(part);
    }
  }
  return { links, rejected };
}

export function startNew(text = '', presetId?: string): void {
  const s = get();
  const draft = s.draft.editJobId || s.draft.editPresetId ? blankDraft(s.settings) : { ...s.draft };
  if (text) {
    const existing = draft.text.trim();
    draft.text = existing ? `${existing}\n${text}` : text;
  }
  set({ view: 'new', draft });
  const id = presetId ?? (draft.presetId || s.settings.lastPresetId);
  if (presetId || (!draft.presetId && id)) applyPreset(id);
}

export function applyPreset(id: string): void {
  const s = get();
  const p = s.presets.find((x) => x.id === id);
  if (!p) { setDraft({ presetId: '' }); return; }
  setDraft({ presetId: id, simple: { ...p.simple, folder: s.draft.simple.folder || s.settings.downloadFolder }, advanced: { ...p.advanced }, extraArgs: p.extraArgs, tab: Object.keys(p.advanced).length || p.extraArgs ? s.draft.tab : s.draft.tab });
}
