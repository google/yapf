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
"""Regression coverage for PEP 750, including exact output and stability."""

import ast
import sys
import unittest
import io
import itertools

from yapf_third_party._ylib2to3.pgen2 import token
from yapf_third_party._ylib2to3.pgen2 import tokenize

from yapf.yapflib import errors
from yapf.yapflib.yapf_api import FormatCode


class Pep750Test(unittest.TestCase):

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

  def testPrefixQuoteAndBodyMatrix(self):
    prefixes = ('t', 'T', 'tr', 'tR', 'Tr', 'TR', 'rt', 'rT', 'Rt', 'RT')
    quotes = ('"', "'", '"""', "'" * 3)
    bodies = ('', 'literal', '{{escaped}}', '{name}', '{name=}',
              '{name  =  !r:>{width}}', '{ {1:2} }')
    for prefix, quote, body in itertools.product(prefixes, quotes, bodies):
      literal = prefix + quote + body + quote
      with self.subTest(literal=literal):
        self.assertFormatting('value=' + literal + '\n',
                              'value = ' + literal + '\n')
        tokens = list(tokenize.generate_tokens(io.StringIO(literal).readline))
        self.assertEqual([literal],
                         [t[1] for t in tokens if t[0] == token.STRING])

  def testLexicalContextsAndMixedNesting(self):
    literals = [
        't"{data["key"]}"',
        "t'{data['key']}'",
        't"{t"{value}"}"',
        't"{f"{t"{data["key"]}"}"}"',
        'f"{t"{f"{data["key"]}"}"}"',
        't"{"\\n".join(items)}"',
        't"{value # quote " and } in a comment\n}"',
        't"{value + \\\nother}"',
        't"{value:{width # field\n}.{precision}f}"',
        't"\\N{LEFT CURLY BRACKET}{value}"',
        'rt"\\N{value}"',
        't"""{data["""key"""]}"""',
    ]
    for literal in literals:
      for name in ('pep8', 'google', 'yapf', 'facebook'):
        with self.subTest(literal=literal, style=name):
          result = self.assertFormatting('result=' + literal + '\n', style=name)
          self.assertIn(literal, result)

  def testTemplateConcatenationAndExpressionStatements(self):
    sources = [
        'value=t"hello" t"{name}"\n',
        'value=(t"first"\n # comment\n rt"second {name}")\n',
        't"{value}"\nother=1\n',
        'process(t"{a}",t"{b}")\n',
    ]
    for source in sources:
      with self.subTest(source=source):
        self.assertFormatting(source)

  def testMultilinePositionsAndFollowingTokens(self):
    for newline in ('\n', '\r\n'):
      literal = 't"{value # field' + newline + '}"'
      source = 'result = ' + literal + '; after = 1' + newline
      tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
      string = next(t for t in tokens if t[0] == token.STRING)
      self.assertEqual(literal, string[1])
      self.assertEqual((1, 9), string[2])
      self.assertEqual((2, 2), string[3])
      self.assertEqual(source, string[4])
      semicolon = next(t for t in tokens if t[1] == ';')
      self.assertEqual((2, 2), semicolon[2])
    self.assertFormatting('result=t"{value # field\n}";after=1\n')

  def testInteriorLineSelection(self):
    literal = 't"{value # field\n}"'
    source = 'before=1\nresult=' + literal + '\nafter=2\n'
    expected = 'before=1\nresult = ' + literal + '\nafter=2\n'
    result, changed = FormatCode(source, lines=[(3, 3)])
    self.assertTrue(changed)
    self.assertEqual(expected, result)
    self.assertEqual((expected, False), FormatCode(expected, lines=[(3, 3)]))

  def testIdentifiersAreNotStringPrefixes(self):
    source = 't=1\nT=2\nrt=3\ntr=4\nresult=t+T+rt+tr\n'
    self.assertFormatting(
        source, 't = 1\nT = 2\nrt = 3\ntr = 4\n'
        'result = t + T + rt + tr\n')
    self.assertFormatting('value=t"{target + starter + rt}"\n')

  def testMalformedLexicalContexts(self):
    for literal in ('t"{value', 't"{(value]}"', 't"}"', 't"{x # missing end',
                    't"line\nbreak"'):
      with self.subTest(literal=literal):
        with self.assertRaises(tokenize.TokenError):
          list(tokenize.generate_tokens(io.StringIO(literal).readline))
    for prefix in ('ft', 'tf', 'bt', 'tb', 'ut', 'tu', 'rrt', 'trr'):
      with self.subTest(prefix=prefix):
        with self.assertRaises(errors.YapfError):
          FormatCode('value=' + prefix + '"text"\n')

  @unittest.skipUnless(sys.version_info >= (3, 14), 'requires Python 3.14')
  def testNativeInterpolationMetadataIsPreserved(self):
    source = 'total=6\nmessage=t"{ total + 1   = !r:>{2+1}}"\n'
    formatted = self.assertFormatting(source)
    before, after = {}, {}
    exec(source, before)
    exec(formatted, after)
    left, right = before['message'], after['message']
    self.assertEqual(left.strings, right.strings)
    for a, b in zip(left.interpolations, right.interpolations):
      for attribute in ('value', 'expression', 'conversion', 'format_spec'):
        self.assertEqual(getattr(a, attribute), getattr(b, attribute))


if __name__ == '__main__':
  unittest.main()
