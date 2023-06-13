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

from yapf.yapflib import reformatter
from yapf.yapflib import style

from yapftests import yapf_test_helper


class TestsForPython3Code(yapf_test_helper.YAPFTest):
  """Test a few constructs that are new Python 3 syntax."""

  @classmethod
  def setUpClass(cls):  # pylint: disable=g-missing-super-call
    style.SetGlobalStyle(style.CreatePEP8Style())

  def testTypedNames(self):
    unformatted_code = textwrap.dedent("""\
        def x(aaaaaaaaaaaaaaa:int,bbbbbbbbbbbbbbbb:str,ccccccccccccccc:dict,eeeeeeeeeeeeee:set={1, 2, 3})->bool:
          pass
    """)  # noqa
    expected_formatted_code = textwrap.dedent("""\
        def x(aaaaaaaaaaaaaaa: int,
              bbbbbbbbbbbbbbbb: str,
              ccccccccccccccc: dict,
              eeeeeeeeeeeeee: set = {1, 2, 3}) -> bool:
            pass
    """)  # noqa
    llines = yapf_test_helper.ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(llines))

  def testTypedNameWithLongNamedArg(self):
    unformatted_code = textwrap.dedent("""\
        def func(arg=long_function_call_that_pushes_the_line_over_eighty_characters()) -> ReturnType:
          pass
    """)  # noqa
    expected_formatted_code = textwrap.dedent("""\
        def func(arg=long_function_call_that_pushes_the_line_over_eighty_characters()
                 ) -> ReturnType:
            pass
    """)  # noqa
    llines = yapf_test_helper.ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(llines))

  def testKeywordOnlyArgSpecifier(self):
    unformatted_code = textwrap.dedent("""\
        def foo(a, *, kw):
          return a+kw
    """)  # noqa
    expected_formatted_code = textwrap.dedent("""\
        def foo(a, *, kw):
            return a + kw
    """)  # noqa
    llines = yapf_test_helper.ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(llines))

  def testAnnotations(self):
    unformatted_code = textwrap.dedent("""\
        def foo(a: list, b: "bar") -> dict:
          return a+b
    """)  # noqa
    expected_formatted_code = textwrap.dedent("""\
        def foo(a: list, b: "bar") -> dict:
            return a + b
    """)  # noqa
    llines = yapf_test_helper.ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(llines))

  def testExecAsNonKeyword(self):
    unformatted_code = 'methods.exec( sys.modules[name])\n'
    expected_formatted_code = 'methods.exec(sys.modules[name])\n'
    llines = yapf_test_helper.ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(llines))

  def testAsyncFunctions(self):
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
    """)  # noqa
    llines = yapf_test_helper.ParseAndUnwrap(code)
    self.assertCodeEqual(code, reformatter.Reformat(llines, verify=False))

  def testNoSpacesAroundPowerOperator(self):
    unformatted_code = textwrap.dedent("""\
        a**b
    """)  # noqa
    expected_formatted_code = textwrap.dedent("""\
        a ** b
    """)  # noqa

    try:
      style.SetGlobalStyle(
          style.CreateStyleFromConfig(
              '{based_on_style: pep8, SPACES_AROUND_POWER_OPERATOR: True}'))

      llines = yapf_test_helper.ParseAndUnwrap(unformatted_code)
      self.assertCodeEqual(expected_formatted_code,
                           reformatter.Reformat(llines))
    finally:
      style.SetGlobalStyle(style.CreatePEP8Style())

  def testSpacesAroundDefaultOrNamedAssign(self):
    unformatted_code = textwrap.dedent("""\
        f(a=5)
    """)  # noqa
    expected_formatted_code = textwrap.dedent("""\
        f(a = 5)
    """)  # noqa

    try:
      style.SetGlobalStyle(
          style.CreateStyleFromConfig(
              '{based_on_style: pep8, '
              'SPACES_AROUND_DEFAULT_OR_NAMED_ASSIGN: True}'))

      llines = yapf_test_helper.ParseAndUnwrap(unformatted_code)
      self.assertCodeEqual(expected_formatted_code,
                           reformatter.Reformat(llines))
    finally:
      style.SetGlobalStyle(style.CreatePEP8Style())

  def testTypeHint(self):
    unformatted_code = textwrap.dedent("""\
        def foo(x: int=42):
            pass


        def foo2(x: 'int' =42):
            pass
    """)  # noqa
    expected_formatted_code = textwrap.dedent("""\
        def foo(x: int = 42):
            pass


        def foo2(x: 'int' = 42):
            pass
    """)  # noqa
    llines = yapf_test_helper.ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(llines))

  def testMatrixMultiplication(self):
    unformatted_code = textwrap.dedent("""\
        a=b@c
    """)  # noqa
    expected_formatted_code = textwrap.dedent("""\
        a = b @ c
    """)  # noqa
    llines = yapf_test_helper.ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(llines))

  def testNoneKeyword(self):
    code = textwrap.dedent("""\
        None.__ne__()
    """)  # noqa
    llines = yapf_test_helper.ParseAndUnwrap(code)
    self.assertCodeEqual(code, reformatter.Reformat(llines))

  def testAsyncWithPrecedingComment(self):
    unformatted_code = textwrap.dedent("""\
        import asyncio

        # Comment
        async def bar():
            pass

        async def foo():
            pass
    """)  # noqa
    expected_formatted_code = textwrap.dedent("""\
        import asyncio


        # Comment
        async def bar():
            pass


        async def foo():
            pass
    """)  # noqa
    llines = yapf_test_helper.ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(llines))

  def testAsyncFunctionsNested(self):
    code = textwrap.dedent("""\
        async def outer():

            async def inner():
                pass
    """)  # noqa
    llines = yapf_test_helper.ParseAndUnwrap(code)
    self.assertCodeEqual(code, reformatter.Reformat(llines))

  def testKeepTypesIntact(self):
    unformatted_code = textwrap.dedent("""\
        def _ReduceAbstractContainers(
            self, *args: Optional[automation_converter.PyiCollectionAbc]) -> List[
                automation_converter.PyiCollectionAbc]:
            pass
    """)  # noqa
    expected_formatted_code = textwrap.dedent("""\
        def _ReduceAbstractContainers(
            self, *args: Optional[automation_converter.PyiCollectionAbc]
        ) -> List[automation_converter.PyiCollectionAbc]:
            pass
    """)  # noqa
    llines = yapf_test_helper.ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(llines))

  def testContinuationIndentWithAsync(self):
    unformatted_code = textwrap.dedent("""\
        async def start_websocket():
            async with session.ws_connect(
                r"ws://a_really_long_long_long_long_long_long_url") as ws:
                pass
    """)  # noqa
    expected_formatted_code = textwrap.dedent("""\
        async def start_websocket():
            async with session.ws_connect(
                    r"ws://a_really_long_long_long_long_long_long_url") as ws:
                pass
    """)  # noqa
    llines = yapf_test_helper.ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(llines))

  def testSplittingArguments(self):
    unformatted_code = textwrap.dedent("""\
        async def open_file(file, mode='r', buffering=-1, encoding=None, errors=None, newline=None, closefd=True, opener=None):
            pass

        async def run_sync_in_worker_thread(sync_fn, *args, cancellable=False, limiter=None):
            pass

        def open_file(file, mode='r', buffering=-1, encoding=None, errors=None, newline=None, closefd=True, opener=None):
            pass

        def run_sync_in_worker_thread(sync_fn, *args, cancellable=False, limiter=None):
            pass
    """)  # noqa
    expected_formatted_code = textwrap.dedent("""\
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
    """)  # noqa

    try:
      style.SetGlobalStyle(
          style.CreateStyleFromConfig(
              '{based_on_style: pep8, '
              'dedent_closing_brackets: true, '
              'coalesce_brackets: false, '
              'space_between_ending_comma_and_closing_bracket: false, '
              'split_arguments_when_comma_terminated: true, '
              'split_before_first_argument: true}'))

      llines = yapf_test_helper.ParseAndUnwrap(unformatted_code)
      self.assertCodeEqual(expected_formatted_code,
                           reformatter.Reformat(llines))
    finally:
      style.SetGlobalStyle(style.CreatePEP8Style())

  def testDictUnpacking(self):
    unformatted_code = textwrap.dedent("""\
        class Foo:
            def foo(self):
                foofoofoofoofoofoofoofoo('foofoofoofoofoo', {

                    'foo': 'foo',

                    **foofoofoo
                })
    """)  # noqa
    expected_formatted_code = textwrap.dedent("""\
        class Foo:

            def foo(self):
                foofoofoofoofoofoofoofoo('foofoofoofoofoo', {
                    'foo': 'foo',
                    **foofoofoo
                })
    """)  # noqa
    llines = yapf_test_helper.ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(llines))

  def testMultilineFormatString(self):
    # https://github.com/google/yapf/issues/513
    code = textwrap.dedent("""\
        # yapf: disable
        (f'''
          ''')
        # yapf: enable
    """)  # noqa
    llines = yapf_test_helper.ParseAndUnwrap(code)
    self.assertCodeEqual(code, reformatter.Reformat(llines))

  def testEllipses(self):
    # https://github.com/google/yapf/issues/533
    code = textwrap.dedent("""\
        def dirichlet(x12345678901234567890123456789012345678901234567890=...) -> None:
            return
    """)  # noqa
    llines = yapf_test_helper.ParseAndUnwrap(code)
    self.assertCodeEqual(code, reformatter.Reformat(llines))

  def testFunctionTypedReturnNextLine(self):
    code = textwrap.dedent("""\
        def _GenerateStatsEntries(
            process_id: Text,
            timestamp: Optional[ffffffff.FFFFFFFFFFF] = None
        ) -> Sequence[ssssssssssss.SSSSSSSSSSSSSSS]:
            pass
    """)  # noqa
    llines = yapf_test_helper.ParseAndUnwrap(code)
    self.assertCodeEqual(code, reformatter.Reformat(llines))

  def testFunctionTypedReturnSameLine(self):
    code = textwrap.dedent("""\
        def rrrrrrrrrrrrrrrrrrrrrr(
                ccccccccccccccccccccccc: Tuple[Text, Text]) -> List[Tuple[Text, Text]]:
            pass
    """)  # noqa
    llines = yapf_test_helper.ParseAndUnwrap(code)
    self.assertCodeEqual(code, reformatter.Reformat(llines))

  def testAsyncForElseNotIndentedInsideBody(self):
    code = textwrap.dedent("""\
        async def fn():
            async for message in websocket:
                for i in range(10):
                    pass
                else:
                    pass
            else:
                pass
    """)  # noqa
    llines = yapf_test_helper.ParseAndUnwrap(code)
    self.assertCodeEqual(code, reformatter.Reformat(llines))

  def testForElseInAsyncNotMixedWithAsyncFor(self):
    code = textwrap.dedent("""\
        async def fn():
            for i in range(10):
                pass
            else:
                pass
    """)  # noqa
    llines = yapf_test_helper.ParseAndUnwrap(code)
    self.assertCodeEqual(code, reformatter.Reformat(llines))

  def testParameterListIndentationConflicts(self):
    unformatted_code = textwrap.dedent("""\
        def raw_message(  # pylint: disable=too-many-arguments
                    self, text, user_id=1000, chat_type='private', forward_date=None, forward_from=None):
                pass
    """)  # noqa
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
    llines = yapf_test_helper.ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(llines))

  def testTypeHintedYieldExpression(self):
    # https://github.com/google/yapf/issues/1092
    code = textwrap.dedent("""\
       def my_coroutine():
           x: int = yield
    """)  # noqa
    llines = yapf_test_helper.ParseAndUnwrap(code)
    self.assertCodeEqual(code, reformatter.Reformat(llines))

  def testSyntaxMatch(self):
    # https://github.com/google/yapf/issues/1045
    # https://github.com/google/yapf/issues/1085
    unformatted_code = textwrap.dedent("""\
        a=3
        b=0
        match a :
            case 0 :
                b=1
            case _	:
                b=2
    """)  # noqa
    expected_formatted_code = textwrap.dedent("""\
        a = 3
        b = 0
        match a:
            case 0:
                b = 1
            case _:
                b = 2
    """)  # noqa
    llines = yapf_test_helper.ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(llines))

  def testParenthsizedContextManager(self):
    # https://github.com/google/yapf/issues/1064
    unformatted_code = textwrap.dedent("""\
        def test_copy_dimension(self):
            with (Dataset() as target_ds,
                  Dataset() as source_ds):
                do_something
    """)  # noqa
    expected_formatted_code = textwrap.dedent("""\
        def test_copy_dimension(self):
            with (Dataset() as target_ds, Dataset() as source_ds):
                do_something
    """)  # noqa
    llines = yapf_test_helper.ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(llines))

  def testUnpackedTuple(self):
    # https://github.com/google/yapf/issues/830
    # https://github.com/google/yapf/issues/1060
    unformatted_code = textwrap.dedent("""\
        def a():
          t = (2,3)
          for i in range(5):
            yield i,*t
    """)  # noqa
    expected_formatted_code = textwrap.dedent("""\
        def a():
            t = (2, 3)
            for i in range(5):
                yield i, *t
    """)  # noqa
    llines = yapf_test_helper.ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(llines))

  def testTypedTuple(self):
    # https://github.com/google/yapf/issues/412
    # https://github.com/google/yapf/issues/1058
    code = textwrap.dedent("""\
        t: tuple = 1, 2
        args = tuple(x for x in [2], )
    """)  # noqa
    llines = yapf_test_helper.ParseAndUnwrap(code)
    self.assertCodeEqual(code, reformatter.Reformat(llines))

  def testWalrusOperator(self):
    # https://github.com/google/yapf/issues/894
    unformatted_code = textwrap.dedent("""\
        import os
        a=[1,2,3,4]
        if (n:=len(a))>2:
            print()
    """)  # noqa
    expected_formatted_code = textwrap.dedent("""\
        import os

        a = [1, 2, 3, 4]
        if (n := len(a)) > 2:
            print()
    """)  # noqa
    llines = yapf_test_helper.ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(llines))

  def testCondAssign(self):
    # https://github.com/google/yapf/issues/856
    unformatted_code = textwrap.dedent("""\
        def json(self) -> JSONTask:
                result: JSONTask = {
                    "id": self.id,
                    "text": self.text,
                    "status": self.status,
                    "last_mod": self.last_mod_time
                }
                for i in "parent_id", "deadline", "reminder":
                    if x := getattr(self , i):
                        result[i] = x  # type: ignore
                return result
    """)  # noqa
    expected_formatted_code = textwrap.dedent("""\
        def json(self) -> JSONTask:
            result: JSONTask = {
                "id": self.id,
                "text": self.text,
                "status": self.status,
                "last_mod": self.last_mod_time
            }
            for i in "parent_id", "deadline", "reminder":
                if x := getattr(self, i):
                    result[i] = x  # type: ignore
            return result
    """)  # noqa
    llines = yapf_test_helper.ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(llines))

  def testCopyDictionary(self):
    # https://github.com/google/yapf/issues/233
    # https://github.com/google/yapf/issues/402
    code = textwrap.dedent("""\
        a_dict = {'key': 'value'}
        a_dict_copy = {**a_dict}
        print('a_dict:', a_dict)
        print('a_dict_copy:', a_dict_copy)
    """)  # noqa
    llines = yapf_test_helper.ParseAndUnwrap(code)
    self.assertCodeEqual(code, reformatter.Reformat(llines))


if __name__ == '__main__':
  unittest.main()
