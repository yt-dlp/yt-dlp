// Parity test: every control the app shows produces arguments the real
// engine accepts and acts on. Writes docs/parity-report.json, which
// gen-matrix uses for the Status column of FEATURE_MATRIX.md.
// Run: npx tsx scripts/parity.ts
import { execFileSync } from 'node:child_process';
import { mkdirSync, mkdtempSync, writeFileSync } from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { buildArgs, buildOptionArgs } from '../src/shared/command';
import { join } from '../src/shared/shlex';
import { meta } from '../src/shared/meta';
import { schema, type Control, type Value } from '../src/shared/schema';

const fixtures = mkdtempSync(path.join(os.tmpdir(), 'dubdeck-parity-'));
const conf = path.join(fixtures, 'test.conf');
writeFileSync(conf, '--no-mtime\n');
const batch = path.join(fixtures, 'links.txt');
writeFileSync(batch, 'https://example.com/a\n');

// Sample values that pass the engine's own validation.
const samples: Record<string, Value> = {
  '--update-to': 'stable@latest', '--use-extractors': 'youtube,-generic', '--default-search': 'ytsearch', '--config-locations': [conf],
  '--plugin-dirs': ['/tmp/plugins'], '--js-runtimes': ['node'], '--remote-components': ['ejs:github'], '--wait-for-video': '30-120', '--color': ['never'],
  '--compat-options': 'no-live-chat', '--alias': [['--dd-test', '-f best']], '--preset-alias': ['mp3'], '--proxy': 'socks5://127.0.0.1:1080',
  '--socket-timeout': '15', '--source-address': '127.0.0.1', '--impersonate': 'chrome', '--geo-verification-proxy': 'http://127.0.0.1:8080', '--xff': 'US',
  '--playlist-items': '1:3,7', '--min-filesize': '50k', '--max-filesize': '2G', '--date': '20240101', '--datebefore': 'today', '--dateafter': 'today-1month',
  '--match-filters': ['duration>60'], '--break-match-filters': ['upload_date>=20240101'], '--age-limit': '18', '--download-archive': 'archive.txt',
  '--max-downloads': '5', '--skip-playlist-after-errors': '3', '--concurrent-fragments': '4', '--limit-rate': '4.2M', '--throttled-rate': '100K',
  '--retries': '15', '--file-access-retries': '5', '--fragment-retries': 'infinite', '--retry-sleep': ['fragment:exp=1:20'], '--buffer-size': '16K',
  '--http-chunk-size': '10M', '--download-sections': ['*10:15-20:00'], '--downloader': ['aria2c'], '--downloader-args': ['aria2c:-x 8'],
  '--batch-file': batch, '--paths': ['/tmp/out'], '--output': ['%(title)s.%(ext)s'], '--output-na-placeholder': 'none', '--trim-filenames': '120',
  '--load-info-json': '/tmp/x.info.json', '--cookies': '/tmp/cookies.txt', '--cookies-from-browser': 'firefox', '--cache-dir': '/tmp/cache',
  '--print': ['%(title)s'], '--print-to-file': [['%(id)s', 'ids.txt']], '--progress-template': ['download:%(progress._percent_str)s'], '--progress-delta': '2',
  '--encoding': 'utf-8', '--add-headers': ['Referer:https://example.com/'], '--sleep-requests': '1', '--sleep-interval': '2', '--max-sleep-interval': '5',
  '--sleep-subtitles': '1', '--format': 'bv*+ba/b', '--format-sort': 'res:1080', '--merge-output-format': 'mkv', '--sub-format': 'srt/best',
  '--sub-langs': 'en.*,de', '--username': 'someone', '--password': 'secret', '--twofactor': '123456', '--netrc-location': '/tmp/netrc',
  '--netrc-cmd': 'echo {}', '--video-password': 'pw', '--ap-mso': 'Comcast_SSO', '--ap-username': 'u', '--ap-password': 'p',
  '--client-certificate': '/tmp/c.pem', '--client-certificate-key': '/tmp/k.pem', '--client-certificate-password': 'pw', '--audio-format': 'mp3',
  '--audio-quality': '192K', '--remux-video': 'mkv', '--recode-video': 'mp4', '--postprocessor-args': ['ffmpeg:-threads 2'],
  '--parse-metadata': ['title:%(artist)s - %(title)s'], '--replace-in-metadata': [['title', '_', ' ']], '--concat-playlist': 'always', '--fixup': 'never',
  '--ffmpeg-location': '/tmp/ffmpeg', '--exec': ['after_move:echo %(filepath)q'], '--convert-subs': 'srt', '--convert-thumbnails': 'jpg',
  '--remove-chapters': ['intro'], '--use-postprocessor': ['FFmpegCopyStream:when=post_process'], '--sponsorblock-mark': 'all,-preview',
  '--sponsorblock-remove': 'sponsor', '--sponsorblock-chapter-title': '[SB] %(category_names)l', '--sponsorblock-api': 'https://sponsor.example.org',
  '--extractor-retries': '5', '--extractor-args': ['youtube:player_client=web'],
};
// These leave the parser before it returns settings, so they are checked by running them instead.
const runInstead = new Set(['--help', '--version']);

interface Case { id: string; control: string; args: string[]; prefix?: string[]; bare?: boolean; note?: string; acceptOnly?: boolean }

// Flags that only undo something: set that thing first, then check the flag undoes it.
const undo: Record<string, string[]> = {
  '--no-config-locations': ['--config-locations', conf], '--no-remote-components': ['--remote-components', 'ejs:github'],
  '--no-wait-for-video': ['--wait-for-video', '30'], '--no-match-filters': ['--match-filters', 'duration>60'],
  '--no-break-match-filters': ['--break-match-filters', 'duration>60'], '--no-download-archive': ['--download-archive', 'a.txt'],
  '--no-batch-file': ['--batch-file', batch], '--no-cookies': ['--cookies', '/tmp/c.txt'], '--no-cookies-from-browser': ['--cookies-from-browser', 'firefox'],
  '--format-sort-reset': ['-S', 'res'], '--no-exec': ['--exec', 'echo'], '--no-remove-chapters': ['--remove-chapters', 'intro'],
  '--no-plugin-dirs': ['--plugin-dirs', '/tmp/p'], '--no-js-runtimes': ['--js-runtimes', 'bun'],
};
// Options the engine only accepts together with another one.
const together: Record<string, { args: string[]; note: string }> = {
  '--username': { args: ['--username', 'u', '--password', 'p'], note: 'tested with --password; alone, the engine asks for the password in the terminal (the app always passes both)' },
  '--password': { args: ['--username', 'u', '--password', 'p'], note: 'tested with --username, which the engine requires' },
  '--ap-username': { args: ['--ap-mso', 'Comcast_SSO', '--ap-username', 'u', '--ap-password', 'p'], note: 'tested with --ap-password' },
  '--ap-password': { args: ['--ap-mso', 'Comcast_SSO', '--ap-username', 'u', '--ap-password', 'p'], note: 'tested with --ap-username, which the engine requires' },
  '--max-sleep-interval': { args: ['--sleep-interval', '2', '--max-sleep-interval', '5'], note: 'tested with --sleep-interval, which the engine requires' },
  '--alias': { args: ['--alias', '--dd-test', '-f best', '--dd-test'], note: 'defined and then used' },
};
const cases: Case[] = [];
const missing: string[] = [];
for (const c of schema.controls) {
  if (runInstead.has(c.id)) continue;
  if (c.kind === 'switch') {
    for (const m of c.members) {
      const other = c.members.find((x) => x !== m);
      const prefix = undo[m.id] ?? (other ? buildOptionArgs({ [c.id]: other.id }) : undefined);
      cases.push({ id: m.id, control: c.id, args: buildOptionArgs({ [c.id]: m.id }), prefix, bare: m.id === '--ignore-config' });
    }
    continue;
  }
  if (together[c.id]) { cases.push({ id: c.id, control: c.id, args: together[c.id].args, note: together[c.id].note }); continue; }
  const v = samples[c.id];
  if (v === undefined) { missing.push(c.id); continue; }
  cases.push({ id: c.id, control: c.id, args: buildOptionArgs({ [c.id]: v }) });
}
// Hidden and deprecated flags: no control, but typed into Extra arguments they must reach the engine intact.
const hiddenSamples: Record<string, string> = { '--sponskrub-location': '/tmp', '--sponskrub-args': '-x', '--cn-verification-proxy': 'http://127.0.0.1:1', '--load-info': '/tmp/x.json', '--referer': 'https://example.com/', '--user-agent': 'Mozilla/5.0', '--max-views': '10', '--min-views': '1', '--match-title': 'a', '--reject-title': 'b', '--include-ads': '', '--geo-bypass-country': 'US', '--geo-bypass-ip-block': '203.0.113.0/24' };
for (const o of schema.options.filter((x) => x.hidden)) {
  const extra = join([o.id, ...(o.takesValue ? Array(o.nargs).fill(hiddenSamples[o.id] ?? (o.type === 'int' || o.type === 'float' ? '3' : o.choices ? o.choices[0] : 'x')) : [])]);
  cases.push({ id: o.id, control: '(extra arguments)', args: buildArgs({ values: {}, extraArgs: extra }), acceptOnly: true, note: 'deprecated or hidden; typed into Extra arguments' });
}
if (missing.length) throw new Error(`No sample value for ${missing.join(', ')}`);

const here = path.dirname(new URL(import.meta.url).pathname);
const out = execFileSync(process.env.PYTHON || 'python3', [path.join(here, 'parity_check.py')], { input: JSON.stringify(cases), maxBuffer: 64 << 20 }).toString();
const results = (JSON.parse(out) as { id: string; ok: boolean; reason: string; note?: string }[]).map((r) => ({ ...r, note: cases.find((c) => c.id === r.id)?.note }));

// Run --help and --version through the real engine entry point.
for (const flag of runInstead) {
  let ok = false, reason = '';
  try {
    const text = execFileSync(process.env.PYTHON || 'python3', ['-m', 'yt_dlp', flag], { cwd: path.resolve(here, '..', '..') }).toString();
    ok = flag === '--help' ? text.includes('--format') : /^\d{4}\.\d{2}\.\d{2}/.test(text.trim());
    reason = ok ? '' : 'unexpected output';
  } catch (e) { reason = String((e as Error).message).slice(0, 200); }
  results.push({ id: flag, ok, reason, note: 'run through the engine, since it prints and exits' });
}

const failed = results.filter((r) => !r.ok);
const byId = Object.fromEntries(results.map((r) => [r.id, r]));
mkdirSync(path.join(here, '..', 'docs'), { recursive: true });
writeFileSync(path.join(here, '..', 'docs', 'parity-report.json'), JSON.stringify({ engineVersion: schema.engineVersion, date: new Date().toISOString().slice(0, 10), total: results.length, passed: results.length - failed.length, results: byId }, null, 1) + '\n');
console.log(`${results.length - failed.length} of ${results.length} flags accepted and applied by yt-dlp ${schema.engineVersion}`);
for (const f of failed) console.log(`  FAIL ${f.id}: ${f.reason}`);
const labelled = schema.controls.every((c: Control) => meta[c.id]);
if (!labelled) console.log('  some controls have no label');
process.exit(failed.length ? 1 : 0);
