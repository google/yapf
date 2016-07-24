# Copyright 2015-2016 Google Inc. All Rights Reserved.
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
"""Tests for yapf.unwrapped_line."""

import textwrap
import unittest

from lib2to3 import pytree
from lib2to3.pgen2 import token

from yapf.yapflib import comment_splicer
from yapf.yapflib import format_token
from yapf.yapflib import pytree_unwrapper
from yapf.yapflib import pytree_utils
from yapf.yapflib import split_penalty
from yapf.yapflib import subtype_assigner
from yapf.yapflib import unwrapped_line


def _MakeFormatTokenLeaf(token_type, token_value):
  return format_token.FormatToken(pytree.Leaf(token_type, token_value))


def _MakeFormatTokenList(token_type_values):
  return [_MakeFormatTokenLeaf(token_type, token_value)
          for token_type, token_value in token_type_values]


class UnwrappedLineBasicTest(unittest.TestCase):

  def testConstruction(self):
    toks = _MakeFormatTokenList([(token.DOT, '.'), (token.VBAR, '|')])
    uwl = unwrapped_line.UnwrappedLine(20, toks)
    self.assertEqual(20, uwl.depth)
    self.assertEqual(['DOT', 'VBAR'], [tok.name for tok in uwl.tokens])

  def testFirstLast(self):
    toks = _MakeFormatTokenList([(token.DOT, '.'), (token.LPAR, '('),
                                 (token.VBAR, '|')])
    uwl = unwrapped_line.UnwrappedLine(20, toks)
    self.assertEqual(20, uwl.depth)
    self.assertEqual('DOT', uwl.first.name)
    self.assertEqual('VBAR', uwl.last.name)

  def testAsCode(self):
    toks = _MakeFormatTokenList([(token.DOT, '.'), (token.LPAR, '('),
                                 (token.VBAR, '|')])
    uwl = unwrapped_line.UnwrappedLine(2, toks)
    self.assertEqual('    . ( |', uwl.AsCode())

  def testAppendToken(self):
    uwl = unwrapped_line.UnwrappedLine(0)
    uwl.AppendToken(_MakeFormatTokenLeaf(token.LPAR, '('))
    uwl.AppendToken(_MakeFormatTokenLeaf(token.RPAR, ')'))
    self.assertEqual(['LPAR', 'RPAR'], [tok.name for tok in uwl.tokens])

  def testAppendNode(self):
    uwl = unwrapped_line.UnwrappedLine(0)
    uwl.AppendNode(pytree.Leaf(token.LPAR, '('))
    uwl.AppendNode(pytree.Leaf(token.RPAR, ')'))
    self.assertEqual(['LPAR', 'RPAR'], [tok.name for tok in uwl.tokens])


class UnwrappedLineFormattingInformationTest(unittest.TestCase):

  def _ParseAndUnwrap(self, code):
    tree = pytree_utils.ParseCodeToTree(code)
    comment_splicer.SpliceComments(tree)
    subtype_assigner.AssignSubtypes(tree)
    split_penalty.ComputeSplitPenalties(tree)

    uwlines = pytree_unwrapper.UnwrapPyTree(tree)
    for i, uwline in enumerate(uwlines):
      uwlines[i] = unwrapped_line.UnwrappedLine(
          uwline.depth, [ft for ft in uwline.tokens
                         if ft.name not in pytree_utils.NONSEMANTIC_TOKENS])
    return uwlines

  def testFuncDef(self):
    code = textwrap.dedent(r'''
      def f(a, b):
        pass
      ''')
    uwlines = self._ParseAndUnwrap(code)
    uwlines[0].CalculateFormattingInformation()

    f = uwlines[0].tokens[1]
    self.assertFalse(f.can_break_before)
    self.assertFalse(f.must_break_before)
    self.assertEqual(f.split_penalty, split_penalty.UNBREAKABLE)

    lparen = uwlines[0].tokens[2]
    self.assertFalse(lparen.can_break_before)
    self.assertFalse(lparen.must_break_before)
    self.assertEqual(lparen.split_penalty, split_penalty.UNBREAKABLE)


if __name__ == '__main__':
  unittest.main()
