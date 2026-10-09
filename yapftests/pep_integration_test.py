# Copyright 2026 The YAPF Authors. All Rights Reserved.
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
"""Regression coverage for the combined PEP features, including exact output and stability."""

import ast
import sys
import unittest

from yapf.yapflib.yapf_api import FormatCode


class PepIntegrationTest(unittest.TestCase):

  def assertFormatting(self, source, expected=None, style='pep8'):
    result, _ = FormatCode(source, style_config=style)
    if expected is not None:
      self.assertEqual(expected, result)
    again, changed = FormatCode(result, style_config=style)
    self.assertEqual(result, again)
    self.assertFalse(changed)
    if sys.version_info >= (3, 15):
      self.assertEqual(ast.dump(ast.parse(source)), ast.dump(ast.parse(result)))
    return result

  def testFeaturesComposeInTheSameModule(self):
    sources = [
        'lazy from collections.abc import Iterable\n'
        'def flatten[T=int](groups:Iterable[list[T]])->tuple[T,...]:\n'
        ' return tuple(*items for items in groups)\n',
        'type Message[T=int]=tuple[T,str]\nlazy import json\n'
        'result=t"{data["name"]}"\n',
        'try:\n result=tuple(*items for items in groups)\n'
        'except* ValueError,TypeError,RuntimeError:\n'
        ' error=t"{info["reason"]}"\n',
        'lazy from types import SimpleNamespace\n'
        'class Collection[T=int](Base[T]):\n'
        ' type Member[U=str]=tuple[T,U]\n'
        ' def render(self):\n  return t"{self.values["first"]}"\n',
        'type Alias[T=type(t"payload")]=list[T]\n',
        'result=t"{[*items for items in groups]}"\n',
    ]
    for source in sources:
      for name in ('pep8', 'google', 'yapf', 'facebook'):
        for limit in (32, 79):
          with self.subTest(source=source, style=name, limit=limit):
            self.assertFormatting(
                source,
                style={
                    'BASED_ON_STYLE': name,
                    'COLUMN_LIMIT': limit,
                    'DEDENT_CLOSING_BRACKETS': True
                })

  def testSoftKeywordsDoNotInterfere(self):
    sources = [
        'def lazy[type=int](lazy:type)->type:\n return lazy\n',
        'type lazy[type=int]=list[type]\n',
        'lazy from lazy import type as lazy\n',
        'type type[lazy=int]=list[lazy]\n',
        'lazy(lambda type:type,lazy=type)\n',
    ]
    for source in sources:
      with self.subTest(source=source):
        self.assertFormatting(source)

  def testRangeFormattingAcrossNewSyntax(self):
    source = ('type Alias[T=int]=list[T]\nresult=t"{value # field\n}"\n'
              'lazy  import json\n')
    expected = ('type Alias[T=int]=list[T]\nresult = t"{value # field\n}"\n'
                'lazy  import json\n')
    self.assertEqual((expected, True), FormatCode(source, lines=[(3, 3)]))
    self.assertEqual((expected, False), FormatCode(expected, lines=[(3, 3)]))

  def testDisabledRegionKeepsNewSyntaxVerbatim(self):
    prefix = ('# yapf: disable\ntype Alias[T=int]=list[T]\n'
              'result=t"{data["key"]}"\n# yapf: enable\n')
    source = prefix + 'lazy  import json\n'
    expected = prefix + 'lazy import json\n'
    self.assertFormatting(source, expected)

  def testDiffOutputAndFileName(self):
    source = 'type Alias[T=int]=list[T]\nvalue=t"{data["key"]}"\n'
    diff, changed = FormatCode(
        source, filename='new_syntax.py', print_diff=True)
    self.assertTrue(changed)
    self.assertIn('new_syntax.py', diff)
    self.assertIn('+type Alias[T = int] = list[T]', diff)
    self.assertIn('+value = t"{data["key"]}"', diff)


if __name__ == '__main__':
  unittest.main()
