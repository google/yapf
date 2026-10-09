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
"""PEP 695 regression tests; new syntax stays in string fixtures.

Native AST comparisons run on Python 3.12 and newer.
"""

import ast
import sys
import unittest

from yapf_third_party._ylib2to3 import pytree
from yapf_third_party._ylib2to3.pgen2 import token

from yapf.yapflib import format_token
from yapf.yapflib.yapf_api import FormatCode


class Pep695Test(unittest.TestCase):

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

  def testTypeAliases(self):
    cases = [
        ('type Alias=int\n', 'type Alias = int\n'),
        ('type Vector[T]=list[T]\n', 'type Vector[T] = list[T]\n'),
        ('type Pair[T,U]=tuple[T,U]\n', 'type Pair[T, U] = tuple[T, U]\n'),
        ('type Bounded[T:int]=list[T]\n', 'type Bounded[T: int] = list[T]\n'),
        ('type Constrained[T:(str,bytes)]=list[T]\n',
         'type Constrained[T: (str, bytes)] = list[T]\n'),
        ('type Shape[* Ts]=tuple[* Ts]\n', 'type Shape[*Ts] = tuple[*Ts]\n'),
        ('type Callback[** P]=Callable[P,int]\n',
         'type Callback[**P] = Callable[P, int]\n'),
        ('type type[T]=tuple[T,type]\n', 'type type[T] = tuple[T, type]\n'),
    ]
    for source, expected in cases:
      with self.subTest(source=source):
        self.assertFormatting(source, expected)

  def testGenericDefinitions(self):
    cases = [
        ('def identity[T](value:T)->T:\n return value\n',
         'def identity[T](value: T) -> T:\n    return value\n'),
        ('async def identity[T](value:T)->T:\n return value\n',
         'async def identity[T](value: T) -> T:\n    return value\n'),
        ('class Box[T]:\n pass\n', 'class Box[T]:\n    pass\n'),
        ('class Box[T](Base[T]):\n pass\n',
         'class Box[T](Base[T]):\n    pass\n'),
        ('def pack[T,* Ts,** P](value:T,*args: *Ts,**kwargs:P.kwargs):\n'
         ' return value\n',
         'def pack[T, *Ts, **P](value: T, *args: *Ts, **kwargs: P.kwargs):\n'
         '    return value\n'),
    ]
    for source, expected in cases:
      with self.subTest(source=source):
        self.assertFormatting(source, expected)

  def testSoftKeywordRemainsAnIdentifier(self):
    for source, expected in [
        ('type=object\n', 'type = object\n'),
        ('value=type(item)\n', 'value = type(item)\n'),
        ('type[T]=value\n', 'type[T] = value\n'),
        ('def type(value):\n return value\n',
         'def type(value):\n    return value\n'),
        ('type(type,type=type)\n', 'type(type, type=type)\n'),
    ]:
      with self.subTest(source=source):
        self.assertFormatting(source, expected)

  def testDetachedTypeNameIsNotAKeyword(self):
    leaf = pytree.Leaf(token.NAME, 'type')
    wrapped = format_token.FormatToken(leaf, 'NAME')
    self.assertFalse(wrapped.is_keyword)
    self.assertTrue(wrapped.is_name)

  def testWrappedTypeParameters(self):
    sources = [
        'type Mapping[LongKeyParameter, LongValueParameter] = '
        'dict[LongKeyParameter, LongValueParameter]\n',
        'def convert[LongInputParameter, LongOutputParameter]('
        'value: LongInputParameter, fallback: LongOutputParameter = None'
        ') -> LongOutputParameter:\n    return fallback\n',
        'class Collection[LongKeyParameter, LongValueParameter]('
        'Base[LongKeyParameter, LongValueParameter]):\n    pass\n',
        'type Alias[\n    T,  # key\n    U,  # value\n] = tuple[T, U]\n',
        'def identity[\n    T,  # retain this comment\n](value: T) -> T:\n'
        '    return value\n',
        '@decorate\nasync def identity[T](value: T) -> T:\n'
        '    return value\n',
        'def outer[T](value: T):\n'
        '    def inner[U](other: U) -> U:\n'
        '        return other\n'
        '    return inner(value)\n',
    ]
    for name in ['pep8', 'google', 'yapf', 'facebook']:
      for source in sources:
        with self.subTest(style=name, source=source):
          result = self.assertFormatting(
              source,
              style={
                  'BASED_ON_STYLE': name,
                  'COLUMN_LIMIT': 48,
                  'DEDENT_CLOSING_BRACKETS': True,
              })
          for line in source.splitlines():
            if '#' in line:
              self.assertIn(line[line.index('#'):], result)

  def testTrailingTypeParameterCommas(self):
    cases = [
        ('type Alias[T,U,]=tuple[T,U]\n',
         'type Alias[\n    T,\n    U,\n] = tuple[T, U]\n'),
        ('def identity[T,U,](x:T,y:U)->tuple[T,U]:\n return x,y\n',
         'def identity[\n    T,\n    U,\n]'
         '(x: T, y: U) -> tuple[T, U]:\n    return x, y\n'),
        ('class Container[T,* Ts,** P,](Base):\n pass\n',
         'class Container[\n    T,\n    *Ts,\n    **P,\n](Base):\n    pass\n'),
    ]
    for source, expected in cases:
      with self.subTest(source=source):
        self.assertFormatting(
            source,
            expected,
            style={
                'BASED_ON_STYLE': 'pep8',
                'DEDENT_CLOSING_BRACKETS': True
            })

  def testTypeParameterComments(self):
    for source in [
        'type Alias[\n # leading\n T # trailing\n]=list[T]\n',
        'def f[\n # leading\n T # trailing\n](value:T):\n return value\n',
        'class Box[\n # leading\n T # trailing\n]:\n pass\n',
    ]:
      with self.subTest(source=source):
        result = self.assertFormatting(source)
        self.assertIn('# leading', result)
        self.assertIn('# trailing', result)


if __name__ == '__main__':
  unittest.main()
