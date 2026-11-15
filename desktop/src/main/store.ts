// Small JSON files with atomic writes. A corrupt file is set aside rather
// than crashing the app or being silently overwritten.

import { existsSync, mkdirSync, readFileSync, renameSync, writeFileSync } from 'node:fs';
import path from 'node:path';

export class JsonStore<T> {
  private data: T;
  private timer: NodeJS.Timeout | null = null;

  constructor(private file: string, fallback: T, private merge: (loaded: unknown, fallback: T) => T = (l) => l as T) {
    this.data = fallback;
    mkdirSync(path.dirname(file), { recursive: true });
    if (existsSync(file)) {
      try {
        this.data = this.merge(JSON.parse(readFileSync(file, 'utf8')), fallback);
      } catch {
        try { renameSync(file, `${file}.corrupt-${Date.now()}`); } catch { /* keep going with defaults */ }
      }
    }
  }

  get(): T { return this.data; }

  set(next: T, immediate = false): void {
    this.data = next;
    if (immediate) { this.flush(); return; }
    if (!this.timer) this.timer = setTimeout(() => this.flush(), 400);
  }

  flush(): void {
    if (this.timer) { clearTimeout(this.timer); this.timer = null; }
    const tmp = `${this.file}.tmp`;
    try {
      writeFileSync(tmp, JSON.stringify(this.data, null, 1));
      renameSync(tmp, this.file);
    } catch { /* disk full or read-only: keep running with in-memory state */ }
  }
}
