// POSIX-style shell word splitting and quoting, matching what yt-dlp does when
// it reads a config file (Python's shlex with comments enabled).

export function split(input: string, comments = true): string[] {
  const out: string[] = [];
  let cur = '';
  let has = false;
  let i = 0;
  const n = input.length;
  while (i < n) {
    const ch = input[i];
    if (ch === "'") {
      const end = input.indexOf("'", i + 1);
      if (end === -1) throw new Error('Unclosed single quote');
      cur += input.slice(i + 1, end);
      has = true;
      i = end + 1;
    } else if (ch === '"') {
      i++;
      let closed = false;
      while (i < n) {
        const c = input[i];
        if (c === '"') { closed = true; i++; break; }
        if (c === '\\' && i + 1 < n && '"\\$`\n'.includes(input[i + 1])) {
          if (input[i + 1] !== '\n') cur += input[i + 1];
          i += 2;
        } else { cur += c; i++; }
      }
      if (!closed) throw new Error('Unclosed double quote');
      has = true;
    } else if (ch === '\\') {
      if (i + 1 < n) {
        if (input[i + 1] !== '\n') { cur += input[i + 1]; has = true; }
        i += 2;
      } else i++;
    } else if (ch === '#' && comments && !has) {
      while (i < n && input[i] !== '\n') i++;
    } else if (/\s/.test(ch)) {
      if (has) { out.push(cur); cur = ''; has = false; }
      i++;
    } else { cur += ch; has = true; i++; }
  }
  if (has) out.push(cur);
  return out;
}

export function quote(arg: string): string {
  if (arg === '') return "''";
  if (/^[A-Za-z0-9_@%+=:,./~-]+$/.test(arg)) return arg;
  return "'" + arg.replace(/'/g, `'"'"'`) + "'";
}

export function join(args: string[]): string {
  return args.map(quote).join(' ');
}
