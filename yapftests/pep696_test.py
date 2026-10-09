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
"""Regression coverage for PEP 696, including exact output and stability."""

import ast
import sys
import unittest

from yapf.yapflib import errors
from yapf.yapflib.yapf_api import FormatCode


class Pep696Test(unittest.TestCase):

  def assertFormatting(self, source, expected=None, style='pep8'):
    result, _ = FormatCode(source, style_config=style)
    if expected is not None:
      self.assertEqual(expected, result)
    again, changed = FormatCode(result, style_config=style)
    self.assertEqual(result, again)
    self.assertFalse(changed)
    if sys.version_info >= (3, 13):
      self.assertEqual(ast.dump(ast.parse(source)), ast.dump(ast.parse(result)))
    return result

  def testTypeVariableDefaults(self):
    cases = [
        ('class Box[T=int]:\n pass\n', 'class Box[T = int]:\n    pass\n'),
        ('type Vector[T=int]=list[T]\n', 'type Vector[T = int] = list[T]\n'),
        ('def identity[T=int](value:T)->T:\n return value\n',
         'def identity[T = int](value: T) -> T:\n    return value\n'),
        ('async def identity[T=int](value:T)->T:\n return value\n',
         'async def identity[T = int](value: T) -> T:\n    return value\n'),
        ('class Box[T:int=int]:\n pass\n',
         'class Box[T: int = int]:\n    pass\n'),
        ('type Text[T:(str,bytes)=str]=T\n',
         'type Text[T: (str, bytes) = str] = T\n'),
    ]
    for source, expected in cases:
      with self.subTest(source=source):
        self.assertFormatting(source, expected)

  def testVariadicDefaults(self):
    cases = [
        ('type Shape[* Ts=*tuple[int,str]]=tuple[*Ts]\n',
         'type Shape[*Ts = *tuple[int, str]] = tuple[*Ts]\n'),
        ('type Shape[*Ts=Unpack[tuple[int,str]]]=tuple[*Ts]\n',
         'type Shape[*Ts = Unpack[tuple[int, str]]] = tuple[*Ts]\n'),
        ('type Callback[** P=[int,str]]=Callable[P,int]\n',
         'type Callback[**P = [int, str]] = Callable[P, int]\n'),
        ('type Callback[**P=...]=Callable[P,int]\n',
         'type Callback[**P = ...] = Callable[P, int]\n'),
        ('class Box[T,*Ts=*tuple[int],**P=[str]]:\n pass\n',
         'class Box[T, *Ts = *tuple[int], **P = [str]]:\n    pass\n'),
    ]
    for source, expected in cases:
      with self.subTest(source=source):
        self.assertFormatting(source, expected)

  def testNestedDefaultExpressionsKeepTheirOwnSpacing(self):
    cases = [
        ('type Box[T=Factory(option=True)]=list[T]\n',
         'type Box[T = Factory(option=True)] = list[T]\n'),
        ('type Box[T=int|None]=list[T]\n',
         'type Box[T = int | None] = list[T]\n'),
        ('type Box[T=int if enabled else str]=list[T]\n',
         'type Box[T = int if enabled else str] = list[T]\n'),
        ('type Box[T=tuple[int,tuple[str,...]]]=list[T]\n',
         'type Box[T = tuple[int, tuple[str, ...]]] = list[T]\n'),
        ('def f[T=int](value=1,*,other:T=2):\n return value\n',
         'def f[T = int](value=1, *, other: T = 2):\n    return value\n'),
    ]
    for source, expected in cases:
      with self.subTest(source=source):
        self.assertFormatting(source, expected)

  def testTypeDefaultSpacingIsNotKeywordArgumentSpacing(self):
    for setting in (False, True):
      result = self.assertFormatting(
          'type Box[T=int]=list[T]\n',
          style={'SPACES_AROUND_DEFAULT_OR_NAMED_ASSIGN': setting})
      self.assertEqual('type Box[T = int] = list[T]\n', result)

  def testWrappedDefaultsCommentsAndTrailingCommas(self):
    sources = [
        'type Alias[\n T: int=int, # default\n ** P=[int,str], # args\n'
        ']=Callable[P,T]\n',
        'class Box[LongParameterName=Mapping[str,list[int]],'
        'OtherLongParameterName=tuple[int,str]](Base):\n pass\n',
        'def f[T=Mapping[str,list[int]],** P=[str,int],]('
        'value:T,other:int=0)->T:\n return value\n',
        '@decorate\nasync def f[T=int](value:T):\n return value\n',
        'type Shape[*Ts=*tuple[int,str],]=tuple[*Ts]\n',
    ]
    for source in sources:
      for name in ('pep8', 'google', 'yapf', 'facebook'):
        for limit in (32, 50, 88):
          with self.subTest(source=source, style=name, limit=limit):
            result = self.assertFormatting(
                source,
                style={
                    'BASED_ON_STYLE': name,
                    'COLUMN_LIMIT': limit,
                    'DEDENT_CLOSING_BRACKETS': True
                })
            for comment in ('# default', '# args'):
              if comment in source:
                self.assertIn(comment, result)

  def testOnlyTupleParameterDefaultsCanBeStarred(self):
    for source in ('type A[T=*tuple[int]]=T\n', 'type A[**P=*tuple[int]]=T\n'):
      with self.subTest(source=source):
        with self.assertRaises(errors.YapfError):
          FormatCode(source)

  @unittest.skipUnless(sys.version_info >= (3, 13), 'requires Python 3.13')
  def testNativeDefaultMetadata(self):
    source = ('class Box[T=int]:\n pass\n'
              'type Callback[**P=[int,str]]=tuple[P]\n')
    result = self.assertFormatting(source)
    namespace = {}
    exec(result, namespace)
    self.assertIs(int, namespace['Box'].__type_params__[0].__default__)
    self.assertEqual([int, str],
                     namespace['Callback'].__type_params__[0].__default__)


if __name__ == '__main__':
  unittest.main()
