# Copyright 2015 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Tests for yapf.subtype_assigner."""

import textwrap
import unittest

from yapf.yapflib import format_token
from yapf.yapflib import pytree_utils
from yapf.yapflib import subtypes

from yapftests import yapf_test_helper


class SubtypeAssignerTest(yapf_test_helper.YAPFTest):

  def _CheckFormatTokenSubtypes(self, uwlines, list_of_expected):
    """Check that the tokens in the UnwrappedLines have the expected subtypes.

    Args:
      uwlines: list of UnwrappedLine.
      list_of_expected: list of (name, subtype) pairs. Non-semantic tokens are
        filtered out from the expected values.
    """
    actual = []
    for uwl in uwlines:
      filtered_values = [(ft.value, ft.subtypes)
                         for ft in uwl.tokens
                         if ft.name not in pytree_utils.NONSEMANTIC_TOKENS]
      if filtered_values:
        actual.append(filtered_values)

    self.assertEqual(list_of_expected, actual)

  def testFuncDefDefaultAssign(self):
    self.maxDiff = None  # pylint: disable=invalid-name
    code = textwrap.dedent(r"""
        def foo(a=37, *b, **c):
          return -x[:42]
        """)
    uwlines = yapf_test_helper.ParseAndUnwrap(code)
    self._CheckFormatTokenSubtypes(uwlines, [
        [
            ('def', [subtypes.NONE]),
            ('foo', {subtypes.FUNC_DEF}),
            ('(', {subtypes.NONE}),
            ('a', {
                subtypes.NONE,
                subtypes.DEFAULT_OR_NAMED_ASSIGN_ARG_LIST,
                subtypes.PARAMETER_START,
            }),
            ('=', {
                subtypes.DEFAULT_OR_NAMED_ASSIGN,
                subtypes.DEFAULT_OR_NAMED_ASSIGN_ARG_LIST,
            }),
            ('37', {
                subtypes.NONE,
                subtypes.PARAMETER_STOP,
                subtypes.DEFAULT_OR_NAMED_ASSIGN_ARG_LIST,
            }),
            (',', {subtypes.NONE}),
            ('*', {
                subtypes.PARAMETER_START,
                subtypes.VARARGS_STAR,
                subtypes.DEFAULT_OR_NAMED_ASSIGN_ARG_LIST,
            }),
            ('b', {
                subtypes.NONE,
                subtypes.PARAMETER_STOP,
                subtypes.DEFAULT_OR_NAMED_ASSIGN_ARG_LIST,
            }),
            (',', {subtypes.NONE}),
            ('**', {
                subtypes.PARAMETER_START,
                subtypes.KWARGS_STAR_STAR,
                subtypes.DEFAULT_OR_NAMED_ASSIGN_ARG_LIST,
            }),
            ('c', {
                subtypes.NONE,
                subtypes.PARAMETER_STOP,
                subtypes.DEFAULT_OR_NAMED_ASSIGN_ARG_LIST,
            }),
            (')', {subtypes.NONE}),
            (':', [subtypes.NONE]),
        ],
        [
            ('return', [subtypes.NONE]),
            ('-', {subtypes.UNARY_OPERATOR}),
            ('x', [subtypes.NONE]),
            ('[', {subtypes.SUBSCRIPT_BRACKET}),
            (':', {subtypes.SUBSCRIPT_COLON}),
            ('42', [subtypes.NONE]),
            (']', {subtypes.SUBSCRIPT_BRACKET}),
        ],
    ])

  def testFuncCallWithDefaultAssign(self):
    code = textwrap.dedent(r"""
        foo(x, a='hello world')
        """)
    uwlines = yapf_test_helper.ParseAndUnwrap(code)
    self._CheckFormatTokenSubtypes(uwlines, [
        [
            ('foo', [subtypes.NONE]),
            ('(', [subtypes.NONE]),
            ('x', {
                subtypes.NONE,
                subtypes.DEFAULT_OR_NAMED_ASSIGN_ARG_LIST,
            }),
            (',', {subtypes.NONE}),
            ('a', {
                subtypes.NONE,
                subtypes.DEFAULT_OR_NAMED_ASSIGN_ARG_LIST,
            }),
            ('=', {subtypes.DEFAULT_OR_NAMED_ASSIGN}),
            ("'hello world'", {subtypes.NONE}),
            (')', [subtypes.NONE]),
        ],
    ])

  def testSetComprehension(self):
    code = textwrap.dedent("""\
        def foo(strs):
          return {s.lower() for s in strs}
        """)
    uwlines = yapf_test_helper.ParseAndUnwrap(code)
    self._CheckFormatTokenSubtypes(uwlines, [
        [
            ('def', [subtypes.NONE]),
            ('foo', {subtypes.FUNC_DEF}),
            ('(', {subtypes.NONE}),
            ('strs', {
                subtypes.NONE,
                subtypes.PARAMETER_START,
                subtypes.PARAMETER_STOP,
            }),
            (')', {subtypes.NONE}),
            (':', [subtypes.NONE]),
        ],
        [
            ('return', [subtypes.NONE]),
            ('{', [subtypes.NONE]),
            ('s', {subtypes.COMP_EXPR}),
            ('.', {subtypes.COMP_EXPR}),
            ('lower', {subtypes.COMP_EXPR}),
            ('(', {subtypes.COMP_EXPR}),
            (')', {subtypes.COMP_EXPR}),
            ('for', {
                subtypes.DICT_SET_GENERATOR,
                subtypes.COMP_FOR,
            }),
            ('s', {subtypes.COMP_FOR}),
            ('in', {subtypes.COMP_FOR}),
            ('strs', {subtypes.COMP_FOR}),
            ('}', [subtypes.NONE]),
        ],
    ])

  def testUnaryNotOperator(self):
    code = textwrap.dedent("""\
        not a
        """)
    uwlines = yapf_test_helper.ParseAndUnwrap(code)
    self._CheckFormatTokenSubtypes(uwlines,
                                   [[('not', {subtypes.UNARY_OPERATOR}),
                                     ('a', [subtypes.NONE])]])

  def testBitwiseOperators(self):
    code = textwrap.dedent("""\
        x = ((a | (b ^ 3) & c) << 3) >> 1
        """)
    uwlines = yapf_test_helper.ParseAndUnwrap(code)
    self._CheckFormatTokenSubtypes(uwlines, [
        [
            ('x', [subtypes.NONE]),
            ('=', {subtypes.ASSIGN_OPERATOR}),
            ('(', [subtypes.NONE]),
            ('(', [subtypes.NONE]),
            ('a', [subtypes.NONE]),
            ('|', {subtypes.BINARY_OPERATOR}),
            ('(', [subtypes.NONE]),
            ('b', [subtypes.NONE]),
            ('^', {subtypes.BINARY_OPERATOR}),
            ('3', [subtypes.NONE]),
            (')', [subtypes.NONE]),
            ('&', {subtypes.BINARY_OPERATOR}),
            ('c', [subtypes.NONE]),
            (')', [subtypes.NONE]),
            ('<<', {subtypes.BINARY_OPERATOR}),
            ('3', [subtypes.NONE]),
            (')', [subtypes.NONE]),
            ('>>', {subtypes.BINARY_OPERATOR}),
            ('1', [subtypes.NONE]),
        ],
    ])

  def testArithmeticOperators(self):
    code = textwrap.dedent("""\
        x = ((a + (b - 3) * (1 % c) @ d) / 3) // 1
        """)
    uwlines = yapf_test_helper.ParseAndUnwrap(code)
    self._CheckFormatTokenSubtypes(uwlines, [
        [
            ('x', [subtypes.NONE]),
            ('=', {subtypes.ASSIGN_OPERATOR}),
            ('(', [subtypes.NONE]),
            ('(', [subtypes.NONE]),
            ('a', [subtypes.NONE]),
            ('+', {subtypes.BINARY_OPERATOR}),
            ('(', [subtypes.NONE]),
            ('b', [subtypes.NONE]),
            ('-', {
                subtypes.BINARY_OPERATOR,
                subtypes.SIMPLE_EXPRESSION,
            }),
            ('3', [subtypes.NONE]),
            (')', [subtypes.NONE]),
            ('*', {subtypes.BINARY_OPERATOR}),
            ('(', [subtypes.NONE]),
            ('1', [subtypes.NONE]),
            ('%', {
                subtypes.BINARY_OPERATOR,
                subtypes.SIMPLE_EXPRESSION,
            }),
            ('c', [subtypes.NONE]),
            (')', [subtypes.NONE]),
            ('@', {subtypes.BINARY_OPERATOR}),
            ('d', [subtypes.NONE]),
            (')', [subtypes.NONE]),
            ('/', {subtypes.BINARY_OPERATOR}),
            ('3', [subtypes.NONE]),
            (')', [subtypes.NONE]),
            ('//', {subtypes.BINARY_OPERATOR}),
            ('1', [subtypes.NONE]),
        ],
    ])

  def testSubscriptColon(self):
    code = textwrap.dedent("""\
        x[0:42:1]
        """)
    uwlines = yapf_test_helper.ParseAndUnwrap(code)
    self._CheckFormatTokenSubtypes(uwlines, [
        [
            ('x', [subtypes.NONE]),
            ('[', {subtypes.SUBSCRIPT_BRACKET}),
            ('0', [subtypes.NONE]),
            (':', {subtypes.SUBSCRIPT_COLON}),
            ('42', [subtypes.NONE]),
            (':', {subtypes.SUBSCRIPT_COLON}),
            ('1', [subtypes.NONE]),
            (']', {subtypes.SUBSCRIPT_BRACKET}),
        ],
    ])

  def testFunctionCallWithStarExpression(self):
    code = textwrap.dedent("""\
        [a, *b]
        """)
    uwlines = yapf_test_helper.ParseAndUnwrap(code)
    self._CheckFormatTokenSubtypes(uwlines, [
        [
            ('[', [subtypes.NONE]),
            ('a', [subtypes.NONE]),
            (',', [subtypes.NONE]),
            ('*', {
                subtypes.UNARY_OPERATOR,
                subtypes.VARARGS_STAR,
            }),
            ('b', [subtypes.NONE]),
            (']', [subtypes.NONE]),
        ],
    ])


if __name__ == '__main__':
  unittest.main()
