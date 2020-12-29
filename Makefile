all: youtube-dlc README.md CONTRIBUTING.md README.txt issuetemplates youtube-dlc.1 youtube-dlc.bash-completion youtube-dlc.zsh youtube-dlc.fish supportedsites
doc: README.md CONTRIBUTING.md issuetemplates supportedsites

clean:
	rm -rf youtube-dlc.1.temp.md youtube-dlc.1 youtube-dlc.bash-completion README.txt MANIFEST build/ dist/ .coverage cover/ youtube-dlc.tar.gz youtube-dlc.zsh youtube-dlc.fish youtube_dlc/extractor/lazy_extractors.py *.dump *.part* *.ytdl *.info.json *.mp4 *.m4a *.flv *.mp3 *.avi *.mkv *.webm *.3gp *.wav *.ape *.swf *.jpg *.png CONTRIBUTING.md.tmp youtube-dlc youtube-dlc.exe
	find . -name "*.pyc" -delete
	find . -name "*.class" -delete

PREFIX ?= /usr/local
BINDIR ?= $(PREFIX)/bin
MANDIR ?= $(PREFIX)/man
SHAREDIR ?= $(PREFIX)/share
PYTHON ?= /usr/bin/env python

# set SYSCONFDIR to /etc if PREFIX=/usr or PREFIX=/usr/local
SYSCONFDIR = $(shell if [ $(PREFIX) = /usr -o $(PREFIX) = /usr/local ]; then echo /etc; else echo $(PREFIX)/etc; fi)

# set markdown input format to "markdown-smart" for pandoc version 2 and to "markdown" for pandoc prior to version 2
MARKDOWN = $(shell if [ `pandoc -v | head -n1 | cut -d" " -f2 | head -c1` = "2" ]; then echo markdown-smart; else echo markdown; fi)

install: youtube-dlc youtube-dlc.1 youtube-dlc.bash-completion youtube-dlc.zsh youtube-dlc.fish
	install -d $(DESTDIR)$(BINDIR)
	install -m 755 youtube-dlc $(DESTDIR)$(BINDIR)
	install -d $(DESTDIR)$(MANDIR)/man1
	install -m 644 youtube-dlc.1 $(DESTDIR)$(MANDIR)/man1
	install -d $(DESTDIR)$(SYSCONFDIR)/bash_completion.d
	install -m 644 youtube-dlc.bash-completion $(DESTDIR)$(SYSCONFDIR)/bash_completion.d/youtube-dlc
	install -d $(DESTDIR)$(SHAREDIR)/zsh/site-functions
	install -m 644 youtube-dlc.zsh $(DESTDIR)$(SHAREDIR)/zsh/site-functions/_youtube-dlc
	install -d $(DESTDIR)$(SYSCONFDIR)/fish/completions
	install -m 644 youtube-dlc.fish $(DESTDIR)$(SYSCONFDIR)/fish/completions/youtube-dlc.fish

codetest:
	flake8 .

test:
	#nosetests --with-coverage --cover-package=youtube_dlc --cover-html --verbose --processes 4 test
	nosetests --verbose test
	$(MAKE) codetest

ot: offlinetest

# Keep this list in sync with devscripts/run_tests.sh
offlinetest: codetest
	$(PYTHON) -m nose --verbose test \
		--exclude test_age_restriction.py \
		--exclude test_download.py \
		--exclude test_iqiyi_sdk_interpreter.py \
		--exclude test_socks.py \
		--exclude test_subtitles.py \
		--exclude test_write_annotations.py \
		--exclude test_youtube_lists.py \
		--exclude test_youtube_signature.py \
		--exclude test_post_hooks.py

tar: youtube-dlc.tar.gz

.PHONY: all clean install test tar bash-completion pypi-files zsh-completion fish-completion ot offlinetest codetest supportedsites

pypi-files: youtube-dlc.bash-completion README.txt youtube-dlc.1 youtube-dlc.fish

youtube-dlc: youtube_dlc/*.py youtube_dlc/*/*.py
	mkdir -p zip
	for d in youtube_dlc youtube_dlc/downloader youtube_dlc/extractor youtube_dlc/postprocessor ; do \
	  mkdir -p zip/$$d ;\
	  cp -pPR $$d/*.py zip/$$d/ ;\
	done
	touch -t 200001010101 zip/youtube_dlc/*.py zip/youtube_dlc/*/*.py
	mv zip/youtube_dlc/__main__.py zip/
	cd zip ; zip -q ../youtube-dlc youtube_dlc/*.py youtube_dlc/*/*.py __main__.py
	rm -rf zip
	echo '#!$(PYTHON)' > youtube-dlc
	cat youtube-dlc.zip >> youtube-dlc
	rm youtube-dlc.zip
	chmod a+x youtube-dlc

README.md: youtube_dlc/*.py youtube_dlc/*/*.py
	COLUMNS=80 $(PYTHON) youtube_dlc/__main__.py --help | $(PYTHON) devscripts/make_readme.py

CONTRIBUTING.md: README.md
	$(PYTHON) devscripts/make_contributing.py README.md CONTRIBUTING.md

issuetemplates: devscripts/make_issue_template.py .github/ISSUE_TEMPLATE_tmpl/1_broken_site.md .github/ISSUE_TEMPLATE_tmpl/2_site_support_request.md .github/ISSUE_TEMPLATE_tmpl/3_site_feature_request.md .github/ISSUE_TEMPLATE_tmpl/4_bug_report.md .github/ISSUE_TEMPLATE_tmpl/5_feature_request.md youtube_dlc/version.py
	$(PYTHON) devscripts/make_issue_template.py .github/ISSUE_TEMPLATE_tmpl/1_broken_site.md .github/ISSUE_TEMPLATE/1_broken_site.md
	$(PYTHON) devscripts/make_issue_template.py .github/ISSUE_TEMPLATE_tmpl/2_site_support_request.md .github/ISSUE_TEMPLATE/2_site_support_request.md
	$(PYTHON) devscripts/make_issue_template.py .github/ISSUE_TEMPLATE_tmpl/3_site_feature_request.md .github/ISSUE_TEMPLATE/3_site_feature_request.md
	$(PYTHON) devscripts/make_issue_template.py .github/ISSUE_TEMPLATE_tmpl/4_bug_report.md .github/ISSUE_TEMPLATE/4_bug_report.md
	$(PYTHON) devscripts/make_issue_template.py .github/ISSUE_TEMPLATE_tmpl/5_feature_request.md .github/ISSUE_TEMPLATE/5_feature_request.md

supportedsites:
	$(PYTHON) devscripts/make_supportedsites.py docs/supportedsites.md

README.txt: README.md
	pandoc -f $(MARKDOWN) -t plain README.md -o README.txt

youtube-dlc.1: README.md
	$(PYTHON) devscripts/prepare_manpage.py youtube-dlc.1.temp.md
	pandoc -s -f $(MARKDOWN) -t man youtube-dlc.1.temp.md -o youtube-dlc.1
	rm -f youtube-dlc.1.temp.md

youtube-dlc.bash-completion: youtube_dlc/*.py youtube_dlc/*/*.py devscripts/bash-completion.in
	$(PYTHON) devscripts/bash-completion.py

bash-completion: youtube-dlc.bash-completion

youtube-dlc.zsh: youtube_dlc/*.py youtube_dlc/*/*.py devscripts/zsh-completion.in
	$(PYTHON) devscripts/zsh-completion.py

zsh-completion: youtube-dlc.zsh

youtube-dlc.fish: youtube_dlc/*.py youtube_dlc/*/*.py devscripts/fish-completion.in
	$(PYTHON) devscripts/fish-completion.py

fish-completion: youtube-dlc.fish

lazy-extractors: youtube_dlc/extractor/lazy_extractors.py

_EXTRACTOR_FILES = $(shell find youtube_dlc/extractor -iname '*.py' -and -not -iname 'lazy_extractors.py')
youtube_dlc/extractor/lazy_extractors.py: devscripts/make_lazy_extractors.py devscripts/lazy_load_template.py $(_EXTRACTOR_FILES)
	$(PYTHON) devscripts/make_lazy_extractors.py $@

youtube-dlc.tar.gz: youtube-dlc README.md README.txt youtube-dlc.1 youtube-dlc.bash-completion youtube-dlc.zsh youtube-dlc.fish ChangeLog AUTHORS
	@tar -czf youtube-dlc.tar.gz --transform "s|^|youtube-dlc/|" --owner 0 --group 0 \
		--exclude '*.DS_Store' \
		--exclude '*.kate-swp' \
		--exclude '*.pyc' \
		--exclude '*.pyo' \
		--exclude '*~' \
		--exclude '__pycache__' \
		--exclude '.git' \
		--exclude 'docs/_build' \
		-- \
		bin devscripts test youtube_dlc docs \
		ChangeLog AUTHORS LICENSE README.md README.txt \
		Makefile MANIFEST.in youtube-dlc.1 youtube-dlc.bash-completion \
		youtube-dlc.zsh youtube-dlc.fish setup.py setup.cfg \
		youtube-dlc
