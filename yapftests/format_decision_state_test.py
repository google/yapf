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

import textwrap
import unittest

from yapf.pytree import pytree_utils
from yapf.yapflib import format_decision_state
from yapf.yapflib import logical_line
from yapf.yapflib import style

from yapftests import yapf_test_helper


class FormatDecisionStateTest(yapf_test_helper.YAPFTest):

  @classmethod
  def setUpClass(cls):
    style.SetGlobalStyle(style.CreateYapfStyle())

  def testSimpleFunctionDefWithNoSplitting(self):
    code = textwrap.dedent("""\
        def f(a, b):
          pass
    """)
    llines = yapf_test_helper.ParseAndUnwrap(code)
    lline = logical_line.LogicalLine(0, _FilterLine(llines[0]))
    lline.CalculateFormattingInformation()

    # Add: 'f'
    state = format_decision_state.FormatDecisionState(lline, 0)
    state.MoveStateToNextToken()
    self.assertEqual('f', state.next_token.value)
    self.assertFalse(state.CanSplit(False))

    # Add: '('
    state.AddTokenToState(False, True)
    self.assertEqual('(', state.next_token.value)
    self.assertFalse(state.CanSplit(False))
    self.assertFalse(state.MustSplit())

    # Add: 'a'
    state.AddTokenToState(False, True)
    self.assertEqual('a', state.next_token.value)
    self.assertTrue(state.CanSplit(False))
    self.assertFalse(state.MustSplit())

    # Add: ','
    state.AddTokenToState(False, True)
    self.assertEqual(',', state.next_token.value)
    self.assertFalse(state.CanSplit(False))
    self.assertFalse(state.MustSplit())

    # Add: 'b'
    state.AddTokenToState(False, True)
    self.assertEqual('b', state.next_token.value)
    self.assertTrue(state.CanSplit(False))
    self.assertFalse(state.MustSplit())

    # Add: ')'
    state.AddTokenToState(False, True)
    self.assertEqual(')', state.next_token.value)
    self.assertTrue(state.CanSplit(False))
    self.assertFalse(state.MustSplit())

    # Add: ':'
    state.AddTokenToState(False, True)
    self.assertEqual(':', state.next_token.value)
    self.assertFalse(state.CanSplit(False))
    self.assertFalse(state.MustSplit())

    clone = state.Clone()
    self.assertEqual(repr(state), repr(clone))

  def testSimpleFunctionDefWithSplitting(self):
    code = textwrap.dedent("""\
        def f(a, b):
          pass
    """)
    llines = yapf_test_helper.ParseAndUnwrap(code)
    lline = logical_line.LogicalLine(0, _FilterLine(llines[0]))
    lline.CalculateFormattingInformation()

    # Add: 'f'
    state = format_decision_state.FormatDecisionState(lline, 0)
    state.MoveStateToNextToken()
    self.assertEqual('f', state.next_token.value)
    self.assertFalse(state.CanSplit(False))

    # Add: '('
    state.AddTokenToState(True, True)
    self.assertEqual('(', state.next_token.value)
    self.assertFalse(state.CanSplit(False))

    # Add: 'a'
    state.AddTokenToState(True, True)
    self.assertEqual('a', state.next_token.value)
    self.assertTrue(state.CanSplit(False))

    # Add: ','
    state.AddTokenToState(True, True)
    self.assertEqual(',', state.next_token.value)
    self.assertFalse(state.CanSplit(False))

    # Add: 'b'
    state.AddTokenToState(True, True)
    self.assertEqual('b', state.next_token.value)
    self.assertTrue(state.CanSplit(False))

    # Add: ')'
    state.AddTokenToState(True, True)
    self.assertEqual(')', state.next_token.value)
    self.assertTrue(state.CanSplit(False))

    # Add: ':'
    state.AddTokenToState(True, True)
    self.assertEqual(':', state.next_token.value)
    self.assertFalse(state.CanSplit(False))

    clone = state.Clone()
    self.assertEqual(repr(state), repr(clone))


def _FilterLine(lline):
  """Filter out nonsemantic tokens from the LogicalLines."""
  return [
      ft for ft in lline.tokens
      if ft.name not in pytree_utils.NONSEMANTIC_TOKENS
  ]


if __name__ == '__main__':
  unittest.main()
