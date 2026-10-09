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
"""Regression coverage for PEP 758, including exact output and stability."""

import ast
import sys
import unittest

from yapf.yapflib import errors
from yapf.yapflib.yapf_api import FormatCode


class Pep758Test(unittest.TestCase):

  def assertFormatting(self, source, expected=None, style='pep8'):
    result, _ = FormatCode(source, style_config=style)
    if expected is not None:
      self.assertEqual(expected, result)
    again, changed = FormatCode(result, style_config=style)
    self.assertEqual(result, again)
    self.assertFalse(changed)
    if sys.version_info >= (3, 14):
      self.assertEqual(ast.dump(ast.parse(source)), ast.dump(ast.parse(result)))
    return result

  def testExceptionListsAndTrailingCommas(self):
    for keyword in ('except', 'except*'):
      for exceptions, expected in (('A,B', 'A, B'), ('A,B,C', 'A, B, C'),
                                   ('A,', 'A,'), ('A,B,C,', 'A, B, C,'),
                                   ('errors.A,get_errors(),B',
                                    'errors.A, get_errors(), B')):
        source = 'try:\n work()\n%s %s:\n pass\n' % (keyword, exceptions)
        target = 'try:\n    work()\n%s %s:\n    pass\n' % (keyword, expected)
        with self.subTest(source=source):
          self.assertFormatting(source, target)

  def testExistingParenthesizedAndBareHandlers(self):
    for handler in ('except:', 'except Exception:',
                    'except Exception as error:', 'except (A, B) as error:',
                    'except* (A, B) as error:'):
      source = 'try:\n work()\n' + handler + '\n pass\n'
      with self.subTest(handler=handler):
        self.assertFormatting(source,
                              'try:\n    work()\n' + handler + '\n    pass\n')

  def testCommentsAndContinuations(self):
    sources = [
        'try:\n work()\nexcept A, \\\n B, C: # retained\n pass\n',
        'try:\n work()\nexcept* A, B, C: # retained\n pass\n',
        'try:\n work()\nexcept (\n A, # retained\n B,\n) as errors:\n pass\n',
    ]
    for source in sources:
      with self.subTest(source=source):
        result = self.assertFormatting(source)
        self.assertIn('# retained', result)

  def testLongListsStaySyntacticallyValid(self):
    for keyword in ('except', 'except*'):
      source = ('try:\n work()\n' + keyword + ' FirstLongExceptionName,'
                'SecondLongExceptionName,ThirdLongExceptionName:\n pass\n')
      for name in ('pep8', 'google', 'yapf', 'facebook'):
        with self.subTest(keyword=keyword, style=name):
          result = self.assertFormatting(
              source, style={
                  'BASED_ON_STYLE': name,
                  'COLUMN_LIMIT': 32
              })
          # Without a bracket pair or explicit continuation, a comma alone
          # cannot introduce a physical newline in an exception clause.
          self.assertIn(
              'FirstLongExceptionName, SecondLongExceptionName, '
              'ThirdLongExceptionName:', result)

  def testMultipleHandlersElseAndFinally(self):
    source = (
        'try:\n work()\nexcept A,B,C:\n handle()\nexcept D,E:\n handle()\n'
        'else:\n success()\nfinally:\n cleanup()\n')
    self.assertFormatting(source)

  def testUnparenthesizedListsCannotBindAnAsTarget(self):
    for keyword in ('except', 'except*'):
      for exceptions in ('A,B', 'A,B,C', 'A,'):
        with self.subTest(keyword=keyword, exceptions=exceptions):
          with self.assertRaises(errors.YapfError):
            FormatCode('try:\n pass\n%s %s as error:\n pass\n' %
                       (keyword, exceptions))

  def testOtherCommaColonSpacingIsUnchanged(self):
    self.assertFormatting('value=items[1,:]\n', 'value = items[1, :]\n')

  @unittest.skipUnless(sys.version_info >= (3, 14), 'requires Python 3.14')
  def testNativeHandlerSemantics(self):
    for keyword, raised in (('except', 'ValueError()'),
                            ('except*',
                             'ExceptionGroup("errors", [ValueError()])')):
      source = ('caught=False\ntry:\n raise %s\n'
                '%s ValueError,TypeError,RuntimeError:\n caught=True\n' %
                (raised, keyword))
      namespace = {}
      exec(self.assertFormatting(source), namespace)
      self.assertTrue(namespace['caught'])


if __name__ == '__main__':
  unittest.main()
