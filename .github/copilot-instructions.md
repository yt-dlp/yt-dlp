# yt-dlp AI Agent Instructions

## Project Overview
**yt-dlp** is a feature-rich command-line audio/video downloader supporting thousands of sites. It's a maintained fork of youtube-dl with active development focusing on extractors, post-processing, and format handling.

## Core Architecture

### Main Components
1. **Extractors** (`yt_dlp/extractor/`): Site-specific video/metadata extraction logic
   - All inherit from `InfoExtractor` base class
   - Each implements `_real_extract(url)` returning metadata dict
   - Use lazy loading via `lazy_extractors.py` for fast startup
   - Pattern: `class SiteNameIE(InfoExtractor)` → auto-registered in CLI

2. **YoutubeDL** (`yt_dlp/YoutubeDL.py`): Main orchestrator
   - Downloads videos, applies post-processors, manages output
   - Handles format selection, metadata parsing, playlist processing
   - ~4500 lines; critical coordination point

3. **Post-Processors** (`yt_dlp/postprocessor/`): Media transformations
   - FFmpeg integration for merging, encoding, subtitle embedding
   - Metadata embedding, chapter splitting, SponsorBlock integration

4. **Downloaders** (`yt_dlp/downloader/`): Protocol-specific download
   - HTTP, HLS, DASH, RTMP, etc.
   - Fragmented media reassembly

5. **Networking** (`yt_dlp/networking/`): Request handling
   - Browser impersonation (curl_cffi, default fallbacks)
   - Cookie management, proxy support

## Critical Developer Workflows

### Running Tests
```bash
hatch test [ExtractorName]        # Test specific extractor
hatch test --pytest-args "-k pattern"  # Test by pattern
python -m pytest test/test_utils.py    # Specific test file
make offlinetest                   # Run without downloading
```

### Building & Testing Locally
```bash
make yt-dlp                        # Build zipimport binary
hatch fmt --check                  # Check code style
hatch fmt                          # Auto-fix issues
python -m yt_dlp -vU               # Debug verbose output
```

### Code Standards (Enforced via ruff/autopep8)
- **120 char soft limit** (not hard rule); prioritize readability
- **Single quotes** for strings; double quotes for docstrings  
- **No line breaks** in URLs/string literals to fit limits
- **Import style**: `from module import items` with isort ordering
- **Null handling**: Use `traverse_obj()`, `.get()`, not `[]` access
- **Safe conversions**: `int_or_none()`, `float_or_none()`, `url_or_none()`

### Extractor Patterns
When adding site support (`yt_dlp/extractor/yoursite.py`):

1. **Required fields** in info dict: `id`, `title`, and either `url` or `formats`
2. **Mandatory structure**:
   ```python
   from .common import InfoExtractor
   
   class YourSiteIE(InfoExtractor):
       _VALID_URL = r'https?://(?:www\.)?yoursite\.com/...'
       _TESTS = [{'url': '...', 'info_dict': {...}}]
       
       def _real_extract(self, url):
           video_id = self._match_id(url)
           webpage = self._download_webpage(url, video_id)
           return {'id': video_id, 'title': title, ...}
   ```

3. **Optional fields**: Use `.get()` and `fatal=False` for robustness
4. **Regex patterns**: Keep fuzzy/relaxed; avoid capturing unused groups
5. **Fallbacks**: Extract metadata from multiple sources for future-proofing

### Testing Extractors
- Tests must include full `md5` hash of first 10241 bytes OR skip reason
- Run: `hatch test YourSiteIE` to auto-validate extracted fields
- Must pass Python 3.10+ and PyPy 3.11+

## Special Topics

### Format Selection & Merging
- Default: `-f bestvideo*+bestaudio/best` (merges video+audio via ffmpeg)
- Filtering: `-f "bv[height<=720]/b"` uses bracket syntax
- Sorting: `-S res:720,fps` (descending by default; use `+` to reverse)
- **Critical**: Merging requires ffmpeg + `--merge-output-format`

### Plugins System
- Plugins auto-load from `yt_dlp_plugins.{extractor,postprocessor}` namespace packages
- Extractors take priority over built-ins
- Set `YTDLP_NO_PLUGINS` env var to disable

### Lazy Extractors
- Auto-generated file `yt_dlp/extractor/lazy_extractors.py` delays import until needed
- Run `make lazy-extractors` or `python devscripts/make_lazy_extractors.py`
- Never edit manually; regenerate after adding extractors

### Configuration Files
- Searched in: portable config, home, user (`~/.config/yt-dlp/config`), system (`/etc/yt-dlp.conf`)
- Same syntax as CLI options (no whitespace after `-`/`--`)

## Project-Specific Conventions

### Metadata Dictionary (Info Dict)
Returned by extractors; processed by YoutubeDL:
- **Core**: `id`, `title` (required); `ext` or `formats` (required)
- **Common**: `url`, `uploader`, `upload_date`, `duration`, `description`, `thumbnail`
- **Advanced**: `formats[]` (list of quality options), `chapters`, `subtitles`, `automatic_captions`
- Always use **YYYYMMDD** for dates, **Unix epoch** for timestamps

### Extractor Error Handling
- `ExtractorError`: Expected failures (video deleted, geo-restricted)
  ```python
  raise ExtractorError('Video unavailable', expected=True)
  ```
- Missing optional fields: Log warning or return `None` (don't break extraction)
- Use `traverse_obj()` for nested dict safety:
  ```python
  traverse_obj(json_data, ('video', 'format', 'url'), expected_type=url_or_none)
  ```

### Version & Release Channels
- **Stable**: Standard releases
- **Nightly**: Daily builds; recommended for users
- **Master**: Every commit; bleeding edge with potential regressions
- Version: YYYYMMDD format (auto-updated via `devscripts/update-version.py`)

## Critical Files & Patterns

| File | Purpose |
|------|---------|
| `yt_dlp/__main__.py` | CLI entry point; imports YoutubeDL |
| `yt_dlp/YoutubeDL.py` | Core download orchestration |
| `yt_dlp/extractor/common.py` | `InfoExtractor` base class; 4100+ lines |
| `yt_dlp/options.py` | CLI argument definitions |
| `yt_dlp/utils/` | Reusable utilities (`traverse_obj`, parsing, etc.) |
| `test/test_YoutubeDL.py` | Core integration tests |
| `test/test_utils.py` | Utility function tests |
| `devscripts/make_lazy_extractors.py` | Generates lazy loader |

## Common Gotchas

1. **Extractor import**: Only import at class level; avoid circular deps
2. **Regex escaping**: Use raw strings (`r''`); escape `/` in URLs carefully
3. **Format merging**: Requires ffmpeg + valid merge format; fails silently if unavailable
4. **Metadata changes**: Post-processing can modify fields; use `--print` hooks for final state
5. **Plugin conflicts**: Built-in extractors override plugins; be explicit with plugin namespaces
6. **Test data changes**: Sites frequently alter HTML/JSON; consider using `--write-pages` for debugging

## Contribution Rules

- **No AI-generated code without human review** (per CONTRIBUTING.md policy)
- Always understand every line you change/add
- Add tests for all new extractors (even `skip` reason is mandatory)
- Follow ruff/autopep8 formatting (auto-fixed by `hatch fmt`)
- Create issue first for major features (discuss with maintainers)
