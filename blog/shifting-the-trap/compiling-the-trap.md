# Compiling the Trap

*A follow-up to "Shifting the Trap" and to Jacob K's "Writing custom programs for yt-dlp's jsinterp."*

In *Shifting the Trap* I argued that `yt_dlp/jsinterp.py` is, despite the
hedging, a real interpreter for a subset of JavaScript — and that an
interpreter faithfully executing a non-free, Google-authored program
(`base.js`) is The JavaScript Trap, merely relocated from the browser to
the terminal.

Jacob K then went further, empirically. He hand-wrote Fibonacci and a
Rule 110 simulator *in jsinterp's language* and observed them run. His
conclusion: at some point enough machinery accreted — `for`, `switch`,
arrays — that the interpreter became Turing-complete. He left an explicit
open question: which release crossed that line, and can it be shown
rigorously rather than anecdotally?

This post closes the loop with a constructive proof. Not "here is a
program that looks Turing-complete," but: **here is a compiler whose
target is yt-dlp's interpreter, and here is the formal reduction that
makes its existence a proof.**

## Why a compiler proves anything

Turing-completeness is a statement about a *computational class*. The
clean way to establish it for a system *S* is a reduction: exhibit a
language *T* already known to be Turing-complete, and a **total**
translation `compile : T → S` that preserves observable behaviour. If
every *T*-program can be mechanically turned into an *S*-program that
computes the same thing, then *S* can compute everything *T* can — which
is everything.

So the question is only: which *T*?

The brief floated a C compiler. I want to explain why that would be the
*wrong* instrument, because the reasoning is the proof's spine.

A C frontend would be enormous, and worse, it would lean on exactly the
features jsinterp *lacks*. Reading the actual 972-line source on this
branch:

- There is **no `while`** and no `do/while`. The only loop is `for`.
- There is **no `else if`** (the code says so, in a `TODO`).
- Function calls share a single recursion budget (~100), decremented per
  statement *and* per expression. Anything recursion-heavy dies fast.
- There are no structs, no pointer arithmetic, no real type system.

A C compiler would spend thousands of lines fighting those gaps and
would prove nothing extra: Turing-completeness is not about whether the
language is *pleasant*, only about what it can *compute*. The right *T*
is the smallest language already proven Turing-complete. That is
**Brainfuck** — eight commands, a tape, and a loop; reducible to and from
a Turing machine by a well-known construction.

Brainfuck also maps onto a small, old part of jsinterp's grammar — the
part Jacob K's own programs already leaned on. *How* old is an empirical
question, not a rhetorical one, so the compiler is written against the
intersection of current jsinterp and **yt-dlp 2022.04.08**, the exact
release Jacob used in his forum post. Direct inspection of that older
interpreter is instructive: it has *no* comparison operators (no `==`,
`!=`, `<`, `>`), no `if`/`else`, no ternary, and no string `+` (which
matches Jacob's diagnosis in his reply to a draft of this post). The
only loop guard is truthiness of a single value. The compiler is
constrained accordingly — countdown loops, array-and-`join` output, no
ternary, no comparisons — and the same `run_proof.py` runs unchanged
against the 2022.04.08 interpreter (`pip install yt-dlp==2022.04.08` in
a venv, then `run_proof.py` with that venv's Python) and passes
identically.

## The compiler (`bfc.py`)

`compile_bf` is about sixty lines and imports nothing from yt-dlp. It is
a total function from Brainfuck source to a single JavaScript function,
written against the *intersection* of JavaScript and what jsinterp
actually implements:

| Brainfuck | Emitted JavaScript |
|---|---|
| `+` `-` | `t[p]=(t[p]+1)&255;` — `& 255` gives mod-256 cells; jsinterp's bit ops use Python `&`, so `(0-1)&255 == 255`, the correct Brainfuck wrap |
| `>` `<` | `p=p+1;` |
| `.` | `o.push(String.fromCharCode(t[p]));` — output is an array, joined at the end, because old jsinterp has no string `+` |
| `,` | `t[p]=inp[ip];ip=ip+1;` — unguarded, because old jsinterp has no `if`/`else`/ternary; the harness always supplies enough bytes |
| `[` `]` | **`for(;t[p];){` … `}`** — truthiness of the current cell, the only loop guard the older interpreter accepts |

The one load-bearing trick is the loop. jsinterp has no `while`, so
Brainfuck's `[ ]` becomes a `for` with empty init and increment whose
guard re-reads the current cell. Nested Brainfuck loops are just nested
`for`s. The tape itself is built with a countdown loop for the same
reason — there is no `i < N` in the older grammar.

Nothing in the output recurses. Brainfuck loops compile to JavaScript
loops, so the proof never touches jsinterp's ~100-deep recursion budget.
The compiler also coalesces runs of `+`/`>` into a single statement —
the textbook Brainfuck optimization, observationally identical, included
only so the regex-walking interpreter isn't re-parsing thousands of
one-character statements.

## The demonstration (`run_proof.py`)

Each program is compiled and then executed by the **real, unmodified
`yt_dlp.jsinterp.JSInterpreter` from this repository** — the same class,
reached the same way (`JSInterpreter(code).call_function(...)`), that
decodes YouTube's signatures — and its output is checked against an
independent Python oracle.

- **Hello World** — the canonical Brainfuck program. Loops and I/O, exact
  output. Sanity.
- **Unary echo** — output *n* asterisks, where *n* comes from the input.
  This matters: the iteration count is *data-dependent*, decided at run
  time, not baked into the program text. Straight-line code cannot do
  this; an interpreter with genuine loops can. It is the smallest honest
  witness that the `[ ]` → `for` lowering does real, unbounded work.
- **Rule 110** — Cook's elementary cellular automaton, *proven*
  Turing-complete, and the very automaton Jacob K simulated on older
  jsinterp. Width is fixed; the number of generations comes from input,
  so the outer loop is again data-dependent. Every generation is checked,
  cell for cell, against a pure-Python Rule 110.

All pass, in about 23 seconds, on the interpreter as shipped:

```
[PASS] hello world
[PASS] unary echo n=0 / 1 / 5 / 23
[PASS] rule 110 (w=24, g=1 / 8 / 20)
ALL PROOFS PASSED   (on real yt_dlp.jsinterp)
```

Rule 110 from a single right-edge seed — the familiar fractal — emitted
by `yt_dlp/jsinterp.py` and byte-for-byte equal to the oracle:

```
..............................##
.............................###
............................##.#
...........................#####
..........................##...#
.........................###..##
........................##.#.###
.......................#######.#
......................##.....###
.....................###....##.#
....................##.#...#####
...................#####..##...#
..................##...#.###..##
.................###..####.#.###
................##.#.##..#####.#
...............########.##...###
..............##......####..##.#
.............###.....##..#.#####
............##.#....###.####...#
...........#####...##.###..#..##
..........##...#..#####.#.##.###
.........###..##.##...########.#
........##.#.######..##......###
.......#######....#.###.....##.#
```

## The honest caveat

The real interpreter has a finite tape and a finite recursion budget.
The Turing-completeness *of the model* is unaffected: the reduction is
total, and the limits are resource bounds, not expressivity bounds. This
is the same footnote that applies to every physical computer, and the
same one Jacob K reached for when he noted that loop-unrolling in *very*
old youtube-dl still satisfies the colloquial definition. Stating it
plainly strengthens the claim rather than weakening it. The compiler is
exact; the machine, like all machines, is merely large.

It also bears on Jacob K's open question, though only in one direction.
If the ladder *passes* on a given revision, that revision is
Turing-complete — the compiler is the witness, contingent on its output
being valid on that revision. The other direction does not follow: a
failure means only that *this particular compiler* doesn't target *that
particular revision*, not that the revision lacks Turing-completeness.
Settling that in the negative needs either a different compiler or a
direct argument about the language's expressivity, and in full
generality the question is undecidable. Jacob K corrected me on this
point and he is right.

What the empirical compatibility *does* show is that the proof here is
not dependent on any of jsinterp's recent accretions. The same emitter
runs the same ladder unchanged on the 2022.04.08 release (Jacob's
version) and on the current branch. That is a sturdier ground than the
draft of this post claimed before Jacob corrected it.

## Why this is the proof the argument needed

*Shifting the Trap* made a definitional claim — jsinterp is an
interpreter. The natural rejoinder was "an interpreter of *what*, and how
much?" If it could only pattern-match signature functions, one might
argue the freedom question is narrow. It cannot only do that. A faithful
interpreter of a Turing-complete language is, by construction, a
general-purpose execution engine: whatever Google ships in `base.js`,
jsinterp will run, because there is no computable behaviour it *can't*
run. The signature dance is not the ceiling; it is one program among all
programs.

That is the technical spine of the original essay's thesis. The trap was
never "yt-dlp runs a specific clever string function." The trap is that a
free program, in its normal operation, hands a non-free, Google-authored,
daily-mutating program to a general-purpose interpreter on the user's
machine and runs it. The compiler doesn't accuse yt-dlp of anything. It
just removes the last place to hide the word "interpreter," and with it,
the last reason to believe the question in the first post can be safely
left unasked:

> Whose program is running on your computer right now, and did you agree
> to run it?

## Reproducing

From the repository root:

```
python3 blog/shifting-the-trap/run_proof.py
```

- `bfc.py` — the compiler. The proof object. No yt-dlp dependency.
- `bf.py` — a small Brainfuck macro-assembler, used only to *author* the
  echo and Rule 110 programs correctly. jsinterp never sees it; it only
  ever runs compiled JavaScript.
- `run_proof.py` — compiles each program, runs it on the real
  `yt_dlp.jsinterp`, and checks it against an independent oracle.

To run the same proof against the 2022.04.08 release in a venv:

```
python3 -m venv /tmp/v22
/tmp/v22/bin/pip install 'yt-dlp==2022.04.08'
PYTHONPATH=blog/shifting-the-trap /tmp/v22/bin/python blog/shifting-the-trap/run_proof.py
```

## Acknowledgments

Jacob K read a draft of this post and made three corrections, all of
which improved it. First: an aside about Brainfuck self-interpretation —
since Brainfuck is Turing-complete one can write a Brainfuck interpreter
in Brainfuck, and so the compiler here implicitly gives a Brainfuck
interpreter on top of jsinterp. Second: my "oldest, most exercised"
phrasing overclaimed, and the receipts were specific (`<` was added in
commit 8f53dc4, string `+` in d108ca1); the empirical 2022.04.08 result
above is the answer to "how old, really?". Third: my claim that the
unary-echo test was a mechanical decision procedure for
Turing-completeness was wrong in the negative direction, as discussed
above.
