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
"""Regression coverage for PEP 810, including exact output and stability."""

import ast
import sys
import unittest
from yapf_third_party._ylib2to3 import pytree
from yapf_third_party._ylib2to3.pgen2 import token

from yapf.yapflib import format_token

from yapf.yapflib import errors
from yapf.yapflib.yapf_api import FormatCode


class Pep810Test(unittest.TestCase):

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

  def testLazyImportForms(self):
    cases = [
        ('lazy import json\n', 'lazy import json\n'),
        ('lazy import a.b as c,d.e as f\n', 'lazy import a.b as c, d.e as f\n'),
        ('lazy from package import one as first,two\n',
         'lazy from package import one as first, two\n'),
        ('lazy from ..package import one,two\n',
         'lazy from ..package import one, two\n'),
        ('lazy from . import one,two\n', 'lazy from . import one, two\n'),
        ('lazy import lazy as lazy\n', 'lazy import lazy as lazy\n'),
        ('lazy from lazy import lazy as lazy\n',
         'lazy from lazy import lazy as lazy\n'),
    ]
    for source, expected in cases:
      with self.subTest(source=source):
        self.assertFormatting(source, expected)

  def testSoftKeywordIsStillAnIdentifier(self):
    sources = [
        'lazy=1\n',
        'lazy(lazy=1)\n',
        'obj.lazy()\n',
        'obj.lazy[0]=lazy\n',
        'def lazy(lazy):\n return lazy\n',
        'class lazy:\n pass\n',
        'from lazy import lazy as lazy\n',
        'match value:\n case {"lazy":lazy}:\n  print(lazy)\n',
        'lazy: Callable=other\n',
    ]
    for source in sources:
      with self.subTest(source=source):
        result = self.assertFormatting(source)
        if sys.version_info >= (3, 10):
          self.assertEqual(
              ast.dump(ast.parse(source)), ast.dump(ast.parse(result)))
    leaf = pytree.Leaf(token.NAME, 'lazy')
    self.assertFalse(format_token.FormatToken(leaf, 'NAME').is_keyword)

  def testParenthesizedImportsAndComments(self):
    sources = [
        'lazy from package import (first,second,third,)\n',
        'lazy from package import (\n first, # retained\n second,\n)\n',
        'lazy import package # retained\n',
        'lazy from package import first, \\\n second\n',
    ]
    for source in sources:
      for name in ('pep8', 'google', 'yapf', 'facebook'):
        with self.subTest(source=source, style=name):
          result = self.assertFormatting(
              source,
              style={
                  'BASED_ON_STYLE': name,
                  'COLUMN_LIMIT': 30,
                  'DEDENT_CLOSING_BRACKETS': True
              })
          if '# retained' in source:
            self.assertIn('# retained', result)

  def testMixedEagerLazyAndGuardedImports(self):
    sources = [
        'import sys\nlazy import json\nfrom os import path\n'
        'lazy from collections import Counter\n',
        'if enabled:\n lazy import json\nelse:\n import json\n',
        'if TYPE_CHECKING:\n lazy from package import Something\n',
        'lazy import json;lazy import re\n',
    ]
    for source in sources:
      with self.subTest(source=source):
        self.assertFormatting(source)

  def testTopLevelImportVariableSpacing(self):
    custom = {'BLANK_LINES_BETWEEN_TOP_LEVEL_IMPORTS_AND_VARIABLES': 2}
    for keyword in ('import json', 'from json import dumps', 'lazy import json',
                    'lazy from json import dumps'):
      self.assertFormatting(
          keyword + '\nvalue=1\n', keyword + '\n\n\nvalue = 1\n', style=custom)
    # An ordinary name must not become an import just because it is spelled lazy.
    self.assertFormatting(
        'lazy=1\nvalue=2\n', 'lazy = 1\nvalue = 2\n', style=custom)

  def testDocstringsAndDefinitions(self):
    for declaration in ('def f():\n pass\n', 'class C:\n pass\n'):
      source = '"""Documentation."""\nlazy import json\n' + declaration
      result = self.assertFormatting(source)
      self.assertIn('lazy import json\n\n\n', result)

  def testIncompleteLazyImportsAreRejected(self):
    for source in ('lazy import\n', 'lazy from json\n',
                   'lazy from json import\n', 'lazy lazy import json\n'):
      with self.subTest(source=source):
        with self.assertRaises(errors.YapfError):
          FormatCode(source)

  @unittest.skipUnless(sys.version_info >= (3, 15), 'requires Python 3.15')
  def testNativeLazyImportFlagIsPreserved(self):
    source = 'lazy import json\nlazy from collections import Counter\n'
    output = self.assertFormatting(source)
    for node in ast.parse(output).body:
      self.assertTrue(node.is_lazy)


if __name__ == '__main__':
  unittest.main()
