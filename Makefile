all: lazy-extractors yt-dlp doc pypi-files
all-extra: lazy-extractors yt-dlp-extra doc pypi-files
clean: clean-test clean-dist
clean-all: clean clean-cache
completions: completion-bash completion-fish completion-zsh
doc: README.md CONTRIBUTING.md CONTRIBUTORS issuetemplates supportedsites
ot: offlinetest
tar: yt-dlp.tar.gz

# Keep this list in sync with pyproject.toml includes/artifacts
# intended use: when building a source distribution,
# make pypi-files && python3 -m build -sn .
pypi-files: AUTHORS Changelog.md LICENSE README.md README.txt supportedsites \
            completions yt-dlp.1 pyproject.toml devscripts/* test/*

.PHONY: all clean clean-all clean-test clean-dist clean-cache \
        completions completion-bash completion-fish completion-zsh \
        doc issuetemplates supportedsites ot offlinetest codetest test \
        tar pypi-files lazy-extractors install uninstall \
        all-extra yt-dlp-extra current-ejs-version

.IGNORE: current-ejs-version
.SILENT: current-ejs-version

clean-test:
	rm -rf tmp/ *.annotations.xml *.aria2 *.description *.dump *.frag \
	*.frag.aria2 *.frag.urls *.info.json *.live_chat.json *.meta *.part* *.tmp *.temp *.unknown_video *.ytdl \
	*.3gp *.ape *.ass *.avi *.desktop *.f4v *.flac *.flv *.gif *.jpeg *.jpg *.lrc *.m4a *.m4v *.mhtml *.mkv *.mov *.mp3 *.mp4 \
	*.mpg *.mpga *.oga *.ogg *.opus *.png *.sbv *.srt *.ssa *.swf *.tt *.ttml *.url *.vtt *.wav *.webloc *.webm *.webp \
	test/testdata/sigs/player-*.js test/testdata/thumbnails/empty.webp "test/testdata/thumbnails/foo %d bar/foo_%d."*
clean-dist:
	rm -rf yt-dlp.1.temp.md yt-dlp.1 README.txt MANIFEST build/ dist/ .coverage cover/ yt-dlp.tar.gz completions/ \
	yt_dlp/extractor/lazy_extractors.py *.spec CONTRIBUTING.md.tmp yt-dlp yt-dlp.exe yt_dlp.egg-info/ AUTHORS \
	yt-dlp.zip .ejs-* yt_dlp_ejs/
clean-cache:
	find . \( \
		-type d -name ".*_cache" -o -type d -name __pycache__ -o -name "*.pyc" -o -name "*.class" \
	\) -prune -exec rm -rf {} \;

completion-bash: completions/bash/yt-dlp
completion-fish: completions/fish/yt-dlp.fish
completion-zsh: completions/zsh/_yt-dlp
lazy-extractors: yt_dlp/extractor/lazy_extractors.py

PREFIX ?= /usr/local
BINDIR ?= $(PREFIX)/bin
MANDIR ?= $(PREFIX)/man
SHAREDIR ?= $(PREFIX)/share
PYTHON ?= /usr/bin/env python3
GNUTAR ?= tar

# set markdown input format to "markdown-smart" for pandoc version 2+ and to "markdown" for pandoc prior to version 2
PANDOC_VERSION_CMD = pandoc -v 2>/dev/null | head -n1 | cut -d' ' -f2 | head -c1
PANDOC_VERSION != $(PANDOC_VERSION_CMD)
PANDOC_VERSION ?= $(shell $(PANDOC_VERSION_CMD))
MARKDOWN_CMD = if [ "$(PANDOC_VERSION)" = "1" -o "$(PANDOC_VERSION)" = "0" ]; then echo markdown; else echo markdown-smart; fi
MARKDOWN != $(MARKDOWN_CMD)
MARKDOWN ?= $(shell $(MARKDOWN_CMD))

install: lazy-extractors yt-dlp yt-dlp.1 completions
	mkdir -p $(DESTDIR)$(BINDIR)
	install -m755 yt-dlp $(DESTDIR)$(BINDIR)/yt-dlp
	mkdir -p $(DESTDIR)$(MANDIR)/man1
	install -m644 yt-dlp.1 $(DESTDIR)$(MANDIR)/man1/yt-dlp.1
	mkdir -p $(DESTDIR)$(SHAREDIR)/bash-completion/completions
	install -m644 completions/bash/yt-dlp $(DESTDIR)$(SHAREDIR)/bash-completion/completions/yt-dlp
	mkdir -p $(DESTDIR)$(SHAREDIR)/zsh/site-functions
	install -m644 completions/zsh/_yt-dlp $(DESTDIR)$(SHAREDIR)/zsh/site-functions/_yt-dlp
	mkdir -p $(DESTDIR)$(SHAREDIR)/fish/vendor_completions.d
	install -m644 completions/fish/yt-dlp.fish $(DESTDIR)$(SHAREDIR)/fish/vendor_completions.d/yt-dlp.fish

uninstall:
	rm -f $(DESTDIR)$(BINDIR)/yt-dlp
	rm -f $(DESTDIR)$(MANDIR)/man1/yt-dlp.1
	rm -f $(DESTDIR)$(SHAREDIR)/bash-completion/completions/yt-dlp
	rm -f $(DESTDIR)$(SHAREDIR)/zsh/site-functions/_yt-dlp
	rm -f $(DESTDIR)$(SHAREDIR)/fish/vendor_completions.d/yt-dlp.fish

codetest:
	ruff check .
	autopep8 --diff .

test:
	$(PYTHON) -m pytest -Werror
	$(MAKE) codetest

offlinetest: codetest
	$(PYTHON) -m pytest -Werror -m "not download"

PY_CODE_FOLDERS_CMD = find yt_dlp -type f -name '__init__.py' | sed 's|/__init__\.py||' | grep -v '/__' | sort
PY_CODE_FOLDERS != $(PY_CODE_FOLDERS_CMD)
PY_CODE_FOLDERS ?= $(shell $(PY_CODE_FOLDERS_CMD))

PY_CODE_FILES_CMD = for f in $(PY_CODE_FOLDERS) ; do echo "$$f" | sed 's|$$|/*.py|' ; done
PY_CODE_FILES != $(PY_CODE_FILES_CMD)
PY_CODE_FILES ?= $(shell $(PY_CODE_FILES_CMD))

JS_CODE_FOLDERS_CMD = find yt_dlp -type f -name '*.js' | sed 's|/[^/]\{1,\}\.js$$||' | uniq
JS_CODE_FOLDERS != $(JS_CODE_FOLDERS_CMD)
JS_CODE_FOLDERS ?= $(shell $(JS_CODE_FOLDERS_CMD))

JS_CODE_FILES_CMD = for f in $(JS_CODE_FOLDERS) ; do echo "$$f" | sed 's|$$|/*.js|' ; done
JS_CODE_FILES != $(JS_CODE_FILES_CMD)
JS_CODE_FILES ?= $(shell $(JS_CODE_FILES_CMD))

yt-dlp.zip: $(PY_CODE_FILES) $(JS_CODE_FILES)
	mkdir -p zip
	for d in $(PY_CODE_FOLDERS) ; do \
	  mkdir -p zip/$$d ;\
	  cp -pPR $$d/*.py zip/$$d/ ;\
	done
	for d in $(JS_CODE_FOLDERS) ; do \
	  mkdir -p zip/$$d ;\
	  cp -pPR $$d/*.js zip/$$d/ ;\
	done
	(cd zip && touch -t 200001010101 $(PY_CODE_FILES) $(JS_CODE_FILES))
	rm -f zip/yt_dlp/__main__.py
	(cd zip && zip -q ../yt-dlp.zip $(PY_CODE_FILES) $(JS_CODE_FILES))
	rm -rf zip

yt-dlp: yt-dlp.zip
	mkdir -p zip
	cp -pP yt_dlp/__main__.py zip/
	touch -t 200001010101 zip/__main__.py
	(cd zip && zip -q ../yt-dlp.zip __main__.py)
	echo '#!$(PYTHON)' > yt-dlp
	cat yt-dlp.zip >> yt-dlp
	rm yt-dlp.zip
	chmod a+x yt-dlp
	rm -rf zip

README.md: $(PY_CODE_FILES) devscripts/make_readme.py
	COLUMNS=80 $(PYTHON) yt_dlp/__main__.py --ignore-config --help | $(PYTHON) devscripts/make_readme.py

CONTRIBUTING.md: README.md devscripts/make_contributing.py
	$(PYTHON) devscripts/make_contributing.py README.md CONTRIBUTING.md

issuetemplates: devscripts/make_issue_template.py .github/ISSUE_TEMPLATE_tmpl/1_broken_site.yml .github/ISSUE_TEMPLATE_tmpl/2_site_support_request.yml .github/ISSUE_TEMPLATE_tmpl/3_site_feature_request.yml .github/ISSUE_TEMPLATE_tmpl/4_bug_report.yml .github/ISSUE_TEMPLATE_tmpl/5_feature_request.yml yt_dlp/version.py
	$(PYTHON) devscripts/make_issue_template.py .github/ISSUE_TEMPLATE_tmpl/1_broken_site.yml .github/ISSUE_TEMPLATE/1_broken_site.yml
	$(PYTHON) devscripts/make_issue_template.py .github/ISSUE_TEMPLATE_tmpl/2_site_support_request.yml .github/ISSUE_TEMPLATE/2_site_support_request.yml
	$(PYTHON) devscripts/make_issue_template.py .github/ISSUE_TEMPLATE_tmpl/3_site_feature_request.yml .github/ISSUE_TEMPLATE/3_site_feature_request.yml
	$(PYTHON) devscripts/make_issue_template.py .github/ISSUE_TEMPLATE_tmpl/4_bug_report.yml .github/ISSUE_TEMPLATE/4_bug_report.yml
	$(PYTHON) devscripts/make_issue_template.py .github/ISSUE_TEMPLATE_tmpl/5_feature_request.yml .github/ISSUE_TEMPLATE/5_feature_request.yml
	$(PYTHON) devscripts/make_issue_template.py .github/ISSUE_TEMPLATE_tmpl/6_question.yml .github/ISSUE_TEMPLATE/6_question.yml

supportedsites:
	$(PYTHON) devscripts/make_supportedsites.py supportedsites.md

README.txt: README.md
	pandoc -f $(MARKDOWN) -t plain README.md -o README.txt

yt-dlp.1: README.md devscripts/prepare_manpage.py
	$(PYTHON) devscripts/prepare_manpage.py yt-dlp.1.temp.md
	pandoc -s -f $(MARKDOWN) -t man yt-dlp.1.temp.md -o yt-dlp.1
	rm -f yt-dlp.1.temp.md

completions/bash/yt-dlp: $(PY_CODE_FILES) devscripts/bash-completion.in
	mkdir -p completions/bash
	$(PYTHON) devscripts/bash-completion.py

completions/zsh/_yt-dlp: $(PY_CODE_FILES) devscripts/zsh-completion.in
	mkdir -p completions/zsh
	$(PYTHON) devscripts/zsh-completion.py

completions/fish/yt-dlp.fish: $(PY_CODE_FILES) devscripts/fish-completion.in
	mkdir -p completions/fish
	$(PYTHON) devscripts/fish-completion.py

_EXTRACTOR_FILES_CMD = find yt_dlp/extractor -name '*.py' -and -not -name 'lazy_extractors.py'
_EXTRACTOR_FILES != $(_EXTRACTOR_FILES_CMD)
_EXTRACTOR_FILES ?= $(shell $(_EXTRACTOR_FILES_CMD))
yt_dlp/extractor/lazy_extractors.py: devscripts/make_lazy_extractors.py devscripts/lazy_load_template.py $(_EXTRACTOR_FILES)
	$(PYTHON) devscripts/make_lazy_extractors.py $@

yt-dlp.tar.gz: all
	@$(GNUTAR) -czf yt-dlp.tar.gz --transform "s|^|yt-dlp/|" --owner 0 --group 0 \
		--exclude '*.DS_Store' \
		--exclude '*.kate-swp' \
		--exclude '*.pyc' \
		--exclude '*.pyo' \
		--exclude '*~' \
		--exclude '__pycache__' \
		--exclude '.*_cache' \
		--exclude '.git' \
		-- \
		README.md supportedsites.md Changelog.md LICENSE \
		CONTRIBUTING.md Maintainers.md CONTRIBUTORS AUTHORS \
		Makefile yt-dlp.1 README.txt completions .gitignore \
		yt-dlp yt_dlp pyproject.toml devscripts test

AUTHORS: Changelog.md
	@if [ -d '.git' ] && command -v git > /dev/null ; then \
	  echo 'Generating $@ from git commit history' ; \
	  git shortlog -s -n HEAD | cut -f2 | sort > $@ ; \
	fi

CONTRIBUTORS: Changelog.md
	@if [ -d '.git' ] && command -v git > /dev/null ; then \
	  echo 'Updating $@ from git commit history' ; \
	  $(PYTHON) devscripts/make_changelog.py -v -c > /dev/null ; \
	fi

# The following EJS_-prefixed variables are auto-generated by devscripts/update_ejs.py
# DO NOT EDIT!
EJS_VERSION = 0.3.2
EJS_WHEEL_NAME = yt_dlp_ejs-0.3.2-py3-none-any.whl
EJS_WHEEL_HASH = sha256:f2dc6b3d1b909af1f13e021621b0af048056fca5fb07c4db6aa9bbb37a4f66a9
EJS_PY_FOLDERS = yt_dlp_ejs yt_dlp_ejs/yt yt_dlp_ejs/yt/solver
EJS_PY_FILES = yt_dlp_ejs/__init__.py yt_dlp_ejs/_version.py yt_dlp_ejs/yt/__init__.py yt_dlp_ejs/yt/solver/__init__.py
EJS_JS_FOLDERS = yt_dlp_ejs/yt/solver
EJS_JS_FILES = yt_dlp_ejs/yt/solver/core.min.js yt_dlp_ejs/yt/solver/lib.min.js

yt-dlp-extra: current-ejs-version .ejs-$(EJS_VERSION) $(EJS_PY_FILES) $(EJS_JS_FILES) yt-dlp.zip
	mkdir -p zip
	for d in $(EJS_PY_FOLDERS) ; do \
	  mkdir -p zip/$$d ;\
	  cp -pPR $$d/*.py zip/$$d/ ;\
	done
	for d in $(EJS_JS_FOLDERS) ; do \
	  mkdir -p zip/$$d ;\
	  cp -pPR $$d/*.js zip/$$d/ ;\
	done
	(cd zip && touch -t 200001010101 $(EJS_PY_FILES) $(EJS_JS_FILES))
	(cd zip && zip -q ../yt-dlp.zip $(EJS_PY_FILES) $(EJS_JS_FILES))
	cp -pP yt_dlp/__main__.py zip/
	touch -t 200001010101 zip/__main__.py
	(cd zip && zip -q ../yt-dlp.zip __main__.py)
	echo '#!$(PYTHON)' > yt-dlp
	cat yt-dlp.zip >> yt-dlp
	rm yt-dlp.zip
	chmod a+x yt-dlp
	rm -rf zip

.ejs-$(EJS_VERSION):
	@echo Downloading yt-dlp-ejs
	@echo "yt-dlp-ejs==$(EJS_VERSION) --hash $(EJS_WHEEL_HASH)" > .ejs-requirements.txt
	$(PYTHON) -m pip download -d ./build --no-deps --require-hashes -r .ejs-requirements.txt
	unzip -o build/$(EJS_WHEEL_NAME) "yt_dlp_ejs/*"
	@touch .ejs-$(EJS_VERSION)

current-ejs-version:
	rm -rf .ejs-*
	touch .ejs-$$($(PYTHON) -c 'import sys; sys.path = [""]; from yt_dlp_ejs import version; print(version)' 2>/dev/null)
