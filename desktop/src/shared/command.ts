// Turns option values into a yt-dlp argument list and back again.

import { schema as defaultSchema, type Control, type OptionValues, type Schema, type Value } from './schema';
import { join, split } from './shlex';

function rows(control: Control, value: Value): string[][] {
  if (control.nargs > 1) {
    return (value as string[][]).filter((r) => Array.isArray(r) && r.some((x) => x !== ''));
  }
  if (Array.isArray(value)) return (value as string[]).filter((v) => v !== '').map((v) => [v]);
  return value === '' || value == null ? [] : [[String(value)]];
}

/** Arguments for the options alone, in the parser's own order. */
export function buildOptionArgs(values: OptionValues, schema: Schema = defaultSchema): string[] {
  const args: string[] = [];
  for (const control of schema.controls) {
    const value = values[control.id];
    if (value === undefined || value === null) continue;
    if (control.kind === 'switch') {
      if (typeof value === 'string' && control.members.some((m) => m.id === value)) args.push(value);
      continue;
    }
    for (const row of rows(control, value)) args.push(control.id, ...row);
  }
  return args;
}

export interface CommandParts {
  values: OptionValues;
  extraArgs?: string;
  urls?: string[];
}

/** The full user-facing argument list: options, raw extra arguments, then URLs. */
export function buildArgs(parts: CommandParts, schema: Schema = defaultSchema): string[] {
  const args = buildOptionArgs(parts.values, schema);
  if (parts.extraArgs?.trim()) args.push(...split(parts.extraArgs, false));
  if (parts.urls?.length) {
    if (parts.urls.some((u) => u.startsWith('-'))) args.push('--');
    args.push(...parts.urls);
  }
  return args;
}

export function formatCommand(args: string[], program = 'yt-dlp'): string {
  return join([program, ...args]);
}

export interface ParsedArgs {
  values: OptionValues;
  /** Arguments that are valid for the engine but have no control (hidden or deprecated flags). */
  extra: string[];
  urls: string[];
  /** Arguments the engine would not recognise at all. */
  unknown: string[];
}

/** The reverse of buildArgs. Used to import config files and pasted commands. */
export function parseArgs(argv: string[], schema: Schema = defaultSchema): ParsedArgs {
  const values: OptionValues = {};
  const extra: string[] = [];
  const urls: string[] = [];
  const unknown: string[] = [];

  const apply = (flag: string, vals: string[]) => {
    const control = schema.controlByFlag.get(flag);
    const option = schema.byFlag.get(flag)!;
    if (!control) { extra.push(flag, ...vals); return; }
    if (control.kind === 'switch') { values[control.id] = option.id; return; }
    if (control.nargs > 1) {
      values[control.id] = [...((values[control.id] as string[][]) ?? []), vals];
    } else if (control.multiple) {
      values[control.id] = [...((values[control.id] as string[]) ?? []), vals[0]];
    } else values[control.id] = vals[0];
  };

  let i = 0;
  const take = (flag: string, inline: string | undefined): void => {
    const option = schema.byFlag.get(flag)!;
    if (!option.takesValue) { apply(flag, []); return; }
    const vals: string[] = [];
    if (inline !== undefined) vals.push(inline);
    while (vals.length < option.nargs && i < argv.length) vals.push(argv[i++]);
    apply(flag, vals);
  };

  while (i < argv.length) {
    const arg = argv[i++];
    if (arg === '--') { urls.push(...argv.slice(i)); break; }
    if (arg.startsWith('--')) {
      const eq = arg.indexOf('=');
      const name = eq === -1 ? arg : arg.slice(0, eq);
      const inline = eq === -1 ? undefined : arg.slice(eq + 1);
      let flag = schema.byFlag.has(name) ? name : undefined;
      if (!flag) {
        // optparse accepts unambiguous abbreviations
        const hits = [...schema.byFlag.keys()].filter((f) => f.startsWith(name));
        const targets = new Set(hits.map((f) => schema.byFlag.get(f)!.id));
        if (hits.length && targets.size === 1) flag = hits[0];
      }
      if (!flag) { unknown.push(arg); continue; }
      take(flag, inline);
    } else if (arg.startsWith('-') && arg.length > 1) {
      let j = 1;
      while (j < arg.length) {
        const flag = '-' + arg[j++];
        const option = schema.byFlag.get(flag);
        if (!option) { unknown.push(flag); continue; }
        if (option.takesValue) {
          const rest = arg.slice(j);
          take(flag, rest === '' ? undefined : rest);
          break;
        }
        take(flag, undefined);
      }
    } else urls.push(arg);
  }
  return { values, extra, urls, unknown };
}

/** Parse the text of a yt-dlp config file. */
export function parseConfigText(text: string, schema: Schema = defaultSchema): ParsedArgs {
  return parseArgs(split(text.replace(/^﻿/, ''), true), schema);
}

/** Write option values as a yt-dlp config file, one option per line. */
export function toConfigText(parts: CommandParts, header: string, schema: Schema = defaultSchema): string {
  const lines = header ? header.split('\n').map((l) => `# ${l}`) : [];
  const args = buildOptionArgs(parts.values, schema);
  let i = 0;
  while (i < args.length) {
    const option = schema.byFlag.get(args[i])!;
    const n = option.takesValue ? option.nargs : 0;
    lines.push(join(args.slice(i, i + 1 + n)));
    i += 1 + n;
  }
  if (parts.extraArgs?.trim()) lines.push(parts.extraArgs.trim());
  return lines.join('\n') + '\n';
}
