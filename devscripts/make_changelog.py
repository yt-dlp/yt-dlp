from __future__ import annotations

# Allow direct execution
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import enum
import itertools
import json
import logging
import re
from collections import defaultdict
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from devscripts.utils import read_file, run_process, write_file

BASE_URL = 'https://github.com'
LOCATION_PATH = Path(__file__).parent
HASH_LENGTH = 7

logger = logging.getLogger(__name__)


class CommitGroup(enum.Enum):
    PRIORITY = 'Important'
    CORE = 'Core'
    EXTRACTOR = 'Extractor'
    DOWNLOADER = 'Downloader'
    POSTPROCESSOR = 'Postprocessor'
    NETWORKING = 'Networking'
    MISC = 'Misc.'

    @classmethod
    @lru_cache
    def subgroup_lookup(cls):
        return {
            name: group
            for group, names in {
                cls.MISC: {
                    'build',
                    'ci',
                    'cleanup',
                    'devscripts',
                    'docs',
                    'test',
                },
                cls.NETWORKING: {
                    'rh',
                },
            }.items()
            for name in names
        }

    @classmethod
    @lru_cache
    def group_lookup(cls):
        result = {
            'fd': cls.DOWNLOADER,
            'ie': cls.EXTRACTOR,
            'pp': cls.POSTPROCESSOR,
            'upstream': cls.CORE,
        }
        result.update({item.name.lower(): item for item in iter(cls)})
        return result

    @classmethod
    def get(cls, value: str) -> tuple[CommitGroup | None, str | None]:
        group, _, subgroup = (group.strip().lower() for group in value.partition('/'))

        result = cls.group_lookup().get(group)
        if not result:
            if subgroup:
                return None, value
            subgroup = group
            result = cls.subgroup_lookup().get(subgroup)

        return result, subgroup or None


@dataclass
class Commit:
    hash: str | None
    short: str
    authors: list[str]

    def __str__(self):
        result = f'{self.short!r}'

        if self.hash:
            result += f' ({self.hash[:HASH_LENGTH]})'

        if self.authors:
            authors = ', '.join(self.authors)
            result += f' by {authors}'

        return result


@dataclass
class CommitInfo:
    details: str | None
    sub_details: tuple[str, ...]
    message: str
    issues: list[str]
    commit: Commit
    fixes: list[Commit]

    def key(self):
        return ((self.details or '').lower(), self.sub_details, self.message)


def unique(items):
    return sorted({item.strip().lower(): item for item in items if item}.values())


class Changelog:
    MISC_RE = re.compile(r'(?:^|\b)(?:lint(?:ing)?|misc|format(?:ting)?|fixes)(?:\b|$)', re.IGNORECASE)
    ALWAYS_SHOWN = (CommitGroup.PRIORITY,)

    def __init__(self, groups, repo, collapsible=False):
        self._groups = groups
        self._repo = repo
        self._collapsible = collapsible

    def __str__(self):
        return '\n'.join(self._format_groups(self._groups)).replace('\t', '    ')

    def _format_groups(self, groups):
        first = True
        for item in CommitGroup:
            if self._collapsible and item not in self.ALWAYS_SHOWN and first:
                first = False
                yield '\n<details><summary><h3>Changelog</h3></summary>\n'

            group = groups[item]
            if group:
                yield self.format_module(item.value, group)

        if self._collapsible:
            yield '\n</details>'

    def format_module(self, name, group):
        result = f'\n#### {name} changes\n' if name else '\n'
        return result + '\n'.join(self._format_group(group))

    def _format_group(self, group):
        sorted_group = sorted(group, key=CommitInfo.key)
        detail_groups = itertools.groupby(sorted_group, lambda item: (item.details or '').lower())
        for _, items in detail_groups:
            items = list(items)
            details = items[0].details

            if details == 'cleanup':
                items = self._prepare_cleanup_misc_items(items)

            prefix = '-'
            if details:
                if len(items) == 1:
                    prefix = f'- **{details}**:'
                else:
                    yield f'- **{details}**'
                    prefix = '\t-'

            sub_detail_groups = itertools.groupby(items, lambda item: tuple(map(str.lower, item.sub_details)))
            for sub_details, entries in sub_detail_groups:
                if not sub_details:
                    for entry in entries:
                        yield f'{prefix} {self.format_single_change(entry)}'
                    continue

                entries = list(entries)
                sub_prefix = f'{prefix} {", ".join(entries[0].sub_details)}'
                if len(entries) == 1:
                    yield f'{sub_prefix}: {self.format_single_change(entries[0])}'
                    continue

                yield sub_prefix
                for entry in entries:
                    yield f'\t{prefix} {self.format_single_change(entry)}'

    def _prepare_cleanup_misc_items(self, items):
        cleanup_misc_items = defaultdict(list)
        sorted_items = []
        for item in items:
            if self.MISC_RE.search(item.message):
                cleanup_misc_items[tuple(item.commit.authors)].append(item)
            else:
                sorted_items.append(item)

        for commit_infos in cleanup_misc_items.values():
            sorted_items.append(CommitInfo(
                'cleanup', ('Miscellaneous',), ', '.join(
                    self._format_message_link(None, info.commit.hash)
                    for info in sorted(commit_infos, key=lambda item: item.commit.hash or '')),
                [], Commit(None, '', commit_infos[0].commit.authors), []))

        return sorted_items

    def format_single_change(self, info: CommitInfo):
        message, sep, rest = info.message.partition('\n')
        if '[' not in message:
            # If the message doesn't already contain markdown links, try to add a link to the commit
            message = self._format_message_link(message, info.commit.hash)

        if info.issues:
            message = f'{message} ({self._format_issues(info.issues)})'

        if info.commit.authors:
            message = f'{message} by {self._format_authors(info.commit.authors)}'

        if info.fixes:
            fix_message = ', '.join(f'{self._format_message_link(None, fix.hash)}' for fix in info.fixes)

            authors = sorted({author for fix in info.fixes for author in fix.authors}, key=str.casefold)
            if authors != info.commit.authors:
                fix_message = f'{fix_message} by {self._format_authors(authors)}'

            message = f'{message} (With fixes in {fix_message})'

        return message if not sep else f'{message}{sep}{rest}'

    def _format_message_link(self, message, hash):
        assert message or hash, 'Improperly defined commit message or override'
        message = message if message else hash[:HASH_LENGTH]
        return f'[{message}]({self.repo_url}/commit/{hash})' if hash else message

    def _format_issues(self, issues):
        return ', '.join(f'[#{issue}]({self.repo_url}/issues/{issue})' for issue in issues)

    @staticmethod
    def _format_authors(authors):
        return ', '.join(f'[{author}]({BASE_URL}/{author})' for author in authors)

    @property
    def repo_url(self):
        return f'{BASE_URL}/{self._repo}'


class CommitRange:
    COMMAND = 'git'
    COMMIT_SEPARATOR = '-----'

    AUTHOR_INDICATOR_RE = re.compile(r'Authored by:? ', re.IGNORECASE)
    MESSAGE_RE = re.compile(r'''
        (?:\[(?P<prefix>[^\]]+)\]\ )?
        (?:(?P<sub_details>`?[\w.-]+`?): )?
        (?P<message>.+?)
        (?:\ \((?P<issues>\#\d+(?:,\ \#\d+)*)\))?
        ''', re.VERBOSE | re.DOTALL)
    EXTRACTOR_INDICATOR_RE = re.compile(r'(?:Fix|Add)\s+Extractors?', re.IGNORECASE)
    REVERT_RE = re.compile(r'(?:\[[^\]]+\]\s+)?(?i:Revert)\s+([\da-f]{40})')
    FIXES_RE = re.compile(r'(?i:Fix(?:es)?(?:\s+bugs?)?(?:\s+in|\s+for)?|Revert|Improve)\s+([\da-f]{40})')
    UPSTREAM_MERGE_RE = re.compile(r'Update to ytdl-commit-([\da-f]+)')

    def __init__(self, start, end, default_author=None):
        self._start, self._end = start, end
        self._commits, self._fixes = self._get_commits_and_fixes(default_author)
        self._commits_added = []

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

    def _get_commits_and_fixes(self, default_author):
        result = run_process(
            self.COMMAND, 'log', f'--format=%H%n%s%n%b%n{self.COMMIT_SEPARATOR}',
            f'{self._start}..{self._end}' if self._start else self._end).stdout

        commits, reverts = {}, {}
        fixes = defaultdict(list)
        lines = iter(result.splitlines(False))
        for i, commit_hash in enumerate(lines):
            short = next(lines)
            skip = short.startswith('Release ') or short == '[version] update'

            authors = [default_author] if default_author else []
            for line in iter(lambda: next(lines), self.COMMIT_SEPARATOR):
                match = self.AUTHOR_INDICATOR_RE.match(line)
                if match:
                    authors = sorted(map(str.strip, line[match.end():].split(',')), key=str.casefold)

            commit = Commit(commit_hash, short, authors)
            if skip and (self._start or not i):
                logger.debug(f'Skipped commit: {commit}')
                continue
            elif skip:
                logger.debug(f'Reached Release commit, breaking: {commit}')
                break

            revert_match = self.REVERT_RE.fullmatch(commit.short)
            if revert_match:
                reverts[revert_match.group(1)] = commit
                continue

            fix_match = self.FIXES_RE.search(commit.short)
            if fix_match:
                commitish = fix_match.group(1)
                fixes[commitish].append(commit)

            commits[commit.hash] = commit

        for commitish, revert_commit in reverts.items():
            reverted = commits.pop(commitish, None)
            if reverted:
                logger.debug(f'{commitish} fully reverted {reverted}')
            else:
                commits[revert_commit.hash] = revert_commit

        for commitish, fix_commits in fixes.items():
            if commitish in commits:
                hashes = ', '.join(commit.hash[:HASH_LENGTH] for commit in fix_commits)
                logger.info(f'Found fix(es) for {commitish[:HASH_LENGTH]}: {hashes}')
                for fix_commit in fix_commits:
                    del commits[fix_commit.hash]
            else:
                logger.debug(f'Commit with fixes not in changes: {commitish[:HASH_LENGTH]}')

        return commits, fixes

    def apply_overrides(self, overrides):
        for override in overrides:
            when = override.get('when')
            if when and when not in self and when != self._start:
                logger.debug(f'Ignored {when!r} override')
                continue

            override_hash = override.get('hash') or when
            if override['action'] == 'add':
                commit = Commit(override.get('hash'), override['short'], override.get('authors') or [])
                logger.info(f'ADD    {commit}')
                self._commits_added.append(commit)

            elif override['action'] == 'remove':
                if override_hash in self._commits:
                    logger.info(f'REMOVE {self._commits[override_hash]}')
                    del self._commits[override_hash]

            elif override['action'] == 'change':
                if override_hash not in self._commits:
                    continue
                commit = Commit(override_hash, override['short'], override.get('authors') or [])
                logger.info(f'CHANGE {self._commits[commit.hash]} -> {commit}')
                self._commits[commit.hash] = commit

        self._commits = {key: value for key, value in reversed(self._commits.items())}

    def groups(self):
        group_dict = defaultdict(list)
        for commit in self:
            upstream_re = self.UPSTREAM_MERGE_RE.search(commit.short)
            if upstream_re:
                commit.short = f'[upstream] Merged with youtube-dl {upstream_re.group(1)}'

            match = self.MESSAGE_RE.fullmatch(commit.short)
            if not match:
                logger.error(f'Error parsing short commit message: {commit.short!r}')
                continue

            prefix, sub_details_alt, message, issues = match.groups()
            issues = [issue.strip()[1:] for issue in issues.split(',')] if issues else []

            if prefix:
                groups, details, sub_details = zip(*map(self.details_from_prefix, prefix.split(',')))
                group = next(iter(filter(None, groups)), None)
                details = ', '.join(unique(details))
                sub_details = list(itertools.chain.from_iterable(sub_details))
            else:
                group = CommitGroup.CORE
                details = None
                sub_details = []

            if sub_details_alt:
                sub_details.append(sub_details_alt)
            sub_details = tuple(unique(sub_details))

            if not group:
                if self.EXTRACTOR_INDICATOR_RE.search(commit.short):
                    group = CommitGroup.EXTRACTOR
                    logger.error(f'Assuming [ie] group for {commit.short!r}')
                else:
                    group = CommitGroup.CORE

            commit_info = CommitInfo(
                details, sub_details, message.strip(),
                issues, commit, self._fixes[commit.hash])

            logger.debug(f'Resolved {commit.short!r} to {commit_info!r}')
            group_dict[group].append(commit_info)

        return group_dict

    @staticmethod
    def details_from_prefix(prefix):
        if not prefix:
            return CommitGroup.CORE, None, ()

        prefix, *sub_details = prefix.split(':')

        group, details = CommitGroup.get(prefix)
        if group is CommitGroup.PRIORITY and details:
            details = details.partition('/')[2].strip()

        if details and '/' in details:
            logger.error(f'Prefix is overnested, using first part: {prefix}')
            details = details.partition('/')[0].strip()

        if details == 'common':
            details = None
        elif group is CommitGroup.NETWORKING and details == 'rh':
            details = 'Request Handler'

        return group, details, sub_details


def get_new_contributors(contributors_path, commits):
    contributors = set()
    if contributors_path.exists():
        for line in read_file(contributors_path).splitlines():
            author, _, _ = line.strip().partition(' (')
            authors = author.split('/')
            contributors.update(map(str.casefold, authors))

    new_contributors = set()
    for commit in commits:
        for author in commit.authors:
            author_folded = author.casefold()
            if author_folded not in contributors:
                contributors.add(author_folded)
                new_contributors.add(author)

    return sorted(new_contributors, key=str.casefold)


def create_changelog(args):
    logging.basicConfig(
        datefmt='%Y-%m-%d %H-%M-%S', format='{asctime} | {levelname:<8} | {message}',
        level=logging.WARNING - 10 * args.verbosity, style='{', stream=sys.stderr)

    commits = CommitRange(None, args.commitish, args.default_author)

    if not args.no_override:
        if args.override_path.exists():
            overrides = json.loads(read_file(args.override_path))
            commits.apply_overrides(overrides)
        else:
            logger.warning(f'File {args.override_path.as_posix()} does not exist')

    logger.info(f'Loaded {len(commits)} commits')

    new_contributors = get_new_contributors(args.contributors_path, commits)
    if new_contributors:
        if args.contributors:
            write_file(args.contributors_path, '\n'.join(new_contributors) + '\n', mode='a')
        logger.info(f'New contributors: {", ".join(new_contributors)}')

    return Changelog(commits.groups(), args.repo, args.collapsible)


def create_parser():
    import argparse

    parser = argparse.ArgumentParser(
        description='Create a changelog markdown from a git commit range')
    parser.add_argument(
        'commitish', default='HEAD', nargs='?',
        help='The commitish to create the range from (default: %(default)s)')
    parser.add_argument(
        '-v', '--verbosity', action='count', default=0,
        help='increase verbosity (can be used twice)')
    parser.add_argument(
        '-c', '--contributors', action='store_true',
        help='update CONTRIBUTORS file (default: %(default)s)')
    parser.add_argument(
        '--contributors-path', type=Path, default=LOCATION_PATH.parent / 'CONTRIBUTORS',
        help='path to the CONTRIBUTORS file')
    parser.add_argument(
        '--no-override', action='store_true',
        help='skip override json in commit generation (default: %(default)s)')
    parser.add_argument(
        '--override-path', type=Path, default=LOCATION_PATH / 'changelog_override.json',
        help='path to the changelog_override.json file')
    parser.add_argument(
        '--default-author', default='pukkandan',
        help='the author to use without a author indicator (default: %(default)s)')
    parser.add_argument(
        '--repo', default='yt-dlp/yt-dlp',
        help='the github repository to use for the operations (default: %(default)s)')
    parser.add_argument(
        '--collapsible', action='store_true',
        help='make changelog collapsible (default: %(default)s)')

    return parser


if __name__ == '__main__':
    print(create_changelog(create_parser().parse_args()))
