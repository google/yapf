# Copyright 2026 Google Inc. All Rights Reserved.
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
"""Contracts for the LibCST parser, emission bridge and public tree API."""

import ast
import builtins
import importlib.util
import unittest
from unittest import mock

import libcst as cst

from yapf.layout import frontend
from yapf.layout import tokens
from yapf.layout import utils
from yapf.yapflib import errors
from yapf.yapflib import yapf_api
from yapftests import yapf_test_helper


class LibCSTFrontendTest(yapf_test_helper.YAPFTest):

  def assertStable(self, source, expected=None, **kwargs):
    kwargs.setdefault('style_config', 'pep8')
    result, _ = yapf_api.FormatCode(source, **kwargs)
    if expected is not None:
      self.assertCodeEqual(expected, result)
    self.assertEqual(ast.dump(ast.parse(source)), ast.dump(ast.parse(result)))
    self.assertEqual(result, yapf_api.FormatCode(result, **kwargs)[0])
    return result

  def testSourceRoundTrip(self):
    cases = [
        '',
        '\n',
        '# only a comment\n',
        'x=1\n',
        'x=1',
        'x=1\r\n # first\r\n # second\r\n',
        'x = (1  # inline\n     + 2)\n',
        'def f():\n\treturn "a\\nb"\n',
        'x = 1 + \\\n    2\n',
        'x = f"value={a!r:>{width}}"\n',
    ]
    for source in cases:
      with self.subTest(source=source):
        normalized = source if source.endswith('\n') else source + '\n'
        module = frontend.ParseModule(source)
        self.assertEqual(normalized, module.code)
        state = frontend._Emissions(module)
        module._codegen(state)
        self.assertEqual(normalized, ''.join(state.tokens))

  def testCallPunctuationMaterialized(self):
    tree = frontend.ParseCode('f(a, b=2)\n')
    leaves = [
        leaf for leaf in tree.leaves()
        if leaf.type not in (tokens.NEWLINE, tokens.ENDMARKER)
    ]
    self.assertEqual(['f', '(', 'a', ',', 'b', '=', '2', ')'],
                     [leaf.value for leaf in leaves])
    self.assertEqual([0, 1, 2, 3, 5, 6, 7, 8], [leaf.column for leaf in leaves])

  def testMultipleLexicalTokensPerOperator(self):
    tree = frontend.ParseCode('x is not y and x not in z\n')
    self.assertEqual(
        ['x', 'is', 'not', 'y', 'and', 'x', 'not', 'in', 'z'],
        [leaf.value for leaf in tree.leaves() if leaf.type == tokens.NAME])

  def testStringInteriorsAreOpaque(self):
    source = '''x=f"{a +  b=}:{x!r:>{width}}"\ny=("a" f"{b}")\n'''
    tree = frontend.ParseCode(source)
    strings = [
        leaf.value for leaf in tree.leaves() if leaf.type == tokens.STRING
    ]
    self.assertEqual(['f"{a +  b=}:{x!r:>{width}}"', '"a"', 'f"{b}"'], strings)
    self.assertStable(source)

  def testMultilineStringPositions(self):
    tree = frontend.ParseCode('x="""first\nsecond"""; y=2\n')
    second_name = next(leaf for leaf in tree.leaves() if leaf.value == 'y')
    self.assertEqual((2, 11), (second_name.lineno, second_name.column))

  def testNonAsciiSourcePositions(self):
    source = '\u2118=1; a\u0301=2\n'
    tree = frontend.ParseCode(source)
    second_name = next(
        leaf for leaf in tree.leaves() if leaf.value == 'a\u0301')
    self.assertEqual((1, 5), (second_name.lineno, second_name.column))
    self.assertStable(source)

  def testFooterRoundTripWorkaround(self):
    # Regression for LibCST 1.9.0 dropping indented EOF comment lines.
    for prefix in ('x=1\n', 'if x:\n pass\n', '# header\n'):
      for indent in (' ', '    ', '\t'):
        source = prefix + indent + '# first\n' + indent + '# second\n'
        with self.subTest(source=source):
          module = frontend.ParseModule(source)
          self.assertEqual(source, module.code)
          result = self.assertStable(source)
          self.assertEqual(1, result.count('# first'))
          self.assertEqual(1, result.count('# second'))

  def testFooterWorkaroundDoesNotLeaveSentinel(self):
    result = self.assertStable('x=1\n # one\n # two\n')
    self.assertNotIn('pass', result)

  def testLossyParserFailsClosed(self):
    lossy = cst.parse_module('x=2\n')
    with mock.patch.object(frontend.cst, 'parse_module', return_value=lossy):
      with self.assertRaises(SyntaxError):
        frontend.ParseModule('x=1\n')

  def testTreeApiDoesNotMutateModule(self):
    source = 'def f(a,b=2):\n return a+b\n'
    module = cst.parse_module(source)
    first = yapf_api.FormatTree(module)
    self.assertEqual(source, module.code)
    self.assertEqual(first, yapf_api.FormatTree(module))
    self.assertEqual(first, yapf_api.FormatCode(source)[0])

  def testConstructedModule(self):
    module = cst.Module(body=[
        cst.SimpleStatementLine(body=[
            cst.Assign(
                targets=[cst.AssignTarget(cst.Name('x'))],
                value=cst.Integer('1'))
        ])
    ])
    self.assertEqual('x = 1\n', yapf_api.FormatTree(module))

  def testConstructedModuleWithSharedNodes(self):
    name = cst.Name('a')
    expression = cst.BinaryOperation(name, cst.Add(), name)
    module = cst.Module(body=[
        cst.SimpleStatementLine(
            body=[cst.Assign([cst.AssignTarget(name)], expression)])
    ])
    before = module.code
    self.assertEqual('a = a + a\n', yapf_api.FormatTree(module))
    self.assertEqual(before, module.code)

  def testUnsupportedSyntaxKeepsFilename(self):
    with self.assertRaisesRegex(errors.YapfError,
                                r'example.py:1:1:.*TypeAlias'):
      yapf_api.FormatCode('type Alias = int\n', filename='example.py')

  def testLossyParserReportsLocatedError(self):
    lossy = cst.parse_module('x=2\n')
    with mock.patch.object(frontend.cst, 'parse_module', return_value=lossy):
      with self.assertRaisesRegex(errors.YapfError, r'example.py:1:1:'):
        yapf_api.FormatCode('x=1\n', filename='example.py')

  def testNonSyntaxExceptionsHaveUsefulMessages(self):
    self.assertEqual('internal error',
                     errors.FormatErrorMsg(ValueError('internal error')))

  def testTreeApiRejectsOtherTrees(self):
    with self.assertRaisesRegex(TypeError, 'libcst.Module'):
      yapf_api.FormatTree(ast.parse('x=1'))
    with self.assertRaisesRegex(TypeError, 'libcst.Module'):
      yapf_api.FormatTree(frontend.ParseCode('x=1'))

  def testRemovedAstApi(self):
    self.assertFalse(hasattr(yapf_api, 'FormatAST'))

  def testParserPackagesAreRemoved(self):
    self.assertIsNone(importlib.util.find_spec('yapf.pyparser'))
    self.assertIsNone(importlib.util.find_spec('yapf.pytree'))
    if importlib.util.find_spec('yapf_third_party') is not None:
      self.assertIsNone(importlib.util.find_spec('yapf_third_party._ylib2to3'))

  def testNoLegacyParserImported(self):
    original_import = builtins.__import__

    def checked_import(name, *args, **kwargs):
      if '_ylib2to3' in name or name.startswith(('lib2to3', 'yapf.pyparser')):
        self.fail('Legacy parser import: ' + name)
      return original_import(name, *args, **kwargs)

    with mock.patch.object(builtins, '__import__', side_effect=checked_import):
      self.assertStable('result=type(value)\n')

  def testSyntaxErrorHasFilenameAndLocation(self):
    with self.assertRaisesRegex(errors.YapfError, r'broken.py:\d+:\d+:'):
      yapf_api.FormatCode('if:\n pass\n', filename='broken.py')

  def testKnownUpstreamClassArgumentRestriction(self):
    # Valid Python and accepted by main, but LibCST 1.9.0 rejects this ordering.
    # Keep the limitation visible until the dependency can represent it.
    source = 'class C(metaclass=M,*bases): pass\n'
    ast.parse(source)
    with self.assertRaisesRegex(errors.YapfError,
                                'Positional argument follows keyword argument'):
      yapf_api.FormatCode(source, filename='class_order.py')

  def testModernPythonValidation(self):
    for source in ('x=100L\n', 'f(x for x in y,)\n',
                   'try:\n pass\nexcept:\n pass\nexcept:\n pass\n'):
      with self.subTest(source=source):
        with self.assertRaises(errors.YapfError):
          yapf_api.FormatCode(source)

  def testUnsupportedNewNodeFailsClearly(self):
    # This branch ports main; it does not merge the type-parameter feature.
    with self.assertRaisesRegex(errors.YapfError, 'TypeAlias'):
      yapf_api.FormatCode('type Alias = int\n')

  def testGenericDeclarationIsOutsideMigrationScope(self):
    with self.assertRaisesRegex(errors.YapfError, 'Type parameters'):
      yapf_api.FormatCode('def f[T](x:T): return x\n')

  def testSelectedLines(self):
    source = 'a= 1\nb= 2\nc= 3\n'
    self.assertStable(source, 'a= 1\nb = 2\nc= 3\n', lines=[(2, 2)])

  def testDisabledCommentsAtEndOfFile(self):
    source = '# yapf: disable\ndef f():\n    x= 1\n# yapf: enable\n'
    self.assertStable(source, source)

  def testMatchSequencePatterns(self):
    patterns = [
        '[x,*rest]', '*head,tail', '(x,*rest)', '[*_]', '(1 | 2) as x',
        '{"x":Point(a,b),**rest}'
    ]
    for pattern in patterns:
      with self.subTest(pattern=pattern):
        self.assertStable('match subject:\n case ' + pattern +
                          ':\n  result=1\n')

  def testAsyncDecoratedFunctionAndComprehensions(self):
    source = ('@decorate(x)\nasync def f(items):\n'
              ' async for a,b in items:\n'
              '  async with a as x,b as y:\n'
              '   result=[await f(x) async for x in y if x]\n')
    self.assertStable(source)

  def testParenthesizedWithAndExceptStar(self):
    source = ('try:\n with (a as b,c as d,):\n  f(b,d)\n'
              'except* (ValueError,TypeError) as e:\n g(e)\n')
    self.assertStable(source)

  def testExplicitContinuations(self):
    source = 'result = first + \\\n second\n'
    self.assertStable(source)

  def testLayoutLeafIdentityAndOrdering(self):
    source = ('@d\ndef f(x:int=1,/,*args,**kwargs):\n'
              ' return {k:v for k,v in values if k}\n')
    tree = frontend.ParseCode(source)
    leaves = list(tree.leaves())
    self.assertEqual(len(leaves), len({id(leaf) for leaf in leaves}))
    self.assertEqual(list(range(len(leaves))), [leaf._start for leaf in leaves])
    self.assertTrue(all(leaf.parent is not None for leaf in leaves))


if __name__ == '__main__':
  unittest.main()
