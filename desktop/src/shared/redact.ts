// Removes secrets from anything that leaves the app: logs, reports, the
// command preview and copied text.

const SECRET_FLAGS = new Set([
  '-p', '--password', '-2', '--twofactor', '--video-password', '--ap-password',
  '--client-certificate-password', '-u', '--username', '--ap-username',
]);
const SECRET_HEADERS = /^(authorization|cookie|proxy-authorization|x-[\w-]*(?:token|key|auth)[\w-]*)\s*:/i;
const SECRET_PARAMS = /([?&;](?:token|sig|signature|key|api_?key|auth|password|pass|pwd|session|sid|access_token|hdnea|hdnts|expire|policy|lsig|pot)=)[^&#\s'"]+/gi;

export const MASK = '•••';

export function redactArgs(args: string[]): string[] {
  const out: string[] = [];
  for (let i = 0; i < args.length; i++) {
    const a = args[i];
    const eq = a.startsWith('--') ? a.indexOf('=') : -1;
    const name = eq === -1 ? a : a.slice(0, eq);
    if (SECRET_FLAGS.has(name)) {
      if (eq !== -1) out.push(`${name}=${MASK}`);
      else { out.push(a); if (i + 1 < args.length) { out.push(MASK); i++; } }
      continue;
    }
    if (name === '--add-headers' || name === '--add-header') {
      out.push(a);
      if (eq === -1 && i + 1 < args.length) {
        const v = args[++i];
        out.push(SECRET_HEADERS.test(v) ? v.replace(/:.*/s, `:${MASK}`) : redactText(v));
      }
      continue;
    }
    out.push(redactText(a));
  }
  return out;
}

export function redactText(text: string, home?: string, user?: string): string {
  let s = text;
  // credentials inside URLs: scheme://user:pass@host
  s = s.replace(/\b([a-z][a-z0-9+.-]*:\/\/)([^\s/:@]+):([^\s/@]+)@/gi, `$1${MASK}:${MASK}@`);
  s = s.replace(SECRET_PARAMS, `$1${MASK}`);
  s = s.replace(/\b(Authorization|Cookie|Set-Cookie|Proxy-Authorization)(["']?\s*[:=]\s*)([^\r\n]+)/gi, `$1$2${MASK}`);
  s = s.replace(/\b(Bearer|Basic)\s+[A-Za-z0-9._~+/=-]{8,}/g, `$1 ${MASK}`);
  s = s.replace(/((?:--?(?:password|video-password|ap-password|twofactor|client-certificate-password|username|ap-username)|-[pu2])(?:=|\s+))(?:'[^']*'|"[^"]*"|\S+)/g, `$1${MASK}`);
  s = s.replace(/\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b/g, `${MASK}@${MASK}`);
  if (home && home.length > 1) s = s.split(home).join('~');
  if (user && user.length > 2) {
    s = s.replace(new RegExp(`([/\\\\](?:Users|home)[/\\\\])${user.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}(?=[/\\\\]|$)`, 'g'), '$1user');
  }
  return s;
}
