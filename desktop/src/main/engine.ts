// Finds, runs and updates the yt-dlp engine and ffmpeg. No Electron imports
// here, so the same code runs under the test runner.

import { spawn, type ChildProcess } from 'node:child_process';
import { createHash } from 'node:crypto';
import { createReadStream, createWriteStream, existsSync } from 'node:fs';
import { chmod, mkdir, rename, rm, stat } from 'node:fs/promises';
import path from 'node:path';
import { Readable } from 'node:stream';
import { pipeline } from 'node:stream/promises';
import { createGunzip } from 'node:zlib';
import { instrumentation } from '../shared/output';
import { parseArgs } from '../shared/command';
import { split } from '../shared/shlex';
import type { OptionValues } from '../shared/schema';
import type { EngineChannel, EngineInfo, EngineUpdateStatus } from '../shared/types';

export interface AppPaths {
  userData: string;
  logs: string;
  /** read-only files shipped inside the app (engine/, ffmpeg/), or null when running from source */
  resources: string | null;
  /** the yt-dlp source tree, used when no engine binary exists (development) */
  repoRoot: string | null;
}

export interface Resolved { cmd: string; pre: string[]; source: EngineInfo['source']; path: string; cwd?: string }

const WIN = process.platform === 'win32';
const EXE = WIN ? '.exe' : '';
const FFMPEG_RELEASE = 'https://github.com/eugeneware/ffmpeg-static/releases/download/b6.1.1';

export const channelRepos: Record<Exclude<EngineChannel, 'custom'>, string> = {
  stable: 'yt-dlp/yt-dlp',
  nightly: 'yt-dlp/yt-dlp-nightly-builds',
  master: 'yt-dlp/yt-dlp-master-builds',
  fork: 'Nardi05/yt-dlp',
};

export function engineAssetName(platform = process.platform, arch = process.arch): string {
  if (platform === 'win32') return arch === 'arm64' ? 'yt-dlp_arm64.exe' : arch === 'ia32' ? 'yt-dlp_x86.exe' : 'yt-dlp.exe';
  if (platform === 'darwin') return 'yt-dlp_macos';
  return arch === 'arm64' ? 'yt-dlp_linux_aarch64' : 'yt-dlp_linux';
}

export function compareVersions(a: string, b: string): number {
  const pa = a.split(/[.\-_]/).map((x) => parseInt(x, 10) || 0);
  const pb = b.split(/[.\-_]/).map((x) => parseInt(x, 10) || 0);
  for (let i = 0; i < Math.max(pa.length, pb.length); i++) {
    const d = (pa[i] ?? 0) - (pb[i] ?? 0);
    if (d) return d < 0 ? -1 : 1;
  }
  return 0;
}

export function parseSource(channel: EngineChannel, custom: string): { repo: string; tag: string | null } {
  if (channel !== 'custom') return { repo: channelRepos[channel], tag: null };
  const m = /^\s*(?:https?:\/\/github\.com\/)?([\w.-]+\/[\w.-]+?)(?:@([\w.-]+))?\s*$/.exec(custom);
  if (!m) throw new Error('Write the source as owner/repository, optionally followed by @tag.');
  return { repo: m[1], tag: m[2] && m[2] !== 'latest' ? m[2] : null };
}

async function sha256(file: string): Promise<string> {
  const h = createHash('sha256');
  await pipeline(createReadStream(file), h);
  return h.digest('hex');
}

export interface RunResult { code: number | null; signal: string | null; stdout: string; stderr: string }

export class Engine {
  private versionCache: { key: string; version: string } | null = null;
  fetchImpl: typeof fetch = (...a) => fetch(...a);

  constructor(readonly paths: AppPaths) {}

  get engineDir(): string { return path.join(this.paths.userData, 'engine'); }
  get ffmpegDir(): string { return path.join(this.paths.userData, 'ffmpeg'); }
  get userEngine(): string { return path.join(this.engineDir, `yt-dlp${EXE}`); }

  resolve(): Resolved {
    if (existsSync(this.userEngine)) return { cmd: this.userEngine, pre: [], source: 'updated', path: this.userEngine };
    if (this.paths.resources) {
      const bundled = path.join(this.paths.resources, 'engine', `yt-dlp${EXE}`);
      if (existsSync(bundled)) return { cmd: bundled, pre: [], source: 'bundled', path: bundled };
    }
    if (this.paths.repoRoot && existsSync(path.join(this.paths.repoRoot, 'yt_dlp', '__main__.py'))) {
      return { cmd: process.env.DUBDECK_PYTHON || (WIN ? 'python' : 'python3'), pre: ['-m', 'yt_dlp'], source: 'source', path: this.paths.repoRoot, cwd: this.paths.repoRoot };
    }
    return { cmd: '', pre: [], source: 'missing', path: '' };
  }

  private env(r: Resolved): NodeJS.ProcessEnv {
    const env: NodeJS.ProcessEnv = { ...process.env, PYTHONIOENCODING: 'utf-8', PYTHONUTF8: '1', PYTHONUNBUFFERED: '1', ELECTRON_RUN_AS_NODE: '1' };
    if (r.source === 'source' && r.cwd) env.PYTHONPATH = [r.cwd, process.env.PYTHONPATH].filter(Boolean).join(path.delimiter);
    return env;
  }

  spawn(args: string[], cwd?: string): ChildProcess {
    const r = this.resolve();
    if (r.source === 'missing') throw new Error('engine binary not found');
    return spawn(r.cmd, [...r.pre, ...args], {
      cwd: cwd ?? this.paths.userData, env: this.env(r), stdio: ['ignore', 'pipe', 'pipe'], windowsHide: true,
      detached: !WIN, // own process group, so ffmpeg children can be stopped with it
    });
  }

  run(args: string[], opts: { timeoutMs?: number; signal?: AbortSignal; cwd?: string } = {}): Promise<RunResult> {
    return new Promise((resolve) => {
      let child: ChildProcess;
      try { child = this.spawn(args, opts.cwd); } catch (e) {
        resolve({ code: null, signal: null, stdout: '', stderr: String((e as Error).message) });
        return;
      }
      let stdout = '', stderr = '';
      child.stdout!.setEncoding('utf8').on('data', (d) => { stdout += d; });
      child.stderr!.setEncoding('utf8').on('data', (d) => { stderr += d; });
      const timer = opts.timeoutMs ? setTimeout(() => { stderr += '\nERROR: timed out'; killTree(child); }, opts.timeoutMs) : null;
      opts.signal?.addEventListener('abort', () => killTree(child), { once: true });
      child.on('error', (e) => { if (timer) clearTimeout(timer); resolve({ code: null, signal: null, stdout, stderr: stderr + String(e.message) }); });
      child.on('close', (code, signal) => { if (timer) clearTimeout(timer); resolve({ code, signal, stdout, stderr }); });
    });
  }

  async version(): Promise<string> {
    const r = this.resolve();
    if (r.source === 'missing') return '';
    let key = r.path;
    try { key += (await stat(r.source === 'source' ? path.join(r.path, 'yt_dlp', 'version.py') : r.path)).mtimeMs; } catch { /* ignore */ }
    if (this.versionCache?.key === key) return this.versionCache.version;
    const out = await this.run(['--version'], { timeoutMs: 60_000 });
    const version = out.stdout.trim().split(/\s+/)[0] ?? '';
    if (version) this.versionCache = { key, version };
    return version;
  }

  ffmpeg(): { dir: string | null; source: EngineInfo['ffmpeg']['source'] } {
    const has = (dir: string) => existsSync(path.join(dir, `ffmpeg${EXE}`));
    if (this.paths.resources && has(path.join(this.paths.resources, 'ffmpeg'))) return { dir: path.join(this.paths.resources, 'ffmpeg'), source: 'bundled' };
    if (has(this.ffmpegDir)) return { dir: this.ffmpegDir, source: 'installed' };
    return { dir: null, source: 'system' };
  }

  async info(): Promise<EngineInfo> {
    const r = this.resolve();
    const ff = this.ffmpeg();
    const bin = ff.dir ? path.join(ff.dir, `ffmpeg${EXE}`) : 'ffmpeg';
    const ffVersion = await new Promise<string>((resolve) => {
      try {
        const c = spawn(bin, ['-version'], { windowsHide: true });
        let out = '';
        c.stdout.on('data', (d) => { out += d; });
        c.on('error', () => resolve(''));
        c.on('close', () => resolve(/ffmpeg version (\S+)/.exec(out)?.[1] ?? ''));
      } catch { resolve(''); }
    });
    return {
      version: await this.version(), source: r.source, path: r.path,
      ffmpeg: { path: ffVersion ? bin : '', version: ffVersion, source: ffVersion ? ff.source : 'missing' },
      jsRuntime: `node ${process.versions.node}`,
    };
  }

  /** Arguments the app adds on top of the user's own. Nothing here overrides a user choice. */
  internalArgs(values: OptionValues, extraArgs: string, eventsFile?: string, progress = true): string[] {
    const set = new Set(Object.keys(values).filter((k) => values[k] !== '' && values[k] != null));
    try { for (const k of Object.keys(parseArgs(split(extraArgs || '', false)).values)) set.add(k); } catch { /* reported by the engine */ }
    const args: string[] = [];
    for (const inst of instrumentation) {
      if (!progress && inst.unlessSet.includes('--progress-template')) continue;
      if (!inst.unlessSet.some((f) => set.has(f))) args.push(...inst.args);
    }
    const ff = this.ffmpeg();
    if (ff.dir && !set.has('--ffmpeg-location')) args.push('--ffmpeg-location', ff.dir);
    if (!set.has('--js-runtimes') && !set.has('--no-js-runtimes')) args.push('--js-runtimes', `node:${process.execPath}`);
    if (eventsFile) args.push('--print-to-file', 'after_move:%(.{filepath,id,title,thumbnail,uploader,duration,webpage_url})j', eventsFile);
    return args;
  }

  // ---- updates -------------------------------------------------------------

  private async latest(channel: EngineChannel, custom: string): Promise<{ base: string; tag: string | null; sums: Map<string, string>; repo: string }> {
    const { repo, tag } = parseSource(channel, custom);
    const base = `https://github.com/${repo}/releases/${tag ? `download/${tag}` : 'latest/download'}`;
    const res = await this.fetchImpl(`${base}/SHA2-256SUMS`, { redirect: 'follow' });
    if (res.status === 404) throw new Error(`${repo} has not published an engine release${tag ? ` called ${tag}` : ''}. Pick another update channel in Settings.`);
    if (!res.ok) throw new Error(`The release server answered ${res.status}.`);
    const sums = new Map<string, string>();
    for (const line of (await res.text()).split('\n')) {
      const m = /^([0-9a-f]{64})\s+\*?(\S+)$/i.exec(line.trim());
      if (m) sums.set(m[2], m[1].toLowerCase());
    }
    let found = /\/releases\/download\/([^/]+)\//.exec(res.url)?.[1] ?? tag;
    if (!found) {
      // some network stacks hide the final address; ask where "latest" points instead
      try {
        const hop = await this.fetchImpl(`${base}/SHA2-256SUMS`, { redirect: 'manual' });
        found = /\/releases\/download\/([^/]+)\//.exec(hop.headers.get('location') ?? '')?.[1] ?? null;
      } catch { /* the version stays unknown; checksums still decide */ }
    }
    return { base: found ? `https://github.com/${repo}/releases/download/${found}` : base, tag: found ?? null, sums, repo };
  }

  async checkUpdate(channel: EngineChannel, custom: string): Promise<EngineUpdateStatus> {
    try {
      const current = await this.version();
      const rel = await this.latest(channel, custom);
      const asset = engineAssetName();
      if (!rel.sums.has(asset)) return { state: 'error', current, message: `That release has no build for this computer (${asset}).` };
      let available: boolean;
      if (rel.tag && current) available = compareVersions(rel.tag, current) > 0;
      else {
        // the release did not say which version it is, so compare the files themselves
        const r = this.resolve();
        available = r.source !== 'source' && (await sha256(r.path)) !== rel.sums.get(asset);
      }
      return { state: available ? 'available' : 'current', current, latest: rel.tag ?? undefined };
    } catch (e) {
      return { state: 'error', message: friendlyNet(e) };
    }
  }

  async update(channel: EngineChannel, custom: string, onProgress: (s: EngineUpdateStatus) => void, force = false): Promise<EngineUpdateStatus> {
    const tmp = path.join(this.engineDir, `download-${process.pid}${EXE}`);
    try {
      const current = await this.version();
      onProgress({ state: 'checking', current });
      const rel = await this.latest(channel, custom);
      const asset = engineAssetName();
      const expected = rel.sums.get(asset);
      if (!expected) return { state: 'error', current, message: `That release has no build for this computer (${asset}).` };
      if (!force && rel.tag && current && compareVersions(rel.tag, current) <= 0 && this.resolve().source !== 'missing') {
        return { state: 'current', current, latest: rel.tag };
      }
      await mkdir(this.engineDir, { recursive: true });
      await this.download(`${rel.base}/${asset}`, tmp, (percent) => onProgress({ state: 'downloading', current, latest: rel.tag ?? undefined, percent }));
      const actual = await sha256(tmp);
      if (actual !== expected) throw new Error('The downloaded engine did not match its published checksum, so it was thrown away. Try again.');
      if (!WIN) await chmod(tmp, 0o755);
      const test = await new Promise<string>((resolve) => {
        const c = spawn(tmp, ['--version'], { windowsHide: true });
        let out = '';
        c.stdout.on('data', (d) => { out += d; });
        c.on('error', () => resolve(''));
        c.on('close', () => resolve(out.trim()));
      });
      if (!test) throw new Error('The downloaded engine would not start on this computer, so the current one was kept.');
      if (existsSync(this.userEngine)) {
        const old = `${this.userEngine}.old`;
        await rm(old, { force: true }).catch(() => {});
        await rename(this.userEngine, old);
        rm(old, { force: true }).catch(() => {});
      }
      await rename(tmp, this.userEngine);
      this.versionCache = null;
      return { state: 'installed', current: test, latest: test };
    } catch (e) {
      await rm(tmp, { force: true }).catch(() => {});
      return { state: 'error', message: friendlyNet(e) };
    }
  }

  async revert(): Promise<void> {
    await rm(this.userEngine, { force: true });
    this.versionCache = null;
  }

  private async download(url: string, dest: string, onPercent: (p: number) => void, gunzip = false): Promise<void> {
    const res = await this.fetchImpl(url, { redirect: 'follow' });
    if (!res.ok || !res.body) throw new Error(`The download server answered ${res.status}.`);
    const total = Number(res.headers.get('content-length')) || 0;
    let got = 0, last = -1;
    const body = Readable.fromWeb(res.body as never);
    body.on('data', (chunk: Buffer) => {
      got += chunk.length;
      const p = total ? Math.floor((got / total) * 100) : 0;
      if (p !== last) { last = p; onPercent(p); }
    });
    if (gunzip) await pipeline(body, createGunzip(), createWriteStream(dest));
    else await pipeline(body, createWriteStream(dest));
  }

  async installFfmpeg(onPercent: (p: number) => void): Promise<{ ok: boolean; message?: string }> {
    const arch = process.arch === 'arm64' && process.platform !== 'win32' ? 'arm64' : 'x64';
    const plat = process.platform === 'win32' ? 'win32' : process.platform === 'darwin' ? 'darwin' : 'linux';
    try {
      await mkdir(this.ffmpegDir, { recursive: true });
      const tools = ['ffmpeg', 'ffprobe'];
      for (let i = 0; i < tools.length; i++) {
        const tmp = path.join(this.ffmpegDir, `${tools[i]}.download`);
        await this.download(`${FFMPEG_RELEASE}/${tools[i]}-${plat}-${arch}.gz`, tmp, (p) => onPercent(Math.round((i * 100 + p) / tools.length)), true);
        if (!WIN) await chmod(tmp, 0o755);
        await rename(tmp, path.join(this.ffmpegDir, `${tools[i]}${EXE}`));
      }
      return { ok: true };
    } catch (e) {
      return { ok: false, message: friendlyNet(e) };
    }
  }
}

function friendlyNet(e: unknown): string {
  const msg = e instanceof Error ? e.message : String(e);
  const cause = e instanceof Error && e.cause ? String((e.cause as Error).message ?? e.cause) : '';
  if (/fetch failed|ENOTFOUND|EAI_AGAIN|ECONNREFUSED|ENETUNREACH|ERR_INTERNET|ERR_NAME_NOT_RESOLVED|ERR_CONNECTION|ETIMEDOUT/i.test(msg + cause)) {
    return 'Could not reach the download server. Check your internet connection and try again.';
  }
  return msg;
}

/** Stop a process and everything it started (ffmpeg, external downloaders). */
export function killTree(child: ChildProcess, graceful = false): void {
  if (!child.pid || child.exitCode !== null) return;
  if (WIN) {
    spawn('taskkill', ['/pid', String(child.pid), '/T', '/F'], { windowsHide: true }).on('error', () => child.kill());
    return;
  }
  const sig = graceful ? 'SIGINT' : 'SIGTERM';
  try { process.kill(-child.pid, sig); } catch { try { child.kill(sig); } catch { /* already gone */ } }
  setTimeout(() => {
    if (child.exitCode === null && child.signalCode === null) {
      try { process.kill(-child.pid!, 'SIGKILL'); } catch { try { child.kill('SIGKILL'); } catch { /* gone */ } }
    }
  }, 4000).unref();
}
