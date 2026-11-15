// Persistent log files: one for the app, one per download.

import { appendFileSync, existsSync, mkdirSync, readdirSync, readFileSync, renameSync, statSync, unlinkSync } from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { redactText } from '../shared/redact';
import type { LogFile } from '../shared/types';

const MAX_APP_LOG = 2 * 1024 * 1024;
const home = os.homedir();
const user = os.userInfo().username;

export const scrub = (s: string): string => redactText(s, home, user);

export class Logs {
  readonly jobsDir: string;
  private appFile: string;

  constructor(readonly dir: string) {
    this.jobsDir = path.join(dir, 'downloads');
    mkdirSync(this.jobsDir, { recursive: true });
    this.appFile = path.join(dir, 'app.log');
  }

  app(level: 'info' | 'warn' | 'error', message: string): void {
    try {
      if (existsSync(this.appFile) && statSync(this.appFile).size > MAX_APP_LOG) {
        renameSync(this.appFile, path.join(this.dir, 'app.1.log'));
      }
      appendFileSync(this.appFile, `${new Date().toISOString()} ${level.toUpperCase().padEnd(5)} ${scrub(message)}\n`);
    } catch { /* logging must never take the app down */ }
  }

  jobFile(id: string): string { return path.join(this.jobsDir, `${id}.log`); }

  job(id: string, text: string): void {
    try { appendFileSync(this.jobFile(id), scrub(text.endsWith('\n') ? text : `${text}\n`)); } catch { /* see above */ }
  }

  readJob(id: string): string {
    try { return readFileSync(this.jobFile(id), 'utf8'); } catch { return ''; }
  }

  list(): LogFile[] {
    const out: LogFile[] = [];
    const add = (dir: string, kind: LogFile['kind']) => {
      let names: string[] = [];
      try { names = readdirSync(dir); } catch { return; }
      for (const name of names) {
        if (!name.endsWith('.log')) continue;
        try {
          const s = statSync(path.join(dir, name));
          out.push({ name, path: path.join(dir, name), size: s.size, modified: s.mtimeMs, kind });
        } catch { /* removed meanwhile */ }
      }
    };
    add(this.dir, 'app');
    add(this.jobsDir, 'job');
    return out.sort((a, b) => b.modified - a.modified);
  }

  read(file: string): string {
    const resolved = path.resolve(file);
    if (!resolved.startsWith(path.resolve(this.dir) + path.sep)) return '';
    try {
      const s = statSync(resolved);
      const text = readFileSync(resolved, 'utf8');
      return s.size > 1_500_000 ? `(showing the last part of a large log)\n${text.slice(-1_500_000)}` : text;
    } catch { return ''; }
  }

  prune(days: number): void {
    if (days <= 0) return;
    const cutoff = Date.now() - days * 86_400_000;
    let names: string[] = [];
    try { names = readdirSync(this.jobsDir); } catch { return; }
    for (const name of names) {
      const f = path.join(this.jobsDir, name);
      try { if (statSync(f).mtimeMs < cutoff) unlinkSync(f); } catch { /* ignore */ }
    }
  }
}
