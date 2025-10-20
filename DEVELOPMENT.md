# YT-DLP Development Setup

This is your personal fork of YT-DLP for development and contributions.

## 🚀 Quick Start

### Environment Setup
```bash
# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Run YT-DLP from source
& .\.venv\Scripts\python.exe -m yt_dlp [URL]

# Run tests
& .\.venv\Scripts\python.exe -m pytest test/

# Code formatting and linting
& .\.venv\Scripts\python.exe -m ruff check
& .\.venv\Scripts\python.exe -m ruff format
```

### Development Workflow

1. **Make changes** to extractors in `yt_dlp/extractor/`
2. **Test your changes** with real videos
3. **Run tests** to ensure nothing breaks
4. **Format code** with ruff
5. **Commit and push** your changes

### Key Directories

- `yt_dlp/extractor/` - All site extractors
- `yt_dlp/extractor/youtube/` - YouTube-specific extractors
- `test/` - Test files
- `devscripts/` - Development utilities

### Testing Your Changes

```bash
# Test specific extractor
& .\.venv\Scripts\python.exe -m yt_dlp --simulate [URL]

# Extract with verbose logging
& .\.venv\Scripts\python.exe -m yt_dlp -v [URL]

# List available formats
& .\.venv\Scripts\python.exe -m yt_dlp -F [URL]
```

### Creating a New Extractor

1. Create new file in `yt_dlp/extractor/your_site.py`
2. Add import to `yt_dlp/extractor/_extractors.py`
3. Follow the patterns in existing extractors
4. Test thoroughly

### Contributing Back

1. **Fork** the main repository on GitHub
2. **Add your fork** as a remote: `git remote add fork https://github.com/YOUR_USERNAME/yt-dlp.git`
3. **Push** to your fork: `git push fork my-contributions`
4. **Create pull request** on GitHub

## 🛠️ Development Tips

- Always test with multiple videos from the target site
- Use `--write-info-json` to debug extraction data
- Check existing extractors for similar sites as examples
- Follow the coding style (use ruff for formatting)
- Add tests for new extractors when possible

## 📚 Resources

- [YT-DLP Documentation](https://github.com/yt-dlp/yt-dlp)
- [Extractor Development Guide](https://github.com/yt-dlp/yt-dlp/blob/master/yt_dlp/extractor/common.py)
- [Contributing Guidelines](https://github.com/yt-dlp/yt-dlp/blob/master/CONTRIBUTING.md)