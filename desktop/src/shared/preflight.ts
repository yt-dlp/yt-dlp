// Problems that can be spotted before the engine starts. Each one would
// otherwise end in a confusing engine failure.
import type { OptionValues } from './schema';

const has = (v: OptionValues, k: string) => {
  const x = v[k];
  return Array.isArray(x) ? x.some((r) => (Array.isArray(r) ? r.some(Boolean) : !!r)) : x !== undefined && x !== '';
};

export function preflight(v: OptionValues): string[] {
  const out: string[] = [];
  if (has(v, '--username') && !has(v, '--password') && !has(v, '--netrc-cmd')) out.push('A username is set but no password. The engine would ask for the password in a terminal, which the app does not have. Fill in Password under Sign-in and cookies.');
  if (has(v, '--password') && !has(v, '--username')) out.push('A password is set without a username. Fill in Username under Sign-in and cookies.');
  if (has(v, '--ap-username') && !has(v, '--ap-password')) out.push('A TV provider username is set but no password. Fill in TV provider password under Sign-in and cookies.');
  if (has(v, '--ap-password') && !has(v, '--ap-username')) out.push('A TV provider password is set without a username.');
  if (has(v, '--max-sleep-interval') && !has(v, '--sleep-interval')) out.push('“Longest random wait” only works together with “Wait before each download” under Network.');
  if (v['--batch-file'] === '-') out.push('“Read links from file” cannot read from standard input in the app. Choose a file, or paste the links into the Links box.');
  return out;
}
