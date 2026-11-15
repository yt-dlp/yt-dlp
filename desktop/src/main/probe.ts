// Looks a link up without downloading it, for the preview.

import { buildOptionArgs } from '../shared/command';
import { errorLines, translate } from '../shared/errors';
import { meta } from '../shared/meta';
import type { OptionValues } from '../shared/schema';
import type { FormatInfo, ProbeEntry, ProbeResult } from '../shared/types';
import type { Engine } from './engine';
import { scrub } from './logs';

const PROBE_CATEGORIES = new Set(['network', 'auth', 'extractor', 'config']);
const PROBE_EXTRA = new Set(['--yes-playlist']);

/** Only the options that change what a site returns: sign-in, network, site settings. */
export function probeValues(values: OptionValues): OptionValues {
  const out: OptionValues = {};
  for (const [k, v] of Object.entries(values)) {
    if (PROBE_EXTRA.has(k) || PROBE_CATEGORIES.has(meta[k]?.category ?? '')) out[k] = v;
  }
  delete out['--mark-watched'];
  delete out['--alias'];
  delete out['--preset-alias'];
  return out;
}

type Json = Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any

function thumb(j: Json): string | undefined {
  if (typeof j.thumbnail === 'string') return j.thumbnail;
  const list = Array.isArray(j.thumbnails) ? j.thumbnails : [];
  return list.length ? list[list.length - 1].url : undefined;
}

function format(f: Json): FormatInfo {
  const hasV = f.vcodec && f.vcodec !== 'none';
  const hasA = f.acodec && f.acodec !== 'none';
  const isImage = f.ext === 'mhtml' || /storyboard/i.test(f.format_note ?? '');
  return {
    id: String(f.format_id), ext: f.ext ?? '', resolution: f.resolution ?? (f.height ? `${f.width ?? '?'}x${f.height}` : hasA && !hasV ? 'audio only' : ''),
    height: f.height ?? undefined, fps: f.fps ?? undefined,
    vcodec: hasV ? String(f.vcodec).split('.')[0] : undefined, acodec: hasA ? String(f.acodec).split('.')[0] : undefined,
    tbr: f.tbr ?? undefined, size: f.filesize ?? f.filesize_approx ?? undefined, sizeApprox: !f.filesize && !!f.filesize_approx,
    note: [f.format_note, f.language, f.dynamic_range && f.dynamic_range !== 'SDR' ? f.dynamic_range : null].filter(Boolean).join(', '),
    kind: isImage ? 'other' : f.vcodec === 'none' && f.acodec !== 'none' ? 'audio' : f.acodec === 'none' && f.vcodec !== 'none' ? 'video' : 'video+audio',
  };
}

export class Prober {
  private active = new Map<string, AbortController>();
  constructor(private engine: Engine) {}

  cancel(url: string): void { this.active.get(url)?.abort(); }

  async probe(url: string, values: OptionValues): Promise<ProbeResult> {
    this.cancel(url);
    const ctl = new AbortController();
    this.active.set(url, ctl);
    const pv = probeValues(values);
    const args = [...buildOptionArgs(pv), ...this.engine.internalArgs(pv, '', undefined, false), '--dump-single-json', '--flat-playlist', '--no-warnings', '--', url];
    const res = await this.engine.run(args, { timeoutMs: 180_000, signal: ctl.signal });
    if (this.active.get(url) === ctl) this.active.delete(url);
    const log = scrub(res.stderr.trim());
    if (ctl.signal.aborted) return { ok: false, url, log };

    let j: Json | null = null;
    try { j = JSON.parse(res.stdout.trim().split('\n').filter((l) => l.startsWith('{')).pop() ?? ''); } catch { j = null; }
    if (!j) {
      const lines = errorLines(res.stderr);
      const raw = lines.length ? lines.join('\n').replace(/^ERROR: /gm, '') : res.stderr.trim() || 'engine binary not found';
      return { ok: false, url, error: res.code === null && !res.stderr ? translate('ENOENT', 'starting') : translate(raw, 'info'), log };
    }
    if (j._type === 'playlist' || Array.isArray(j.entries)) {
      const entries: ProbeEntry[] = (j.entries ?? []).filter(Boolean).map((e: Json, i: number) => ({
        id: e.id, title: e.title ?? e.url ?? `Item ${i + 1}`, url: e.url ?? e.webpage_url, duration: e.duration ?? undefined,
        uploader: e.uploader ?? e.channel ?? undefined, thumbnail: thumb(e), index: i + 1,
      }));
      return {
        ok: true, url, kind: 'playlist', title: j.title ?? url, uploader: j.uploader ?? j.channel ?? undefined,
        thumbnail: thumb(j) ?? entries[0]?.thumbnail, extractor: j.extractor_key ?? j.extractor, webpageUrl: j.webpage_url,
        entries, count: j.playlist_count ?? entries.length, log,
      };
    }
    const formats: FormatInfo[] = (j.formats ?? []).map(format).filter((f: FormatInfo) => f.kind !== 'other').reverse();
    return {
      ok: true, url, kind: 'video', title: j.title ?? url, uploader: j.uploader ?? j.channel ?? j.creator ?? undefined,
      duration: j.duration ?? undefined, thumbnail: thumb(j), extractor: j.extractor_key ?? j.extractor, webpageUrl: j.webpage_url,
      live: j.is_live === true || j.live_status === 'is_upcoming', formats,
      subtitles: Object.keys(j.subtitles ?? {}), autoSubtitles: Object.keys(j.automatic_captions ?? {}).length, log,
    };
  }
}
