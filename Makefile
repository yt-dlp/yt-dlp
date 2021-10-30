all: lazy-extractors yt-dlp doc pypi-files
clean: clean-test clean-dist clean-cache
completions: completion-bash completion-fish completion-zsh
doc: README.md CONTRIBUTING.md issuetemplates supportedsites
ot: offlinetest
tar: yt-dlp.tar.gz

# Keep this list in sync with MANIFEST.in
# intended use: when building a source distribution,
# make pypi-files && python setup.py sdist
pypi-files: AUTHORS Changelog.md LICENSE README.md README.txt supportedsites completions yt-dlp.1 devscripts/* test/*

.PHONY: all clean install test tar pypi-files completions ot offlinetest codetest supportedsites

clean-test:
	rm -rf *.3gp *.annotations.xml *.ape *.avi *.description *.dump *.flac *.flv *.frag *.frag.aria2 *.frag.urls \
	*.info.json *.jpeg *.jpg *.live_chat.json *.m4a *.m4v *.mkv *.mp3 *.mp4 *.ogg *.opus *.part* *.png *.sbv *.srt \
	*.swf *.swp *.ttml *.vtt *.wav *.webm *.webp *.ytdl test/testdata/player-*.js
clean-dist:
	rm -rf yt-dlp.1.temp.md yt-dlp.1 README.txt MANIFEST build/ dist/ .coverage cover/ yt-dlp.tar.gz completions/ yt_dlp/extractor/lazy_extractors.py *.spec CONTRIBUTING.md.tmp yt-dlp yt-dlp.exe yt_dlp.egg-info/ AUTHORS .mailmap
clean-cache:
	find . -name "*.pyc" -o -name "*.class" -delete

completion-bash: completions/bash/yt-dlp
completion-fish: completions/fish/yt-dlp.fish
completion-zsh: completions/zsh/_yt-dlp
lazy-extractors: yt_dlp/extractor/lazy_extractors.py

PREFIX ?= /usr/local
DESTDIR ?= .
BINDIR ?= $(PREFIX)/bin
MANDIR ?= $(PREFIX)/man
SHAREDIR ?= $(PREFIX)/share
# make_supportedsites.py doesnot work correctly in python2
PYTHON ?= /usr/bin/env python3

# set SYSCONFDIR to /etc if PREFIX=/usr or PREFIX=/usr/local
SYSCONFDIR = $(shell if [ $(PREFIX) = /usr -o $(PREFIX) = /usr/local ]; then echo /etc; else echo $(PREFIX)/etc; fi)

# set markdown input format to "markdown-smart" for pandoc version 2 and to "markdown" for pandoc prior to version 2
MARKDOWN = $(shell if [ `pandoc -v | head -n1 | cut -d" " -f2 | head -c1` = "2" ]; then echo markdown-smart; else echo markdown; fi)

install: lazy-extractors yt-dlp yt-dlp.1 completions
	install -Dm755 yt-dlp $(DESTDIR)$(BINDIR)/yt-dlp
	install -Dm644 yt-dlp.1 $(DESTDIR)$(MANDIR)/man1/yt-dlp.1
	install -Dm644 completions/bash/yt-dlp $(DESTDIR)$(SHAREDIR)/bash-completion/completions/yt-dlp
	install -Dm644 completions/zsh/_yt-dlp $(DESTDIR)$(SHAREDIR)/zsh/site-functions/_yt-dlp
	install -Dm644 completions/fish/yt-dlp.fish $(DESTDIR)$(SHAREDIR)/fish/vendor_completions.d/yt-dlp.fish

codetest:
	flake8 .

test:
	$(PYTHON) -m pytest
	$(MAKE) codetest

offlinetest: codetest
	$(PYTHON) -m pytest -k "not download"

yt-dlp: yt_dlp/*.py yt_dlp/*/*.py
	mkdir -p zip
	for d in yt_dlp yt_dlp/downloader yt_dlp/extractor yt_dlp/postprocessor ; do \
	  mkdir -p zip/$$d ;\
	  cp -pPR $$d/*.py zip/$$d/ ;\
	done
	touch -t 200001010101 zip/yt_dlp/*.py zip/yt_dlp/*/*.py
	mv zip/yt_dlp/__main__.py zip/
	cd zip ; zip -q ../yt-dlp yt_dlp/*.py yt_dlp/*/*.py __main__.py
	rm -rf zip
	echo '#!$(PYTHON)' > yt-dlp
	cat yt-dlp.zip >> yt-dlp
	rm yt-dlp.zip
	chmod a+x yt-dlp

README.md: yt_dlp/*.py yt_dlp/*/*.py
	COLUMNS=80 $(PYTHON) yt_dlp/__main__.py --help | $(PYTHON) devscripts/make_readme.py

CONTRIBUTING.md: README.md
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

yt-dlp.1: README.md
	$(PYTHON) devscripts/prepare_manpage.py yt-dlp.1.temp.md
	pandoc -s -f $(MARKDOWN) -t man yt-dlp.1.temp.md -o yt-dlp.1
	rm -f yt-dlp.1.temp.md

completions/bash/yt-dlp: yt_dlp/*.py yt_dlp/*/*.py devscripts/bash-completion.in
	mkdir -p completions/bash
	$(PYTHON) devscripts/bash-completion.py

completions/zsh/_yt-dlp: yt_dlp/*.py yt_dlp/*/*.py devscripts/zsh-completion.in
	mkdir -p completions/zsh
	$(PYTHON) devscripts/zsh-completion.py

completions/fish/yt-dlp.fish: yt_dlp/*.py yt_dlp/*/*.py devscripts/fish-completion.in
	mkdir -p completions/fish
	$(PYTHON) devscripts/fish-completion.py

_EXTRACTOR_FILES = $(shell find yt_dlp/extractor -iname '*.py' -and -not -iname 'lazy_extractors.py')
yt_dlp/extractor/lazy_extractors.py: devscripts/make_lazy_extractors.py devscripts/lazy_load_template.py $(_EXTRACTOR_FILES)
	$(PYTHON) devscripts/make_lazy_extractors.py $@

yt-dlp.tar.gz: all
	@tar -czf $(DESTDIR)/yt-dlp.tar.gz --transform "s|^|yt-dlp/|" --owner 0 --group 0 \
		--exclude '*.DS_Store' \
		--exclude '*.kate-swp' \
		--exclude '*.pyc' \
		--exclude '*.pyo' \
		--exclude '*~' \
		--exclude '__pycache__' \
		--exclude '.git' \
		-- \
		README.md supportedsites.md Changelog.md LICENSE \
		CONTRIBUTING.md Collaborators.md CONTRIBUTORS AUTHORS \
		Makefile MANIFEST.in yt-dlp.1 README.txt completions \
		setup.py setup.cfg yt-dlp yt_dlp requirements.txt \
		devscripts test tox.ini pytest.ini

AUTHORS: .mailmap
	git shortlog -s -n | cut -f2 | sort > AUTHORS

.mailmap:
	git shortlog -s -e -n | awk '!(out[$$NF]++) { $$1="";sub(/^[ \t]+/,""); print}' > .mailmap
