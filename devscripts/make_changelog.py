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
        self.groups = groups

    @classmethod
    def from_commits(cls, commits: list[Commit]):
        return cls(cls.group_commits(commits))

    def __str__(self):
        return "\n".join(self._format_groups(self.groups))

    def _format_groups(self, groups: dict[CommitGroup, list[CommitInfo]]):
        yield "## Changelog"

        for item in CommitGroup:
            group = groups[item]
            if group:
                yield self.format_module(item.value, group)

    def format_module(self, name: str | None, group: Iterable[CommitInfo]):
        result = f"### {name} changes\n" if isinstance(name, str) else ""
        return result + "\n".join(self._format_group(group))

    def _format_group(self, group: Iterable[CommitInfo]):
        current = None
        indent = ""
        for item in sorted(group, key=CommitInfo.key):
            details = item.details or item.prefix
            logger.debug(f"{details} != {current} = {details != current}")
            if details != current:
                yield f"- {details}"
                current = details
                indent = "    "

            yield f"{indent}- {self.format_single_change(item)}"

    def format_single_change(self, commit_info: CommitInfo):
        message = (
            f"[{commit_info.message}]({REPO_URL}/commit/{commit_info.commit.hash})"
            if commit_info.commit.hash is not None
            else commit_info.message
        )
        if commit_info.issue:
            issue = f"[#{commit_info.issue}]({REPO_URL}/issues/{commit_info.issue})"
            message = f"{message} ({issue})"

        if not commit_info.commit.authors:
            return message

        # fmt: off
        authors = ", ".join(f"[{author}]({USER_URL}/{author})" for author in commit_info.commit.authors)
        # fmt: on
        return f"{message} by {authors}"

    @staticmethod
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
        override = json.load(file)

    commit_lookup = {commit.hash: commit for commit in commits}
    for commit_hash, data in override["change"].items():
        if commit_hash not in commit_lookup:
            continue
        commit = Commit(commit_hash, data["short"], data["authors"])
        logger.info(f"CHANGE {commit_lookup[commit_hash]}")
        logger.info(f"       -> {commit}")
        commit_lookup[commit_hash] = commit

    for commit_hash in override["remove"]:
        if commit_hash in commit_lookup:
            logger.info(f"REMOVE {commit_lookup[commit_hash]}")
            del commit_lookup[commit_hash]

    for data in override["add"].get(args.start) or ():
        commit = Commit(data.get("hash"), data["short"], data.get("authors"))
        logger.info(f"ADD    {commit}")
        yield commit

    yield from commit_lookup.values()


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

    print(Changelog.from_commits(commits))
