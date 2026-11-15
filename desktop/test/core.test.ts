import assert from 'node:assert/strict';
import { test } from 'node:test';
import { buildArgs, buildOptionArgs, formatCommand, parseArgs, parseConfigText, toConfigText } from '../src/shared/command';
import { categories, meta } from '../src/shared/meta';
import { LineBuffer, parseLine, PROGRESS_PREFIX, POST_PREFIX, formatBytes, formatDuration } from '../src/shared/output';
import { MASK, redactArgs, redactText } from '../src/shared/redact';
import { schema } from '../src/shared/schema';
import { split, quote } from '../src/shared/shlex';
import { defaultSimple, effectiveValues, simpleToValues } from '../src/shared/simple';

test('every visible engine option belongs to exactly one control', () => {
  const seen = new Map<string, string>();
  for (const c of schema.controls) {
    for (const o of c.option ? [c.option] : c.members) {
      assert.ok(!seen.has(o.id), `${o.id} appears in two controls`);
      seen.set(o.id, c.id);
    }
  }
  for (const o of schema.options) if (!o.hidden) assert.ok(seen.has(o.id), `${o.id} has no control`);
});

test('every control has a hand-written name, explanation and category', () => {
  const cats = new Set(categories.map((c) => c.id));
  for (const c of schema.controls) {
    const m = meta[c.id];
    assert.ok(m, `no entry in meta.ts for ${c.id}`);
    assert.ok(m.label.length > 2 && m.tip.length > 15, `${c.id} needs a real label and tip`);
    assert.ok(cats.has(m.category), `${c.id} has unknown category ${m.category}`);
    assert.ok(!/!/.test(m.label + m.tip.replace(/!is_live/, '')), `${c.id}: no exclamation marks in copy`);
    if (c.kind === 'switch' && !c.onFlag && c.members.length > 1) {
      for (const mem of c.members) assert.ok(m.memberLabels?.[mem.id], `${c.id}: member ${mem.id} needs a label`);
    }
    if (c.nargs > 1) assert.equal(m.parts?.length, c.nargs, `${c.id} needs a name for each of its ${c.nargs} fields`);
  }
  for (const id of Object.keys(meta)) assert.ok(schema.controlById.has(id), `meta.ts has an entry for ${id}, which the engine no longer has`);
});

test('builds arguments in parser order and round-trips them', () => {
  const values = {
    '--format': 'bv*+ba/b', '--write-subs': '--write-subs', '--sub-langs': 'en.*,de', '--output': ['%(title)s.%(ext)s', 'thumbnail:covers/%(id)s.%(ext)s'],
    '--replace-in-metadata': [['title,uploader', '[ _]', '-']], '--continue': '--no-continue', '--ignore-errors': '--abort-on-error',
    '--limit-rate': '2M', '--print-to-file': [['%(id)s', 'ids.txt']],
  };
  const args = buildOptionArgs(values);
  assert.deepEqual(parseArgs(args).values, values);
  assert.ok(args.indexOf('--abort-on-error') < args.indexOf('--limit-rate'), 'General options come before Download options');
  const full = buildArgs({ values, extraArgs: '--youtube-skip-dash-manifest -v', urls: ['https://example.com/a b'] });
  assert.deepEqual(full.slice(-3), ['--youtube-skip-dash-manifest', '-v', 'https://example.com/a b']);
  assert.match(formatCommand(full), /^yt-dlp .*'https:\/\/example.com\/a b'$/);
});

test('urls that look like options are protected with --', () => {
  assert.deepEqual(buildArgs({ values: {}, urls: ['-weird'] }), ['--', '-weird']);
});

test('parses short flags, clusters, = forms, aliases and abbreviations', () => {
  const p = parseArgs(['-xk', '-f', 'best', '-ores.mp4', '--audio-format=mp3', '--add-metadata', '--no-mtime', '-N4', '--write-auto-sub', 'URL', '--bogus']);
  assert.equal(p.values['--extract-audio'], '--extract-audio');
  assert.equal(p.values['--keep-video'], '--keep-video');
  assert.equal(p.values['--format'], 'best');
  assert.deepEqual(p.values['--output'], ['res.mp4']);
  assert.equal(p.values['--audio-format'], 'mp3');
  assert.equal(p.values['--embed-metadata'], '--embed-metadata');
  assert.equal(p.values['--mtime'], '--no-mtime');
  assert.equal(p.values['--concurrent-fragments'], '4');
  assert.equal(p.values['--write-auto-subs'], '--write-auto-subs');
  assert.deepEqual(p.urls, ['URL']);
  assert.deepEqual(p.unknown, ['--bogus']);
});

test('hidden and deprecated flags survive an import as extra arguments', () => {
  const p = parseArgs(['--prefer-ffmpeg', '--sponskrub-args', 'x y', '-f', 'b']);
  assert.deepEqual(p.extra, ['--prefer-ffmpeg', '--sponskrub-args', 'x y']);
  assert.equal(p.values['--format'], 'b');
});

test('config files: comments, quotes and export', () => {
  const text = `# my config\n-x  # audio only\n--audio-format mp3\n-o "~/Music/%(title)s.%(ext)s"\n--parse-metadata 'title:%(artist)s - %(title)s'\n`;
  const p = parseConfigText(text);
  assert.equal(p.values['--extract-audio'], '--extract-audio');
  assert.deepEqual(p.values['--output'], ['~/Music/%(title)s.%(ext)s']);
  assert.deepEqual(p.values['--parse-metadata'], ['title:%(artist)s - %(title)s']);
  const out = toConfigText({ values: p.values, extraArgs: '--prefer-ffmpeg' }, 'Exported');
  assert.deepEqual(parseConfigText(out).values, p.values);
  assert.match(out, /^# Exported\n/);
  assert.match(out, /--prefer-ffmpeg\n$/);
});

test('shell splitting and quoting', () => {
  assert.deepEqual(split(`a "b c" 'd e' f\\ g "h\\"i"`), ['a', 'b c', 'd e', 'f g', 'h"i']);
  assert.deepEqual(split(`--ppa "ffmpeg:-c:v libx264" # note`), ['--ppa', 'ffmpeg:-c:v libx264']);
  assert.throws(() => split(`"unclosed`));
  assert.equal(quote("it's"), `'it'"'"'s'`);
  assert.equal(quote(''), "''");
  assert.equal(quote('%(title)s'), `'%(title)s'`);
});

test('simple mode compiles to ordinary options and advanced values win', () => {
  assert.deepEqual(simpleToValues({ ...defaultSimple, quality: '1080', folder: '/dl' }), {
    '--format-sort': 'res:1080,vcodec:h264,acodec:aac', '--merge-output-format': 'mp4', '--remux-video': 'mp4',
    '--embed-metadata': '--embed-metadata', '--paths': ['/dl'],
  });
  const audio = simpleToValues({ ...defaultSimple, kind: 'audio', audioFormat: 'mp3', audioQuality: '192K', metadata: false });
  assert.deepEqual(audio, { '--format': 'bestaudio/best', '--extract-audio': '--extract-audio', '--audio-format': 'mp3', '--audio-quality': '192K' });
  const eff = effectiveValues({ ...defaultSimple, quality: '720' }, { '--format-sort': 'size' }, { '--ignore-config': '--ignore-config' });
  assert.equal(eff['--format-sort'], 'size');
  assert.equal(eff['--ignore-config'], '--ignore-config');
});

test('progress lines', () => {
  const line = `${PROGRESS_PREFIX}{"status": "downloading", "downloaded_bytes": 1024, "total_bytes_estimate": 4096, "speed": 512.5, "eta": 6, "fragment_index": 1, "fragment_count": 4} {"id": "x", "title": "A {tricky} \\"title\\"", "playlist_index": 2, "n_entries": 9}`;
  const ev = parseLine(line);
  assert.equal(ev.type, 'progress');
  if (ev.type !== 'progress') return;
  assert.equal(ev.total, 4096);
  assert.equal(ev.estimated, true);
  assert.equal(ev.info.title, 'A {tricky} "title"');
  assert.equal(ev.info.n_entries, 9);
  assert.deepEqual(parseLine(`${POST_PREFIX}{"status": "started", "postprocessor": "Merger"}`), { type: 'post', status: 'started', name: 'Merger' });
  assert.equal(parseLine(`${PROGRESS_PREFIX}{broken`).type, 'text');
});

test('engine output lines are classified', () => {
  assert.deepEqual(parseLine('ERROR: [youtube] abc: Private video'), { type: 'error', message: '[youtube] abc: Private video' });
  assert.deepEqual(parseLine('WARNING: something'), { type: 'warning', message: 'something' });
  assert.deepEqual(parseLine('[download] Downloading item 3 of 12'), { type: 'item', index: 3, count: 12 });
  assert.deepEqual(parseLine('[download] Destination: /x/y.mp4'), { type: 'destination', path: '/x/y.mp4' });
  assert.deepEqual(parseLine('[download] /x/y.mp4 has already been downloaded'), { type: 'already', path: '/x/y.mp4' });
  assert.equal(parseLine('[Merger] Merging formats into "a.mkv"').type, 'stage');
  assert.deepEqual(parseLine('[info] abc: Downloading 1 format(s): 22'), { type: 'stage', stage: 'format' });
  assert.deepEqual(parseLine('[youtube] abc: Downloading webpage'), { type: 'stage', stage: 'info' });
  assert.deepEqual(parseLine('[MoveFiles] Moving file'), { type: 'stage', stage: 'write', label: 'Moving files into place' });
  assert.deepEqual(parseLine('__main__.py: error: invalid retries value'), { type: 'error', message: 'yt-dlp: error: invalid retries value' });
  assert.equal(parseLine('plain printed text').type, 'text');
});

test('line buffer handles split chunks and carriage returns', () => {
  const b = new LineBuffer();
  assert.deepEqual(b.push('one\ntw'), ['one']);
  assert.deepEqual(b.push('o\r\nthree\rfour'), ['two', 'three']);
  assert.deepEqual(b.flush(), ['four']);
});

test('formatting helpers', () => {
  assert.equal(formatBytes(0), '0 B');
  assert.equal(formatBytes(1536), '1.50 KB');
  assert.equal(formatBytes(123456789), '118 MB');
  assert.equal(formatBytes(undefined), '');
  assert.equal(formatDuration(59), '0:59');
  assert.equal(formatDuration(3725), '1:02:05');
});

test('secrets are removed from commands', () => {
  const r = redactArgs(['-u', 'me@example.com', '--password', 'hunter2', '--video-password=abc', '--add-headers', 'Authorization:Bearer xyz', '--add-headers', 'Referer:https://a.b/', '--proxy', 'socks5://bob:pw@10.0.0.1:1080', 'https://x.y/v?id=1&token=SECRET&t=2']);
  const s = r.join(' ');
  for (const secret of ['me@example.com', 'hunter2', 'abc', 'xyz', 'bob', 'pw@', 'SECRET']) assert.ok(!s.includes(secret), `leaked ${secret}: ${s}`);
  assert.ok(s.includes('Referer:https://a.b/'));
  assert.ok(s.includes('id=1') && s.includes('t=2'));
});

test('secrets are removed from log text', () => {
  const t = redactText('GET /api?sig=abcdef&x=1\nCookie: SID=verysecret; other=1\nfile /home/alice/Videos/a.mp4 by alice@mail.com\nyt-dlp -p swordfish --twofactor 123456 -u bob', '/home/alice', 'alice');
  for (const secret of ['abcdef', 'verysecret', 'alice', 'swordfish', '123456', 'mail.com']) assert.ok(!t.includes(secret), `leaked ${secret}: ${t}`);
  assert.ok(t.includes('~/Videos/a.mp4'));
  assert.ok(t.includes(MASK));
  assert.equal(redactText('C:\\Users\\alice\\Downloads', undefined, 'alice'), 'C:\\Users\\user\\Downloads');
});

import { preflight } from '../src/shared/preflight';
test('preflight catches option combinations the engine would choke on', () => {
  assert.equal(preflight({}).length, 0);
  assert.equal(preflight({ '--username': 'a', '--password': 'b' }).length, 0);
  assert.match(preflight({ '--username': 'a' })[0], /no password/);
  assert.match(preflight({ '--password': 'b' })[0], /without a username/);
  assert.match(preflight({ '--max-sleep-interval': '5' })[0], /Wait before each download/);
  assert.equal(preflight({ '--username': 'a', '--netrc-cmd': 'pass {}' }).length, 0);
});
