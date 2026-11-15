// Drives the real engine through the job queue against a local web server.
// Needs python3 and ffmpeg on the machine; no internet.
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { existsSync, mkdtempSync, readdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import http from 'node:http';
import type { AddressInfo } from 'node:net';
import os from 'node:os';
import path from 'node:path';
import { after, before, test } from 'node:test';
import { Engine } from '../src/main/engine';
import { JobManager } from '../src/main/jobs';
import { Logs } from '../src/main/logs';
import { Prober } from '../src/main/probe';
import { JsonStore } from '../src/main/store';
import { defaultSimple, effectiveValues } from '../src/shared/simple';
import { defaultSettings, type Job, type JobSpec, type Settings } from '../src/shared/types';

const tmp = mkdtempSync(path.join(os.tmpdir(), 'dubdeck-test-'));
const dl = path.join(tmp, 'downloads');
const clip = path.join(tmp, 'clip.mp4');
let server: http.Server;
let base = '';
let jobs: JobManager;
let engine: Engine;
let logs: Logs;
let last: Job[] = [];
const settings: Settings = { ...defaultSettings, downloadFolder: dl, maxParallel: 2, autoRetry: 0 };
process.env.NO_PROXY = '127.0.0.1,localhost';
process.env.no_proxy = '127.0.0.1,localhost';

before(() => {
  execFileSync('ffmpeg', ['-v', 'error', '-f', 'lavfi', '-i', 'testsrc=size=320x240:rate=15:duration=4', '-f', 'lavfi', '-i', 'sine=frequency=440:duration=4',
    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-shortest', '-y', clip]);
  const data = readFileSync(clip);
  server = http.createServer((req, res) => {
    const url = req.url ?? '';
    if (url.startsWith('/clip') || url.startsWith('/slow')) {
      res.writeHead(200, { 'content-type': 'video/mp4', 'content-length': data.length });
      if (req.method === 'HEAD') { res.end(); return; }
      if (!url.startsWith('/slow')) { res.end(data); return; }
      let i = 0;
      const timer = setInterval(() => {
        if (i >= data.length) { clearInterval(timer); res.end(); return; }
        res.write(data.subarray(i, i + 2048)); i += 2048;
      }, 60);
      res.on('close', () => clearInterval(timer));
    } else if (url === '/feed.rss') {
      res.writeHead(200, { 'content-type': 'application/rss+xml' });
      res.end(`<?xml version="1.0"?><rss version="2.0"><channel><title>Test feed</title>${[1, 2, 3].map((n) => `<item><title>Episode ${n}</title><enclosure url="${base}/clip${n}.mp4" type="video/mp4"/></item>`).join('')}</channel></rss>`);
    } else { res.writeHead(404); res.end('gone'); }
  });
  return new Promise<void>((resolve) => server.listen(0, '127.0.0.1', () => {
    base = `http://127.0.0.1:${(server.address() as AddressInfo).port}`;
    engine = new Engine({ userData: path.join(tmp, 'data'), logs: path.join(tmp, 'data', 'logs'), resources: null, repoRoot: path.resolve(__dirname, '..', '..') });
    logs = new Logs(path.join(tmp, 'data', 'logs'));
    jobs = new JobManager({
      engine, logs, settings: () => settings,
      queue: new JsonStore<Job[]>(path.join(tmp, 'data', 'queue.json'), []),
      history: new JsonStore<Job[]>(path.join(tmp, 'data', 'history.json'), []),
      onChange: (l) => { last = l; },
    });
    resolve();
  }));
});

after(() => {
  jobs.shutdown();
  server.close();
  rmSync(tmp, { recursive: true, force: true });
});

function spec(url: string, advanced = {}, simple = {}, extraArgs = ''): JobSpec {
  return { url, summary: 'test', extraArgs, values: effectiveValues({ ...defaultSimple, container: 'auto', metadata: false, folder: dl, ...simple }, advanced, settings.baseValues) };
}

async function until(pred: (j: Job) => boolean, url: string, ms = 60_000): Promise<Job> {
  const start = Date.now();
  for (;;) {
    const j = jobs.list().find((x) => x.url === url);
    if (j && pred(j)) return j;
    if (Date.now() - start > ms) throw new Error(`timed out waiting on ${url}; state=${j?.state} stage=${j?.stage} note=${j?.note}\n${j ? logs.readJob(j.id) : ''}`);
    await new Promise((r) => setTimeout(r, 50));
  }
}
const settled = (j: Job) => ['done', 'error', 'cancelled'].includes(j.state);

test('engine reports its version', async () => {
  const info = await engine.info();
  assert.match(info.version, /^\d{4}\.\d{2}\.\d{2}/);
  assert.equal(info.source, 'source');
  assert.ok(info.ffmpeg.version);
});

test('downloads a video and records the finished file', async () => {
  const url = `${base}/clip.mp4`;
  jobs.add([spec(url)]);
  const j = await until(settled, url);
  assert.equal(j.state, 'done', JSON.stringify(j.error));
  assert.equal(j.files.length, 1);
  assert.ok(existsSync(j.files[0]));
  assert.equal(j.progress.percent, 100);
  assert.equal(j.title, 'clip');
  assert.ok(jobs.history().some((h) => h.id === j.id));
  assert.match(logs.readJob(j.id), /\[progress\] 100\.0%/);
});

test('does not overwrite: a second run finds the file and leaves it alone', async () => {
  const url = `${base}/clip.mp4`;
  const first = jobs.list().find((x) => x.url === url)!;
  const mtime = readFileSync(first.files[0]).length;
  jobs.action([first.id], 'retry');
  await until((j) => j.state === 'running' || j.attempts === 2, url);
  const j = await until(settled, url);
  assert.equal(j.state, 'done');
  assert.equal(j.note, 'Already downloaded');
  assert.equal(readFileSync(j.files[0]).length, mtime);
});

test('extracts audio to mp3', async () => {
  const url = `${base}/clip-audio.mp4`;
  jobs.add([spec(url, {}, { kind: 'audio', audioFormat: 'mp3', audioQuality: '128K' })]);
  const j = await until(settled, url);
  assert.equal(j.state, 'done', JSON.stringify(j.error));
  assert.match(j.files[0], /\.mp3$/);
  assert.ok(existsSync(j.files[0]));
});

test('follows a playlist item by item', async () => {
  const url = `${base}/feed.rss`;
  jobs.add([spec(url)]);
  const j = await until(settled, url);
  assert.equal(j.state, 'done', JSON.stringify(j.error));
  assert.equal(j.files.length, 3);
  assert.deepEqual(j.item && { index: j.item.index, count: j.item.count }, { index: 3, count: 3 });
});

test('a broken link fails with a plain explanation and the right stage', async () => {
  const url = `${base}/missing-page`;
  jobs.add([spec(url)]);
  const j = await until(settled, url);
  assert.equal(j.state, 'error');
  assert.equal(j.error?.code, 'removed');
  assert.equal(j.error?.stage, 'info');
  assert.ok(j.error?.fixes.length);
  const report = await jobs.report(j.id);
  assert.match(report, /Problem: +The video is gone \[removed\]/);
  assert.match(report, /HTTP Error 404/);
});

test('an invalid option is caught before anything is downloaded', async () => {
  const url = `${base}/clip-badopt.mp4`;
  jobs.add([spec(url, { '--retries': 'lots' })]);
  const j = await until(settled, url);
  assert.equal(j.state, 'error');
  assert.equal(j.error?.code, 'bad-option');
  assert.equal(j.error?.stage, 'starting');
});

test('cancel stops the engine and removes the partial file', async () => {
  const url = `${base}/slow-cancel.mp4`;
  jobs.add([spec(url)]);
  const running = await until((j) => (j.progress.downloaded ?? 0) > 4096, url);
  assert.equal(running.state, 'running');
  jobs.action([running.id], 'cancel');
  const j = await until(settled, url);
  assert.equal(j.state, 'cancelled');
  assert.deepEqual(readdirSync(dl).filter((f) => f.includes('slow-cancel')), []);
});

test('pause keeps the partial file and resume finishes it', async () => {
  const url = `${base}/slow-pause.mp4`;
  jobs.add([spec(url)]);
  const running = await until((j) => (j.progress.downloaded ?? 0) > 4096, url);
  jobs.action([running.id], 'pause');
  const paused = await until((j) => j.state === 'paused', url);
  assert.ok(readdirSync(dl).some((f) => f.includes('slow-pause') && f.endsWith('.part')), 'partial file kept');
  jobs.action([paused.id], 'resume');
  const j = await until(settled, url);
  assert.equal(j.state, 'done', JSON.stringify(j.error));
  assert.equal(j.attempts, 2);
  assert.ok(!readdirSync(dl).some((f) => f.endsWith('.part')));
});

test('print jobs capture what the engine prints', async () => {
  const url = `${base}/clip-print.mp4`;
  jobs.add([spec(url, { '--print': ['%(title)s|%(ext)s'] })]);
  const j = await until(settled, url);
  assert.equal(j.state, 'done');
  assert.equal(j.printOnly, true);
  assert.equal(jobs.output(j.id).trim(), 'clip-print|mp4');
  assert.equal(j.files.length, 0);
});

test('runs downloads in parallel up to the limit', async () => {
  const urls = [1, 2, 3].map((n) => `${base}/slow-par${n}.mp4`);
  jobs.add(urls.map((u) => spec(u)));
  await until((j) => j.state === 'running', urls[1]);
  const states = jobs.list().filter((j) => urls.includes(j.url)).map((j) => j.state);
  assert.deepEqual(states, ['running', 'running', 'queued']);
  for (const u of urls) assert.equal((await until(settled, u)).state, 'done');
});

test('secrets never reach the log or the command preview', async () => {
  const url = `${base}/clip-secret.mp4?token=TOPSECRET`;
  jobs.add([spec(url, { '--username': 'someone', '--password': 'hunter2', '--add-headers': ['Authorization:Bearer abc123456789'] })]);
  const j = await until(settled, url);
  const text = logs.readJob(j.id) + jobs.command(j.id, true) + (await jobs.report(j.id));
  for (const s of ['TOPSECRET', 'hunter2', 'someone', 'abc123456789']) assert.ok(!text.includes(s), `leaked ${s}`);
});

test('preview reads a single video and a playlist', async () => {
  const prober = new Prober(engine);
  const v = await prober.probe(`${base}/clip.mp4`, settings.baseValues);
  assert.equal(v.ok, true, v.log);
  assert.equal(v.kind, 'video');
  assert.equal(v.title, 'clip');
  assert.ok(v.formats?.length);
  const p = await prober.probe(`${base}/feed.rss`, settings.baseValues);
  assert.equal(p.kind, 'playlist');
  assert.equal(p.title, 'Test feed');
  assert.deepEqual(p.entries?.map((e) => e.title), ['Episode 1', 'Episode 2', 'Episode 3']);
  const bad = await prober.probe(`${base}/nope`, settings.baseValues);
  assert.equal(bad.ok, false);
  assert.equal(bad.error?.code, 'removed');
});

test('the queue survives a restart and resumes unfinished work', async () => {
  const url = `${base}/slow-restart.mp4`;
  jobs.add([spec(url)]);
  await until((j) => (j.progress.downloaded ?? 0) > 4096, url);
  jobs.shutdown();
  await new Promise((r) => setTimeout(r, 1500));
  jobs = new JobManager({
    engine, logs, settings: () => settings,
    queue: new JsonStore<Job[]>(path.join(tmp, 'data', 'queue.json'), []),
    history: new JsonStore<Job[]>(path.join(tmp, 'data', 'history.json'), []),
    onChange: (l) => { last = l; },
  });
  const j = await until(settled, url);
  assert.equal(j.state, 'done', JSON.stringify(j.error));
  assert.equal(j.note, 'Resumed after the app was closed');
  writeFileSync(path.join(tmp, 'last.json'), JSON.stringify(last.length));
});
