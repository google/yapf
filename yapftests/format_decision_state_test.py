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
"""Tests for yapf.format_decision_state."""

import sys
import textwrap
import unittest

from yapf.yapflib import comment_splicer
from yapf.yapflib import format_decision_state
from yapf.yapflib import pytree_unwrapper
from yapf.yapflib import pytree_utils
from yapf.yapflib import pytree_visitor
from yapf.yapflib import split_penalty
from yapf.yapflib import subtype_assigner
from yapf.yapflib import unwrapped_line


class FormatDecisionStateTest(unittest.TestCase):

  def _ParseAndUnwrap(self, code, dumptree=False):
    """Produces unwrapped lines from the given code.

    Parses the code into a tree, performs comment splicing and runs the
    unwrapper.

    Arguments:
      code: code to parse as a string
      dumptree: if True, the parsed pytree (after comment splicing) is dumped
        to stderr. Useful for debugging.

    Returns:
      List of unwrapped lines.
    """
    tree = pytree_utils.ParseCodeToTree(code)
    comment_splicer.SpliceComments(tree)
    subtype_assigner.AssignSubtypes(tree)
    split_penalty.ComputeSplitPenalties(tree)

    if dumptree:
      pytree_visitor.DumpPyTree(tree, target_stream=sys.stderr)

    return pytree_unwrapper.UnwrapPyTree(tree)

  def _FilterLine(self, uwline):
    """Filter out nonsemantic tokens from the UnwrappedLines."""
    return [ft for ft in uwline.tokens
            if ft.name not in pytree_utils.NONSEMANTIC_TOKENS]

  def testSimpleFunctionDefWithNoSplitting(self):
    code = textwrap.dedent(r"""
      def f(a, b):
        pass
      """)
    uwlines = self._ParseAndUnwrap(code)
    uwline = unwrapped_line.UnwrappedLine(0, self._FilterLine(uwlines[0]))
    uwline.CalculateFormattingInformation()

    # Add: 'f'
    state = format_decision_state.FormatDecisionState(uwline, 0)
    self.assertEqual('f', state.next_token.value)
    self.assertFalse(state.CanSplit())

    # Add: '('
    state.AddTokenToState(False, True)
    self.assertEqual('(', state.next_token.value)
    self.assertFalse(state.CanSplit())
    self.assertFalse(state.MustSplit())

    # Add: 'a'
    state.AddTokenToState(False, True)
    self.assertEqual('a', state.next_token.value)
    self.assertTrue(state.CanSplit())
    self.assertFalse(state.MustSplit())

    # Add: ','
    state.AddTokenToState(False, True)
    self.assertEqual(',', state.next_token.value)
    self.assertFalse(state.CanSplit())
    self.assertFalse(state.MustSplit())

    # Add: 'b'
    state.AddTokenToState(False, True)
    self.assertEqual('b', state.next_token.value)
    self.assertTrue(state.CanSplit())
    self.assertFalse(state.MustSplit())

    # Add: ')'
    state.AddTokenToState(False, True)
    self.assertEqual(')', state.next_token.value)
    self.assertTrue(state.CanSplit())
    self.assertFalse(state.MustSplit())

    # Add: ':'
    state.AddTokenToState(False, True)
    self.assertEqual(':', state.next_token.value)
    self.assertFalse(state.CanSplit())
    self.assertFalse(state.MustSplit())

    clone = state.Clone()
    self.assertEqual(repr(state), repr(clone))

  def testSimpleFunctionDefWithSplitting(self):
    code = textwrap.dedent(r"""
      def f(a, b):
        pass
      """)
    uwlines = self._ParseAndUnwrap(code)
    uwline = unwrapped_line.UnwrappedLine(0, self._FilterLine(uwlines[0]))
    uwline.CalculateFormattingInformation()

    # Add: 'f'
    state = format_decision_state.FormatDecisionState(uwline, 0)
    self.assertEqual('f', state.next_token.value)
    self.assertFalse(state.CanSplit())

    # Add: '('
    state.AddTokenToState(True, True)
    self.assertEqual('(', state.next_token.value)
    self.assertFalse(state.CanSplit())

    # Add: 'a'
    state.AddTokenToState(True, True)
    self.assertEqual('a', state.next_token.value)
    self.assertTrue(state.CanSplit())

    # Add: ','
    state.AddTokenToState(True, True)
    self.assertEqual(',', state.next_token.value)
    self.assertFalse(state.CanSplit())

    # Add: 'b'
    state.AddTokenToState(True, True)
    self.assertEqual('b', state.next_token.value)
    self.assertTrue(state.CanSplit())

    # Add: ')'
    state.AddTokenToState(True, True)
    self.assertEqual(')', state.next_token.value)
    self.assertTrue(state.CanSplit())

    # Add: ':'
    state.AddTokenToState(True, True)
    self.assertEqual(':', state.next_token.value)
    self.assertFalse(state.CanSplit())

    clone = state.Clone()
    self.assertEqual(repr(state), repr(clone))


if __name__ == '__main__':
  unittest.main()
