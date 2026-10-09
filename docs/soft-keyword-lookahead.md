# Soft-keyword lookahead isolation

The PEP 695 and PEP 810 grammars add the contextual keywords `type` and `lazy`.
That exposed two problems in the existing speculative token reader:

* Nested lookahead could attach tokens to the wrong release record. Valid code
  such as `match(type)` and `match (type):\n case _: pass` then failed to parse.
* Release records survived until the end of the file, and every committed token
  scanned every earlier record. Ordinary repeated `type(value)` calls therefore
  made parsing quadratic rather than linear in the length of the token stream.

`TokenProxy` now uses one absolute-position buffer for unread tokens and a stack
of independent speculative cursors. Nested routes start immediately after the
parent's currently observed token. Exiting a route restores its parent without
consuming input. Committed tokens are removed from the buffer immediately.
This bounds token storage by outstanding lookahead rather than by the number of
soft keywords already parsed, and makes buffered token access constant-time.
The parser's existing grammar-selection algorithm is unchanged.

Tests cover replay, competing and nested routes, exceptions, end of input,
negative offsets, prompt removal of consumed tokens, and AST-preserving
formatting of ambiguous calls, subscripts, and match subjects. Buffer lifetime
is asserted structurally rather than with a machine-dependent timing threshold.
The implementation and tests remain compatible with YAPF's Python 3.7 minimum;
native AST comparisons for match statements require Python 3.10 or later.

```bash
PYTHONPATH=third_party:. python -m unittest yapftests.token_proxy_test
```
