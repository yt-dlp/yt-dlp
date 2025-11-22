#!/usr/bin/env python3
"""Sanitize a Markdown README for reliable rendering on PyPI.

This module provides utilities and a CLI to transform a repository's
README.md into a PyPI-friendly variant while keeping the source README
clean for GitHub.

Transformations applied:
- Add stable id attributes to Markdown headings so in-page links like
  [Link](#some-section) work on PyPI.
- Rewrite relative links (e.g. CONTRIBUTING.md, docs/file.md#frag) to
  absolute GitHub "blob" URLs.
- Preserve absolute URLs and content inside fenced code blocks.

The CLI can operate in-place or write to a separate output file and will
attempt to infer the GitHub user/repo from pyproject.toml.

Example:
    $ python devscripts/sanitize_readme.py --in-place

This will overwrite README.md with the sanitized content.
"""

import argparse
import re
from pathlib import Path
from collections.abc import Iterable


def _infer_repo_from_pyproject(pyproject_path: Path = Path('pyproject.toml')) -> tuple[str, str]:
    """Infer the GitHub user and repository from pyproject.toml.

    This is a best-effort extraction of the repository coordinates from
    the [project.urls].Repository field. If the file is not present or the
    field cannot be parsed, sensible defaults are returned.

    Args:
        pyproject_path: Path to the pyproject.toml file.

    Returns:
        A 2-tuple of (user, repo). Defaults to ('yt-dlp', 'yt-dlp').
    """
    user = repo = 'yt-dlp'
    if not pyproject_path.is_file():
        return user, repo
    try:
        txt = pyproject_path.read_text(encoding='utf-8', errors='ignore')
    except OSError:
        return user, repo

    # Look for a GitHub repository URL
    m = re.search(r'(?im)^\s*Repository\s*=\s*\"https?://github\.com/([^/\"]+)/([^/\"#?]+)\"', txt)
    if m:
        user, repo = m.group(1), m.group(2)
    return user, repo


def _is_relative_url(url: str) -> bool:
    """Return True if the URL is relative to the repository.

    A relative URL here means it has no explicit scheme (http, https, etc.)
    and is not an in-page anchor beginning with '#'. Any URL beginning with
    a valid scheme followed by ':' (e.g., https:, mailto:, ftp:) is treated
    as absolute and will not be rewritten.

    Args:
        url: The URL string from a Markdown link.

    Returns:
        True if the URL should be treated as a path within the repository.
    """
    if url.startswith('#'):
        return False
    # Consider any scheme form "scheme:..." as absolute
    return not re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:', url)


def _is_repo_root_relative(url: str) -> bool:
    """Return True if the URL is root-relative (starts with '/').

    GitHub supports links rooted at the repository root beginning with '/'.
    These need a small normalization step before converting to a blob URL.

    Args:
        url: The URL string from a Markdown link.

    Returns:
        True if the URL is root-relative.
    """
    return url.startswith('/')


def _to_abs_url(url: str, *, user: str, repo: str, branch: str, is_image: bool) -> str:
    """Convert a relative repository URL to an absolute GitHub blob URL.

    Args:
        url: Relative path (or root-relative) to a file in the repository.
        user: GitHub user/organization name.
        repo: GitHub repository name.
        branch: Git branch name (e.g., 'master').
        is_image: Unused. Kept for compatibility with earlier versions.

    Returns:
        An absolute https://github.com/{user}/{repo}/blob/{branch}/{path} URL.
    """
    # Normalize leading '/'
    path = url[1:] if _is_repo_root_relative(url) else url
    base = f'https://github.com/{user}/{repo}/blob/{branch}/'
    return base + path


def _to_readme_anchor_url(anchor: str, *, user: str, repo: str, branch: str) -> str:
    """Build an absolute URL to the README with the given fragment.

    Note: Currently unused since in-page anchors are preserved and we
    generate ids for headings. Kept for parity and potential future use.

    Args:
        anchor: The anchor string (may include leading '#').
        user: GitHub user/organization name.
        repo: GitHub repository name.
        branch: Git branch name (e.g., 'master').

    Returns:
        An absolute README URL with the fragment, or the page URL if empty.
    """
    frag = anchor.lstrip('#')
    base = f'https://github.com/{user}/{repo}/blob/{branch}/README.md'
    return f'{base}#{frag}' if frag else base


def _split_fenced(text: str) -> Iterable[tuple[bool, str]]:
    """Split text into code and non-code segments based on fenced blocks.

    The function yields (is_code_block, segment) pairs, where is_code_block
    indicates whether the segment represents a fenced code block. Both
    backtick (```) and tilde (~~~) fences are supported. Fence markers are
    included in the returned code segments and left unmodified.

    Args:
        text: The complete Markdown content.

    Yields:
        Tuples of (is_code_block, segment) covering the entire input text.
    """
    out = []
    i = 0
    fence_re = re.compile(r'^(?P<fence>```|~~~)[^\n]*\n', re.MULTILINE)
    while i < len(text):
        m = fence_re.search(text, i)
        if not m:
            out.append((False, text[i:]))
            break
        # Non-code chunk before fence
        if m.start() > i:
            out.append((False, text[i:m.start()]))
        fence = m.group('fence')
        # Find closing fence
        end_pat = re.compile(rf'^{re.escape(fence)}\s*$', re.MULTILINE)
        m_end = end_pat.search(text, m.end())
        end_idx = (m_end.end() if m_end else len(text))
        # Include a trailing newline after closing fence if present right after
        if m_end and end_idx < len(text) and text[end_idx] == '\n':
            end_idx += 1
        out.append((True, text[m.start():end_idx]))
        i = end_idx
    return out


def rewrite_links_in_text(text: str, *, user: str, repo: str, branch: str) -> str:
    """Rewrite Markdown links in a content segment.

    This function operates on non-code segments and performs two
    transformations:
    1. Keep in-page anchors (#...) unchanged; they will resolve to the
       heading IDs we generate separately.
    2. Convert relative links to absolute GitHub blob URLs.

    Args:
        text: A Markdown segment with no fenced code blocks.
        user: GitHub user/organization name.
        repo: GitHub repository name.
        branch: Git branch name (e.g., 'master').

    Returns:
        The segment with rewritten links.
    """
    # 0) Special-case: links that wrap an image, e.g. [![alt](img)](url "title")
    # The generic inline pattern cannot match nested brackets; handle this first
    def repl_img_link(m: re.Match) -> str:
        url = m.group('url')
        title = m.group('title') or ''
        if url.startswith('#') or not _is_relative_url(url):
            return m.group(0)
        new_url = _to_abs_url(url, user=user, repo=repo, branch=branch, is_image=False)
        return f"{m.group('label')}({new_url}{title})"

    img_link_pat = re.compile(r'(?P<label>\[!\[[^\]]+\]\([^)]+\)\])\((?P<url>[^)\s]+)(?P<title>\s+\"[^\"]*\")?\)')
    text = img_link_pat.sub(repl_img_link, text)

    # 1) Rewrite inline images and links: ![alt](url "title") and [text](url "title")
    def repl_inline(m: re.Match) -> str:
        label = m.group('label')
        url = m.group('url')
        title = m.group('title') or ''

        # Keep in-page anchors as-is; we'll add IDs to headings separately
        if url.startswith('#'):
            return m.group(0)
        if _is_relative_url(url):
            new_url = _to_abs_url(url, user=user, repo=repo, branch=branch, is_image=False)
            return f"{m.group('bang') or ''}[{label}]({new_url}{title})"
        return m.group(0)

    inline_pat = re.compile(r'(?P<bang>!?)\[(?P<label>[^\]]+)\]\((?P<url>[^)\s]+)(?P<title>\s+\"[^\"]*\")?\)')
    text = inline_pat.sub(repl_inline, text)

    # 2) Rewrite reference-style link/image definitions: [id]: url 'title'
    def repl_ref(m: re.Match) -> str:
        url = m.group('url')
        rest = m.group('rest') or ''
        if url.startswith('#'):
            return m.group(0)
        if _is_relative_url(url):
            new_url = _to_abs_url(url, user=user, repo=repo, branch=branch, is_image=False)
            return f"{m.group('lead')}[{m.group('id')}]:{m.group('spc')}{new_url}{rest}"
        return m.group(0)

    ref_pat = re.compile(r'(?m)^(?P<lead>[ \t]*)\[(?P<id>[^\]]+)\]:(?P<spc>[ \t]*)(?P<url>\S+)(?P<rest>.*)$')
    return ref_pat.sub(repl_ref, text)


_heading_pat = re.compile(r'^(?P<hashes>#{1,6})[ \t]*(?P<title>.+?)[ \t]*$', re.MULTILINE)


def _slugify(str_: str) -> str:
    """Create a stable fragment identifier for a heading title.

    The behavior is intentionally conservative and close to GitHub's
    slugification so that internal links work consistently between
    GitHub and PyPI.

    Args:
        str_: The original heading text.

    Returns:
        A lowercase, hyphenated slug suitable for use as an HTML id.
    """
    str_ = str_.strip().lower()
    # Remove anything except lowercase ASCII, digits, space, and hyphen
    str_ = re.sub(r'[^a-z0-9\- ]+', '', str_)
    str_ = re.sub(r'\s+', '-', str_)
    str_ = re.sub(r'-{2,}', '-', str_)
    return str_.strip('-')


def _add_heading_ids(text: str) -> str:
    """Replace Markdown ATX headings with HTML headings carrying ids.

    This enables in-page navigation on PyPI, where automatic heading
    IDs are not generated. The original heading level and text are
    preserved.

    Args:
        text: A Markdown segment with no fenced code blocks.

    Returns:
        The segment with ATX headings replaced by HTML headings.
    """
    def repl(m: re.Match) -> str:
        title = m.group('title')
        frag = _slugify(title)
        level = len(m.group('hashes'))
        return f'<h{level} id="{frag}">{title}</h{level}>'
    return _heading_pat.sub(repl, text)


_pypi_badge_pat = re.compile(r'\[!\[PyPI\]\([^)]+\)\]\((?P<url>https?://pypi\.org/project/[^)\s]+)(?P<title>\s+\"[^\"]*\")?\)')


def _replace_pypi_badges(text: str, *, user: str, repo: str) -> str:
    """Replace common PyPI shields badges with a GitHub badge.

    This targets the pattern [![PyPI](...)](https://pypi.org/project/<name>
    "...") and replaces it with a GitHub badge pointing to the repository.

    Args:
        text: The Markdown segment to transform.
        user: GitHub user/organization name.
        repo: GitHub repository name.

    Returns:
        The segment with PyPI badges replaced, if any.
    """
    badge_img = 'https://img.shields.io/badge/-GitHub-181717.svg?logo=github&labelColor=555555&style=for-the-badge'

    def repl(_: re.Match) -> str:
        return f'[![GitHub]({badge_img})](https://github.com/{user}/{repo} "GitHub")'

    return _pypi_badge_pat.sub(repl, text)


def _ensure_block_spacing(text: str) -> str:
    """Ensure a blank line after HTML headings to keep Markdown blocks intact.

    Some Markdown renderers (including PyPI's) require a blank line between an
    HTML block (like <h2>...</h2>) and the next Markdown block (tables, lists,
    etc.) to avoid mis-parsing. This normalizes spacing without changing
    low-level heading generation or tests that assert exact strings. I now see
    why https://commonmark.org/ and that ecosystem enforce it.

    If there is exactly one newline after </hX>, add one more. If there are
    already 2+ newlines, leave as-is.
    """
    return re.sub(r'(?m)(</h[1-6]>\n)(?!\n)', r'\1\n', text)


def sanitize_readme(text: str, *, user: str, repo: str, branch: str) -> str:
    """Produce a PyPI-friendly README from Markdown content.

    This function is the main transformation pipeline. It splits the README
    into fenced and non-fenced segments, preserves fenced code blocks verbatim,
    injects id attributes into ATX headings, replaces common PyPI badges with
    a GitHub badge, and rewrites relative links to absolute GitHub blob URLs.

    Args:
        text: The original README content.
        user: GitHub user/organization name.
        repo: GitHub repository name.
        branch: Git branch name (e.g., 'master').

    Returns:
        The sanitized README content as a single string.
    """
    segments = []
    for is_code, seg in _split_fenced(text):
        if is_code:
            segments.append(seg)  # Do not touch code blocks
        else:
            # First, add id attributes to headings so in-page anchors work on PyPI
            seg = _add_heading_ids(seg)
            # Replace PyPI badge(s) with GitHub badge
            seg = _replace_pypi_badges(seg, user=user, repo=repo)
            # Then, rewrite relative links to absolute GitHub blob URLs
            seg = rewrite_links_in_text(seg, user=user, repo=repo, branch=branch)
            # Finally, normalize spacing after HTML headings for safe Markdown parsing
            seg = _ensure_block_spacing(seg)
        segments.append(seg)
    return ''.join(segments)


def main():
    """CLI entry point.

    This command reads a README, sanitizes it for PyPI compatibility, and
    either writes the result back in-place or to a specified output file.
    Repository coordinates are inferred from pyproject.toml if not provided.
    """
    ap = argparse.ArgumentParser(description='Sanitize README for PyPI: rewrite relative links and add heading ids')
    ap.add_argument('--readme', default='README.md', help='Path to input README (default: README.md)')
    ap.add_argument('--output', default=None, help='Output path. If omitted, will write <stem>_PyPI<suffix> unless --in-place')
    ap.add_argument('--in-place', action='store_true', help='Overwrite the input README in-place')
    ap.add_argument('--user', default=None, help='GitHub user/organization (default: inferred from pyproject, then yt-dlp)')
    ap.add_argument('--repo', default=None, help='GitHub repository name (default: inferred from pyproject, then yt-dlp)')
    ap.add_argument('--branch', default='master', help='Repository branch to link to (default: master)')
    args = ap.parse_args()

    user, repo = (args.user, args.repo)
    if not user or not repo:
        inf_user, inf_repo = _infer_repo_from_pyproject()
        user = user or inf_user
        repo = repo or inf_repo

    readme_path = Path(args.readme)
    original = readme_path.read_text(encoding='utf-8')

    updated = sanitize_readme(original, user=user, repo=repo, branch=args.branch)

    if args.in_place:
        readme_path.write_text(updated, encoding='utf-8')
        print(f'{readme_path} sanitized for PyPI')
    else:
        out_path = Path(args.output or (readme_path.with_name(readme_path.stem + '_PyPI' + readme_path.suffix)))
        out_path.write_text(updated, encoding='utf-8')
        print(f'Wrote sanitized README to {out_path}')


if __name__ == '__main__':
    main()
