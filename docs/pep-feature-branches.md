# PEP feature branches

All changes are based on the uploaded repository at
`12005095296072751e3e4c1f33a047d41b0ce18d`. `main` is unchanged.

| Branch | Prerequisite |
| --- | --- |
| `fix/grammar-cache-isolation-20261009` | Original `main` |
| `fix/soft-keyword-lookahead-20261009` | Cache isolation |
| `feature/pep-695-type-parameters-20261009` | Cache isolation + lookahead |
| `feature/pep-696-type-defaults-20261009` | PEP 695 |
| `feature/pep-701-fstrings-20261009` | Cache isolation + lookahead |
| `feature/pep-750-template-strings-20261009` | PEP 701 |
| `feature/pep-758-exception-lists-20261009` | Cache isolation + lookahead |
| `feature/pep-798-unpacking-comprehensions-20261009` | Cache isolation + lookahead |
| `feature/pep-810-lazy-imports-20261009` | Cache isolation + lookahead |
| `feature/python-syntax-integration-20261009` | Merges all seven PEP branches |

Each PEP branch has its own implementation, regression tests, and notes. The
integration branch retains merge ancestry, combines the two contextual keyword
checks in `FormatToken.is_keyword`, adds cross-feature tests, and extends CI/tox
coverage through Python 3.15. It does not squash or replace the feature branches.
For isolated reviews, target PEP 696 at PEP 695, and PEP 750 at PEP 701.

## Review follow-up

The original feature commits are retained. Every PEP branch now also includes
`fix/soft-keyword-lookahead-20261009`, which reimplements the shared token buffer
to fix nested speculative parsing and quadratic scanning of old release records.
The new `type` and `lazy` soft keywords exposed those defects: for example,
`match(type)` parsed on original `main` but failed after the PEP additions.
Nine regression test methods cover stream invariants and 68 syntax subcases.
See [the lookahead design note](soft-keyword-lookahead.md).

No PEP grammar or interpolation scanner was replaced merely for stylistic reasons.
The reviewed integration preserves the original seven implementation branches,
and the follow-up commits are fast-forward descendants of their prior heads.

The shared cache fix fingerprints the grammar source. Without it, checkouts with
the same YAPF/interpreter version can reuse a different branch's cached grammar.

## Validation

Local execution uses CPython 3.13.5 on Linux. Formatter tests run on every host;
native AST comparisons and native semantic tests for newer syntax run only when
the interpreter supports it. Python 3.12/3.14/3.15 downloads were unavailable in
the implementation environment. CI configuration is supplied but was not run on
GitHub; Windows and macOS are not locally validated.

```bash
PYTHONPATH=third_party:. python -m unittest discover -p '*_test.py' yapftests/
```

This is syntax-formatting support, not type checking or complete compiler
validation. F-string and t-string interiors are preserved, not reformatted.
Long unparenthesized exception lists remain on one physical line. The separate
Unicode-identifier limitation from the earlier audit is not addressed by these
PEP branches. See each PEP's implementation note for scope details.
