#!/usr/bin/env python3
"""Feeds argument lists produced by the app to yt-dlp's real option parser.

Reads JSON cases on stdin: [{"id": ..., "args": [...]}, ...]
Writes JSON results on stdout. A case passes when the engine accepts the
arguments and its settings differ from a run with only the case's "prefix"
(for "off" and "reset" flags the prefix sets the opposite first).
"""
import contextlib
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

import yt_dlp  # noqa: E402


def snapshot(argv, bare=False):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        parsed = yt_dlp.parse_options([*([] if bare else ['--ignore-config']), *argv, 'https://example.com/v'])
    state = {'ydl': repr(sorted(parsed.ydl_opts.items(), key=lambda kv: kv[0])), 'opts': repr(sorted(vars(parsed.options).items()))}
    return state, out.getvalue() + err.getvalue()


def main():
    cases = json.load(sys.stdin)
    results = []
    for case in cases:
        try:
            bare = case.get('bare', False)
            base, _ = snapshot(case.get('prefix', []), bare)
            state, printed = snapshot(case.get('prefix', []) + case['args'], bare)
            changed = state != base or case.get('acceptOnly', False)
            results.append({'id': case['id'], 'ok': changed, 'reason': '' if changed else 'accepted, but no setting changed', 'printed': printed[-300:]})
        except SystemExit as e:
            results.append({'id': case['id'], 'ok': False, 'reason': f'engine exited ({e.code})'})
        except BaseException as e:  # noqa: BLE001 - report everything the parser raises
            results.append({'id': case['id'], 'ok': False, 'reason': f'{type(e).__name__}: {e}'[:300]})
    json.dump(results, sys.stdout)


if __name__ == '__main__':
    main()
