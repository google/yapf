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
"""PEP 701 regression tests; new syntax stays in string fixtures.

Native AST comparisons run on Python 3.12 and newer.
"""

import ast
import io
import sys
import unittest

from yapf_third_party._ylib2to3.pgen2 import token
from yapf_third_party._ylib2to3.pgen2 import tokenize

from yapf.yapflib.yapf_api import FormatCode


class Pep701Test(unittest.TestCase):

  def assertFormatting(self, source, expected=None, style='pep8'):
    result, _ = FormatCode(source, style_config=style)
    if expected is not None:
      self.assertEqual(expected, result)
    again, changed = FormatCode(result, style_config=style)
    self.assertEqual(result, again)
    self.assertFalse(changed)
    if sys.version_info >= (3, 12):
      self.assertEqual(
          ast.dump(ast.parse(source, feature_version=(3, 12))),
          ast.dump(ast.parse(result, feature_version=(3, 12))))
    return result

  def testFStringSourceIsPreserved(self):
    literals = [
        'f"{data["key"]}"',
        "f'{data['key']}'",
        'f"{f"{f"{value}"}"}"',
        'f"{"\\n".join(items)}"',
        'f"{value # quotes " and } are part of this comment\n}"',
        'f"{value + \\\nother}"',
        'f"{value\n}"',
        'f"{value  =  !r}"',
        'f"{value:{width # ignored }\n}.{precision}f}"',
        'f"""{data["""key"""]}"""',
        'rf"{{literal}} {data["key"]}"',
        'f"\\N{LEFT CURLY BRACKET}{value}"',
    ]
    for literal in literals:
      with self.subTest(literal=literal):
        source = 'result=' + literal + '\n'
        self.assertFormatting(source, 'result = ' + literal + '\n')
        tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
        self.assertEqual([literal],
                         [t[1] for t in tokens if t[0] == token.STRING])

  def testMultilineFStringFollowedByCode(self):
    source = 'result=f"{value # field\n}";other=1\n'
    result = self.assertFormatting(source)
    self.assertIn('f"{value # field\n}"', result)
    self.assertIn('other = 1', result)
    source = ('result = [f"{value # field\n}",f"{data["key"]}"]\n'
              'following=2\n')
    result = self.assertFormatting(source)
    self.assertIn('following = 2', result)

  def testFStringTokenPositions(self):
    source = 'result = f"{value # comment\n}"; after = 1\n'
    tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
    literal = next(t for t in tokens if t[0] == token.STRING)
    self.assertEqual((1, 9), literal[2])
    self.assertEqual((2, 2), literal[3])
    semicolon = next(t for t in tokens if t[1] == ';')
    self.assertEqual((2, 2), semicolon[2])

  def testMultilineStringRangeFormatting(self):
    literals = [
        'f"{value # comment\n}"',
        'f"""value={value}\n"""',
        '"""line\ncontinued"""',
        "'line\\\ncontinued'",
    ]
    for literal in literals:
      source = 'before=1\nresult=' + literal + '\nafter=2\n'
      expected = 'before=1\nresult = ' + literal + '\nafter=2\n'
      for selected_line in (2, 3):
        with self.subTest(literal=literal, selected_line=selected_line):
          result, changed = FormatCode(
              source,
              style_config='pep8',
              lines=[(selected_line, selected_line)])
          self.assertEqual(expected, result)
          self.assertTrue(changed)
          again, changed = FormatCode(
              result,
              style_config='pep8',
              lines=[(selected_line, selected_line)])
          self.assertEqual(result, again)
          self.assertFalse(changed)

  def testCrLfTokenPositions(self):
    source = 'result = f"{value # comment\r\n}"; after = 1\r\n'
    tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
    literal = next(t for t in tokens if t[0] == token.STRING)
    self.assertEqual('f"{value # comment\r\n}"', literal[1])
    self.assertEqual((1, 9), literal[2])
    self.assertEqual((2, 2), literal[3])
    self.assertEqual(source, literal[4])
    semicolon = next(t for t in tokens if t[1] == ';')
    self.assertEqual((2, 2), semicolon[2])

  def testMalformedFStringRaisesTokenError(self):
    for source in [
        'f"{value', 'f"{(value]}"', 'f"}"', 'f"{value # missing newline'
    ]:
      with self.subTest(source=source):
        with self.assertRaises(tokenize.TokenError):
          list(tokenize.generate_tokens(io.StringIO(source).readline))


if __name__ == '__main__':
  unittest.main()
