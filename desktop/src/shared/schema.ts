// The option schema. Everything here is derived from options.generated.json,
// which is dumped straight from yt-dlp's own argument parser, so the app can
// never know fewer options than the engine does.

import generated from './options.generated.json';

export interface RawOption {
  id: string;
  flags: string[];
  group: string;
  action: string;
  type: string | null;
  dest: string | null;
  default: unknown;
  const: unknown;
  choices: string[] | null;
  metavar: string | null;
  help: string;
  hidden: boolean;
  takesValue: boolean;
  nargs: number;
  callback: string | null;
  allowedKeys: string | null;
  allowedValues: unknown;
  multipleKeys: boolean | null;
}

/** A single thing the user can set. Either one value-taking option, or a set
 * of mutually exclusive no-argument flags that write to the same setting. */
export interface Control {
  id: string;
  kind: 'value' | 'switch';
  group: string;
  dest: string | null;
  /** value controls */
  option?: RawOption;
  multiple: boolean;
  nargs: number;
  /** switch controls: every flag that can be chosen */
  members: RawOption[];
  /** switch with exactly one "--x" and one "--no-x" member */
  onFlag?: string;
  offFlag?: string;
  defaultOn?: boolean;
}

export type Value = string | string[] | string[][];
export type OptionValues = Record<string, Value>;

export interface Schema {
  engineVersion: string;
  options: RawOption[];
  controls: Control[];
  byFlag: Map<string, RawOption>;
  controlById: Map<string, Control>;
  controlByFlag: Map<string, Control>;
}

const REPEATABLE_CALLBACKS = new Set([
  '_dict_from_options_callback',
  '_create_alias',
  '_preset_alias_callback',
]);
// List-style options where repeating the flag adds to the list.
const REPEATABLE_IDS = new Set([
  '--js-runtimes', '--remote-components', '--plugin-dirs', '--use-postprocessor',
  '--match-filters', '--break-match-filters', '--download-sections', '--remove-chapters',
  '--config-locations',
]);

function memberValue(o: RawOption): unknown {
  if (o.action === 'store_true') return true;
  if (o.action === 'store_false') return false;
  if (o.action === 'store_const') return o.const;
  return undefined;
}

function same(a: unknown, b: unknown): boolean {
  return JSON.stringify(a ?? false) === JSON.stringify(b ?? false);
}

export function buildSchema(raw: { engineVersion: string; options: RawOption[] } = generated as never): Schema {
  const options = raw.options;
  const byFlag = new Map<string, RawOption>();
  for (const o of options) for (const f of o.flags) byFlag.set(f, o);

  const controls: Control[] = [];
  const switchByDest = new Map<string, Control>();
  for (const o of options) {
    if (o.hidden) continue;
    if (o.takesValue) {
      const multiple = o.action === 'append' || o.nargs > 1 || REPEATABLE_IDS.has(o.id)
        || (o.callback !== null && REPEATABLE_CALLBACKS.has(o.callback));
      controls.push({ id: o.id, kind: 'value', group: o.group, dest: o.dest, option: o, multiple, nargs: o.nargs, members: [] });
      continue;
    }
    const key = o.dest ?? o.id;
    let c = switchByDest.get(key);
    if (!c) {
      c = { id: o.id, kind: 'switch', group: o.group, dest: o.dest, multiple: false, nargs: 0, members: [] };
      switchByDest.set(key, c);
      controls.push(c);
    }
    c.members.push(o);
  }
  for (const c of controls) {
    if (c.kind !== 'switch' || c.members.length !== 2) continue;
    const neg = c.members.filter((m) => m.id.startsWith('--no-'));
    if (neg.length !== 1) continue;
    const on = c.members.find((m) => m !== neg[0])!;
    c.id = on.id;
    c.onFlag = on.id;
    c.offFlag = neg[0].id;
    c.defaultOn = same(on.default, memberValue(on));
  }
  const controlById = new Map<string, Control>();
  const controlByFlag = new Map<string, Control>();
  for (const c of controls) {
    controlById.set(c.id, c);
    for (const o of c.option ? [c.option] : c.members) for (const f of o.flags) controlByFlag.set(f, c);
  }
  return { engineVersion: raw.engineVersion, options, controls, byFlag, controlById, controlByFlag };
}

export const schema: Schema = buildSchema();
