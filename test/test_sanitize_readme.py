import importlib.util
from importlib.abc import Loader
from typing import cast
from pathlib import Path

import pytest


def _load_sanitizer_module():
    mod_path = Path('devscripts/sanitize_readme.py')
    spec = importlib.util.spec_from_file_location('sanitize_readme', str(mod_path))
    assert spec is not None
    mod = importlib.util.module_from_spec(spec)
    loader = cast(Loader, spec.loader)
    assert loader is not None
    loader.exec_module(mod)
    return mod


@pytest.fixture(scope='module')
def san():
    return _load_sanitizer_module()


def test_slugify_basic(san):
    assert san._slugify('Download Options:') == 'download-options'
    assert san._slugify('INSTALLATION') == 'installation'
    assert san._slugify('Notes about environment variables') == 'notes-about-environment-variables'


@pytest.mark.parametrize(
    'title,expected',
    [
        ('Network Options:', 'network-options'),
        ('Video Format Options:', 'video-format-options'),
        ('Notes — advanced!', 'notes-advanced'),  # em-dash and bang removed
        ('Title with 123', 'title-with-123'),
    ],
)
def test_slugify_param(san, title, expected):
    assert san._slugify(title) == expected


@pytest.mark.parametrize(
    'src,expected',
    [
        ('# Title', '<h1 id="title">Title</h1>'),
        ('## Download Options:', '<h2 id="download-options">Download Options:</h2>'),
        ('### Subtitle here', '<h3 id="subtitle-here">Subtitle here</h3>'),
    ],
)
def test_add_heading_ids(san, src, expected):
    out = san._add_heading_ids(src)
    assert out == expected


def test_keep_in_page_anchor(san):
    src = 'See [Usage](#usage-and-options) for details.'
    out = san.rewrite_links_in_text(src, user='yt-dlp', repo='yt-dlp', branch='master')
    # Anchor should be preserved as-is
    assert out == src


@pytest.mark.parametrize(
    'src,expected',
    [
        (
            'Read [Contrib](CONTRIBUTING.md#how-to).',
            'Read [Contrib](https://github.com/yt-dlp/yt-dlp/blob/master/CONTRIBUTING.md#how-to).',
        ),
        (
            'See [Doc](/docs/file.md).',
            'See [Doc](https://github.com/yt-dlp/yt-dlp/blob/master/docs/file.md).',
        ),
        (
            'Ref [link][id]\n\n[id]: docs/guide.md#sec',
            'Ref [link][id]\n\n[id]: https://github.com/yt-dlp/yt-dlp/blob/master/docs/guide.md#sec',
        ),
    ],
)
def test_relative_link_rewrite(san, src, expected):
    out = san.rewrite_links_in_text(src, user='yt-dlp', repo='yt-dlp', branch='master')
    assert out == expected


def test_absolute_url_unchanged(san):
    src = 'Visit [Site](https://example.com/x).'
    out = san.rewrite_links_in_text(src, user='yt-dlp', repo='yt-dlp', branch='master')
    assert out == src


def test_nested_image_link_relative_target_rewritten(san):
    src = (
        '[![Donate](https://img.shields.io/badge/_-Donate-red.svg?logo=githubsponsors&labelColor=555555&style=for-the-badge)]'
        '(Collaborators.md#collaborators "Donate")'
    )
    expected = (
        '[![Donate](https://img.shields.io/badge/_-Donate-red.svg?logo=githubsponsors&labelColor=555555&style=for-the-badge)]'
        '(https://github.com/yt-dlp/yt-dlp/blob/master/Collaborators.md#collaborators "Donate")'
    )
    out = san.rewrite_links_in_text(src, user='yt-dlp', repo='yt-dlp', branch='master')
    assert out == expected


@pytest.mark.parametrize(
    'url,expected',
    [
        ('CONTRIBUTING.md', True),
        ('/docs/file.md', True),
        ('#section', False),
        ('https://example.com/x', False),
        ('mailto:user@example.com', False),
    ],
)
def test_is_relative_url(san, url, expected):
    assert san._is_relative_url(url) is expected


@pytest.mark.parametrize(
    'url,expected',
    [
        ('/docs/file.md', True),
        ('docs/file.md', False),
        ('#x', False),
    ],
)
def test_is_repo_root_relative(san, url, expected):
    assert san._is_repo_root_relative(url) is expected


@pytest.mark.parametrize(
    'url,expect_suffix',
    [
        ('CONTRIBUTING.md', 'https://github.com/yt-dlp/yt-dlp/blob/master/CONTRIBUTING.md'),
        ('/docs/file.md', 'https://github.com/yt-dlp/yt-dlp/blob/master/docs/file.md'),
    ],
)
def test_to_abs_url(san, url, expect_suffix):
    out = san._to_abs_url(url, user='yt-dlp', repo='yt-dlp', branch='master', is_image=False)
    assert out == expect_suffix


def test_to_readme_anchor_url(san):
    out = san._to_readme_anchor_url('#usage', user='yt-dlp', repo='yt-dlp', branch='master')
    assert out.endswith('/README.md#usage')


@pytest.mark.parametrize('fence', ['```', '~~~'])
def test_fenced_code_blocks_untouched(san, fence):
    src = (
        f'Outside [file](CONTRIBUTING.md)\n\n'
        f'{fence}python\n'
        f'# inside code: [file](CONTRIBUTING.md)\n'
        f'{fence}\n'
    )
    out = san.sanitize_readme(src, user='yt-dlp', repo='yt-dlp', branch='master')
    # Outside gets rewritten
    assert 'https://github.com/yt-dlp/yt-dlp/blob/master/CONTRIBUTING.md' in out
    # Inside code remains literal
    assert '# inside code: [file](CONTRIBUTING.md)' in out


@pytest.mark.parametrize(
    'src',
    [
        '[![PyPI](https://img.shields.io/badge/-PyPI-blue.svg?logo=pypi&labelColor=555555&style=for-the-badge)](https://pypi.org/project/yt-dlp "PyPI")',
        '[![PyPI](https://img.shields.io/badge/-PyPI-blue.svg)](https://pypi.org/project/yt-dlp)',
    ],
)
def test_pypi_badge_replaced(san, src):
    out = san.sanitize_readme(src, user='yt-dlp', repo='yt-dlp', branch='master')
    assert 'img.shields.io/badge/-GitHub-181717.svg' in out
    assert 'pypi.org/project' not in out


def test_infer_repo_from_pyproject(tmp_path, san):
    pp = tmp_path / 'pyproject.toml'
    pp.write_text('[project]\nname = "x"\n\n[project.urls]\nRepository = "https://github.com/userX/repoY"\n', encoding='utf-8')
    user, repo = san._infer_repo_from_pyproject(pp)
    assert (user, repo) == ('userX', 'repoY')


def test_split_fenced_segments(san):
    src = 'a\n```\ncode\n```\nb\n'
    segments = list(san._split_fenced(src))
    assert segments == [
        (False, 'a\n'),
        (True, '```\ncode\n```\n'),
        (False, 'b\n'),
    ]


def test_pipeline_keeps_anchors_and_rewrites_relative_links(san):
    src = (
        '# Title\n\n'
        '* [USAGE](#usage-and-options)\n'
        '* [Contrib](CONTRIBUTING.md#how-to)\n'
    )
    out = san.sanitize_readme(src, user='yt-dlp', repo='yt-dlp', branch='master')
    # Heading gets id
    assert '<h1 id="title">Title</h1>' in out
    # Internal anchor preserved
    assert '[USAGE](#usage-and-options)' in out
    # Relative link rewritten
    assert '(https://github.com/yt-dlp/yt-dlp/blob/master/CONTRIBUTING.md#how-to)' in out


def test_ensure_block_spacing_inserts_blank_line(san):
    src = '<h2 id="sec">Section</h2>\n- item\n'
    expected = '<h2 id="sec">Section</h2>\n\n- item\n'
    out = san._ensure_block_spacing(src)
    assert out == expected


def test_ensure_block_spacing_keeps_existing_blank_line(san):
    src = '<h3 id="x">X</h3>\n\n1. one\n'
    out = san._ensure_block_spacing(src)
    assert out == src


def test_ensure_block_spacing_end_of_string_behavior(san):
    # Closing h4 followed by exactly one newline at end of string -> add a second newline
    src1 = '<h4 id="eof">followed by exactly one newline</h4>\n'
    expected1 = '<h4 id="eof">followed by exactly one newline</h4>\n\n'
    assert san._ensure_block_spacing(src1) == expected1

    # Closing h4 with no trailing newline at end of string -> unchanged
    src2 = '<h4 id="eof">no trailing newline</h4>'
    assert san._ensure_block_spacing(src2) == src2


def test_block_spacing_applied_in_pipeline(san):
    src = '# Heading\n- item\n'
    out = san.sanitize_readme(src, user='yt-dlp', repo='yt-dlp', branch='master')
    assert '<h1 id="heading">Heading</h1>\n\n- item' in out
