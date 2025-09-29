# yt-dlp Tests

This directory contains tests for the yt-dlp codebase.

## Running Tests

### Using hatch (requires `pip install hatch`)

```bash
# Run tests for a specific test file
hatch run hatch-test:run test/test_utils.py

# Run a specific test class or method
hatch run hatch-test:run test/test_utils.py::TestUtil
hatch run hatch-test:run test/test_utils.py::TestUtil::test_url_basename

# Run with verbosity
hatch run hatch-test:run -- test/test_utils.py -v
```

### Using pytest directly

```bash
# Run a specific test file
python -m pytest test/test_utils.py

# Run a specific test class or method
python -m pytest test/test_utils.py::TestUtil
python -m pytest test/test_utils.py::TestUtil::test_url_basename

# Run with verbosity
python -m pytest -v test/test_utils.py
```

**Important:** Always run tests from the project root directory, not from a subdirectory.

## Code Coverage

For information on running tests with code coverage, see the documentation in `.coverage-reports/README.md`.