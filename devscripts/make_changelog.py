import enum
import itertools
import json
import logging
import re
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass
from functools import cache
from pathlib import Path

BASE_URL = 'https://github.com'
LOCATION_PATH = Path(__file__).parent

logger = logging.getLogger(__name__)


class CommitGroup(enum.Enum):
    PRIORITY = 'Important'
    CORE = 'Core'
    EXTRACTOR = 'Extractor'
    DOWNLOADER = 'Downloader'
    POSTPROCESSOR = 'Postprocessor'
    MISC = 'Misc.'

    @classmethod
    @cache
    def commit_lookup(cls):
        return {
            name: group
            for group, names in {
                cls.PRIORITY: {''},
                cls.CORE: {
                    'aes',
                    'cache',
                    'compat_utils',
                    'compat',
                    'cookies',
                    'dependencies',
                    'jsinterp',
                    'plugins',
                    'update',
                    'utils',
                },
                cls.MISC: {
                    'build',
                    'cleanup',
                    'devscripts',
                    'docs',
                },
                cls.EXTRACTOR: {'extractor'},
                cls.DOWNLOADER: {'downloader'},
                cls.POSTPROCESSOR: {'postprocessor'},
            }.items()
            for name in names
        }

    @classmethod
    def get(cls, value):
        result = cls.commit_lookup().get(value, cls.EXTRACTOR)
        logger.debug(f'Mapped {value!r} => {result.name}')
        return result


@dataclass
class Commit:
    hash: str | None
    short: str
    authors: list[str] | None

    def __str__(self):
        result = f'{self.short!r}'

        if self.hash:
            result += f' ({self.hash[:7]})'

        if self.authors:
            authors = ', '.join(self.authors)
            result += f' by {authors}'

        return result


@dataclass
class CommitInfo:
    details: str | None
    message: str
    issue: str | None
    commit: Commit

    def key(self):
        return (self.details or '', self.message)


class Changelog:
    MISC_RE = re.compile(r'(?:^|\b)(?:misc|format(?:ting)?|fixes)(?:\b|$)', re.IGNORECASE)

    def __init__(self, groups, repo):
        self._groups = groups
        self._repo = repo

    def __str__(self):
        return '\n'.join(self._format_groups(self._groups)).replace('\t', '    ')

    def _format_groups(self, groups):
        yield '## Changelog'

        for item in CommitGroup:
            group = groups[item]
            if group:
                yield self.format_module(item.value, group)

    def format_module(self, name: str, group):
        return f'### {name} changes\n' + '\n'.join(self._format_group(group))

    def _format_group(self, group):
        cleanup_misc = defaultdict(list)

        current = None
        indent = ''
        for item in sorted(group, key=CommitInfo.key):
            if item.details != current:
                if current == 'cleanup' and cleanup_misc:
                    yield from self.format_misc_items(cleanup_misc)

                yield f'- {item.details}'
                current = item.details
                indent = '\t'

            if current == 'cleanup' and self.MISC_RE.search(item.message):
                cleanup_misc[tuple(item.commit.authors or ())].append(item)
            else:
                yield f'{indent}- {self.format_single_change(item)}'

        if current == 'cleanup' and cleanup_misc:
            yield from self.format_misc_items(cleanup_misc)

    def format_misc_items(self, group):
        prefix = '\t- Miscellaneous'
        if len(group) == 1:
            yield f'{prefix}: {next(self._format_misc_items(group))}'
            return

        yield prefix
        for message in self._format_misc_items(group):
            yield f'\t\t- {message}'

    def _format_misc_items(self, group):
        for authors, infos in group.items():
            message = ', '.join(
                f'[{info.commit.hash or "unknown":.7}]({self.repo_url}/commit/{info.commit.hash})'
                for info in sorted(infos, key=lambda item: item.commit.hash or ''))
            yield f'{message} by {self._format_authors(authors)}'

    def format_single_change(self, info):
        message = (
            info.message if info.commit.hash is None else
            f'[{info.message}]({self.repo_url}/commit/{info.commit.hash})')
        if info.issue:
            issue = f'[#{info.issue}]({self.repo_url}/issues/{info.issue})'
            message = f'{message} ({issue})'

        if not info.commit.authors:
            return message

        return f'{message} by {self._format_authors(info.commit.authors)}'

    @staticmethod
    def _format_authors(authors):
        return ', '.join(f'[{author}]({BASE_URL}/{author})' for author in authors or ())

    @property
    def repo_url(self):
        return f'{BASE_URL}/{self._repo}'


class CommitRange:
    COMMAND = 'git'
    COMMIT_SEPARATOR = '-----'

    AUTHOR_INDICATOR_RE = re.compile(r'Authored by:? ', re.IGNORECASE)
    MESSAGE_RE = re.compile(r'''
        (?:\[
            (?P<prefix>[^\]\/:,]+)
            (?:/(?P<details>[^\]:,]+))?
            (?:[:,](?P<sub_details>[^\]]+))?
        \]\ )?
        (?P<message>.+?)
        (?:\ \(\#(?P<issue>\d+)\))?
        ''', re.VERBOSE)

    def __init__(self, start, end, default_author=None) -> None:
        self._start = start
        self._end = end
        self._commits = {commit.hash: commit for commit in self._get_commits_raw(default_author)}
        self._commits_added = []

    @classmethod
    def from_single(cls, commitish='HEAD', default_author=None):
        start_commitish = cls.get_prev_tag(commitish)
        end_commitish = cls.get_next_tag(commitish)
        if start_commitish == end_commitish:
            start_commitish = cls.get_prev_tag(f'{commitish}~')
        logger.info(f'Determined range from {commitish!r}: {start_commitish}..{end_commitish}')
        return cls(start_commitish, end_commitish, default_author)

    @classmethod
    def get_prev_tag(cls, commitish):
        command = [cls.COMMAND, 'describe', '--tags', '--abbrev=0', commitish]
        return subprocess.check_output(command, text=True).strip()

    @classmethod
    def get_next_tag(cls, commitish):
        result = subprocess.run(
            [cls.COMMAND, 'describe', '--contains', '--abbrev=0', commitish],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        if result.returncode:
            return 'HEAD'

        return result.stdout.partition('~')[0].strip()

    def __iter__(self):
        return iter(itertools.chain(self._commits.values(), self._commits_added))

    def __len__(self):
        return len(self._commits) + len(self._commits_added)

    def __contains__(self, commit):
        if isinstance(commit, Commit):
            if not commit.hash:
                return False
            commit = commit.hash

        return commit in self._commits

    def _is_ancestor(self, commitish):
        return bool(subprocess.call(
            [self.COMMAND, 'merge-base', '--is-ancestor', commitish, self._start]))

    def _get_commits_raw(self, default_author):
        result = subprocess.check_output([
            self.COMMAND, 'log', f'--format=%H%n%s%n%b%n{self.COMMIT_SEPARATOR}',
            f'{self._start}..{self._end}'], text=True)
        lines = iter(result.splitlines(False))
        for line in lines:
            commit_hash = line
            short = next(lines)
            skip = short.startswith('Release ') or short == '[version] update'

            authors = [default_author] if default_author else []
            for line in iter(lambda: next(lines), self.COMMIT_SEPARATOR):
                match = self.AUTHOR_INDICATOR_RE.match(line)
                if match:
                    authors = line[match.end():].split(', ')

            commit = Commit(commit_hash, short, authors)
            if skip:
                logger.debug(f'Skipped commit: {commit}')
            else:
                yield commit

    def apply_overrides(self, overrides):
        for override in overrides:
            when = override.get('when')
            if when and when not in self and when != self._start:
                logger.debug(f'Ignored {when!r}, not in commits {self._start!r}')
                continue

            override_hash = override.get('hash')
            if override['action'] == 'add':
                commit = Commit(override.get('hash'), override['short'], override.get('authors'))
                logger.info(f'ADD    {commit}')
                self._commits_added.append(commit)

            elif override['action'] == 'remove':
                if override_hash in self._commits:
                    logger.info(f'REMOVE {self._commits[override_hash]}')
                    del self._commits[override_hash]

            elif override['action'] == 'change':
                if override_hash not in self._commits:
                    continue
                commit = Commit(override_hash, override['short'], override['authors'])
                logger.info(f'CHANGE {self._commits[commit.hash]} -> {commit}')
                self._commits[commit.hash] = commit

        self._commits = {key: value for key, value in reversed(self._commits.items())}

    def groups(self):
        groups = defaultdict(list)
        for commit in self:
            match = self.MESSAGE_RE.fullmatch(commit.short)
            if not match:
                logger.error(f'Error parsing short commit message: {commit.short!r}')
                continue

            prefix, details, sub_details, message, issue = match.groups()
            group = None
            if prefix:
                if prefix == 'priority':
                    prefix, _, details = (details or '').partition('/')
                    logger.debug(f'Priority: {message!r}')
                    group = CommitGroup.PRIORITY

                if sub_details:
                    message = f'`{sub_details}`: {message}'

                elif not details:
                    details = prefix or None

                if details and not group:
                    details = details.lower()

            else:
                group = CommitGroup.CORE

            if not group:
                group = CommitGroup.get(prefix.lower())
            groups[group].append(CommitInfo(details, message, issue, commit))

        return groups


def get_new_contributors(contributors_path, commits):
    contributors = set()
    if contributors_path.exists():
        with contributors_path.open() as file:
            for line in filter(None, map(str.strip, file)):
                author, _, _ = line.partition(' (')
                authors = author.split('/')
                contributors.update(authors)

    new_contributors = {}
    for commit in commits:
        for author in commit.authors or ():
            if author in contributors:
                continue
            contributors.add(author)
            new_contributors[author] = None

    return list(reversed(new_contributors))


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(
        description='Create a changelog markdown from a git commit range')
    parser.add_argument(
        'commitish', default='HEAD', nargs='?',
        help='The commitish to create the range from (default: HEAD)')
    parser.add_argument(
        '-v', '--verbosity', action='count', default=0,
        help='increase verbosity each time specified')
    parser.add_argument(
        '-c', '--contributors', action='store_true',
        help='update CONTRIBUTORS file (default: false)')
    parser.add_argument(
        '--contributors-path', type=Path, default=LOCATION_PATH.parent / 'CONTRIBUTORS',
        help='path to the override CONTRIBUTORS file')
    parser.add_argument(
        '-o', '--override', action='store_true',
        help='use the override json in commit generation (default: false)')
    parser.add_argument(
        '--override-path', type=Path, default=LOCATION_PATH / 'changelog_override.json',
        help='path to the override json file')
    parser.add_argument(
        '--default-author', default='pukkandan',
        help='the author to use when no author indicator is specified')
    parser.add_argument(
        '--repo', default='yt-dlp/yt-dlp',
        help='the github repository to use for the operations')
    args = parser.parse_args()

    logging.basicConfig(
        datefmt='%Y-%m-%d %H-%M-%S', format='{asctime} | {levelname:<8} | {message}',
        level=logging.WARNING - 10 * args.verbosity, style='{', stream=sys.stderr)

    commits = CommitRange.from_single(args.commitish, args.default_author)

    if args.override:
        if args.override_path.exists():
            with args.override_path.open() as file:
                overrides = json.load(file)
            commits.apply_overrides(overrides)
        else:
            logger.warning(f'File {args.override.as_posix()} does not exist')

    logger.info(f'Loaded {len(commits)} commits')

    new_contributors = get_new_contributors(args.contributors_path, commits)
    if args.contributors:
        with args.contributors_path.open('a') as file:
            for contributor in new_contributors:
                file.write(f'{contributor}\n')
        logger.info(f'Added new contributors: {new_contributors}')
    else:
        logger.debug(f'New contributors: {new_contributors}')

    print(Changelog(commits.groups(), args.repo))
