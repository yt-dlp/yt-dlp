// The download queue. Each job is one engine process; this file starts them,
// follows their output, and keeps the queue and history on disk.

import type { ChildProcess } from 'node:child_process';
import { existsSync, readdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { buildArgs, formatCommand, parseArgs } from '../shared/command';
import { stageLabels, translate, translateExit, type Friendly, type Stage } from '../shared/errors';
import { LineBuffer, parseLine, postLabel, PROGRESS_PREFIX, POST_PREFIX, formatBytes } from '../shared/output';
import { redactArgs } from '../shared/redact';
import type { OptionValues } from '../shared/schema';
import { split } from '../shared/shlex';
import type { Job, JobSpec, Settings } from '../shared/types';
import { killTree, type Engine } from './engine';
import { scrub, type Logs } from './logs';
import type { JsonStore } from './store';

const MAX_OUTPUT = 512 * 1024;
const MAX_HISTORY = 2000;
const PRINT_FLAGS = ['--simulate', '--print', '--dump-json', '--dump-single-json', '--list-formats', '--list-subs', '--list-thumbnails'];
const RETRYABLE = new Set(['network-down', 'connection-dropped']);

interface Running {
  child: ChildProcess;
  intent: 'pause' | 'cancel' | null;
  partials: Set<string>;
  errors: string[];
  lastProgressLog: number;
  eventsFile: string;
}

export interface JobDeps {
  engine: Engine;
  logs: Logs;
  settings: () => Settings;
  queue: JsonStore<Job[]>;
  history: JsonStore<Job[]>;
  onChange: (jobs: Job[]) => void;
  onFinished?: (job: Job) => void;
  appVersion?: string;
}

export function isPrintOnly(values: OptionValues, extraArgs: string): boolean {
  const all: OptionValues = { ...values };
  try { Object.assign(all, parseArgs(split(extraArgs || '', false)).values); } catch { /* engine will complain */ }
  if (all['--simulate'] === '--no-simulate') return false;
  if (/(^|\s)--get-\w+|(^|\s)-[a-zA-Z]*[FjJOs]/.test(extraArgs || '')) return true;
  return PRINT_FLAGS.some((f) => {
    const v = all[f];
    return Array.isArray(v) ? v.length > 0 : v !== undefined && v !== '' && v !== '--no-simulate';
  });
}

export class JobManager {
  private jobs: Job[];
  private running = new Map<string, Running>();
  private emitTimer: NodeJS.Timeout | null = null;
  private tick: NodeJS.Timeout;
  private closed = false;

  constructor(private deps: JobDeps) {
    this.jobs = deps.queue.get().map((j) => ({
      ...j,
      // anything that was mid-flight when the app last closed picks up where it stopped
      state: j.state === 'running' ? 'queued' : j.state,
      note: j.state === 'running' ? 'Resumed after the app was closed' : j.note,
      progress: j.state === 'running' ? { ...j.progress, speed: undefined, eta: undefined } : j.progress,
    }));
    this.tick = setInterval(() => this.promoteScheduled(), 3000);
    this.tick.unref();
    setImmediate(() => this.pump());
  }

  // ---- queries -------------------------------------------------------------

  list(): Job[] {
    return this.jobs.map((j) => ({ ...j, output: '' }));
  }

  get(id: string): Job | undefined { return this.jobs.find((j) => j.id === id) ?? this.deps.history.get().find((j) => j.id === id); }

  history(): Job[] { return this.deps.history.get().map((j) => ({ ...j, output: '' })); }

  activeCount(): number { return this.running.size; }

  userArgs(job: Job): string[] {
    return buildArgs({ values: job.values, extraArgs: job.extraArgs, urls: job.url ? [job.url] : [] });
  }

  fullArgs(job: Job, eventsFile?: string): string[] {
    const options = buildArgs({ values: job.values, extraArgs: job.extraArgs });
    const urls = job.url ? (job.url.startsWith('-') ? ['--', job.url] : [job.url]) : [];
    return [...options, ...this.deps.engine.internalArgs(job.values, job.extraArgs, eventsFile), ...urls];
  }

  command(id: string, internal: boolean): string {
    const job = this.get(id);
    if (!job) return '';
    return formatCommand(redactArgs(internal ? this.fullArgs(job, path.join(this.deps.logs.jobsDir, `${job.id}.events`)) : this.userArgs(job)));
  }

  async report(id: string): Promise<string> {
    const job = this.get(id);
    if (!job) return '';
    const info = await this.deps.engine.info();
    const log = this.deps.logs.readJob(id).split('\n');
    const lines = [
      'Dubdeck problem report',
      '',
      `App version:    ${this.deps.appVersion ?? 'unknown'}`,
      `Engine:         yt-dlp ${info.version || 'missing'} (${info.source})`,
      `ffmpeg:         ${info.ffmpeg.version || 'missing'} (${info.ffmpeg.source})`,
      `System:         ${os.type()} ${os.release()} ${os.arch()}`,
      `Link:           ${scrub(job.url)}`,
      `Result:         ${job.state}${job.exitCode != null ? ` (exit code ${job.exitCode})` : ''}`,
      `Stage:          ${stageLabels[job.error?.stage ?? job.stage]}`,
      `Problem:        ${job.error ? `${job.error.title} [${job.error.code}]` : 'none recorded'}`,
      `Engine message: ${job.error ? scrub(job.error.raw) : ''}`,
      '',
      'Command:',
      `  ${this.command(id, false)}`,
      '',
      `Log (last ${Math.min(log.length, 300)} lines, private details removed):`,
      ...log.slice(-300).map((l) => `  ${l}`),
    ];
    return lines.join('\n');
  }

  // ---- changes -------------------------------------------------------------

  add(specs: JobSpec[]): void {
    const now = Date.now();
    specs.forEach((s, i) => {
      const scheduled = s.scheduledFor && s.scheduledFor > now + 1000;
      this.jobs.push({
        id: `${(now + i).toString(36)}${Math.random().toString(36).slice(2, 6)}`,
        url: s.url, title: s.title || s.url || 'Download', thumbnail: s.thumbnail, uploader: s.uploader, duration: s.duration,
        summary: s.summary, values: s.values, extraArgs: s.extraArgs,
        state: scheduled ? 'scheduled' : 'queued', stage: 'starting', progress: {}, files: [], warnings: [], output: '', outputSize: 0,
        createdAt: now + i, scheduledFor: scheduled ? s.scheduledFor : undefined, attempts: 0,
        printOnly: isPrintOnly(s.values, s.extraArgs),
      });
    });
    this.changed();
    this.pump();
  }

  action(ids: string[], action: 'pause' | 'resume' | 'cancel' | 'retry' | 'remove' | 'start'): void {
    for (const id of ids) {
      const job = this.jobs.find((j) => j.id === id);
      if (!job) continue;
      const run = this.running.get(id);
      switch (action) {
        case 'pause':
          if (run) { run.intent = 'pause'; killTree(run.child, true); }
          else if (job.state === 'queued' || job.state === 'scheduled') { job.state = 'paused'; job.scheduledFor = undefined; }
          break;
        case 'resume':
        case 'start':
          if (job.state === 'paused' || job.state === 'scheduled') { job.state = 'queued'; job.scheduledFor = undefined; job.note = undefined; }
          break;
        case 'retry':
          if (['error', 'cancelled', 'done', 'paused'].includes(job.state)) this.requeue(job);
          break;
        case 'cancel':
          if (run) { run.intent = 'cancel'; killTree(run.child); }
          else if (['queued', 'scheduled', 'paused'].includes(job.state)) this.finish(job, 'cancelled');
          break;
        case 'remove':
          if (run) { run.intent = 'cancel'; killTree(run.child); }
          this.jobs = this.jobs.filter((j) => j.id !== id);
          break;
      }
    }
    this.changed();
    this.pump();
  }

  private requeue(job: Job): void {
    Object.assign(job, {
      state: 'queued', stage: 'starting', stageLabel: undefined, error: undefined, note: undefined, finishedAt: undefined,
      scheduledFor: undefined, exitCode: undefined, warnings: [], output: '', outputSize: 0, item: undefined,
      progress: {}, printOnly: isPrintOnly(job.values, job.extraArgs),
    } satisfies Partial<Job>);
  }

  update(id: string, patch: { values?: OptionValues; extraArgs?: string; url?: string }, retry: boolean): void {
    const job = this.jobs.find((j) => j.id === id);
    if (!job || this.running.has(id)) return;
    if (patch.values) job.values = patch.values;
    if (patch.extraArgs !== undefined) job.extraArgs = patch.extraArgs;
    if (patch.url !== undefined) { if (job.title === job.url) job.title = patch.url; job.url = patch.url; }
    if (retry) this.requeue(job);
    this.changed();
    this.pump();
  }

  async applyFix(id: string, fix: string): Promise<{ ok: boolean; message?: string }> {
    const job = this.jobs.find((j) => j.id === id);
    if (!job) return { ok: false, message: 'That download is no longer in the queue.' };
    const s = this.deps.settings();
    switch (fix) {
      case 'retry': break;
      case 'update-engine': {
        const r = await this.deps.engine.update(s.engineChannel, s.engineCustomSource, () => {}, false);
        if (r.state === 'error') return { ok: false, message: r.message };
        if (r.state === 'current') job.note = 'The engine is already the newest version';
        break;
      }
      case 'install-ffmpeg': {
        const r = await this.deps.engine.installFfmpeg(() => {});
        if (!r.ok) return r;
        break;
      }
      case 'switch-format': {
        const v = { ...job.values };
        delete v['--format']; delete v['--format-sort']; delete v['--merge-output-format']; delete v['--remux-video'];
        job.values = v;
        job.summary = 'Best available format';
        break;
      }
      case 'trim-names': job.values = { ...job.values, '--trim-filenames': '120' }; break;
      case 'retry-later':
        this.requeue(job);
        job.state = 'scheduled';
        job.scheduledFor = Date.now() + 15 * 60_000;
        this.changed();
        return { ok: true };
      default: return { ok: false, message: 'Unknown fix.' };
    }
    this.requeue(job);
    this.changed();
    this.pump();
    return { ok: true };
  }

  clearFinished(): void {
    this.jobs = this.jobs.filter((j) => !['done', 'cancelled', 'error'].includes(j.state));
    this.changed();
  }

  removeHistory(ids: string[]): Job[] {
    const set = new Set(ids);
    this.deps.history.set(this.deps.history.get().filter((j) => !set.has(j.id)));
    return this.history();
  }

  clearHistory(): Job[] {
    this.deps.history.set([], true);
    return [];
  }

  output(id: string): string { return this.get(id)?.output ?? ''; }

  /** Stop everything, keeping partial files so the jobs resume on next launch. */
  shutdown(): void {
    clearInterval(this.tick);
    this.closed = true;
    for (const [id, run] of this.running) {
      run.intent = 'pause';
      killTree(run.child, true);
      const job = this.jobs.find((j) => j.id === id);
      if (job) job.state = 'running'; // restored as queued next time
    }
    this.deps.queue.set(this.jobs.map((j) => ({ ...j, output: j.output.slice(0, 20_000) })), true);
    this.deps.history.flush();
  }

  // ---- running -------------------------------------------------------------

  private promoteScheduled(): void {
    const now = Date.now();
    let any = false;
    for (const j of this.jobs) {
      if (j.state === 'scheduled' && (j.scheduledFor ?? 0) <= now) { j.state = 'queued'; j.scheduledFor = undefined; any = true; }
    }
    if (any) { this.changed(); this.pump(); }
  }

  private pump(): void {
    if (this.closed) return;
    const limit = Math.max(1, Math.min(16, this.deps.settings().maxParallel || 1));
    for (const job of this.jobs) {
      if (this.running.size >= limit) break;
      if (job.state === 'queued') this.start(job);
    }
  }

  private start(job: Job): void {
    const { logs, engine } = this.deps;
    const eventsFile = path.join(logs.jobsDir, `${job.id}.events`);
    try { rmSync(eventsFile, { force: true }); } catch { /* ignore */ }
    const args = this.fullArgs(job, eventsFile);
    const folder = this.deps.settings().downloadFolder;
    job.state = 'running';
    job.stage = 'starting';
    job.stageLabel = undefined;
    job.startedAt = Date.now();
    job.attempts += 1;
    job.error = undefined;
    logs.job(job.id, `\n=== ${new Date().toISOString()} attempt ${job.attempts} ===\n$ ${formatCommand(redactArgs(args))}\n`);

    let child: ChildProcess;
    try {
      child = engine.spawn(args, folder && existsSync(folder) ? folder : undefined);
    } catch (e) {
      this.fail(job, translate(String((e as Error).message), 'starting'), null);
      return;
    }
    const run: Running = { child, intent: null, partials: new Set(), errors: [], lastProgressLog: 0, eventsFile };
    this.running.set(job.id, run);
    const out = new LineBuffer();
    const err = new LineBuffer();
    child.stdout!.setEncoding('utf8').on('data', (d: string) => { for (const l of out.push(d)) this.onLine(job, run, l, true); });
    child.stderr!.setEncoding('utf8').on('data', (d: string) => { for (const l of err.push(d)) this.onLine(job, run, l, false); });
    child.on('error', (e) => {
      if (!this.running.delete(job.id)) return;
      logs.job(job.id, `could not start engine: ${e.message}`);
      this.fail(job, translate(`ENOENT ${e.message}`, 'starting'), null);
    });
    child.on('close', (code, signal) => {
      for (const l of out.flush()) this.onLine(job, run, l, true);
      for (const l of err.flush()) this.onLine(job, run, l, false);
      if (!this.running.delete(job.id)) return;
      this.onExit(job, run, code, signal);
    });
    this.changed();
  }

  private onLine(job: Job, run: Running, line: string, stdout: boolean): void {
    if (!line) return;
    if (line.includes(`${job.id}.events`)) return; // the app's own bookkeeping
    const ev = parseLine(line);
    const isMarker = line.startsWith(PROGRESS_PREFIX) || line.startsWith(POST_PREFIX);
    if (!isMarker) this.deps.logs.job(job.id, line);

    const appendOutput = (text: string) => {
      if (job.output.length < MAX_OUTPUT) job.output += `${text}\n`;
      job.outputSize = job.output.length;
    };
    if (stdout && !isMarker && (ev.type === 'text' || job.printOnly)) appendOutput(line);

    switch (ev.type) {
      case 'progress': {
        job.stage = 'download';
        job.stageLabel = undefined;
        const percent = ev.total && ev.downloaded !== undefined ? Math.min(100, (ev.downloaded / ev.total) * 100)
          : ev.fragments && ev.fragment !== undefined ? Math.min(100, (ev.fragment / ev.fragments) * 100) : undefined;
        job.progress = { percent, downloaded: ev.downloaded, total: ev.total, estimated: ev.estimated, speed: ev.speed, eta: ev.eta };
        if (ev.info.title) {
          if (job.item) job.item.title = ev.info.title;
          else if (!job.title || job.title === job.url) job.title = ev.info.title;
        }
        if (!job.thumbnail && ev.info.thumbnail) job.thumbnail = ev.info.thumbnail;
        if (!job.uploader && ev.info.uploader) job.uploader = ev.info.uploader;
        if (!job.item && ev.info.playlist_index && (ev.info.n_entries ?? ev.info.playlist_count)) {
          job.item = { index: ev.info.playlist_index, count: (ev.info.n_entries ?? ev.info.playlist_count)!, title: ev.info.title };
        }
        const now = Date.now();
        if (now - run.lastProgressLog > 2000 || ev.status === 'finished') {
          run.lastProgressLog = now;
          this.deps.logs.job(job.id, `[progress] ${percent !== undefined ? `${percent.toFixed(1)}%` : '?'} of ${formatBytes(ev.total) || '?'}${ev.speed ? ` at ${formatBytes(ev.speed)}/s` : ''}`);
        }
        break;
      }
      case 'post':
        if (ev.status === 'started') {
          job.stage = ev.name === 'Merger' ? 'merge' : ev.name === 'MoveFiles' ? 'write' : 'post';
          job.stageLabel = postLabel(ev.name);
          job.progress = { ...job.progress, speed: undefined, eta: undefined };
        }
        break;
      case 'stage':
        job.stage = ev.stage;
        job.stageLabel = ev.label;
        break;
      case 'item':
        job.item = { index: ev.index, count: ev.count };
        job.progress = {};
        job.stage = 'info';
        break;
      case 'destination': run.partials.add(ev.path); job.stage = 'download'; break;
      case 'already': if (ev.path && !job.files.includes(ev.path)) job.files.push(ev.path); job.note = 'Already downloaded'; break;
      case 'skipped': job.note = ev.reason; break;
      case 'waiting': job.stageLabel = ev.message; break;
      case 'warning': if (job.warnings.length < 50) job.warnings.push(ev.message); break;
      case 'error': run.errors.push(ev.message); break;
      case 'text': break;
    }
    this.changed(false);
  }

  private readEvents(job: Job, run: Running): void {
    let text = '';
    try { text = readFileSync(run.eventsFile, 'utf8'); rmSync(run.eventsFile, { force: true }); } catch { return; }
    for (const line of text.split('\n')) {
      if (!line.trim()) continue;
      try {
        const e = JSON.parse(line) as { filepath?: string; title?: string; thumbnail?: string; uploader?: string; duration?: number };
        if (e.filepath && !job.files.includes(e.filepath)) job.files.push(e.filepath);
        if (!job.item && e.title && (!job.title || job.title === job.url)) job.title = e.title;
        if (!job.thumbnail && e.thumbnail) job.thumbnail = e.thumbnail;
        if (!job.uploader && e.uploader) job.uploader = e.uploader;
        if (!job.duration && e.duration && !job.item) job.duration = e.duration;
      } catch { /* a line the engine could not format */ }
    }
  }

  private onExit(job: Job, run: Running, code: number | null, signal: string | null): void {
    if (this.closed) return;
    this.readEvents(job, run);
    job.exitCode = code;
    job.progress = { ...job.progress, speed: undefined, eta: undefined };
    this.deps.logs.job(job.id, `=== finished: exit code ${code ?? 'none'}${signal ? `, signal ${signal}` : ''}${run.intent ? `, ${run.intent} requested` : ''} ===`);

    if (run.intent === 'pause') {
      job.state = 'paused';
      job.note = 'Paused. The part already downloaded is kept.';
      this.changed();
      this.pump();
      return;
    }
    if (run.intent === 'cancel') {
      this.removePartials(run);
      this.finish(job, 'cancelled');
      this.pump();
      return;
    }
    if (code === 0 || code === 101) {
      // 101 is the engine's way of saying a limit you set (max downloads, stop rules) ended the job
      if (code === 101) job.note = 'Stopped by a limit set in the options';
      for (const e of run.errors) if (job.warnings.length < 50) job.warnings.push(e);
      if (!job.printOnly && !job.files.length && !job.note && !job.outputSize) job.note = 'Nothing new to download';
      job.progress = job.files.length ? { ...job.progress, percent: 100 } : job.progress;
      job.stage = 'done';
      job.stageLabel = undefined;
      this.finish(job, 'done');
      this.pump();
      return;
    }
    const tail = this.deps.logs.readJob(job.id).split('\n').slice(-40).join('\n');
    const friendly = run.errors.length ? translate(run.errors.join('\n'), job.stage)
      : /Traceback \(most recent call last\)/.test(tail) ? translate(tail, job.stage) : translateExit(code, signal, job.stage);
    if (run.errors.length > 1) job.note = `${run.errors.length} problems were reported. The first is shown.`;
    this.fail(job, friendly, code);
  }

  private fail(job: Job, friendly: Friendly, code: number | null): void {
    job.exitCode = code;
    const s = this.deps.settings();
    if (RETRYABLE.has(friendly.code) && job.attempts <= (s.autoRetry ?? 0)) {
      job.state = 'scheduled';
      job.scheduledFor = Date.now() + 10_000;
      job.note = `${friendly.title}. Trying again in a moment.`;
      this.deps.logs.job(job.id, `automatic retry scheduled (${friendly.code})`);
      this.changed();
      this.pump();
      return;
    }
    job.error = friendly;
    this.deps.logs.app('warn', `download ${job.id} failed: ${friendly.code} at ${friendly.stage}: ${friendly.raw}`);
    this.finish(job, 'error');
    this.pump();
  }

  private finish(job: Job, state: 'done' | 'error' | 'cancelled'): void {
    job.state = state;
    job.finishedAt = Date.now();
    const entry: Job = { ...job, output: job.output.slice(0, 20_000) };
    const history = this.deps.history.get().filter((h) => h.id !== job.id);
    history.unshift(entry);
    this.deps.history.set(history.slice(0, MAX_HISTORY));
    this.changed();
    this.deps.onFinished?.(job);
  }

  private removePartials(run: Running): void {
    for (const dest of run.partials) {
      for (const suffix of ['.part', '.ytdl']) {
        try { rmSync(dest + suffix, { force: true }); } catch { /* in use or already gone */ }
      }
      try {
        const dir = path.dirname(dest);
        const base = path.basename(dest);
        for (const name of readdirSync(dir)) {
          if (name.startsWith(`${base}.part-Frag`) || name.startsWith(`${base}.part.`)) rmSync(path.join(dir, name), { force: true });
        }
      } catch { /* folder went away */ }
    }
  }

  private changed(persist = true): void {
    if (this.closed) return;
    if (persist) this.persist();
    if (this.emitTimer) return;
    this.emitTimer = setTimeout(() => {
      this.emitTimer = null;
      this.deps.onChange(this.list());
    }, 120);
  }

  private persist(immediate = false): void {
    this.deps.queue.set(this.jobs.map((j) => ({ ...j, output: j.output.slice(0, 20_000) })), immediate);
  }
}

export function exportHistoryCsv(jobs: Job[], file: string): void {
  const esc = (s: unknown) => `"${String(s ?? '').replace(/"/g, '""')}"`;
  const rows = [['Date', 'Title', 'Link', 'Result', 'Files'].map(esc).join(',')];
  for (const j of jobs) rows.push([new Date(j.finishedAt ?? j.createdAt).toISOString(), j.title, j.url, j.state, j.files.join('; ')].map(esc).join(','));
  writeFileSync(file, rows.join('\n'));
}
