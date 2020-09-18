# Copyright 2016 Google Inc. All Rights Reserved.
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
"""Python 3 tests for yapf.reformatter."""

import sys
import textwrap
import unittest

from yapf.yapflib import py3compat
from yapf.yapflib import reformatter
from yapf.yapflib import style

from yapftests import yapf_test_helper


@unittest.skipUnless(py3compat.PY3, 'Requires Python 3')
class TestsForPython3Code(yapf_test_helper.YAPFTest):
  """Test a few constructs that are new Python 3 syntax."""

  @classmethod
  def setUpClass(cls):  # pylint: disable=g-missing-super-call
    style.SetGlobalStyle(style.CreatePEP8Style())

  def testTypedNames(self):
    unformatted_code = textwrap.dedent("""\
        def x(aaaaaaaaaaaaaaa:int,bbbbbbbbbbbbbbbb:str,ccccccccccccccc:dict,eeeeeeeeeeeeee:set={1, 2, 3})->bool:
          pass
        """)
    expected_formatted_code = textwrap.dedent("""\
        def x(aaaaaaaaaaaaaaa: int,
              bbbbbbbbbbbbbbbb: str,
              ccccccccccccccc: dict,
              eeeeeeeeeeeeee: set = {1, 2, 3}) -> bool:
            pass
        """)
    uwlines = yapf_test_helper.ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testTypedNameWithLongNamedArg(self):
    unformatted_code = textwrap.dedent("""\
        def func(arg=long_function_call_that_pushes_the_line_over_eighty_characters()) -> ReturnType:
          pass
        """)
    expected_formatted_code = textwrap.dedent("""\
        def func(arg=long_function_call_that_pushes_the_line_over_eighty_characters()
                 ) -> ReturnType:
            pass
        """)
    uwlines = yapf_test_helper.ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testKeywordOnlyArgSpecifier(self):
    unformatted_code = textwrap.dedent("""\
        def foo(a, *, kw):
          return a+kw
        """)
    expected_formatted_code = textwrap.dedent("""\
        def foo(a, *, kw):
            return a + kw
        """)
    uwlines = yapf_test_helper.ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  @unittest.skipUnless(py3compat.PY36, 'Requires Python 3.6')
  def testPEP448ParameterExpansion(self):
    unformatted_code = textwrap.dedent("""\
    { ** x }
    {   **{}   }
    { **{   **x },  **x }
    {'a': 1,   **kw , 'b':3,  **kw2   }
    """)
    expected_formatted_code = textwrap.dedent("""\
    {**x}
    {**{}}
    {**{**x}, **x}
    {'a': 1, **kw, 'b': 3, **kw2}
    """)
    uwlines = yapf_test_helper.ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testAnnotations(self):
    unformatted_code = textwrap.dedent("""\
        def foo(a: list, b: "bar") -> dict:
          return a+b
        """)
    expected_formatted_code = textwrap.dedent("""\
        def foo(a: list, b: "bar") -> dict:
            return a + b
        """)
    uwlines = yapf_test_helper.ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testExecAsNonKeyword(self):
    unformatted_code = 'methods.exec( sys.modules[name])\n'
    expected_formatted_code = 'methods.exec(sys.modules[name])\n'
    uwlines = yapf_test_helper.ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testAsyncFunctions(self):
    if sys.version_info[1] < 5:
      return
    code = textwrap.dedent("""\
        import asyncio
        import time


        @print_args
        async def slow_operation():
            await asyncio.sleep(1)
            # print("Slow operation {} complete".format(n))


        async def main():
            start = time.time()
            if (await get_html()):
                pass
        """)
    uwlines = yapf_test_helper.ParseAndUnwrap(code)
    self.assertCodeEqual(code, reformatter.Reformat(uwlines, verify=False))

  def testNoSpacesAroundPowerOperator(self):
    unformatted_code = textwrap.dedent("""\
        a**b
        """)
    expected_formatted_code = textwrap.dedent("""\
        a ** b
        """)

    try:
      style.SetGlobalStyle(
          style.CreateStyleFromConfig(
              '{based_on_style: pep8, SPACES_AROUND_POWER_OPERATOR: True}'))

      uwlines = yapf_test_helper.ParseAndUnwrap(unformatted_code)
      self.assertCodeEqual(expected_formatted_code,
                           reformatter.Reformat(uwlines))
    finally:
      style.SetGlobalStyle(style.CreatePEP8Style())

  def testSpacesAroundDefaultOrNamedAssign(self):
    unformatted_code = textwrap.dedent("""\
        f(a=5)
        """)
    expected_formatted_code = textwrap.dedent("""\
        f(a = 5)
        """)

    try:
      style.SetGlobalStyle(
          style.CreateStyleFromConfig(
              '{based_on_style: pep8, '
              'SPACES_AROUND_DEFAULT_OR_NAMED_ASSIGN: True}'))

      uwlines = yapf_test_helper.ParseAndUnwrap(unformatted_code)
      self.assertCodeEqual(expected_formatted_code,
                           reformatter.Reformat(uwlines))
    finally:
      style.SetGlobalStyle(style.CreatePEP8Style())

  def testTypeHint(self):
    unformatted_code = textwrap.dedent("""\
        def foo(x: int=42):
            pass


        def foo2(x: 'int' =42):
            pass
        """)
    expected_formatted_code = textwrap.dedent("""\
        def foo(x: int = 42):
            pass


        def foo2(x: 'int' = 42):
            pass
        """)
    uwlines = yapf_test_helper.ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testMatrixMultiplication(self):
    unformatted_code = textwrap.dedent("""\
        a=b@c
        """)
    expected_formatted_code = textwrap.dedent("""\
        a = b @ c
        """)
    uwlines = yapf_test_helper.ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testNoneKeyword(self):
    code = """\
None.__ne__()
"""
    uwlines = yapf_test_helper.ParseAndUnwrap(code)
    self.assertCodeEqual(code, reformatter.Reformat(uwlines))

  def testAsyncWithPrecedingComment(self):
    if sys.version_info[1] < 5:
      return
    unformatted_code = textwrap.dedent("""\
        import asyncio

        # Comment
        async def bar():
            pass

        async def foo():
            pass
        """)
    expected_formatted_code = textwrap.dedent("""\
        import asyncio


        # Comment
        async def bar():
            pass


        async def foo():
            pass
        """)
    uwlines = yapf_test_helper.ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testAsyncFunctionsNested(self):
    if sys.version_info[1] < 5:
      return
    code = textwrap.dedent("""\
        async def outer():
            async def inner():
                pass
        """)
    uwlines = yapf_test_helper.ParseAndUnwrap(code)
    self.assertCodeEqual(code, reformatter.Reformat(uwlines))

  def testKeepTypesIntact(self):
    if sys.version_info[1] < 5:
      return
    unformatted_code = textwrap.dedent("""\
        def _ReduceAbstractContainers(
            self, *args: Optional[automation_converter.PyiCollectionAbc]) -> List[
                automation_converter.PyiCollectionAbc]:
            pass
        """)
    expected_formatted_code = textwrap.dedent("""\
        def _ReduceAbstractContainers(
            self, *args: Optional[automation_converter.PyiCollectionAbc]
        ) -> List[automation_converter.PyiCollectionAbc]:
            pass
        """)
    uwlines = yapf_test_helper.ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testContinuationIndentWithAsync(self):
    if sys.version_info[1] < 5:
      return
    unformatted_code = textwrap.dedent("""\
        async def start_websocket():
            async with session.ws_connect(
                r"ws://a_really_long_long_long_long_long_long_url") as ws:
                pass
        """)
    expected_formatted_code = textwrap.dedent("""\
        async def start_websocket():
            async with session.ws_connect(
                    r"ws://a_really_long_long_long_long_long_long_url") as ws:
                pass
        """)
    uwlines = yapf_test_helper.ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testSplittingArguments(self):
    if sys.version_info[1] < 5:
      return

    unformatted_code = """\
async def open_file(file, mode='r', buffering=-1, encoding=None, errors=None, newline=None, closefd=True, opener=None):
    pass

async def run_sync_in_worker_thread(sync_fn, *args, cancellable=False, limiter=None):
    pass

def open_file(file, mode='r', buffering=-1, encoding=None, errors=None, newline=None, closefd=True, opener=None):
    pass

def run_sync_in_worker_thread(sync_fn, *args, cancellable=False, limiter=None):
    pass
"""
    expected_formatted_code = """\
async def open_file(
    file,
    mode='r',
    buffering=-1,
    encoding=None,
    errors=None,
    newline=None,
    closefd=True,
    opener=None
):
    pass


async def run_sync_in_worker_thread(
    sync_fn, *args, cancellable=False, limiter=None
):
    pass


def open_file(
    file,
    mode='r',
    buffering=-1,
    encoding=None,
    errors=None,
    newline=None,
    closefd=True,
    opener=None
):
    pass


def run_sync_in_worker_thread(sync_fn, *args, cancellable=False, limiter=None):
    pass
"""

    try:
      style.SetGlobalStyle(
          style.CreateStyleFromConfig(
              '{based_on_style: pep8, '
              'dedent_closing_brackets: true, '
              'coalesce_brackets: false, '
              'space_between_ending_comma_and_closing_bracket: false, '
              'split_arguments_when_comma_terminated: true, '
              'split_before_first_argument: true}'))

      uwlines = yapf_test_helper.ParseAndUnwrap(unformatted_code)
      self.assertCodeEqual(expected_formatted_code,
                           reformatter.Reformat(uwlines))
    finally:
      style.SetGlobalStyle(style.CreatePEP8Style())

  def testDictUnpacking(self):
    if sys.version_info[1] < 5:
      return
    unformatted_code = """\
class Foo:
    def foo(self):
        foofoofoofoofoofoofoofoo('foofoofoofoofoo', {

            'foo': 'foo',

            **foofoofoo
        })
"""
    expected_formatted_code = """\
class Foo:
    def foo(self):
        foofoofoofoofoofoofoofoo('foofoofoofoofoo', {
            'foo': 'foo',
            **foofoofoo
        })
"""
    uwlines = yapf_test_helper.ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testMultilineFormatString(self):
    if sys.version_info[1] < 6:
      return
    code = """\
# yapf: disable
(f'''
  ''')
# yapf: enable
"""
    # https://github.com/google/yapf/issues/513
    uwlines = yapf_test_helper.ParseAndUnwrap(code)
    self.assertCodeEqual(code, reformatter.Reformat(uwlines))

  def testEllipses(self):
    if sys.version_info[1] < 6:
      return
    code = """\
def dirichlet(x12345678901234567890123456789012345678901234567890=...) -> None:
    return
"""
    # https://github.com/google/yapf/issues/533
    uwlines = yapf_test_helper.ParseAndUnwrap(code)
    self.assertCodeEqual(code, reformatter.Reformat(uwlines))

  def testFunctionTypedReturnNextLine(self):
    code = """\
def _GenerateStatsEntries(
    process_id: Text,
    timestamp: Optional[ffffffff.FFFFFFFFFFF] = None
) -> Sequence[ssssssssssss.SSSSSSSSSSSSSSS]:
    pass
"""
    uwlines = yapf_test_helper.ParseAndUnwrap(code)
    self.assertCodeEqual(code, reformatter.Reformat(uwlines))

  def testFunctionTypedReturnSameLine(self):
    code = """\
def rrrrrrrrrrrrrrrrrrrrrr(
        ccccccccccccccccccccccc: Tuple[Text, Text]) -> List[Tuple[Text, Text]]:
    pass
"""
    uwlines = yapf_test_helper.ParseAndUnwrap(code)
    self.assertCodeEqual(code, reformatter.Reformat(uwlines))

  def testAsyncForElseNotIndentedInsideBody(self):
    if sys.version_info[1] < 5:
      return
    code = textwrap.dedent("""\
    async def fn():
        async for message in websocket:
            for i in range(10):
                pass
            else:
                pass
        else:
            pass
    """)
    uwlines = yapf_test_helper.ParseAndUnwrap(code)
    self.assertCodeEqual(code, reformatter.Reformat(uwlines))

  def testForElseInAsyncNotMixedWithAsyncFor(self):
    if sys.version_info[1] < 5:
      return
    code = textwrap.dedent("""\
    async def fn():
        for i in range(10):
            pass
        else:
            pass
    """)
    uwlines = yapf_test_helper.ParseAndUnwrap(code)
    self.assertCodeEqual(code, reformatter.Reformat(uwlines))

  def testParameterListIndentationConflicts(self):
    unformatted_code = textwrap.dedent("""\
        def raw_message(  # pylint: disable=too-many-arguments
                    self, text, user_id=1000, chat_type='private', forward_date=None, forward_from=None):
                pass
        """)
    expected_formatted_code = textwrap.dedent("""\
        def raw_message(  # pylint: disable=too-many-arguments
                self,
                text,
                user_id=1000,
                chat_type='private',
                forward_date=None,
                forward_from=None):
            pass
        """)
    uwlines = yapf_test_helper.ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))


if __name__ == '__main__':
  unittest.main()
