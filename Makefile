all: yt-dlp doc man
doc: README.md CONTRIBUTING.md issuetemplates supportedsites
man: README.txt yt-dlp.1 yt-dlp.bash-completion yt-dlp.zsh yt-dlp.fish


clean:
	rm -rf yt-dlp.1.temp.md yt-dlp.1 yt-dlp.bash-completion README.txt MANIFEST build/ dist/ .coverage cover/ yt-dlp.tar.gz yt-dlp.zsh yt-dlp.fish yt_dlp/extractor/lazy_extractors.py *.dump *.part* *.ytdl *.info.json *.mp4 *.m4a *.flv *.mp3 *.avi *.mkv *.webm *.3gp *.wav *.ape *.swf *.jpg *.png *.spec *.frag *.frag.urls *.frag.aria2 CONTRIBUTING.md.tmp yt-dlp yt-dlp.exe
	find . -name "*.pyc" -delete
	find . -name "*.class" -delete

PREFIX ?= /usr/local
BINDIR ?= $(PREFIX)/bin
MANDIR ?= $(PREFIX)/man
SHAREDIR ?= $(PREFIX)/share
# make_supportedsites.py doesnot work correctly in python2
PYTHON ?= /usr/bin/env python3

# set SYSCONFDIR to /etc if PREFIX=/usr or PREFIX=/usr/local
SYSCONFDIR = $(shell if [ $(PREFIX) = /usr -o $(PREFIX) = /usr/local ]; then echo /etc; else echo $(PREFIX)/etc; fi)

# set markdown input format to "markdown-smart" for pandoc version 2 and to "markdown" for pandoc prior to version 2
MARKDOWN = $(shell if [ `pandoc -v | head -n1 | cut -d" " -f2 | head -c1` = "2" ]; then echo markdown-smart; else echo markdown; fi)

install: yt-dlp yt-dlp.1 yt-dlp.bash-completion yt-dlp.zsh yt-dlp.fish
	install -d $(DESTDIR)$(BINDIR)
	install -m 755 yt-dlp $(DESTDIR)$(BINDIR)
	install -d $(DESTDIR)$(MANDIR)/man1
	install -m 644 yt-dlp.1 $(DESTDIR)$(MANDIR)/man1
	install -d $(DESTDIR)$(SYSCONFDIR)/bash_completion.d
	install -m 644 yt-dlp.bash-completion $(DESTDIR)$(SYSCONFDIR)/bash_completion.d/yt-dlp
	install -d $(DESTDIR)$(SHAREDIR)/zsh/site-functions
	install -m 644 yt-dlp.zsh $(DESTDIR)$(SHAREDIR)/zsh/site-functions/_yt-dlp
	install -d $(DESTDIR)$(SYSCONFDIR)/fish/completions
	install -m 644 yt-dlp.fish $(DESTDIR)$(SYSCONFDIR)/fish/completions/yt-dlp.fish

codetest:
	flake8 .

test:
	#nosetests --with-coverage --cover-package=yt_dlp --cover-html --verbose --processes 4 test
	nosetests --verbose test
	$(MAKE) codetest

ot: offlinetest

# Keep this list in sync with devscripts/run_tests.sh
offlinetest: codetest
	$(PYTHON) -m nose --verbose test \
		--exclude test_age_restriction.py \
		--exclude test_download.py \
		--exclude test_iqiyi_sdk_interpreter.py \
		--exclude test_overwrites.py \
		--exclude test_socks.py \
		--exclude test_subtitles.py \
		--exclude test_write_annotations.py \
		--exclude test_youtube_lists.py \
		--exclude test_youtube_signature.py \
		--exclude test_post_hooks.py

tar: yt-dlp.tar.gz

.PHONY: all clean install test tar bash-completion pypi-files zsh-completion fish-completion ot offlinetest codetest supportedsites

pypi-files: yt-dlp.bash-completion README.txt yt-dlp.1 yt-dlp.fish

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

issuetemplates: devscripts/make_issue_template.py .github/ISSUE_TEMPLATE_tmpl/1_broken_site.md .github/ISSUE_TEMPLATE_tmpl/2_site_support_request.md .github/ISSUE_TEMPLATE_tmpl/3_site_feature_request.md .github/ISSUE_TEMPLATE_tmpl/4_bug_report.md .github/ISSUE_TEMPLATE_tmpl/5_feature_request.md yt_dlp/version.py
	$(PYTHON) devscripts/make_issue_template.py .github/ISSUE_TEMPLATE_tmpl/1_broken_site.md .github/ISSUE_TEMPLATE/1_broken_site.md
	$(PYTHON) devscripts/make_issue_template.py .github/ISSUE_TEMPLATE_tmpl/2_site_support_request.md .github/ISSUE_TEMPLATE/2_site_support_request.md
	$(PYTHON) devscripts/make_issue_template.py .github/ISSUE_TEMPLATE_tmpl/3_site_feature_request.md .github/ISSUE_TEMPLATE/3_site_feature_request.md
	$(PYTHON) devscripts/make_issue_template.py .github/ISSUE_TEMPLATE_tmpl/4_bug_report.md .github/ISSUE_TEMPLATE/4_bug_report.md
	$(PYTHON) devscripts/make_issue_template.py .github/ISSUE_TEMPLATE_tmpl/5_feature_request.md .github/ISSUE_TEMPLATE/5_feature_request.md

supportedsites:
	$(PYTHON) devscripts/make_supportedsites.py docs/supportedsites.md

README.txt: README.md
	pandoc -f $(MARKDOWN) -t plain README.md -o README.txt

yt-dlp.1: README.md
	$(PYTHON) devscripts/prepare_manpage.py yt-dlp.1.temp.md
	pandoc -s -f $(MARKDOWN) -t man yt-dlp.1.temp.md -o yt-dlp.1
	rm -f yt-dlp.1.temp.md

yt-dlp.bash-completion: yt_dlp/*.py yt_dlp/*/*.py devscripts/bash-completion.in
	$(PYTHON) devscripts/bash-completion.py

bash-completion: yt-dlp.bash-completion

yt-dlp.zsh: yt_dlp/*.py yt_dlp/*/*.py devscripts/zsh-completion.in
	$(PYTHON) devscripts/zsh-completion.py

zsh-completion: yt-dlp.zsh

yt-dlp.fish: yt_dlp/*.py yt_dlp/*/*.py devscripts/fish-completion.in
	$(PYTHON) devscripts/fish-completion.py

fish-completion: yt-dlp.fish

lazy-extractors: yt_dlp/extractor/lazy_extractors.py

_EXTRACTOR_FILES = $(shell find yt_dlp/extractor -iname '*.py' -and -not -iname 'lazy_extractors.py')
yt_dlp/extractor/lazy_extractors.py: devscripts/make_lazy_extractors.py devscripts/lazy_load_template.py $(_EXTRACTOR_FILES)
	$(PYTHON) devscripts/make_lazy_extractors.py $@

yt-dlp.tar.gz: yt-dlp README.md README.txt yt-dlp.1 yt-dlp.bash-completion yt-dlp.zsh yt-dlp.fish ChangeLog AUTHORS
	@tar -czf yt-dlp.tar.gz --transform "s|^|yt-dlp/|" --owner 0 --group 0 \
		--exclude '*.DS_Store' \
		--exclude '*.kate-swp' \
		--exclude '*.pyc' \
		--exclude '*.pyo' \
		--exclude '*~' \
		--exclude '__pycache__' \
		--exclude '.git' \
		--exclude 'docs/_build' \
		-- \
		bin devscripts test yt_dlp docs \
		ChangeLog AUTHORS LICENSE README.md README.txt \
		Makefile MANIFEST.in yt-dlp.1 yt-dlp.bash-completion \
		yt-dlp.zsh yt-dlp.fish setup.py setup.cfg \
		yt-dlp
