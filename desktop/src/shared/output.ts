// Reads the engine's output line by line and turns it into events.

import type { Stage } from './errors';

export const PROGRESS_PREFIX = '@@dl ';
export const POST_PREFIX = '@@pp ';

/** Arguments the app adds so it can follow a download. Each entry is skipped
 * when the user has set the same option themselves, so nothing is overridden. */
export const instrumentation: { unlessSet: string[]; args: string[] }[] = [
  { unlessSet: ['--newline'], args: ['--newline'] },
  { unlessSet: ['--color'], args: ['--color', 'no_color'] },
  { unlessSet: ['--encoding'], args: ['--encoding', 'utf-8'] },
  {
    unlessSet: ['--progress-template'],
    args: [
      '--progress-template',
      `download:${PROGRESS_PREFIX}%(progress.{status,downloaded_bytes,total_bytes,total_bytes_estimate,speed,eta,fragment_index,fragment_count})j %(info.{id,title,playlist_index,playlist_count,n_entries,thumbnail,duration,uploader,webpage_url})j`,
      '--progress-template',
      `postprocess:${POST_PREFIX}%(progress.{status,postprocessor})j`,
    ],
  },
];

export interface ItemInfo {
  id?: string;
  title?: string;
  playlist_index?: number;
  playlist_count?: number;
  n_entries?: number;
  thumbnail?: string;
  duration?: number;
  uploader?: string;
  webpage_url?: string;
}

export type OutputEvent =
  | { type: 'progress'; status: string; downloaded?: number; total?: number; estimated: boolean; speed?: number; eta?: number; fragment?: number; fragments?: number; info: ItemInfo }
  | { type: 'post'; status: string; name: string }
  | { type: 'stage'; stage: Stage; label?: string }
  | { type: 'item'; index: number; count: number }
  | { type: 'destination'; path: string }
  | { type: 'already'; path?: string }
  | { type: 'skipped'; reason: string }
  | { type: 'error'; message: string }
  | { type: 'warning'; message: string }
  | { type: 'waiting'; message: string }
  | { type: 'text'; text: string };

const POST_LABELS: Record<string, string> = {
  Merger: 'Merging video and audio',
  ExtractAudio: 'Extracting audio',
  VideoConvertor: 'Converting video',
  VideoRemuxer: 'Changing container',
  Metadata: 'Writing metadata',
  EmbedSubtitle: 'Embedding subtitles',
  EmbedThumbnail: 'Embedding thumbnail',
  ThumbnailsConvertor: 'Converting thumbnail',
  SubtitlesConvertor: 'Converting subtitles',
  SponsorBlock: 'Checking SponsorBlock',
  ModifyChapters: 'Editing chapters',
  SplitChapters: 'Splitting chapters',
  MoveFiles: 'Moving files into place',
  FixupM3u8: 'Repairing container',
  FixupM4a: 'Repairing container',
  FixupStretched: 'Fixing aspect ratio',
  FixupTimestamp: 'Fixing timestamps',
  FixupDuration: 'Fixing duration',
  FixupDuplicateMoov: 'Repairing container',
  Concat: 'Joining files',
  Exec: 'Running your command',
  XAttrMetadata: 'Writing file attributes',
};

export function postLabel(name: string): string {
  return POST_LABELS[name] ?? POST_LABELS[name.replace(/^FFmpeg/, '')] ?? name;
}

function stageForPost(name: string): Stage {
  if (name === 'Merger') return 'merge';
  if (name === 'MoveFiles') return 'write';
  return 'post';
}

function num(v: unknown): number | undefined {
  return typeof v === 'number' && Number.isFinite(v) ? v : undefined;
}

function splitJsonPair(s: string): [string, string] {
  // Two JSON objects separated by a space. Find the end of the first one.
  let depth = 0, inStr = false, esc = false;
  for (let i = 0; i < s.length; i++) {
    const c = s[i];
    if (inStr) { if (esc) esc = false; else if (c === '\\') esc = true; else if (c === '"') inStr = false; continue; }
    if (c === '"') inStr = true;
    else if (c === '{') depth++;
    else if (c === '}' && --depth === 0) return [s.slice(0, i + 1), s.slice(i + 1).trim()];
  }
  return [s, ''];
}

export function parseLine(line: string): OutputEvent {
  const text = line.replace(/\r$/, '');
  if (text.startsWith(PROGRESS_PREFIX)) {
    try {
      const [a, b] = splitJsonPair(text.slice(PROGRESS_PREFIX.length));
      const p = JSON.parse(a) as Record<string, unknown>;
      const info = (b ? JSON.parse(b) : {}) as ItemInfo;
      const total = num(p.total_bytes);
      return {
        type: 'progress', status: String(p.status ?? 'downloading'), downloaded: num(p.downloaded_bytes),
        total: total ?? num(p.total_bytes_estimate), estimated: total === undefined,
        speed: num(p.speed), eta: num(p.eta), fragment: num(p.fragment_index), fragments: num(p.fragment_count), info,
      };
    } catch { return { type: 'text', text }; }
  }
  if (text.startsWith(POST_PREFIX)) {
    try {
      const p = JSON.parse(text.slice(POST_PREFIX.length)) as Record<string, unknown>;
      return { type: 'post', status: String(p.status), name: String(p.postprocessor ?? '') };
    } catch { return { type: 'text', text }; }
  }
  let m: RegExpExecArray | null;
  if ((m = /^(?:\[[^\]]+\] )?ERROR: (.*)$/.exec(text))) return { type: 'error', message: m[1] };
  // a rejected option; the prefix is kept so the translator can tell it apart from a download failure
  if ((m = /^(?:yt-dlp|yt_dlp|__main__\.py)(?:\.exe)?: error: (.*)$/.exec(text))) return { type: 'error', message: `yt-dlp: error: ${m[1]}` };
  if ((m = /^WARNING: (.*)$/.exec(text))) return { type: 'warning', message: m[1] };
  if ((m = /^\[download\] Downloading (?:item|video) (\d+) of (\d+)/.exec(text))) return { type: 'item', index: +m[1], count: +m[2] };
  if ((m = /^\[download\] Destination: (.*)$/.exec(text))) return { type: 'destination', path: m[1] };
  if ((m = /^\[download\] (.*) has already been downloaded/.exec(text))) return { type: 'already', path: m[1] };
  if (/has already been recorded in the archive/.test(text)) return { type: 'skipped', reason: 'Already in the archive' };
  if ((m = /^\[download\] (.*does not pass filter.*)$/.exec(text))) return { type: 'skipped', reason: 'Skipped by a filter rule' };
  if (/^\[wait\]|Waiting for .* (?:video|stream)|will begin in|Remaining time until next attempt/.test(text)) return { type: 'waiting', message: text.replace(/^\[\w+\] /, '') };
  if ((m = /^\[(Merger|ExtractAudio|VideoConvertor|VideoRemuxer|Metadata|EmbedSubtitle|EmbedThumbnail|ThumbnailsConvertor|SubtitlesConvertor|SponsorBlock|ModifyChapters|SplitChapters|MoveFiles|Fixup\w+|FFmpeg\w*|Concat|Exec|XAttrMetadata)\]/.exec(text))) {
    return { type: 'stage', stage: stageForPost(m[1]), label: postLabel(m[1]) };
  }
  if (/^\[info\] .*Downloading \d+ format/.test(text)) return { type: 'stage', stage: 'format' };
  if (/^\[download\]/.test(text)) return { type: 'stage', stage: 'download' };
  if (/^\[[\w:.+-]+\] /.test(text) && !/^\[(?:debug|info|generic)\] /.test(text)) return { type: 'stage', stage: 'info' };
  return { type: 'text', text };
}

/** Splits a stream of chunks into complete lines. */
export class LineBuffer {
  private rest = '';
  push(chunk: string): string[] {
    const parts = (this.rest + chunk).split(/\r?\n|\r/);
    this.rest = parts.pop() ?? '';
    return parts;
  }
  flush(): string[] {
    const r = this.rest;
    this.rest = '';
    return r ? [r] : [];
  }
}

export function formatBytes(n?: number): string {
  if (n === undefined || n === null || !Number.isFinite(n)) return '';
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  let i = 0;
  let v = n;
  while (v >= 1024 && i < units.length - 1) { v /= 1024; i++; }
  return `${v >= 100 || i === 0 ? v.toFixed(0) : v >= 10 ? v.toFixed(1) : v.toFixed(2)} ${units[i]}`;
}

export function formatDuration(seconds?: number): string {
  if (seconds === undefined || seconds === null || !Number.isFinite(seconds)) return '';
  const s = Math.max(0, Math.round(seconds));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const ss = String(s % 60).padStart(2, '0');
  return h ? `${h}:${String(m).padStart(2, '0')}:${ss}` : `${m}:${ss}`;
}
