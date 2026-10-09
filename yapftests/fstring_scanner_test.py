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
"""Lossless scanner tests, independent of YAPF's formatter implementation."""

import ast
import io
import itertools
import random
import sys
import unittest
import warnings

from yapf_third_party._ylib2to3.pgen2 import fstring

_CASES = [
    'f"{data["key"]}"',
    "f'{data['key']}'",
    'f"{f"{f"{f"{f"{1 + 1}"}"}"}"}"',
    'f"{x # outer quote \" and } are ignored\n}"',
    'f"{x\n}"',
    'f"{(x\n + y)}"',
    'f"{\"\\n\".join(items)}"',
    'f"{x + \\\n y}"',
    'f"{(lambda x: x + 1)(2)}"',
    'f"{ {\"k\": \"v\"}[\"k\"] }"',
    'f"{[x for x in values]}"',
    'f"{(value := 2)}"',
    'f"{value!r:>{width}}"',
    'f"{value = !r:>{width}}"',
    'f"{value:{{}}}"',
    'f"{value:}}}"',
    'f"{value:\\N{LEFT CURLY BRACKET}}"',
    'f"\\N{LEFT CURLY BRACKET} {value}"',
    'fr"\\N{value}"',
    'f"\\{value}"',
    'f"{{escaped}} {value}"',
    'f"\\\\{value}"',
    'f"a\\\nb{value}"',
    'f"{\"\"\"inside\ntriple\"\"\"}"',
    'f"""{value:\n>10}"""',
    'f"""{data["""key"""]}"""',
    'f"{value:{width # ignored \" }\n}}"',
    'f"{value:{f"{width}"}}"',
    'f"{await foo()}"',
    'f"{(yield value)}"',
    'f"{(x async for x in y)}"',
    'f"{ {x:y for x,y in z} }"',
    'f"{data[1:2]}"',
    'f"{value != other}"',
]
for prefix, quote, body in itertools.product(
    ['f', 'F', 'fr', 'fR', 'Fr', 'FR', 'rf', 'rF', 'Rf', 'RF'],
    ['"', "'", '"""', "'''"], [
        '', 'text', '{{}}', '{{{value}}}', '{value!r}', '{value=}',
        '{value:>{width}}', '{ {1:2} }', '{value:{width:{precision}}}'
    ]):
  _CASES.append(prefix + quote + body + quote)


class FStringScannerTest(unittest.TestCase):

  def checkLiteral(self, literal, newline='\n'):
    if sys.version_info >= (3, 12):
      with warnings.catch_warnings():
        warnings.simplefilter('ignore', SyntaxWarning)
        ast.parse(literal)
    source = 'value = ' + literal + '; after = 1' + newline
    reader = io.StringIO(source).readline
    first = reader()
    value, end, last_line, physical = fstring.scan_fstring(reader, first, 1, 8)
    self.assertEqual(literal, value)
    column = (8 + len(literal) if '\n' not in literal else len(
        literal.rsplit('\n', 1)[1]))
    self.assertEqual((literal.count('\n') + 1, column), end)
    self.assertEqual('; after = 1' + newline, last_line[end[1]:])
    self.assertEqual(source, physical)
    self.assertEqual('', reader())

  def testFixedAndPrefixMatrix(self):
    for literal in _CASES:
      with self.subTest(literal=literal):
        self.checkLiteral(literal)

  def testCrLf(self):
    for literal in _CASES:
      if '\n' in literal:
        with self.subTest(literal=literal):
          self.checkLiteral(literal.replace('\n', '\r\n'), '\r\n')

  def testDoesNotReadAhead(self):
    literal = 'f"{data["key"]}"'

    def unexpectedRead():
      self.fail('readline called after the literal already ended')

    value, end, last, physical = fstring.scan_fstring(unexpectedRead, literal,
                                                      1, 0)
    self.assertEqual(literal, value)
    self.assertEqual((1, len(literal)), end)
    self.assertEqual(literal, last)
    self.assertEqual(literal, physical)

  def testStopIterationReader(self):
    literal = 'f"{value # comment\n}"'
    lines = iter(literal.splitlines(keepends=True))
    first = next(lines)
    value, _, _, _ = fstring.scan_fstring(lines.__next__, first, 5, 0)
    self.assertEqual(literal, value)
    with self.assertRaises(fstring.FStringError):
      fstring.scan_fstring(iter(()).__next__, 'f"{value', 1, 0)

  def testMalformedLexicalContexts(self):
    literals = [
        'f"{x', 'f"abc', 'f"}"', 'f"{(x]}"', 'f"{x # no newline', 'f"{x:\n}"',
        'f"line\nbreak"', 'f"\\N{no closing brace', 'f"{x:\">10}"'
    ]
    for literal in literals:
      with self.subTest(literal=literal):
        with self.assertRaises(fstring.FStringError):
          fstring.scan_fstring(io.StringIO('').readline, literal, 1, 0)

  @unittest.skipUnless(sys.version_info >= (3, 12), 'requires a PEP 701 oracle')
  def testGeneratedNativeValidLiterals(self):
    rng = random.Random(701)
    expressions = [
        'value',
        'data["key"]',
        "data['key']",
        '"\\n".join(items)',
        '(lambda x: x + 1)(2)',
        '(a := value)',
        '[x for x in y]',
        '{"key": "value"}',
        'value\n',
        'value # comment } "\n',
        '\"\"\"embedded\nstring\"\"\"',
        'f"{value}"',
        'f"{value["key"]}"',
        'value + \\\nother',
        'data[1:2]',
    ]
    valid = 0
    for _ in range(3000):
      prefix = rng.choice(['f', 'F', 'rf', 'FR'])
      quote = rng.choice(['"', "'", '\"\"\"', "\'\'\'"])
      parts = []
      for _ in range(rng.randrange(1, 6)):
        parts.append(rng.choice(['text', '{{escaped}}', '']))
        expr = rng.choice(expressions)
        conversion = rng.choice(['', '!r', '!s', '!a'])
        fmt = rng.choice(['', ':>10', ':>{width}', ':{width}.{precision}f'])
        parts.append('{' + expr + conversion + fmt + '}')
      literal = prefix + quote + ''.join(parts) + quote
      try:
        ast.parse(literal)
      except SyntaxError:
        continue
      with self.subTest(literal=literal):
        self.checkLiteral(literal)
      valid += 1
    self.assertGreater(valid, 2000)


if __name__ == '__main__':
  unittest.main()
