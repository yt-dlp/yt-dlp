from __future__ import annotations

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
from typing import Iterable

DEFAULT_AUTHOR = "pukkandan"
AUTHOR_INDICATOR_RE = re.compile("Authored by:? ")

USER_URL = "https://github.com"
REPO_URL = "https://github.com/yt-dlp/yt-dlp"

MESSAGE_RE = re.compile(
    r"""
    (?:\[
        (?P<prefix>[^\]\/:,]+)
        (?:/(?P<details>[^\]:,]+))?
        (?:[:,](?P<sub_details>[^\]]+))?
    \]\ )?
    (?P<message>.+?)
    (?:\ \(\#(?P<issue>\d+)\))?
    """,
    re.VERBOSE,
)
MISC_RE = re.compile(r"(?:^|\b)(?:misc|format(?:ting)?|fixes)(?:\b|$)", re.IGNORECASE)

OVERRIDE_PATH = Path(__file__).parent / "changelog_override.json"
CONTRIBUTORS_PATH = Path(__file__).parent.parent / "CONTRIBUTORS"

logger = logging.getLogger(__name__)


class CommitGroup(enum.Enum):
    PRIORITY = "Important"
    CORE = "Core"
    EXTRACTOR = "Extractor"
    DOWNLOADER = "Downloader"
    POSTPROCESSOR = "Postprocessor"
    MISC = "Misc."

    @classmethod
    @cache
    def commit_lookup(cls):
        return {
            name: group
            for group, names in {
                cls.PRIORITY: {""},
                cls.CORE: {
                    "aes",
                    "cache",
                    "compat_utils",
                    "compat",
                    "cookies",
                    "dependencies",
                    "jsinterp",
                    "plugins",
                    "update",
                    "utils",
                },
                cls.MISC: {
                    "build",
                    "cleanup",
                    "docs",
                },
                cls.EXTRACTOR: {"extractor"},
                cls.DOWNLOADER: {"downloader"},
                cls.POSTPROCESSOR: {"postprocessor"},
            }.items()
            for name in names
        }

    @classmethod
    def get(cls, value: str):
        result = cls.commit_lookup().get(value, cls.EXTRACTOR)
        logger.debug(f"Mapped {value!r} => {result.name}")
        return result


@dataclass
class CommitInfo:
    details: str | None
    message: str
    issue: str | None
    commit: Commit

    def key(self):
        return (self.details or "", self.message)


@dataclass
class Commit:
    hash: str | None
    short: str
    authors: list[str] | None

    def __str__(self):
        result = f"{self.short!r}"

        if self.hash:
            result += f" ({self.hash[:7]})"

        if self.authors:
            authors = ", ".join(self.authors)
            result += f" by {authors}"

        return result


class Changelog:
    def __init__(self, groups: dict[CommitGroup, list[CommitInfo]]):
        self._groups = groups

    def __str__(self):
        return "\n".join(self._format_groups(self._groups)).replace("\t", "    ")

    def _format_groups(self, groups: dict[CommitGroup, list[CommitInfo]]):
        yield "## Changelog"

        for item in CommitGroup:
            group = groups[item]
            if group:
                yield self.format_module(item.value, group)

    def format_module(self, name: str, group: Iterable[CommitInfo]):
        return f"### {name} changes\n" + "\n".join(self._format_group(group))

    def _format_group(self, group: Iterable[CommitInfo]):
        cleanup_misc = defaultdict(list)

        current = None
        indent = ""
        for item in sorted(group, key=CommitInfo.key):
            if item.details != current:
                if current == "cleanup" and cleanup_misc:
                    yield from self._format_misc_items(cleanup_misc)

                yield f"- {item.details}"
                current = item.details
                indent = "\t"

            if current == "cleanup" and MISC_RE.search(item.message):
                cleanup_misc[tuple(item.commit.authors or ())].append(item)
            else:
                yield f"{indent}- {self.format_single_change(item)}"

        if current == "cleanup" and cleanup_misc:
            yield from self.format_misc_items(cleanup_misc)

    @classmethod
    def format_misc_items(cls, group: dict[tuple[str, ...], list[CommitInfo]]):
        prefix = "\t- Miscellaneous"
        if len(group) == 1:
            yield f"{prefix}: {next(cls._format_misc_items(group))}"
            return

        yield prefix
        for message in cls._format_misc_items(group):
            yield f"\t\t- {message}"

    @classmethod
    def _format_misc_items(cls, group: dict[tuple[str, ...], list[CommitInfo]]):
        for authors, infos in group.items():
            message = ", ".join(
                f"[{info.commit.hash:.7}]({REPO_URL}/commit/{info.commit.hash})"
                for info in sorted(infos, key=lambda item: item.commit.hash or "")
            )
            yield f"{message} by {cls._format_authors(authors)}"

    @classmethod
    def format_single_change(cls, info: CommitInfo):
        message = (
            f"[{info.message}]({REPO_URL}/commit/{info.commit.hash})"
            if info.commit.hash is not None
            else info.message
        )
        if info.issue:
            issue = f"[#{info.issue}]({REPO_URL}/issues/{info.issue})"
            message = f"{message} ({issue})"

        if not info.commit.authors:
            return message

        return f"{message} by {cls._format_authors(info.commit.authors)}"

    @staticmethod
    def _format_authors(authors: Iterable[str] | None):
        return ", ".join(f"[{author}]({USER_URL}/{author})" for author in authors or ())


class CommitRange:
    COMMAND = "git"
    COMMIT_SEPARATOR = "-----"

    def __init__(self, start: str, end: str) -> None:
        self._start = start
        self._end = end
        self._commits = {commit.hash: commit for commit in self._get_commits_raw()}
        self._commits_added = []

    @classmethod
    def from_single(cls, commitish: str = "HEAD"):
        start_commitish = cls.get_prev_tag(commitish)
        end_commitish = cls.get_next_tag(commitish)
        if start_commitish == end_commitish:
            start_commitish = cls.get_prev_tag(f"{commitish}~")
        logger.info(
            f"Determined range from {commitish!r}: {start_commitish}..{end_commitish}"
        )
        return cls(start_commitish, end_commitish)

    @classmethod
    def get_prev_tag(cls, commitish: str) -> str:
        command = [cls.COMMAND, "describe", "--tags", "--abbrev=0", commitish]
        return subprocess.check_output(command, text=True).strip()

    @classmethod
    def get_next_tag(cls, commitish: str) -> str:
        command = [cls.COMMAND, "describe", "--contains", "--abbrev=0", commitish]
        result = subprocess.run(
            command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True
        )
        if result.returncode:
            return "HEAD"

        return result.stdout.partition("~")[0].strip()

    def __iter__(self):
        return iter(itertools.chain(self._commits.values(), self._commits_added))

    def __len__(self):
        return len(self._commits) + len(self._commits_added)

    def __contains__(self, commit: Commit | str):
        if isinstance(commit, Commit):
            if not commit.hash:
                return False
            commit = commit.hash

        return commit in self._commits

    def _is_ancestor(self, commitish):
        command = [self.COMMAND, "merge-base", "--is-ancestor", commitish, self._start]
        return bool(subprocess.call(command))

    def _get_commits_raw(self):
        command = [
            self.COMMAND,
            "log",
            f"--format=%H%n%s%n%b%n{self.COMMIT_SEPARATOR}",
            f"{self._start}..{self._end}",
        ]
        result = subprocess.check_output(command, text=True)
        lines = iter(result.splitlines(False))
        for line in lines:
            commit_hash = line
            short = next(lines)
            skip = short.startswith("Release ") or short == "[version] update"

            authors = [DEFAULT_AUTHOR]
            for line in iter(lambda: next(lines), self.COMMIT_SEPARATOR):
                match = AUTHOR_INDICATOR_RE.match(line)
                if match:
                    authors = line[match.end() :].split(", ")

            commit = Commit(commit_hash, short, authors)
            if skip:
                logger.debug(f"Skipped commit: {commit}")
            else:
                yield commit

    def apply_overrides(self, overrides: list[dict]):
        for override in overrides:
            when = override.get("when")
            if when and when not in self and when != self._start:
                logger.debug(f"Ignored {when}, not in commits {self._start!r}")
                continue

            override_hash = override.get("hash")
            if override["action"] == "add":
                # fmt: off
                commit = Commit(override.get("hash"), override["short"], override.get("authors"))
                # fmt: on
                logger.info(f"ADD    {commit}")
                self._commits_added.append(commit)

            elif override["action"] == "remove":
                if override_hash in self._commits:
                    logger.info(f"REMOVE {self._commits[override_hash]}")
                    del self._commits[override_hash]

            elif override["action"] == "change":
                if override_hash not in self._commits:
                    continue
                commit = Commit(override_hash, override["short"], override["authors"])
                logger.info(f"CHANGE {self._commits[commit.hash]} -> {commit}")
                self._commits[commit.hash] = commit

        self._commits = {key: value for key, value in reversed(self._commits.items())}

    def groups(self) -> dict[CommitGroup, list[CommitInfo]]:
        groups = defaultdict(list)
        for commit in self:
            match = MESSAGE_RE.fullmatch(commit.short)
            if not match:
                logger.error(f"Error parsing short commit message: {commit.short!r}")
                continue

            prefix, details, sub_details, message, issue = match.groups()
            group = None
            if prefix:
                if prefix == "priority":
                    prefix, _, details = (details or "").partition("/")
                    logger.debug(f"Priority: {message!r}")
                    group = CommitGroup.PRIORITY

                if sub_details:
                    message = f"`{sub_details}`: {message}"

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


def update_contributors(commits: Iterable[Commit]):
    contributors = set()
    with CONTRIBUTORS_PATH.open() as file:
        for line in filter(None, map(str.strip, file)):
            author, _, _ = line.partition(" (")
            authors = author.split("/")
            contributors.update(authors)

    new_contributors = {}
    for commit in commits:
        for author in commit.authors or ():
            if author in contributors:
                continue
            contributors.add(author)
            new_contributors[author] = None

    new_contributors = list(reversed(new_contributors))
    with CONTRIBUTORS_PATH.open("a") as file:
        for contributor in new_contributors:
            file.write(f"{contributor}\n")

    return new_contributors


if __name__ == "__main__":
    import argparse

    # fmt: off
    parser = argparse.ArgumentParser(description="Create a changelog from git range")
    parser.add_argument("commitish", default="HEAD", nargs="?", help="The commitish to create the range from (default: HEAD)")
    parser.add_argument("-v", "--verbosity", action="count", default=0, help="Increase verbosity")
    parser.add_argument("-c", "--contributors", action="store_true", help="Update CONTRIBUTORS file")
    parser.add_argument("-o", "--override", type=Path, default=OVERRIDE_PATH, help="Path to override file")
    # fmt: on
    args, _ = parser.parse_known_args()
    logging.basicConfig(
        datefmt="%Y-%m-%d %H-%M-%S",
        format="{asctime} | {levelname:<8} | {message}",
        level=logging.DEBUG
        if args.verbosity >= 2
        else logging.INFO
        if args.verbosity == 1
        else logging.WARNING,
        style="{",
        stream=sys.stderr,
    )

    commits = CommitRange.from_single(args.commitish)

    if args.override:
        if args.override.exists():
            with args.override.open() as file:
                overrides = json.load(file)
            commits.apply_overrides(overrides)
        else:
            logger.warning(f"File {args.override.as_posix()} does not exist")

    logger.info(f"Loaded {len(commits)} commits")

    if args.contributors:
        new_contributors = update_contributors(commits)
        logger.info(f"Added these new contributors: {new_contributors}")

    print(Changelog(commits.groups()))
