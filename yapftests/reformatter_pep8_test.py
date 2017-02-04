# Copyright 2016-2017 Google Inc. All Rights Reserved.
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
"""PEP8 tests for yapf.reformatter."""

import textwrap
import unittest

from yapf.yapflib import reformatter
from yapf.yapflib import style

from yapftests import yapf_test_helper


class TestsForPEP8Style(yapf_test_helper.YAPFTest):

  @classmethod
  def setUpClass(cls):
    style.SetGlobalStyle(style.CreatePEP8Style())

  def testIndent4(self):
    unformatted_code = textwrap.dedent("""\
        if a+b:
          pass
        """)
    expected_formatted_code = textwrap.dedent("""\
        if a + b:
            pass
        """)
    uwlines = yapf_test_helper.ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testSingleLineIfStatements(self):
    code = textwrap.dedent("""\
        if True: a = 42
        elif False: b = 42
        else: c = 42
        """)
    uwlines = yapf_test_helper.ParseAndUnwrap(code)
    self.assertCodeEqual(code, reformatter.Reformat(uwlines))

  def testNoBlankBetweenClassAndDef(self):
    unformatted_code = textwrap.dedent("""\
        class Foo:

          def joe():
            pass
        """)
    expected_formatted_code = textwrap.dedent("""\
        class Foo:
            def joe():
                pass
        """)
    uwlines = yapf_test_helper.ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testSingleWhiteBeforeTrailingComment(self):
    unformatted_code = textwrap.dedent("""\
        if a+b: # comment
          pass
        """)
    expected_formatted_code = textwrap.dedent("""\
        if a + b:  # comment
            pass
        """)
    uwlines = yapf_test_helper.ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testSplittingSemicolonStatements(self):
    unformatted_code = textwrap.dedent("""\
        def f():
          x = y + 42 ; z = n * 42
          if True: a += 1 ; b += 1; c += 1
        """)
    expected_formatted_code = textwrap.dedent("""\
        def f():
            x = y + 42
            z = n * 42
            if True:
                a += 1
                b += 1
                c += 1
        """)
    uwlines = yapf_test_helper.ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testSpaceBetweenEndingCommandAndClosingBracket(self):
    unformatted_code = textwrap.dedent("""\
        a = (
            1,
        )
        """)
    expected_formatted_code = textwrap.dedent("""\
        a = (1, )
        """)
    uwlines = yapf_test_helper.ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testContinuedNonOudentedLine(self):
    code = textwrap.dedent("""\
        class eld(d):
            if str(geom.geom_type).upper(
            ) != self.geom_type and not self.geom_type == 'GEOMETRY':
                ror(code='om_type')
        """)
    uwlines = yapf_test_helper.ParseAndUnwrap(code)
    self.assertCodeEqual(code, reformatter.Reformat(uwlines))

  def testWrappingPercentExpressions(self):
    unformatted_code = textwrap.dedent("""\
        def f():
            if True:
                zzzzz = '%s-%s' % (xxxxxxxxxxxxxxxxxxxxxxxxxx + 1, xxxxxxxxxxxxxxxxx.yyy + 1)
                zzzzz = '%s-%s'.ww(xxxxxxxxxxxxxxxxxxxxxxxxxx + 1, xxxxxxxxxxxxxxxxx.yyy + 1)
                zzzzz = '%s-%s' % (xxxxxxxxxxxxxxxxxxxxxxx + 1, xxxxxxxxxxxxxxxxxxxxx + 1)
                zzzzz = '%s-%s'.ww(xxxxxxxxxxxxxxxxxxxxxxx + 1, xxxxxxxxxxxxxxxxxxxxx + 1)
        """)
    expected_formatted_code = textwrap.dedent("""\
        def f():
            if True:
                zzzzz = '%s-%s' % (xxxxxxxxxxxxxxxxxxxxxxxxxx + 1,
                                   xxxxxxxxxxxxxxxxx.yyy + 1)
                zzzzz = '%s-%s'.ww(xxxxxxxxxxxxxxxxxxxxxxxxxx + 1,
                                   xxxxxxxxxxxxxxxxx.yyy + 1)
                zzzzz = '%s-%s' % (xxxxxxxxxxxxxxxxxxxxxxx + 1,
                                   xxxxxxxxxxxxxxxxxxxxx + 1)
                zzzzz = '%s-%s'.ww(xxxxxxxxxxxxxxxxxxxxxxx + 1,
                                   xxxxxxxxxxxxxxxxxxxxx + 1)
        """)
    uwlines = yapf_test_helper.ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testAlignClosingBracketWithVisualIndentation(self):
    unformatted_code = textwrap.dedent("""\
        TEST_LIST = ('foo', 'bar',  # first comment
                     'baz'  # second comment
                    )
        """)
    expected_formatted_code = textwrap.dedent("""\
        TEST_LIST = (
            'foo',
            'bar',  # first comment
            'baz'  # second comment
        )
        """)
    uwlines = yapf_test_helper.ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

    unformatted_code = textwrap.dedent("""\
        def f():

          def g():
            while (xxxxxxxxxxxxxxxxxxxx(yyyyyyyyyyyyy[zzzzz]) == 'aaaaaaaaaaa' and
                   xxxxxxxxxxxxxxxxxxxx(yyyyyyyyyyyyy[zzzzz].aaaaaaaa[0]) == 'bbbbbbb'
                  ):
              pass
        """)
    expected_formatted_code = textwrap.dedent("""\
        def f():
            def g():
                while (xxxxxxxxxxxxxxxxxxxx(yyyyyyyyyyyyy[zzzzz]) == 'aaaaaaaaaaa' and
                       xxxxxxxxxxxxxxxxxxxx(
                           yyyyyyyyyyyyy[zzzzz].aaaaaaaa[0]) == 'bbbbbbb'):
                    pass
        """)
    uwlines = yapf_test_helper.ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testIndentSizeChanging(self):
    unformatted_code = textwrap.dedent("""\
        if True:
          runtime_mins = (program_end_time - program_start_time).total_seconds() / 60.0
        """)
    expected_formatted_code = textwrap.dedent("""\
        if True:
            runtime_mins = (
                program_end_time - program_start_time).total_seconds() / 60.0
        """)
    uwlines = yapf_test_helper.ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testHangingIndentCollision(self):
    unformatted_code = textwrap.dedent("""\
        if (aaaaaaaaaaaaaa + bbbbbbbbbbbbbbbb == ccccccccccccccccc and xxxxxxxxxxxxx or yyyyyyyyyyyyyyyyy):
            pass
        elif (xxxxxxxxxxxxxxx(aaaaaaaaaaa, bbbbbbbbbbbbbb, cccccccccccc, dddddddddd=None)):
            pass


        def h():
            if (xxxxxxxxxxxx.yyyyyyyy(zzzzzzzzzzzzz[0]) == 'aaaaaaaaaaa' and xxxxxxxxxxxx.yyyyyyyy(zzzzzzzzzzzzz[0].mmmmmmmm[0]) == 'bbbbbbb'):
                pass

            for connection in itertools.chain(branch.contact, branch.address, morestuff.andmore.andmore.andmore.andmore.andmore.andmore.andmore):
                dosomething(connection)
        """)
    expected_formatted_code = textwrap.dedent("""\
        if (aaaaaaaaaaaaaa + bbbbbbbbbbbbbbbb == ccccccccccccccccc and xxxxxxxxxxxxx or
                yyyyyyyyyyyyyyyyy):
            pass
        elif (xxxxxxxxxxxxxxx(
                aaaaaaaaaaa, bbbbbbbbbbbbbb, cccccccccccc, dddddddddd=None)):
            pass


        def h():
            if (xxxxxxxxxxxx.yyyyyyyy(zzzzzzzzzzzzz[0]) == 'aaaaaaaaaaa' and
                    xxxxxxxxxxxx.yyyyyyyy(zzzzzzzzzzzzz[0].mmmmmmmm[0]) == 'bbbbbbb'):
                pass

            for connection in itertools.chain(
                    branch.contact, branch.address,
                    morestuff.andmore.andmore.andmore.andmore.andmore.andmore.andmore):
                dosomething(connection)
        """)
    uwlines = yapf_test_helper.ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testSplittingBeforeLogicalOperator(self):
    try:
      style.SetGlobalStyle(
          style.CreateStyleFromConfig(
              '{based_on_style: pep8, split_before_logical_operator: True}'))
      unformatted_code = textwrap.dedent("""\
          def foo():
              return bool(update.message.new_chat_member or update.message.left_chat_member or
                          update.message.new_chat_title or update.message.new_chat_photo or
                          update.message.delete_chat_photo or update.message.group_chat_created or
                          update.message.supergroup_chat_created or update.message.channel_chat_created
                          or update.message.migrate_to_chat_id or update.message.migrate_from_chat_id or
                          update.message.pinned_message)
          """)
      expected_formatted_code = textwrap.dedent("""\
          def foo():
              return bool(
                  update.message.new_chat_member or update.message.left_chat_member
                  or update.message.new_chat_title or update.message.new_chat_photo
                  or update.message.delete_chat_photo
                  or update.message.group_chat_created
                  or update.message.supergroup_chat_created
                  or update.message.channel_chat_created
                  or update.message.migrate_to_chat_id
                  or update.message.migrate_from_chat_id
                  or update.message.pinned_message)
          """)
      uwlines = yapf_test_helper.ParseAndUnwrap(unformatted_code)
      self.assertCodeEqual(expected_formatted_code,
                           reformatter.Reformat(uwlines))
    finally:
      style.SetGlobalStyle(style.CreatePEP8Style())

  def testContiguousListEndingWithComment(self):
    unformatted_code = textwrap.dedent("""\
        if True:
            if True:
                keys.append(aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa)  # may be unassigned.
        """)
    expected_formatted_code = textwrap.dedent("""\
        if True:
            if True:
                keys.append(
                    aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa)  # may be unassigned.
        """)
    uwlines = yapf_test_helper.ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testSplittingBeforeFirstArgument(self):
    try:
      style.SetGlobalStyle(
          style.CreateStyleFromConfig(
              '{based_on_style: pep8, split_before_first_argument: True}'))
      unformatted_code = textwrap.dedent("""\
          a_very_long_function_name(long_argument_name_1=1, long_argument_name_2=2,
                                    long_argument_name_3=3, long_argument_name_4=4)
          """)
      expected_formatted_code = textwrap.dedent("""\
          a_very_long_function_name(
              long_argument_name_1=1,
              long_argument_name_2=2,
              long_argument_name_3=3,
              long_argument_name_4=4)
          """)
      uwlines = yapf_test_helper.ParseAndUnwrap(unformatted_code)
      self.assertCodeEqual(expected_formatted_code,
                           reformatter.Reformat(uwlines))
    finally:
      style.SetGlobalStyle(style.CreatePEP8Style())

  def testSplittingExpressionsInsideSubscripts(self):
    unformatted_code = textwrap.dedent("""\
        def foo():
            df = df[(df['campaign_status'] == 'LIVE') & (df['action_status'] == 'LIVE')]
        """)
    expected_formatted_code = textwrap.dedent("""\
        def foo():
            df = df[(df['campaign_status'] == 'LIVE') &
                    (df['action_status'] == 'LIVE')]
        """)
    uwlines = yapf_test_helper.ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testSplitListsAndDictSetMakersIfCommaTerminated(self):
    unformatted_code = textwrap.dedent("""\
        DJANGO_TEMPLATES_OPTIONS = {"context_processors": []}
        DJANGO_TEMPLATES_OPTIONS = {"context_processors": [],}
        x = ["context_processors"]
        x = ["context_processors",]
        """)
    expected_formatted_code = textwrap.dedent("""\
        DJANGO_TEMPLATES_OPTIONS = {"context_processors": []}
        DJANGO_TEMPLATES_OPTIONS = {
            "context_processors": [],
        }
        x = ["context_processors"]
        x = [
            "context_processors",
        ]
        """)
    uwlines = yapf_test_helper.ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))


if __name__ == '__main__':
  unittest.main()
