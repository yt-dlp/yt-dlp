# Claude Instructions for yt-dlp

This file provides guidance for Claude (the AI assistant) when working on the yt-dlp project.

## Project Overview

**yt-dlp** is a feature-rich command-line audio/video downloader with support for thousands of sites. It is a fork of youtube-dl based on the now inactive youtube-dlc.

- **Primary Language**: Python
- **Main Module**: `yt_dlp/`
- **Extractors**: Located in `yt_dlp/extractor/`
- **Utilities**: Located in `yt_dlp/utils/`
- **Post-processors**: Located in `yt_dlp/postprocessor/`

## Key Files and Directories

- `yt_dlp/YoutubeDL.py` - Core downloader class
- `yt_dlp/extractor/` - Video site extractors (each site has its own module)
- `yt_dlp/utils/` - Utility functions
- `yt_dlp/postprocessor/` - Post-processing modules (ffmpeg, metadata, etc.)
- `README.md` - User documentation
- `CONTRIBUTING.md` - Contribution guidelines
- `supportedsites.md` - List of supported sites
- `Makefile` - Build and test commands

## Development Practices

### Before Making Changes

1. **Read the file first** - Always read the relevant file(s) before proposing changes
2. **Understand the pattern** - Look at similar implementations in the codebase for consistency
3. **Check CONTRIBUTING.md** - Review contribution guidelines for code standards
4. **Keep it simple** - Avoid over-engineering; focus on the specific task at hand

### Code Style

- Follow PEP 8 guidelines where practical
- Match the existing code style in the file being modified
- Use descriptive variable and function names
- Avoid unnecessary comments - code should be self-explanatory
- Keep functions focused and reasonably sized

### Adding Extractors

When adding or modifying an extractor (in `yt_dlp/extractor/`):

1. Inherit from `InfoExtractor` base class
2. Set `_VALID_URL` regex to match the site's URLs
3. Implement the `_real_extract()` method
4. Extract metadata: id, title, duration, description, etc.
5. Handle error cases appropriately
6. Test with real URLs from the target site

### Testing

- Run `make test` to execute the test suite
- Tests are located in the `tests/` directory
- For extractor tests, follow the pattern in `tests/test_YoutubeDL.py`
- Use `makefile` targets for development tasks

## Common Tasks

### Add Support for a New Site

1. Create a new extractor file in `yt_dlp/extractor/` (or modify existing)
2. Define the `_VALID_URL` pattern
3. Implement `_real_extract()` method
4. Extract and return metadata dictionary
5. Test with real URLs

### Fix Extraction Issues

1. Identify the affected extractor
2. Debug using `print()` or test harness
3. Update extraction logic (DOM parsing, API calls, regex, etc.)
4. Verify the fix works with real URLs
5. Consider edge cases

### Add Utility Functions

1. Add to `yt_dlp/utils/__init__.py` or create a new utility module
2. Include proper error handling
3. Add docstrings for public functions
4. Test with various inputs

### Update Post-Processing

1. Modify relevant file in `yt_dlp/postprocessor/`
2. Ensure compatibility with supported formats
3. Test with various input files
4. Handle missing dependencies gracefully

## Code Organization Tips

- **Extractors** are organized alphabetically by site name
- **Utils** are grouped by functionality
- **Imports** should be at the top of files, sorted alphabetically
- **Constants** are typically UPPERCASE
- **Private methods/functions** start with underscore

## Git Workflow

When committing changes:

- Write clear, descriptive commit messages
- Reference issue numbers if applicable (e.g., `fixes #1234`)
- Group related changes in a single commit
- Keep commits focused and atomic

Example commit message:
```
[ie/sitename] Add support for new video format (#12345)

- Implement extraction for new format
- Update URL regex to match format URLs
- Add tests for new format
```

## Debugging Tips

- Use `print()` for quick debugging in extractors
- Check actual HTML/API responses from target sites
- Verify regex patterns work as expected
- Look for similar extractors for reference implementations
- Check the issue tracker for known problems

## References

- [CONTRIBUTING.md](CONTRIBUTING.md) - Full contribution guidelines
- [README.md](README.md) - User documentation
- [supportedsites.md](supportedsites.md) - Complete list of supported sites
- [YouTube-DL Documentation](https://github.com/ytdl-org/youtube-dl) - For InfoExtractor base class reference
