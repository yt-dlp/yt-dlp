from __future__ import annotations

import enum
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
AUTHOR_INDICATOR = "Authored by: "
COMMIT_SEPARATOR = "---"

USER_URL = "https://github.com"
REPO_URL = "https://github.com/yt-dlp/yt-dlp"

# fmt: off
MESSAGE_RE = re.compile(r"(?:\[(?P<prefix>[^\]]+)\] )?(?P<message>.+?)(?: \(#(?P<issue>\d+)\))?")
MISC_RE = re.compile(r"(?:^|\b)(?:misc|format(?:ting)?|fixes)(?:\b|$)", re.IGNORECASE)
# fmt: on

OVERRIDE_PATH = Path(__file__).parent / "changelog_override.json"
CONTRIBUTORS_PATH = Path(__file__).parent.parent / "CONTRIBUTORS"

logger = logging.getLogger(__name__)


class CommitGroup(enum.Enum):
    PRIORITY = "Important"
    CORE = "Core"
    DOWNLOADER = "Downloader"
    EXTRACTOR = "Extractor"
    MISC = "Misc."

    @classmethod
    @cache
    def commit_lookup(cls):
        return {
            name: group
            for group, names in {
                cls.PRIORITY: {
                    "",
                },
                cls.CORE: {
                    None,
                    "aes",
                    "cache",
                    "cookies",
                    "dependencies",
                    "jsinterp",
                    "plugins",
                    "update",
                    "utils",
                },
                cls.MISC: {
                    "cleanup",
                    "docs",
                    "build",
                },
                cls.DOWNLOADER: {
                    "downloader",
                },
                cls.EXTRACTOR: {
                    "extractor",
                },
            }.items()
            for name in names
        }

    @classmethod
    def get(cls, value: str | None):
        logger.debug(f"Got value: {value!r}")
        return cls.commit_lookup().get(value, cls.EXTRACTOR)


@dataclass
class CommitInfo:
    prefix: str | None
    details: str | None
    message: str
    issue: str | None
    commit: Commit

    def key(self):
        return (self.prefix or "", self.details or "", self.message)


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
            details = item.details or item.prefix
            logger.debug(f"{details!r} != {current!r} = {details != current}")
            if details != current:
                if current == "cleanup" and cleanup_misc:
                    yield from self._format_misc_items(cleanup_misc)

                yield f"- {details}"
                current = details
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
        yield from (f"\t\t- {message}" for message in cls._format_misc_items(group))

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


def group_commits(commits: Iterable[Commit]) -> dict[CommitGroup, list[CommitInfo]]:
    groups = defaultdict(list)
    for commit in commits:
        if commit.short.startswith("Release "):
            continue

        match = MESSAGE_RE.fullmatch(commit.short)
        if not match:
            logger.error(f"Error parsing short commit message: {commit.short!r}")
            continue

        prefix, message, issue = match.groups()
        # Skip version bump commit
        if prefix == "version":
            continue

        group = None
        if prefix:
            if prefix.startswith("priority"):
                _, _, prefix = prefix.partition("/")

                logger.debug(f"Increased priority: {message!r}")
                group = CommitGroup.PRIORITY

            else:
                prefix = prefix.lower()

            prefix, _, detail = prefix.partition("/")
            detail, _, sub_detail = detail.partition(":")
            if sub_detail:
                message = f"`{sub_detail}`: {message}"

            prefix = prefix or None
            detail = detail or None

        else:
            detail = None

        # fmt: off
        if not group:
            group = CommitGroup.get(prefix)
        groups[group].append(CommitInfo(prefix, detail, message, issue, commit))
        # fmt: on

    return groups


def get_commits(start, end):
    # fmt: off
    command = ["git", "log", f"--format=%H%n%s%n%b%n{COMMIT_SEPARATOR}", f"{start}..{end}"]
    # fmt: on
    result = subprocess.run(command, stdout=subprocess.PIPE, text=True)
    lines = iter(result.stdout.splitlines(False))
    for line in lines:
        commit_hash = line
        short = next(lines)

        authors = [DEFAULT_AUTHOR]
        line = next(lines)
        while line != COMMIT_SEPARATOR:
            if line.startswith(AUTHOR_INDICATOR):
                authors = line.removeprefix(AUTHOR_INDICATOR).split(", ")

            line = next(lines)

        yield Commit(commit_hash, short, authors)


def fix_commits(commits: Iterable[Commit]):
    with OVERRIDE_PATH.open("r") as file:
        overrides = json.load(file)

    commit_lookup = {commit.hash: commit for commit in commits}
    added_commits = []
    for override in overrides:
        if override["action"] == "add":
            # fmt: off
            commit = Commit(override.get("hash"), override["short"], override.get("authors"))
            # fmt: on
            logger.info(f"ADD    {commit}")
            added_commits.append(commit)

        elif override["action"] == "remove":
            override_hash = override["hash"]
            if override_hash in commit_lookup:
                logger.info(f"REMOVE {commit_lookup[override_hash]}")
                del commit_lookup[override_hash]

        elif override["action"] == "change":
            override_hash = override["hash"]
            if override_hash not in commit_lookup:
                continue
            commit = Commit(override_hash, override["short"], override["authors"])
            logger.info(f"CHANGE {commit_lookup[commit.hash]} -> {commit}")
            commit_lookup[commit.hash] = commit

    ordered_commits = {key: value for key, value in reversed(commit_lookup.items())}
    yield from ordered_commits.values()
    yield from added_commits


def update_contributors(commits: list[Commit]):
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
    parser.add_argument("start", help="The hash or tag to start from")
    parser.add_argument("end", default="HEAD", nargs="?", help="The hash or tag to end on (default: HEAD)")
    parser.add_argument("-v", "--verbosity", action="count", default=0, help="Increase verbosity")
    parser.add_argument("-c", "--contributors", action="store_true", help="Update CONTRIBUTORS file")
    # fmt: on
    args = parser.parse_args()
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

    commits = get_commits(args.start, args.end)
    commits = list(fix_commits(commits))
    logger.info(f"Loaded {len(commits)} commits")

    if args.contributors:
        new_contributors = update_contributors(commits)
        logger.info(f"Added these new contributors: {new_contributors}")

    print(Changelog(group_commits(commits)))
