// Builds the yt-dlp engine from this repository's source into a single
// executable (PyInstaller) and puts it where the app packager picks it up:
// desktop/vendor/engine/yt-dlp[.exe]
import { execFileSync } from 'node:child_process';
import { copyFileSync, chmodSync, existsSync, mkdirSync, readdirSync, rmSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const desktop = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const repo = path.resolve(desktop, '..');
const win = process.platform === 'win32';
const venv = path.join(desktop, 'build-engine', 'venv');
const py = process.env.PYTHON || (win ? 'python' : 'python3');
const vpy = path.join(venv, win ? 'Scripts' : 'bin', win ? 'python.exe' : 'python');
const run = (cmd, args, cwd = repo) => { console.log(`> ${cmd} ${args.join(' ')}`); execFileSync(cmd, args, { cwd, stdio: 'inherit' }); };

if (!existsSync(vpy)) run(py, ['-m', 'venv', venv]);
run(vpy, ['-m', 'pip', 'install', '--quiet', '--upgrade', 'pip']);
// the same optional dependencies the official builds ship with, plus the bundler
run(vpy, ['-m', 'pip', 'install', '--quiet', '.[default,curl-cffi,pyinstaller]']);
run(vpy, ['devscripts/make_lazy_extractors.py']);
const dist = path.join(desktop, 'build-engine', 'dist');
rmSync(dist, { recursive: true, force: true });
run(vpy, ['-m', 'bundle.pyinstaller', '--onefile', `--distpath=${dist}`, `--workpath=${path.join(desktop, 'build-engine', 'work')}`, `--specpath=${path.join(desktop, 'build-engine')}`]);
rmSync(path.join(repo, 'yt_dlp', 'extractor', 'lazy_extractors.py'), { force: true });

const built = readdirSync(dist).find((f) => f.startsWith('yt-dlp'));
if (!built) throw new Error('PyInstaller did not produce an engine binary');
const out = path.join(desktop, 'vendor', 'engine');
mkdirSync(out, { recursive: true });
const target = path.join(out, win ? 'yt-dlp.exe' : 'yt-dlp');
copyFileSync(path.join(dist, built), target);
if (!win) chmodSync(target, 0o755);
console.log(`Engine written to ${target}`);
console.log(execFileSync(target, ['--version']).toString().trim());
