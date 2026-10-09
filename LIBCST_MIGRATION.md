# LibCST migration

## Scope

This branch starts at `main` commit
`12005095296072751e3e4c1f33a047d41b0ce18d`. It ports the existing formatter;
none of the separate PEP implementation or parser-fix branches is merged.
The original main and all pre-existing branch tips remain unchanged.

The formatter retains its layout search and style options. This is not a
rewrite of the style engine or a promise that every syntax construct accepted
by the dependency has a YAPF formatting rule. Type aliases and generic
declarations, for example, are rejected explicitly by the layout adapter.
String interiors stay verbatim. Incidental additional syntax acceptance by
the upstream parser is not a separately implemented language feature.

## Pipeline and ownership

```
source -> libcst.parse_module -> immutable LibCST Module
       -> code-generation emissions + typed-node lowering
       -> mutable YAPF layout groups and formatting tokens
       -> existing annotation passes and line-breaking search -> source
```

`yapf/layout/frontend.py` is the parser-facing boundary. LibCST's code generator
emits the exact spelling of identifiers, literals, comments, whitespace,
keywords, and punctuation. Its fixed punctuation/keyword fragments are split
into layout tokens; arbitrary Python source is never lexed or parsed again.
Required call parentheses and multi-token operators are materialized here.
Literal contents remain opaque. Source positions are character-based, not
byte offsets. Each lowering is checked for exact token identity and order.

Typed LibCST nodes are lowered into semantic layout categories such as call
arguments, arithmetic precedence groups, suites, and parameter lists. These
are not grammar productions: they contain no parsing rules, lookahead,
backtracking, or syntax validation. Unsupported CST nodes fail explicitly.

`tree.py` is a small mutable layout IR: parent/child links, token spelling,
source position, trivia, and formatting annotations. It is not a copy of the
old parser or its pattern matcher. The active comment/continuation,
blank-line, subtype, split-penalty and logical-line passes are retained under
`yapf.layout` because they express existing formatting policy. They operate on
the layout IR, never mutate the LibCST tree, and do not parse Python.

## Removed code

- `third_party/yapf_third_party/_ylib2to3/` in its entirety, including grammars,
  tokenizer, parser generator/driver, pattern matching, and fixers.
- `yapf/pyparser/` and `FormatAST`, the alternate host-AST/tokenize path.
- `yapf/pytree/`, replaced by the parser-independent layout package.
- Legacy parser exceptions, grammar caches, and packaging of grammar files.

The separate `yapf_diff` utility and its license remain in `third_party`.
Standard-library encoding detection still uses `tokenize.detect_encoding`;
that is not a source-parsing fallback.

## Compatibility

`FormatCode` and `FormatFile` retain their signatures and return values. The
CLI, styles, selected-line formatting, disabled regions, diff generation,
encodings and line endings continue to use the existing formatting policy.

`FormatTree` now takes `libcst.Module`; legacy tree objects and ASTs are not
accepted. It never mutates its input and supports constructed modules, even
when immutable node objects are shared between source locations. Parsed
modules normally have unique node identities; only shared-node modules need
a deep clone before lowering. `FormatAST` is removed with no legacy shim.

Parser diagnostics retain filename/line/column but their wording and exact
error position can differ from the previous parser. LibCST rejects some
invalid inputs previously accepted by the permissive Python-2-era grammar.
Three pre-existing fixtures were corrected while preserving their formatting
intent: duplicate bare `except`, a `1000000L` numeric literal, and an
unparenthesized generator followed by a comma. The stdin diagnostic test now
checks the diagnostic location rather than the old parser's wording. No
original test methods were dropped.

One known valid-input regression remains in the dependency: LibCST 1.9.0
rejects `class C(metaclass=M, *bases): pass`, although CPython and the original
YAPF main accept it. Its class node separates bases from keyword arguments and
its parser rejects a starred base after a keyword. This migration reports the
parser error rather than retaining an alternate parser or silently reordering
the header. The test suite records the restriction explicitly; the successful
differential corpus is not a claim of universal input parity.

The runtime minimum is Python 3.9. LibCST includes a native extension: ensure
wheels exist in the package mirror for each interpreter/platform, or arrange
a Rust source-build toolchain. Python 3.9 through 3.14 and the existing OS
matrix are configured for CI; actual executed environments belong in the
validation report, not an implied support claim.

## Dependency contract and source preservation

LibCST is constrained to `>=1.9.0,<1.10`. The emission adapter deliberately uses
one private interface, `libcst._nodes.internal.CodegenState`, and module code
generation hooks. That keeps all implicit punctuation observable without
adding another Python tokenizer. These are not guaranteed-stable public
interfaces. Before changing the dependency range, run the frontend contract
tests, full suites, source/wheel tests, and differential corpus; inspect hook
changes explicitly.

Every source parse must reproduce the normalized input exactly. A directly
reproduced LibCST 1.9.0 bug can drop an indented comment at module EOF:

```python
import libcst
source = "x=1\n # one\n # two\n"
assert libcst.parse_module(source).code == source  # Fails in the supplied 1.9.0 wheel.
```

Only after an otherwise successful but lossy parse, YAPF reparses with a final
`pass` sentinel so EOF comments become leading lines. It removes that exact
sentinel, restores its leading lines as the module footer, and again requires
exact source-text equality. This does not introduce a parser, change
invalid source to valid source, or suppress errors. If recovery is not exact,
formatting fails closed. An externally supplied `FormatTree` module cannot
recover text that was already lost before the caller passed it to YAPF.

## Verification entry points

```bash
python -m pip install .
python -m unittest discover -p '*_test.py' yapftests/
python -m pytest -q yapftests/libcst_frontend_test.py
```

The migration tests cover emission and source positions, implicit punctuation,
multi-token operators, shared-node modules, input immutability, comment
recovery/fail-closed behavior, API/error boundaries, absence of obsolete
packages, representative modern main-era syntax, and unchanged selection and
disabled-region behavior. Existing formatter tests continue to exercise
layout policy. Differential scripts and results are supplied in the external
validation package; they do not ship in the runtime library.
