// Downloads ffmpeg and ffprobe for the platform being built into
// desktop/vendor/ffmpeg, so installers ship with them inside.
import { execFileSync } from 'node:child_process';
import { createReadStream, createWriteStream, chmodSync, mkdirSync, renameSync, rmSync } from 'node:fs';
import path from 'node:path';
import { Readable } from 'node:stream';
import { pipeline } from 'node:stream/promises';
import { fileURLToPath } from 'node:url';
import { createGunzip } from 'node:zlib';

const RELEASE = 'https://github.com/eugeneware/ffmpeg-static/releases/download/b6.1.1';
const platform = process.env.TARGET_PLATFORM || process.platform;
const arch = process.env.TARGET_ARCH || process.arch;
const plat = platform === 'win32' ? 'win32' : platform === 'darwin' ? 'darwin' : 'linux';
const cpu = arch === 'arm64' && plat !== 'win32' ? 'arm64' : 'x64';
const exe = plat === 'win32' ? '.exe' : '';
const out = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', 'vendor', 'ffmpeg');
mkdirSync(out, { recursive: true });

for (const tool of ['ffmpeg', 'ffprobe']) {
  const url = `${RELEASE}/${tool}-${plat}-${cpu}.gz`;
  console.log(`Fetching ${url}`);
  const tmp = path.join(out, `${tool}.download`);
  const gz = `${tmp}.gz`;
  try {
    const res = await fetch(url, { redirect: 'follow' });
    if (!res.ok) throw new Error(`${url} answered ${res.status}`);
    await pipeline(Readable.fromWeb(res.body), createWriteStream(gz));
  } catch (e) {
    // some proxies break Node's streaming fetch; curl is on every build machine
    console.log(`  fetch failed (${e.message}), retrying with curl`);
    execFileSync('curl', ['-fsSL', '--retry', '3', '-o', gz, url], { stdio: 'inherit' });
  }
  await pipeline(createReadStream(gz), createGunzip(), createWriteStream(tmp));
  rmSync(gz, { force: true });
  const target = path.join(out, `${tool}${exe}`);
  renameSync(tmp, target);
  if (!exe) chmodSync(target, 0o755);
  console.log(`  -> ${target}`);
}
