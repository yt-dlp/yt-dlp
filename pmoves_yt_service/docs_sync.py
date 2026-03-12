import os
import subprocess
import json
import logging
from datetime import datetime, timezone

import requests
import yt_dlp
from yt_dlp.version import __version__ as YT_DLP_VERSION

logger = logging.getLogger(__name__)

SUPA = (
    os.environ.get('SUPABASE_REST_URL')
    or os.environ.get('SUPA_REST_URL')
    or os.environ.get('SUPABASE_URL')
    or 'http://postgrest:3000'
).rstrip('/')


def _candidate_keys() -> list[str]:
    # Only service-role keys are valid for write operations.
    # SUPABASE_ANON_KEY is intentionally excluded — anon tokens lack INSERT
    # privileges on pmoves_core tables and would silently produce 403s.
    keys = [
        os.environ.get('SUPABASE_SERVICE_ROLE_KEY'),
        os.environ.get('SUPABASE_SERVICE_KEY'),
        os.environ.get('SUPABASE_KEY'),
    ]
    out: list[str] = []
    for key in keys:
        if not key:
            continue
        if key not in out:
            out.append(key)
    return out


def _capture_cmd(args: list[str]) -> str | None:
    try:
        proc = subprocess.run(args, capture_output=True, text=True, timeout=20)
        if proc.returncode != 0:
            logger.warning(
                'yt-dlp docs command failed: args=%s rc=%s stderr=%s stdout=%s',
                args,
                proc.returncode,
                proc.stderr.strip(),
                proc.stdout.strip(),
            )
            return None
        return proc.stdout
    except Exception as exc:  # best-effort
        logger.warning('yt-dlp docs command raised: args=%s err=%s', args, exc)
        return None


def collect_yt_dlp_docs() -> dict[str, object]:
    ver = getattr(yt_dlp, '__version__', None) or YT_DLP_VERSION or 'unknown'
    docs: dict[str, object] = {
        'version': ver,
        'ts': datetime.now(timezone.utc).isoformat(),
    }
    for key, args in (
        ('help_cli', ['yt-dlp', '--help']),
        ('extractors', ['yt-dlp', '--list-extractors']),
        ('user_agent', ['yt-dlp', '--dump-user-agent']),
    ):
        output = _capture_cmd(args)
        if output is not None:
            docs[key] = output
    return docs


def sync_to_supabase(docs: dict[str, object]) -> dict[str, object]:
    keys = _candidate_keys()
    if not keys:
        raise RuntimeError('SUPABASE_SERVICE_ROLE_KEY, SUPABASE_SERVICE_KEY, or SUPABASE_KEY is required')
    tool = 'yt-dlp'
    ver = docs.get('version') or 'unknown'
    rows = []
    for k in ('help_cli', 'extractors', 'user_agent'):
        content = docs.get(k)
        if content is None:
            continue
        # Store as JSON with `text` field for consistency
        rows.append({
            'tool': tool,
            'version': str(ver),
            'doc_type': k,
            'content': {'text': content},
        })
    if not rows:
        raise RuntimeError('yt-dlp docs collection returned no usable content')
    on_conflict = 'tool%2Cversion%2Cdoc_type'
    targets = [
        # Preferred: proper PostgREST profile headers for pmoves_core schema.
        {'url': f'{SUPA}/tool_docs?on_conflict={on_conflict}', 'schema': 'pmoves_core'},
        # Legacy fallback: existing callers that encode schema in table path.
        {'url': f'{SUPA}/pmoves_core.tool_docs?on_conflict={on_conflict}', 'schema': None},
        # Last fallback if schema support is not configured.
        {'url': f'{SUPA}/tool_docs?on_conflict={on_conflict}', 'schema': None},
    ]

    last_error: str | None = None
    for target in targets:
        missing_relation = False
        transport_error = False
        auth_failures = 0
        for key in keys:
            headers = {
                'apikey': key,
                'Authorization': f'Bearer {key}',
                'content-type': 'application/json',
                'Prefer': 'resolution=merge-duplicates,return=minimal',
            }
            if target['schema']:
                headers['Accept-Profile'] = target['schema']
                headers['Content-Profile'] = target['schema']
            try:
                r = requests.post(target['url'], headers=headers, json=rows, timeout=20)
            except requests.RequestException as exc:
                last_error = f'transport error: {exc}'
                transport_error = True
                break
            try:
                body = r.json()
            except ValueError:
                body = {'text': r.text}
            if r.ok:
                return {'status': 'ok', 'count': len(rows), 'version': ver}
            last_error = f'{r.status_code} {body}'
            # JWT/key mismatch can happen when layered env files contain stale aliases.
            # Continue trying available keys before failing hard.
            if r.status_code in (401, 403):
                auth_failures += 1
                continue
            # Missing schema/table: move to next target strategy.
            if r.status_code in (404, 406):
                missing_relation = True
            break
        if auth_failures == len(keys):
            logger.error(
                'yt-dlp docs sync auth failed: target=%s schema=%s error=%s',
                target['url'],
                target.get('schema'),
                last_error,
            )
        if missing_relation or transport_error:
            continue

    raise RuntimeError(f'Supabase upsert failed: {last_error}')


if __name__ == '__main__':
    data = collect_yt_dlp_docs()
    out = sync_to_supabase(data)
    print(json.dumps(out))
