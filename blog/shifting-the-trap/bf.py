"""
bf.py -- a tiny Brainfuck macro assembler, used only to *author* the
non-trivial proof programs (unary echo, Rule 110) correctly and readably.

This module never touches yt-dlp. It emits pure Brainfuck text. That text
is then handed to bfc.compile_bf, and only the resulting JavaScript is run
by yt-dlp's jsinterp. So the thing under test is always "jsinterp executes
compiled Brainfuck"; this assembler is just a trustworthy pen.

Addressing is absolute: every cell has a fixed index and the builder
tracks the data pointer in Python so `to(i)` emits the right run of
`>`/`<`. Every loop is opened and closed with the pointer on the loop
cell, which keeps the generated Brainfuck balanced and correct by
construction.
"""

from __future__ import annotations

import contextlib


class BF:
    def __init__(self) -> None:
        self._parts: list[str] = []
        self.pos = 0

    def code(self) -> str:
        return ''.join(self._parts)

    # --- primitives -----------------------------------------------------
    def raw(self, s: str) -> 'BF':
        self._parts.append(s)
        return self

    def to(self, idx: int) -> 'BF':
        delta = idx - self.pos
        self._parts.append('>' * delta if delta > 0 else '<' * (-delta))
        self.pos = idx
        return self

    def add(self, idx: int, n: int) -> 'BF':
        self.to(idx)
        self._parts.append('+' * n if n >= 0 else '-' * (-n))
        return self

    def zero(self, idx: int) -> 'BF':
        self.to(idx)
        self._parts.append('[-]')
        return self

    def out(self, idx: int) -> 'BF':
        self.to(idx)
        self._parts.append('.')
        return self

    def read(self, idx: int) -> 'BF':
        self.to(idx)
        self._parts.append(',')
        return self

    @contextlib.contextmanager
    def loop(self, idx: int):
        """`while cell[idx] != 0`. Pointer is on `idx` at `[` and forced
        back to `idx` before `]`, so nests cleanly."""
        self.to(idx)
        self._parts.append('[')
        yield
        self.to(idx)
        self._parts.append(']')

    # --- compound moves -------------------------------------------------
    def move(self, src: int, dst: int) -> 'BF':
        """dst += src; src = 0."""
        with self.loop(src):
            self.add(src, -1)
            self.add(dst, 1)
        return self

    def move2(self, src: int, d1: int, d2: int) -> 'BF':
        """d1 += src; d2 += src; src = 0."""
        with self.loop(src):
            self.add(src, -1)
            self.add(d1, 1)
            self.add(d2, 1)
        return self

    def copy(self, src: int, dst: int, tmp: int) -> 'BF':
        """dst += src, src preserved. `tmp` must be 0 and is left 0."""
        self.move2(src, dst, tmp)
        self.move(tmp, src)
        return self
