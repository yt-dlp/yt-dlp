#!/usr/bin/env python3
"""
run_proof.py -- the demonstration.

For each program we:

  1. write it in Brainfuck (directly, or via the bf.py assembler),
  2. compile it to JavaScript with bfc.compile_bf,
  3. execute that JavaScript with the *real, unmodified* yt_dlp.jsinterp
     interpreter that ships in this repository,
  4. check the output against an independent Python oracle.

Step 3 is the whole point: the program that runs is exactly the kind of
artifact YouTube's base.js is -- a Google-shaped JavaScript blob fed to
jsinterp -- except here we control it and can prove what it computes.

The ladder:

  * Hello World        -- canonical sanity check; loops + I/O.
  * Unary echo         -- a *data-dependent* runtime `[ ]` loop: the
                          number of iterations comes from input, not from
                          the program text. Straight-line code can't do
                          this; an interpreter with loops can.
  * Rule 110           -- Cook's elementary cellular automaton, proven
                          Turing-complete, and the same automaton Jacob K
                          simulated in older jsinterp. Verified
                          generation-by-generation against a pure-Python
                          oracle.

Run:  python3 blog/shifting-the-trap/run_proof.py
(from the repository root, so that `yt_dlp` is importable)
"""

from __future__ import annotations

import os
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)                                    # bf.py, bfc.py
sys.path.insert(0, os.path.abspath(os.path.join(_HERE, '..', '..')))  # yt_dlp

from bf import BF
from bfc import compile_bf

from yt_dlp.jsinterp import JSInterpreter


def run_js(bf_src: str, inp: list[int], tape_size: int = 4096):
    """Compile Brainfuck, run it on the real jsinterp, return (output, js)."""
    js = compile_bf(bf_src, tape_size=tape_size)
    return JSInterpreter(js).call_function('run', list(inp)), js


# --------------------------------------------------------------------------
# Program 1: Hello World (classic public-domain Brainfuck)
# --------------------------------------------------------------------------
HELLO = ('++++++++[>++++[>++>+++>+++>+<<<<-]>+>+>->>+[<]<-]'
         '>>.>---.+++++++..+++.>>.<-.<.+++.------.--------.>>+.>++.')


# --------------------------------------------------------------------------
# Program 2: unary echo -- output `n` asterisks, where n = input[0].
# cell0 = n (read), cell1 = 42 ('*'). while n: emit '*'; n--.
# --------------------------------------------------------------------------
def build_unary_echo() -> str:
    b = BF()
    b.read(0)
    b.add(1, 42)
    with b.loop(0):
        b.out(1)
        b.add(0, -1)
    return b.code()


# --------------------------------------------------------------------------
# Program 3: Rule 110.
#
# Fixed width W (zero boundaries). Generations come from input[0], so the
# runtime loop count is data-dependent. Seed: a single 1 in the rightmost
# cell (Rule 110 then grows leftward), matching the classic single-seed
# demonstration. After each generation the row is printed as ASCII
# '0'/'1' followed by a newline.
#
# Cell map:
#   0 G (generations remaining / loop var)   1 L (running left neighbor)
#   2 C (center copy)   3 R (right copy)   4 N (new value)
#   5 F (else flag)     6 S0 scratch       7 S1 scratch
#   8 Ln (next L)       9.. row[0..W-1]
#
# Update uses the single-register left-to-right trick (no second buffer):
#   next = C ? (1 - (L & R)) : R          -- exactly Rule 110.
# --------------------------------------------------------------------------
G, L, C, R, N, F, S0, S1, Ln, ROW = 0, 1, 2, 3, 4, 5, 6, 7, 8, 9


def build_rule110(width: int) -> str:
    b = BF()
    b.read(G)                       # generations from input
    b.add(ROW + width - 1, 1)       # seed: single 1 at the right edge

    with b.loop(G):
        b.zero(L)                   # left neighbor of cell 0 is 0
        for k in range(width):
            cell = ROW + k
            b.move2(cell, C, Ln)    # C = Ln = old row[k]; row[k] = 0
            if k < width - 1:
                b.copy(cell + 1, R, S0)   # R = old row[k+1] (preserved)
            b.add(F, 1)             # assume "else" until "then" fires

            with b.loop(C):         # THEN: center != 0  ->  N = 1 - (L & R)
                with b.loop(L):     #   S1 = L & R, consuming L and R
                    with b.loop(R):
                        b.add(S1, 1)
                        b.zero(R)
                    b.zero(L)
                b.zero(R)           #   R may survive if L was 0; force 0
                b.add(N, 1)         #   N = 1
                with b.loop(S1):    #   if S1: N = 0
                    b.add(N, -1)
                    b.zero(S1)
                b.zero(F)           #   cancel else
                b.zero(C)           #   exit THEN

            with b.loop(F):         # ELSE: center == 0  ->  N = R
                b.move(R, N)
                b.zero(F)

            b.move(N, cell)         # row[k] = N
            b.zero(L)               # L := Ln (old row[k])
            b.move(Ln, L)

        for k in range(width):      # print this generation
            b.copy(ROW + k, S0, S1)
            b.add(S0, 48)           # 0/1 -> '0'/'1'
            b.out(S0)
            b.zero(S0)
        b.add(S0, 10)               # newline
        b.out(S0)
        b.zero(S0)

        b.add(G, -1)                # one generation done
    return b.code()


def rule110_oracle(width: int, generations: int) -> str:
    row = [0] * width
    row[-1] = 1
    lines = []
    for _ in range(generations):
        nxt = []
        for i in range(width):
            l = row[i - 1] if i > 0 else 0
            c = row[i]
            r = row[i + 1] if i < width - 1 else 0
            nxt.append((110 >> ((l << 2) | (c << 1) | r)) & 1)
        row = nxt
        lines.append(''.join(map(str, row)))
    return '\n'.join(lines) + '\n'


# --------------------------------------------------------------------------
def main() -> int:
    failures = 0

    def check(name: str, got: str, want: str, js: str) -> None:
        nonlocal failures
        ok = got == want
        failures += not ok
        print(f'[{"PASS" if ok else "FAIL"}] {name}'
              f'  (compiled JS: {len(js)} chars)')
        if not ok:
            print(f'   expected: {want!r}')
            print(f'   got:      {got!r}')

    t0 = time.time()

    out, js = run_js(HELLO, [], tape_size=64)
    check('hello world', out, 'Hello World!\n', js)

    echo = build_unary_echo()
    for n in (0, 1, 5, 23):
        out, js = run_js(echo, [n], tape_size=8)
        check(f'unary echo n={n}', out, '*' * n, js)

    width = 24
    r110 = build_rule110(width)
    for gens in (1, 8, 20):
        out, js = run_js(r110, [gens], tape_size=ROW + width + 1)
        check(f'rule 110 (w={width}, g={gens})',
              out, rule110_oracle(width, gens), js)

    print(f'\n{"-" * 56}')
    print(f'{"ALL PROOFS PASSED" if not failures else f"{failures} FAILURE(S)"}'
          f'   ({time.time() - t0:.1f}s on real yt_dlp.jsinterp)')
    return 1 if failures else 0


if __name__ == '__main__':
    raise SystemExit(main())
