# Copyright 2015 Google Inc. All Rights Reserved.
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
"""Tests for yapf.reformatter."""

import difflib
import sys
import textwrap
import unittest

from yapf.yapflib import blank_line_calculator
from yapf.yapflib import comment_splicer
from yapf.yapflib import continuation_splicer
from yapf.yapflib import py3compat
from yapf.yapflib import pytree_unwrapper
from yapf.yapflib import pytree_utils
from yapf.yapflib import pytree_visitor
from yapf.yapflib import reformatter
from yapf.yapflib import split_penalty
from yapf.yapflib import style
from yapf.yapflib import subtype_assigner
from yapf.yapflib import verifier


class ReformatterTest(unittest.TestCase):

  def assertCodeEqual(self, expected_code, code):
    if code != expected_code:
      msg = ['Code format mismatch:', 'Expected:']
      linelen = style.Get('COLUMN_LIMIT')
      for l in expected_code.splitlines():
        if len(l) > linelen:
          msg.append('!> %s' % l)
        else:
          msg.append(' > %s' % l)
      msg.append('Actual:')
      for l in code.splitlines():
        if len(l) > linelen:
          msg.append('!> %s' % l)
        else:
          msg.append(' > %s' % l)
      msg.append('Diff:')
      msg.extend(difflib.unified_diff(code.splitlines(),
                                      expected_code.splitlines(),
                                      fromfile='actual',
                                      tofile='expected',
                                      lineterm=''))
      self.fail('\n'.join(msg))


class BasicReformatterTest(ReformatterTest):

  @classmethod
  def setUpClass(cls):
    style.SetGlobalStyle(style.CreateChromiumStyle())

  def testSimple(self):
    unformatted_code = textwrap.dedent("""\
        if a+b:
            pass
        """)
    expected_formatted_code = textwrap.dedent("""\
        if a + b:
          pass
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testSimpleFunctions(self):
    unformatted_code = textwrap.dedent("""\
        def g():
          pass

        def f():
          pass
        """)
    expected_formatted_code = textwrap.dedent("""\
        def g():
          pass


        def f():
          pass
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testSimpleFunctionsWithTrailingComments(self):
    unformatted_code = textwrap.dedent("""\
        def g():  # Trailing comment
          if (xxxxxxxxxxxx.yyyyyyyy(zzzzzzzzzzzzz[0]) == 'aaaaaaaaaaa' and
              xxxxxxxxxxxx.yyyyyyyy(zzzzzzzzzzzzz[0].mmmmmmmm[0]) == 'bbbbbbb'):
            pass

        def f(  # Intermediate comment
        ):
          if (xxxxxxxxxxxx.yyyyyyyy(zzzzzzzzzzzzz[0]) == 'aaaaaaaaaaa' and
              xxxxxxxxxxxx.yyyyyyyy(zzzzzzzzzzzzz[0].mmmmmmmm[0]) == 'bbbbbbb'):
            pass
        """)
    expected_formatted_code = textwrap.dedent("""\
        def g():  # Trailing comment
          if (xxxxxxxxxxxx.yyyyyyyy(zzzzzzzzzzzzz[0]) == 'aaaaaaaaaaa' and
              xxxxxxxxxxxx.yyyyyyyy(zzzzzzzzzzzzz[0].mmmmmmmm[0]) == 'bbbbbbb'):
            pass


        def f(  # Intermediate comment
        ):
          if (xxxxxxxxxxxx.yyyyyyyy(zzzzzzzzzzzzz[0]) == 'aaaaaaaaaaa' and
              xxxxxxxxxxxx.yyyyyyyy(zzzzzzzzzzzzz[0].mmmmmmmm[0]) == 'bbbbbbb'):
            pass
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testBlankLinesAtEndOfFile(self):
    unformatted_code = textwrap.dedent("""\
        def foobar(): # foo
         pass



        """)
    expected_formatted_code = textwrap.dedent("""\
        def foobar():  # foo
          pass
    """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

    unformatted_code = textwrap.dedent("""\
        x = {  'a':37,'b':42,

        'c':927}

        """)
    expected_formatted_code = textwrap.dedent("""\
        x = {'a': 37, 'b': 42, 'c': 927}
    """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testMultipleUgliness(self):
    unformatted_code = textwrap.dedent("""\
        x = {  'a':37,'b':42,

        'c':927}

        y = 'hello ''world'
        z = 'hello '+'world'
        a = 'hello {}'.format('world')
        class foo  (     object  ):
          def f    (self   ):
            return       37*-+2
          def g(self, x,y=42):
              return y
        def f  (   a ) :
          return      37+-+a[42-x :  y**3]
        """)
    expected_formatted_code = textwrap.dedent("""\
        x = {'a': 37, 'b': 42, 'c': 927}

        y = 'hello ' 'world'
        z = 'hello ' + 'world'
        a = 'hello {}'.format('world')


        class foo(object):

          def f(self):
            return 37 * -+2

          def g(self, x, y=42):
            return y


        def f(a):
          return 37 + -+a[42 - x:y**3]
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testComments(self):
    unformatted_code = textwrap.dedent("""\
        class Foo(object):
          pass
        # End class Foo

        # Attached comment
        class Bar(object):
          pass

        global_assignment = 42

        # Comment attached to class with decorator.
        # Comment attached to class with decorator.
        @noop
        @noop
        class Baz(object):
          pass

        # Intermediate comment

        class Qux(object):
          pass
        """)
    expected_formatted_code = textwrap.dedent("""\
        class Foo(object):
          pass
        # End class Foo


        # Attached comment
        class Bar(object):
          pass


        global_assignment = 42


        # Comment attached to class with decorator.
        # Comment attached to class with decorator.
        @noop
        @noop
        class Baz(object):
          pass

        # Intermediate comment


        class Qux(object):
          pass
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testSingleComment(self):
    code = textwrap.dedent("""\
        # Thing 1
        """)
    uwlines = _ParseAndUnwrap(code)
    self.assertCodeEqual(code, reformatter.Reformat(uwlines))

  def testCommentsInDataLiteral(self):
    code = textwrap.dedent("""\
        def f():
          return collections.OrderedDict({
              # First comment.
              'fnord': 37,

              # Second comment.
              # Continuation of second comment.
              'bork': 42,

              # Ending comment.
          })
        """)
    uwlines = _ParseAndUnwrap(code)
    self.assertCodeEqual(code, reformatter.Reformat(uwlines))

  def testEndingWhitespaceAfterSimpleStatement(self):
    code = textwrap.dedent("""\
        import foo as bar
        # Thing 1
        # Thing 2
        """)
    uwlines = _ParseAndUnwrap(code)
    self.assertCodeEqual(code, reformatter.Reformat(uwlines))

  def testDocstrings(self):
    unformatted_code = textwrap.dedent('''\
        u"""Module-level docstring."""
        import os
        class Foo(object):

          """Class-level docstring."""
          # A comment for qux.
          def qux(self):


            """Function-level docstring.

            A multiline function docstring.
            """
            print('hello {}'.format('world'))
            return 42
        ''')
    expected_formatted_code = textwrap.dedent('''\
        u"""Module-level docstring."""
        import os


        class Foo(object):
          """Class-level docstring."""

          # A comment for qux.
          def qux(self):
            """Function-level docstring.

            A multiline function docstring.
            """
            print('hello {}'.format('world'))
            return 42
        ''')
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testDocstringAndMultilineComment(self):
    unformatted_code = textwrap.dedent('''\
        """Hello world"""
        # A multiline
        # comment
        class bar(object):
          """class docstring"""
          # class multiline
          # comment
          def foo(self):
            """Another docstring."""
            # Another multiline
            # comment
            pass
        ''')
    expected_formatted_code = textwrap.dedent('''\
        """Hello world"""


        # A multiline
        # comment
        class bar(object):
          """class docstring"""

          # class multiline
          # comment
          def foo(self):
            """Another docstring."""
            # Another multiline
            # comment
            pass
        ''')
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testMultilineDocstringAndMultilineComment(self):
    unformatted_code = textwrap.dedent('''\
        """Hello world

        RIP Dennis Richie.
        """
        # A multiline
        # comment
        class bar(object):
          """class docstring

          A classy class.
          """
          # class multiline
          # comment
          def foo(self):
            """Another docstring.

            A functional function.
            """
            # Another multiline
            # comment
            pass
        ''')
    expected_formatted_code = textwrap.dedent('''\
        """Hello world

        RIP Dennis Richie.
        """


        # A multiline
        # comment
        class bar(object):
          """class docstring

          A classy class.
          """

          # class multiline
          # comment
          def foo(self):
            """Another docstring.

            A functional function.
            """
            # Another multiline
            # comment
            pass
        ''')
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testTupleCommaBeforeLastParen(self):
    unformatted_code = textwrap.dedent("""\
        a = ( 1, )
        """)
    expected_formatted_code = textwrap.dedent("""\
        a = (1,)
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testNoBreakOutsideOfBracket(self):
    # FIXME(morbo): How this is formatted is not correct. But it's syntactically
    # correct.
    unformatted_code = textwrap.dedent("""\
        def f():
          assert port >= minimum, \
'Unexpected port %d when minimum was %d.' % (port, minimum)
        """)
    expected_formatted_code = textwrap.dedent("""\
        def f():
          assert port >= minimum, 'Unexpected port %d when minimum was %d.' % (port,
                                                                               minimum)
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testBlankLinesBeforeDecorators(self):
    unformatted_code = textwrap.dedent("""\
        @foo()
        class A(object):
          @bar()
          @baz()
          def x(self):
            pass
        """)
    expected_formatted_code = textwrap.dedent("""\
        @foo()
        class A(object):

          @bar()
          @baz()
          def x(self):
            pass
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testCommentBetweenDecorators(self):
    unformatted_code = textwrap.dedent("""\
        @foo()
        # frob
        @bar
        def x  (self):
            pass
        """)
    expected_formatted_code = textwrap.dedent("""\
        @foo()
        # frob
        @bar
        def x(self):
          pass
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testListComprehension(self):
    unformatted_code = textwrap.dedent("""\
        def given(y):
            [k for k in ()
              if k in y]
        """)
    expected_formatted_code = textwrap.dedent("""\
        def given(y):
          [k for k in () if k in y]
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testOpeningAndClosingBrackets(self):
    unformatted_code = textwrap.dedent("""\
        foo( ( 1, 2, 3, ) )
        """)
    expected_formatted_code = textwrap.dedent("""\
        foo((1, 2, 3,))
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testSingleLineFunctions(self):
    unformatted_code = textwrap.dedent("""\
        def foo():  return 42
        """)
    expected_formatted_code = textwrap.dedent("""\
        def foo():
          return 42
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testNoQueueSeletionInMiddleOfLine(self):
    # If the queue isn't properly consttructed, then a token in the middle of
    # the line may be selected as the one with least penalty. The tokens after
    # that one are then splatted at the end of the line with no formatting.
    # FIXME(morbo): The formatting here isn't ideal.
    unformatted_code = textwrap.dedent("""\
        find_symbol(node.type) + "< " + " ".join(find_pattern(n) for n in \
node.child) + " >"
        """)
    expected_formatted_code = textwrap.dedent("""\
        find_symbol(node.type) + "< " + " ".join(find_pattern(n)
                                                 for n in node.child) + " >"
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testNoSpacesBetweenSubscriptsAndCalls(self):
    unformatted_code = textwrap.dedent("""\
        aaaaaaaaaa = bbbbbbbb.ccccccccc() [42] (a, 2)
        """)
    expected_formatted_code = textwrap.dedent("""\
        aaaaaaaaaa = bbbbbbbb.ccccccccc()[42](a, 2)
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testNoSpacesBetweenOpeningBracketAndStartingOperator(self):
    # Unary operator.
    unformatted_code = textwrap.dedent("""\
        aaaaaaaaaa = bbbbbbbb.ccccccccc[ -1 ]( -42 )
        """)
    expected_formatted_code = textwrap.dedent("""\
        aaaaaaaaaa = bbbbbbbb.ccccccccc[-1](-42)
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

    # Varargs and kwargs.
    unformatted_code = textwrap.dedent("""\
        aaaaaaaaaa = bbbbbbbb.ccccccccc( *varargs )
        aaaaaaaaaa = bbbbbbbb.ccccccccc( **kwargs )
        """)
    expected_formatted_code = textwrap.dedent("""\
        aaaaaaaaaa = bbbbbbbb.ccccccccc(*varargs)
        aaaaaaaaaa = bbbbbbbb.ccccccccc(**kwargs)
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testMultilineCommentReformatted(self):
    unformatted_code = textwrap.dedent("""\
        if True:
            # This is a multiline
            # comment.
            pass
        """)
    expected_formatted_code = textwrap.dedent("""\
        if True:
          # This is a multiline
          # comment.
          pass
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testDictionaryMakerFormatting(self):
    unformatted_code = textwrap.dedent("""\
        _PYTHON_STATEMENTS = frozenset({
            lambda x, y: 'simple_stmt': 'small_stmt', 'expr_stmt': 'print_stmt', 'del_stmt':
            'pass_stmt', lambda: 'break_stmt': 'continue_stmt', 'return_stmt': 'raise_stmt',
            'yield_stmt': 'import_stmt', lambda: 'global_stmt': 'exec_stmt', 'assert_stmt':
            'if_stmt', 'while_stmt': 'for_stmt',
        })
        """)
    expected_formatted_code = textwrap.dedent("""\
        _PYTHON_STATEMENTS = frozenset({
            lambda x, y: 'simple_stmt': 'small_stmt',
            'expr_stmt': 'print_stmt',
            'del_stmt': 'pass_stmt',
            lambda: 'break_stmt': 'continue_stmt',
            'return_stmt': 'raise_stmt',
            'yield_stmt': 'import_stmt',
            lambda: 'global_stmt': 'exec_stmt',
            'assert_stmt': 'if_stmt',
            'while_stmt': 'for_stmt',
        })
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testSimpleMultilineCode(self):
    unformatted_code = textwrap.dedent("""\
        if True:
          aaaaaaaaaaaaaa.bbbbbbbbbbbbbb.ccccccc(zzzzzzzzzzzz, \
xxxxxxxxxxx, yyyyyyyyyyyy, vvvvvvvvv)
          aaaaaaaaaaaaaa.bbbbbbbbbbbbbb.ccccccc(zzzzzzzzzzzz, \
xxxxxxxxxxx, yyyyyyyyyyyy, vvvvvvvvv)
        """)
    expected_formatted_code = textwrap.dedent("""\
        if True:
          aaaaaaaaaaaaaa.bbbbbbbbbbbbbb.ccccccc(zzzzzzzzzzzz, xxxxxxxxxxx, yyyyyyyyyyyy,
                                                vvvvvvvvv)
          aaaaaaaaaaaaaa.bbbbbbbbbbbbbb.ccccccc(zzzzzzzzzzzz, xxxxxxxxxxx, yyyyyyyyyyyy,
                                                vvvvvvvvv)
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testMultilineComment(self):
    code = textwrap.dedent("""\
        if Foo:
          # Hello world
          # Yo man.
          # Yo man.
          # Yo man.
          # Yo man.
          a = 42
        """)
    uwlines = _ParseAndUnwrap(code)
    self.assertCodeEqual(code, reformatter.Reformat(uwlines))

  def testMultilineString(self):
    code = textwrap.dedent("""\
        code = textwrap.dedent('''\
            if Foo:
              # Hello world
              # Yo man.
              # Yo man.
              # Yo man.
              # Yo man.
              a = 42
            ''')
        """)
    uwlines = _ParseAndUnwrap(code)
    self.assertCodeEqual(code, reformatter.Reformat(uwlines))

    unformatted_code = textwrap.dedent('''\
        def f():
            email_text += """<html>This is a really long docstring that goes over the column limit and is multi-line.<br><br>
        <b>Czar: </b>"""+despot["Nicholas"]+"""<br>
        <b>Minion: </b>"""+serf["Dmitri"]+"""<br>
        <b>Residence: </b>"""+palace["Winter"]+"""<br>
        </body>
        </html>"""
        ''')
    expected_formatted_code = textwrap.dedent('''\
        def f():
          email_text += """<html>This is a really long docstring that goes over the column limit and is multi-line.<br><br>
        <b>Czar: </b>""" + despot["Nicholas"] + """<br>
        <b>Minion: </b>""" + serf["Dmitri"] + """<br>
        <b>Residence: </b>""" + palace["Winter"] + """<br>
        </body>
        </html>"""
        ''')
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testSimpleMultilineWithComments(self):
    code = textwrap.dedent("""\
        if (  # This is the first comment
            a and  # This is the second comment
            # This is the third comment
            b):  # A trailing comment
          # Whoa! A normal comment!!
          pass  # Another trailing comment
        """)
    uwlines = _ParseAndUnwrap(code)
    self.assertCodeEqual(code, reformatter.Reformat(uwlines))

  def testMatchingParenSplittingMatching(self):
    unformatted_code = textwrap.dedent("""\
        def f():
          raise RuntimeError('unable to find insertion point for target node',
                             (target,))
        """)
    expected_formatted_code = textwrap.dedent("""\
        def f():
          raise RuntimeError('unable to find insertion point for target node',
                             (target,))
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testContinuationIndent(self):
    unformatted_code = textwrap.dedent('''\
        class F:
          def _ProcessArgLists(self, node):
            """Common method for processing argument lists."""
            for child in node.children:
              if isinstance(child, pytree.Leaf):
                self._SetTokenSubtype(
                    child, subtype=_ARGLIST_TOKEN_TO_SUBTYPE.get(
                        child.value, format_token.Subtype.NONE))
        ''')
    expected_formatted_code = textwrap.dedent('''\
        class F:

          def _ProcessArgLists(self, node):
            """Common method for processing argument lists."""
            for child in node.children:
              if isinstance(child, pytree.Leaf):
                self._SetTokenSubtype(child,
                                      subtype=_ARGLIST_TOKEN_TO_SUBTYPE.get(
                                          child.value, format_token.Subtype.NONE))
        ''')
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testTrailingCommaAndBracket(self):
    unformatted_code = textwrap.dedent('''\
        a = { 42, }
        b = ( 42, )
        c = [ 42, ]
        ''')
    expected_formatted_code = textwrap.dedent('''\
        a = {42,}
        b = (42,)
        c = [42,]
        ''')
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testI18n(self):
    code = textwrap.dedent("""\
        N_('Some years ago - never mind how long precisely - having little or no money in my purse, and nothing particular to interest me on shore, I thought I would sail about a little and see the watery part of the world.')  # A comment is here.
        """)
    uwlines = _ParseAndUnwrap(code)
    self.assertCodeEqual(code, reformatter.Reformat(uwlines))

    code = textwrap.dedent("""\
        foo('Fake function call')  #. Some years ago - never mind how long precisely - having little or no money in my purse, and nothing particular to interest me on shore, I thought I would sail about a little and see the watery part of the world.
        """)
    uwlines = _ParseAndUnwrap(code)
    self.assertCodeEqual(code, reformatter.Reformat(uwlines))

  def testI18nCommentsInDataLiteral(self):
    code = textwrap.dedent("""\
        def f():
          return collections.OrderedDict({
              #. First i18n comment.
              'bork': 'foo',

              #. Second i18n comment.
              'snork': 'bar#.*=\\\\0',
          })
        """)
    uwlines = _ParseAndUnwrap(code)
    self.assertCodeEqual(code, reformatter.Reformat(uwlines))

  def testClosingBracketIndent(self):
    code = textwrap.dedent('''\
        def f():

          def g():
            while (
                xxxxxxxxxxxxxxxxxxxxx(yyyyyyyyyyyyy[zzzzz]) == 'aaaaaaaaaaa' and
                xxxxxxxxxxxxxxxxxxxxx(yyyyyyyyyyyyy[zzzzz].aaaaaaaa[0]) == 'bbbbbbb'):
              pass
        ''')
    uwlines = _ParseAndUnwrap(code)
    self.assertCodeEqual(code, reformatter.Reformat(uwlines))

  def testClosingBracketsInlinedInCall(self):
    unformatted_code = textwrap.dedent("""\
        class Foo(object):

          def bar(self):
            self.aaaaaaaa = xxxxxxxxxxxxxxxxxxx.yyyyyyyyyyyyy(
                self.cccccc.ddddddddd.eeeeeeee,
                options={
                    "forkforkfork": 1,
                    "borkborkbork": 2,
                    "corkcorkcork": 3,
                    "horkhorkhork": 4,
                    "porkporkpork": 5,
                    })
        """)
    expected_formatted_code = textwrap.dedent("""\
        class Foo(object):

          def bar(self):
            self.aaaaaaaa = xxxxxxxxxxxxxxxxxxx.yyyyyyyyyyyyy(
                self.cccccc.ddddddddd.eeeeeeee,
                options={
                    "forkforkfork": 1,
                    "borkborkbork": 2,
                    "corkcorkcork": 3,
                    "horkhorkhork": 4,
                    "porkporkpork": 5,
                })
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testLineWrapInForExpression(self):
    code = textwrap.dedent("""\
        class A:

          def x(self, node, name, n=1):
            for i, child in enumerate(itertools.ifilter(
                lambda c: pytree_utils.NodeName(c) == name, node.pre_order())):
              pass
        """)
    uwlines = _ParseAndUnwrap(code)
    self.assertCodeEqual(code, reformatter.Reformat(uwlines))

  def testFunctionCallContinuationLine(self):
    code = textwrap.dedent("""\
        class foo:

          def bar(self, node, name, n=1):
            if True:
              if True:
                return [(aaaaaaaaaa, bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb(
                    cccc, ddddddddddddddddddddddddddddddddddddd))]
        """)
    uwlines = _ParseAndUnwrap(code)
    self.assertCodeEqual(code, reformatter.Reformat(uwlines))

  def testI18nNonFormatting(self):
    code = textwrap.dedent("""\
        class F(object):

          def __init__(self, fieldname,
                       #. Error message indicating an invalid e-mail address.
                       message=N_('Please check your email address.'), **kwargs):
            pass
        """)
    uwlines = _ParseAndUnwrap(code)
    self.assertCodeEqual(code, reformatter.Reformat(uwlines))

  def testNoSpaceBetweenUnaryOpAndOpeningParen(self):
    code = textwrap.dedent("""\
        if ~(a or b):
          pass
        """)
    uwlines = _ParseAndUnwrap(code)
    self.assertCodeEqual(code, reformatter.Reformat(uwlines))

  def testCommentBeforeFuncDef(self):
    code = textwrap.dedent("""\
        class Foo(object):

          a = 42

          # This is a comment.
          def __init__(self,
                       xxxxxxx,
                       yyyyy=0,
                       zzzzzzz=None,
                       aaaaaaaaaaaaaaaaaa=False,
                       bbbbbbbbbbbbbbb=False):
            pass
        """)
    uwlines = _ParseAndUnwrap(code)
    self.assertCodeEqual(code, reformatter.Reformat(uwlines))

  def testExcessLineCountWithDefaultKeywords(self):
    unformatted_code = textwrap.dedent("""\
        class Fnord(object):
          def Moo(self):
            aaaaaaaaaaaaaaaa = self._bbbbbbbbbbbbbbbbbbbbbbb(
                ccccccccccccc=ccccccccccccc, ddddddd=ddddddd, eeee=eeee,
                fffff=fffff, ggggggg=ggggggg, hhhhhhhhhhhhh=hhhhhhhhhhhhh,
                iiiiiii=iiiiiiiiiiiiii)
        """)
    expected_formatted_code = textwrap.dedent("""\
        class Fnord(object):

          def Moo(self):
            aaaaaaaaaaaaaaaa = self._bbbbbbbbbbbbbbbbbbbbbbb(
                ccccccccccccc=ccccccccccccc,
                ddddddd=ddddddd,
                eeee=eeee,
                fffff=fffff,
                ggggggg=ggggggg,
                hhhhhhhhhhhhh=hhhhhhhhhhhhh,
                iiiiiii=iiiiiiiiiiiiii)
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testSpaceAfterNotOperator(self):
    code = textwrap.dedent("""\
        if not (this and that):
          pass
        """)
    uwlines = _ParseAndUnwrap(code)
    self.assertCodeEqual(code, reformatter.Reformat(uwlines))

  def testNoPenaltySplitting(self):
    code = textwrap.dedent("""\
        def f():
          if True:
            if True:
              python_files.extend(os.path.join(filename, f)
                                  for f in os.listdir(filename)
                                  if IsPythonFile(os.path.join(filename, f)))
        """)
    uwlines = _ParseAndUnwrap(code)
    self.assertCodeEqual(code, reformatter.Reformat(uwlines))

  def testExpressionPenalties(self):
    code = textwrap.dedent("""\
      def f():
        if ((left.value == '(' and right.value == ')') or
            (left.value == '[' and right.value == ']') or
            (left.value == '{' and right.value == '}')):
          return False
        """)
    uwlines = _ParseAndUnwrap(code)
    self.assertCodeEqual(code, reformatter.Reformat(uwlines))

  def testLineDepthOfSingleLineStatement(self):
    unformatted_code = textwrap.dedent("""\
        while True: continue
        for x in range(3): continue
        try: a = 42
        except: b = 42
        with open(a) as fd: a = fd.read()
        """)
    expected_formatted_code = textwrap.dedent("""\
        while True:
          continue
        for x in range(3):
          continue
        try:
          a = 42
        except:
          b = 42
        with open(a) as fd:
          a = fd.read()
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testSplitListWithTerminatingComma(self):
    unformatted_code = textwrap.dedent("""\
        FOO = ['bar', 'baz', 'mux', 'qux', 'quux', 'quuux', 'quuuux',
          'quuuuux', 'quuuuuux', 'quuuuuuux', lambda a, b: 37,]
        """)
    expected_formatted_code = textwrap.dedent("""\
        FOO = ['bar',
               'baz',
               'mux',
               'qux',
               'quux',
               'quuux',
               'quuuux',
               'quuuuux',
               'quuuuuux',
               'quuuuuuux',
               lambda a, b: 37,]
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testSplitListWithInterspersedComments(self):
    code = textwrap.dedent("""\
        FOO = ['bar',  # bar
               'baz',  # baz
               'mux',  # mux
               'qux',  # qux
               'quux',  # quux
               'quuux',  # quuux
               'quuuux',  # quuuux
               'quuuuux',  # quuuuux
               'quuuuuux',  # quuuuuux
               'quuuuuuux',  # quuuuuuux
               lambda a, b: 37  # lambda
              ]
        """)
    uwlines = _ParseAndUnwrap(code)
    self.assertCodeEqual(code, reformatter.Reformat(uwlines))

  def testRelativeImportStatements(self):
    code = textwrap.dedent("""\
        from ... import bork
        """)
    uwlines = _ParseAndUnwrap(code)
    self.assertCodeEqual(code, reformatter.Reformat(uwlines))

  def testSingleLineList(self):
    # A list on a single line should prefer to remain contiguous.
    unformatted_code = textwrap.dedent("""\
        bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb = aaaaaaaaaaa(
            ("...", "."), "..",
            ".............................................."
        )
        """)
    expected_formatted_code = textwrap.dedent("""\
        bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb = aaaaaaaaaaa(
            ("...", "."), "..", "..............................................")
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testBlankLinesBeforeFunctionsNotInColumnZero(self):
    unformatted_code = textwrap.dedent("""\
        import signal


        try:
          signal.SIGALRM
          # ..................................................................
          # ...............................................................


          def timeout(seconds=1):
            pass
        except:
          pass
        """)
    expected_formatted_code = textwrap.dedent("""\
        import signal

        try:
          signal.SIGALRM

          # ..................................................................
          # ...............................................................


          def timeout(seconds=1):
            pass
        except:
          pass
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testNoKeywordArgumentBreakage(self):
    code = textwrap.dedent("""\
        class A(object):

          def b(self):
            if self.aaaaaaaaaaaaaaaaaaaa not in self.bbbbbbbbbb(
                cccccccccccccccccccc=True):
              pass
        """)
    uwlines = _ParseAndUnwrap(code)
    self.assertCodeEqual(code, reformatter.Reformat(uwlines))

  def testTrailerOnSingleLine(self):
    code = textwrap.dedent("""\
        urlpatterns = patterns('', url(r'^$', 'homepage_view'),
                               url(r'^/login/$', 'login_view'),
                               url(r'^/login/$', 'logout_view'),
                               url(r'^/user/(?P<username>\\w+)/$', 'profile_view'))
        """)
    uwlines = _ParseAndUnwrap(code)
    self.assertCodeEqual(code, reformatter.Reformat(uwlines))

  def testIfConditionalParens(self):
    code = textwrap.dedent("""\
        class Foo:

          def bar():
            if True:
              if (child.type == grammar_token.NAME and
                  child.value in substatement_names):
                pass
        """)
    uwlines = _ParseAndUnwrap(code)
    self.assertCodeEqual(code, reformatter.Reformat(uwlines))

  def testContinuationMarkers(self):
    code = textwrap.dedent("""\
        text = "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Donec a diam lectus. "\\
               "Sed sit amet ipsum mauris. Maecenas congue ligula ac quam viverra nec consectetur "\\
               "ante hendrerit. Donec et mollis dolor. Praesent et diam eget libero egestas mattis "\\
               "sit amet vitae augue. Nam tincidunt congue enim, ut porta lorem lacinia consectetur. "\\
               "Donec ut libero sed arcu vehicula ultricies a non tortor. Lorem ipsum dolor sit amet"
        """)
    uwlines = _ParseAndUnwrap(code)
    self.assertCodeEqual(code, reformatter.Reformat(uwlines))

    code = textwrap.dedent("""\
        from __future__ import nested_scopes, generators, division, absolute_import, with_statement, \\
            print_function, unicode_literals
        """)
    uwlines = _ParseAndUnwrap(code)
    self.assertCodeEqual(code, reformatter.Reformat(uwlines))

    code = textwrap.dedent("""\
        if aaaaaaaaa == 42 and bbbbbbbbbbbbbb == 42 and \\
           cccccccc == 42:
          pass
        """)
    uwlines = _ParseAndUnwrap(code)
    self.assertCodeEqual(code, reformatter.Reformat(uwlines))

  def testCommentsWithContinuationMarkers(self):
    code = textwrap.dedent("""\
        def fn(arg):
          v = fn2(key1=True,
                  #c1
                  key2=arg)\\
                        .fn3()
        """)
    uwlines = _ParseAndUnwrap(code)
    self.assertCodeEqual(code, reformatter.Reformat(uwlines))

  def testEmptyContainers(self):
    code = textwrap.dedent("""\
        flags.DEFINE_list(
            'output_dirs', [],
            'Lorem ipsum dolor sit amet, consetetur adipiscing elit. Donec a diam lectus. '
            'Sed sit amet ipsum mauris. Maecenas congue.')
        """)
    uwlines = _ParseAndUnwrap(code)
    self.assertCodeEqual(code, reformatter.Reformat(uwlines))

  def testSplitStringsIfSurroundedByParens(self):
    unformatted_code = textwrap.dedent("""\
        a = foo.bar({'xxxxxxxxxxxxxxxxxxxxxxx' 'yyyyyyyyyyyyyyyyyyyyyyyyyy': baz[42]} + 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa' 'bbbbbbbbbbbbbbbbbbbbbbbbbb' 'cccccccccccccccccccccccccccccccc' 'ddddddddddddddddddddddddddddd')
        """)
    expected_formatted_code = textwrap.dedent("""\
        a = foo.bar({'xxxxxxxxxxxxxxxxxxxxxxx'
                     'yyyyyyyyyyyyyyyyyyyyyyyyyy': baz[42]} +
                    'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
                    'bbbbbbbbbbbbbbbbbbbbbbbbbb'
                    'cccccccccccccccccccccccccccccccc'
                    'ddddddddddddddddddddddddddddd')
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

    code = textwrap.dedent("""\
        a = 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa' \
'bbbbbbbbbbbbbbbbbbbbbbbbbb' 'cccccccccccccccccccccccccccccccc' \
'ddddddddddddddddddddddddddddd'
        """)
    uwlines = _ParseAndUnwrap(code)
    self.assertCodeEqual(code, reformatter.Reformat(uwlines))

  def testMultilineShebang(self):
    code = textwrap.dedent("""\
        #!/bin/sh
        if "true" : '''\'
        then

        export FOO=123
        exec /usr/bin/env python "$0" "$@"

        exit 127
        fi
        '''

        import os

        assert os.environ['FOO'] == '123'
        """)
    uwlines = _ParseAndUnwrap(code)
    self.assertCodeEqual(code, reformatter.Reformat(uwlines))

  def testNoSplittingAroundTermOperators(self):
    code = textwrap.dedent("""\
        a_very_long_function_call_yada_yada_etc_etc_etc(long_arg1,
                                                        long_arg2 / long_arg3)
        """)
    uwlines = _ParseAndUnwrap(code)
    self.assertCodeEqual(code, reformatter.Reformat(uwlines))

  def testNoSplittingWithinSubscriptList(self):
    code = textwrap.dedent("""\
        somequitelongvariablename.somemember[(a, b)] = {
            'somelongkey': 1,
            'someotherlongkey': 2
        }
        """)
    uwlines = _ParseAndUnwrap(code)
    self.assertCodeEqual(code, reformatter.Reformat(uwlines))

  def testExcessCharacters(self):
    code = textwrap.dedent("""\
        class foo:

          def bar(self):
            self.write(s=['%s%s %s' % ('many of really', 'long strings',
                                       '+ just makes up 81')])
        """)
    uwlines = _ParseAndUnwrap(code)
    self.assertCodeEqual(code, reformatter.Reformat(uwlines))

  def testDictSetGenerator(self):
    code = textwrap.dedent("""\
        foo = {
            variable: 'hello world. How are you today?'
            for variable in fnord if variable != 37
        }
        """)
    uwlines = _ParseAndUnwrap(code)
    self.assertCodeEqual(code, reformatter.Reformat(uwlines))

  def testUnaryOpInDictionaryValue(self):
    code = textwrap.dedent("""\
        beta = "123"

        test = {'alpha': beta[-1]}

        print(beta[-1])
        """)
    uwlines = _ParseAndUnwrap(code)
    self.assertCodeEqual(code, reformatter.Reformat(uwlines))

  def testUnaryNotOperator(self):
    code = textwrap.dedent("""\
        if True:
          if True:
            if True:
              if True:
                remote_checksum = self.get_checksum(conn, tmp, dest, inject,
                                                    not directory_prepended, source)
        """)
    uwlines = _ParseAndUnwrap(code)
    self.assertCodeEqual(code, reformatter.Reformat(uwlines))

  def testRelaxArraySubscriptAffinity(self):
    code = textwrap.dedent("""\
        class A(object):

          def f(self, aaaaaaaaa, bbbbbbbbbbbbb, row):
            if True:
              if True:
                if True:
                  if True:
                    if row[4] is None or row[5] is None:
                      bbbbbbbbbbbbb['..............'] = row[
                          5] if row[5] is not None else 5
        """)
    uwlines = _ParseAndUnwrap(code)
    self.assertCodeEqual(code, reformatter.Reformat(uwlines))

  def testFunctionCallInDict(self):
    code = "a = {'a': b(c=d, **e)}\n"
    uwlines = _ParseAndUnwrap(code)
    self.assertCodeEqual(code, reformatter.Reformat(uwlines))

  def testFunctionCallInNestedDict(self):
    code = "a = {'a': {'a': {'a': b(c=d, **e)}}}\n"
    uwlines = _ParseAndUnwrap(code)
    self.assertCodeEqual(code, reformatter.Reformat(uwlines))

  def testUnbreakableNot(self):
    code = textwrap.dedent("""\
        def test():
          if not "Foooooooooooooooooooooooooooooo" or "Foooooooooooooooooooooooooooooo" == "Foooooooooooooooooooooooooooooo":
            pass
        """)
    uwlines = _ParseAndUnwrap(code)
    self.assertCodeEqual(code, reformatter.Reformat(uwlines))

  def testSplitListWithComment(self):
    code = textwrap.dedent("""\
      a = [
          'a',
          'b',
          'c'  # hello world
      ]
      """)
    uwlines = _ParseAndUnwrap(code)
    self.assertCodeEqual(code, reformatter.Reformat(uwlines))

  def testOverColumnLimit(self):
    unformatted_code = textwrap.dedent("""\
      class Test:

        def testSomething(self):
          expected = {
              ('aaaaaaaaaaaaa', 'bbbb'): 'ccccccccccccccccccccccccccccccccccccccccccc',
              ('aaaaaaaaaaaaa', 'bbbb'): 'ccccccccccccccccccccccccccccccccccccccccccc',
              ('aaaaaaaaaaaaa', 'bbbb'): 'ccccccccccccccccccccccccccccccccccccccccccc',
          }
        """)
    expected_formatted_code = textwrap.dedent("""\
      class Test:

        def testSomething(self):
          expected = {
              ('aaaaaaaaaaaaa',
               'bbbb'): 'ccccccccccccccccccccccccccccccccccccccccccc',
              ('aaaaaaaaaaaaa',
               'bbbb'): 'ccccccccccccccccccccccccccccccccccccccccccc',
              ('aaaaaaaaaaaaa',
               'bbbb'): 'ccccccccccccccccccccccccccccccccccccccccccc',
          }
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testEndingComment(self):
    code = textwrap.dedent("""\
      a = f(a="something",
            b="something requiring comment which is quite long",  # comment about b (pushes line over 79)
            c="something else, about which comment doesn't make sense")
      """)
    uwlines = _ParseAndUnwrap(code)
    self.assertCodeEqual(code, reformatter.Reformat(uwlines))

  def testContinuationSpaceRetention(self):
    code = textwrap.dedent("""\
      def fn():
        return module \\
               .method(Object(data,
                   fn2(arg)
               ))
      """)
    uwlines = _ParseAndUnwrap(code)
    self.assertCodeEqual(code, reformatter.Reformat(uwlines))

  def testIfExpressionWithFunctionCall(self):
    code = textwrap.dedent("""\
      if x or z.y(a,
                  c,
                  aaaaaaaaaaaaaaaaaaaaa=aaaaaaaaaaaaaaaaaa,
                  bbbbbbbbbbbbbbbbbbbbb=bbbbbbbbbbbbbbbbbb):
        pass
      """)
    uwlines = _ParseAndUnwrap(code)
    self.assertCodeEqual(code, reformatter.Reformat(uwlines))

  def testUnformattedAfterMultilineString(self):
    code = textwrap.dedent("""\
      def foo():
        com_text = \\
      '''
      TEST
      ''' % (input_fname, output_fname)
      """)
    uwlines = _ParseAndUnwrap(code)
    self.assertCodeEqual(code, reformatter.Reformat(uwlines))

  def testNoSpacesAroundKeywordDefaultValues(self):
    code = textwrap.dedent("""\
      sources = {
          'json': request.get_json(silent=True) or {},
          'json2': request.get_json(silent=True),
      }
      json = request.get_json(silent=True) or {}
      """)
    uwlines = _ParseAndUnwrap(code)
    self.assertCodeEqual(code, reformatter.Reformat(uwlines))

  def testNoSplittingBeforeEndingSubscriptBracket(self):
    unformatted_code = textwrap.dedent("""\
        if True:
          if True:
            status = cf.describe_stacks(StackName=stackname)[u'Stacks'][0][u'StackStatus']
        """)
    expected_formatted_code = textwrap.dedent("""\
        if True:
          if True:
            status = cf.describe_stacks(
                StackName=stackname)[u'Stacks'][0][u'StackStatus']
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testNoSplittingOnSingleArgument(self):
    unformatted_code = textwrap.dedent("""\
        xxxxxxxxxxxxxx = (re.search(r'(\\d+\\.\\d+\\.\\d+\\.)\\d+',
                                    aaaaaaa.bbbbbbbbbbbb).group(1) +
                          re.search(r'\\d+\\.\\d+\\.\\d+\\.(\\d+)',
                                    ccccccc).group(1))
        xxxxxxxxxxxxxx = (re.search(r'(\\d+\\.\\d+\\.\\d+\\.)\\d+',
                                    aaaaaaa.bbbbbbbbbbbb).group(a.b) +
                          re.search(r'\\d+\\.\\d+\\.\\d+\\.(\\d+)',
                                    ccccccc).group(c.d))
        """)
    expected_formatted_code = textwrap.dedent("""\
        xxxxxxxxxxxxxx = (
            re.search(r'(\\d+\\.\\d+\\.\\d+\\.)\\d+', aaaaaaa.bbbbbbbbbbbb).group(1) +
            re.search(r'\\d+\\.\\d+\\.\\d+\\.(\\d+)', ccccccc).group(1))
        xxxxxxxxxxxxxx = (
            re.search(r'(\\d+\\.\\d+\\.\\d+\\.)\\d+', aaaaaaa.bbbbbbbbbbbb).group(a.b) +
            re.search(r'\\d+\\.\\d+\\.\\d+\\.(\\d+)', ccccccc).group(c.d))
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testSplittingArraysSensibly(self):
    unformatted_code = textwrap.dedent("""\
        while True:
          while True:
            aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa = list['bbbbbbbbbbbbbbbbbbbbbbbbb'].split(',')
            aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa = list('bbbbbbbbbbbbbbbbbbbbbbbbb').split(',')
        """)
    expected_formatted_code = textwrap.dedent("""\
        while True:
          while True:
            aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa = list[
                'bbbbbbbbbbbbbbbbbbbbbbbbb'].split(',')
            aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa = list(
                'bbbbbbbbbbbbbbbbbbbbbbbbb').split(',')
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testComprehensionForAndIf(self):
    unformatted_code = textwrap.dedent("""\
        class f:

          def __repr__(self):
            tokens_repr = ','.join(['{0}({1!r})'.format(tok.name, tok.value) for tok in self._tokens])
        """)
    expected_formatted_code = textwrap.dedent("""\
        class f:

          def __repr__(self):
            tokens_repr = ','.join(['{0}({1!r})'.format(tok.name, tok.value)
                                    for tok in self._tokens])
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testFunctionCallArguments(self):
    unformatted_code = textwrap.dedent("""\
        def f():
          if True:
            pytree_utils.InsertNodesBefore(_CreateCommentsFromPrefix(
                comment_prefix, comment_lineno, comment_column,
                standalone=True), ancestor_at_indent)
            pytree_utils.InsertNodesBefore(_CreateCommentsFromPrefix(
                comment_prefix, comment_lineno, comment_column,
                standalone=True))
        """)
    expected_formatted_code = textwrap.dedent("""\
        def f():
          if True:
            pytree_utils.InsertNodesBefore(
                _CreateCommentsFromPrefix(comment_prefix,
                                          comment_lineno,
                                          comment_column,
                                          standalone=True),
                ancestor_at_indent)
            pytree_utils.InsertNodesBefore(_CreateCommentsFromPrefix(comment_prefix,
                                                                     comment_lineno,
                                                                     comment_column,
                                                                     standalone=True))
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testBinaryOperators(self):
    unformatted_code = textwrap.dedent("""\
        a = b ** 37
        """)
    expected_formatted_code = textwrap.dedent("""\
        a = b**37
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testBinaryOperators(self):
    code = textwrap.dedent("""\
      def f():
        if True:
          if (self.stack[-1].split_before_closing_bracket and
              # FIXME(morbo): Use the 'matching_bracket' instead of this.
              # FIXME(morbo): Don't forget about tuples!
              current.value in ']}'):
            pass
      """)
    uwlines = _ParseAndUnwrap(code)
    self.assertCodeEqual(code, reformatter.Reformat(uwlines))

  def testContiguousList(self):
    code = textwrap.dedent("""\
      [retval1, retval2] = a_very_long_function(argument_1, argument2, argument_3,
                                                argument_4)
      """)
    uwlines = _ParseAndUnwrap(code)
    self.assertCodeEqual(code, reformatter.Reformat(uwlines))

  def testArgsAndKwargsFormatting(self):
    code = textwrap.dedent("""\
      a(a=aaaaaaaaaaaaaaaaaaaaa,
        b=aaaaaaaaaaaaaaaaaaaaaaaa,
        c=aaaaaaaaaaaaaaaaaa,
        *d,
        **e)
      """)
    uwlines = _ParseAndUnwrap(code)
    self.assertCodeEqual(code, reformatter.Reformat(uwlines))

  def testCommentColumnLimitOverflow(self):
    code = textwrap.dedent("""\
      def f():
        if True:
          TaskManager.get_tags = MagicMock(
              name='get_tags_mock',
              return_value=[157031694470475],
              # side_effect=[(157031694470475), (157031694470475),],
          )
      """)
    uwlines = _ParseAndUnwrap(code)
    self.assertCodeEqual(code, reformatter.Reformat(uwlines))

  def testMultilineLambdas(self):
    try:
      style.SetGlobalStyle(style.CreateStyleFromConfig(
          '{based_on_style: chromium, allow_multiline_lambdas: true}'))
      unformatted_code = textwrap.dedent("""\
          class SomeClass(object):
            do_something = True

            def succeeded(self, dddddddddddddd):
              d = defer.succeed(None)

              if self.do_something:
                d.addCallback(lambda _: self.aaaaaa.bbbbbbbbbbbbbbbb.cccccccccccccccccccccccccccccccc(dddddddddddddd))
              return d
          """)
      expected_formatted_code = textwrap.dedent("""\
          class SomeClass(object):
            do_something = True

            def succeeded(self, dddddddddddddd):
              d = defer.succeed(None)

              if self.do_something:
                d.addCallback(lambda _: self.aaaaaa.bbbbbbbbbbbbbbbb.
                              cccccccccccccccccccccccccccccccc(dddddddddddddd))
              return d
          """)
      uwlines = _ParseAndUnwrap(unformatted_code)
      self.assertCodeEqual(expected_formatted_code,
                           reformatter.Reformat(uwlines))
    finally:
      style.SetGlobalStyle(style.CreateChromiumStyle())

  def testStableDictionaryFormatting(self):
    try:
      style.SetGlobalStyle(style.CreateStyleFromConfig(
          '{based_on_style: pep8, indent_width: 2, '
          'continuation_indent_width: 4, indent_dictionary_value: True}'))
      code = textwrap.dedent("""\
          class A(object):
            def method(self):
              filters = {
                  'expressions': [
                      {'field': {
                          'search_field':
                              {'user_field': 'latest_party__number_of_guests'},
                      }}
                  ]
              }
          """)
      uwlines = _ParseAndUnwrap(code)
      reformatted_code = reformatter.Reformat(uwlines)
      self.assertCodeEqual(code, reformatted_code)

      uwlines = _ParseAndUnwrap(reformatted_code)
      reformatted_code = reformatter.Reformat(uwlines)
      self.assertCodeEqual(code, reformatted_code)
    finally:
      style.SetGlobalStyle(style.CreateChromiumStyle())

  def testDontSplitKeywordValueArguments(self):
    code = textwrap.dedent("""\
      def mark_game_scored(gid):
        _connect.execute(_games.update().where(_games.c.gid == gid).values(
            scored=True))
      """)
    uwlines = _ParseAndUnwrap(code)
    self.assertCodeEqual(code, reformatter.Reformat(uwlines))

  def testDontAddBlankLineAfterMultilineString(self):
    code = textwrap.dedent("""\
      query = '''SELECT id 
      FROM table 
      WHERE day in {}'''
      days = ",".join(days)
      """)
    uwlines = _ParseAndUnwrap(code)
    self.assertCodeEqual(code, reformatter.Reformat(uwlines))

  def testFormattingListComprehensions(self):
    code = textwrap.dedent("""\
      def a():
        if True:
          if True:
            if True:
              columns = [x for x, y in self._heap_this_is_very_long
                         if x.route[0] == choice]
              self._heap = [x for x in self._heap if x.route and x.route[0] == choice]
      """)
    uwlines = _ParseAndUnwrap(code)
    self.assertCodeEqual(code, reformatter.Reformat(uwlines))

  def testNoSplittingWhenBinPacking(self):
    try:
      style.SetGlobalStyle(style.CreateStyleFromConfig(
          '{based_on_style: pep8, indent_width: 2, '
          'continuation_indent_width: 4, indent_dictionary_value: True, '
          'dedent_closing_brackets: True, split_before_named_assigns: False}'))
      code = textwrap.dedent("""\
          a_very_long_function_name(
              long_argument_name_1=1,
              long_argument_name_2=2,
              long_argument_name_3=3,
              long_argument_name_4=4,
          )

          a_very_long_function_name(
              long_argument_name_1=1, long_argument_name_2=2, long_argument_name_3=3,
              long_argument_name_4=4
          )
          """)
      uwlines = _ParseAndUnwrap(code)
      reformatted_code = reformatter.Reformat(uwlines)
      self.assertCodeEqual(code, reformatted_code)

      uwlines = _ParseAndUnwrap(reformatted_code)
      reformatted_code = reformatter.Reformat(uwlines)
      self.assertCodeEqual(code, reformatted_code)
    finally:
      style.SetGlobalStyle(style.CreateChromiumStyle())


class BuganizerFixes(ReformatterTest):

  @classmethod
  def setUpClass(cls):
    style.SetGlobalStyle(style.CreateChromiumStyle())

  def testB26382315(self):
    code = textwrap.dedent("""\
        @hello_world
        # This is a first comment

        # Comment
        def foo():
          pass
        """)
    uwlines = _ParseAndUnwrap(code)
    self.assertCodeEqual(code, reformatter.Reformat(uwlines))

  def testB27616132(self):
    unformatted_code = textwrap.dedent("""\
        if True:
          query.fetch_page.assert_has_calls([
              mock.call(100,
                        start_cursor=None),
              mock.call(100,
                        start_cursor=cursor_1),
              mock.call(100,
                        start_cursor=cursor_2),
          ])
        """)
    expected_formatted_code = textwrap.dedent("""\
        if True:
          query.fetch_page.assert_has_calls([
              mock.call(100, start_cursor=None),
              mock.call(100, start_cursor=cursor_1),
              mock.call(100, start_cursor=cursor_2),
          ])
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testB27590179(self):
    unformatted_code = textwrap.dedent("""\
        if True:
          if True:
            self.aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa = (
                { True:
                     self.bbb.cccccccccc(ddddddddddddddddddddddd.eeeeeeeeeeeeeeeeeeeeee),
                 False:
                     self.bbb.cccccccccc(ddddddddddddddddddddddd.eeeeeeeeeeeeeeeeeeeeee)
                })
        """)
    expected_formatted_code = textwrap.dedent("""\
        if True:
          if True:
            self.aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa = ({
                True:
                    self.bbb.cccccccccc(ddddddddddddddddddddddd.eeeeeeeeeeeeeeeeeeeeee),
                False:
                    self.bbb.cccccccccc(ddddddddddddddddddddddd.eeeeeeeeeeeeeeeeeeeeee)
            })
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testB27266946(self):
    unformatted_code = textwrap.dedent("""\
        def _():
          aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa = (self.bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb.cccccccccccccccccccccccccccccccccccc)
        """)
    expected_formatted_code = textwrap.dedent("""\
        def _():
          aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa = (
              self.bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb.
              cccccccccccccccccccccccccccccccccccc)
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testB25505359(self):
    code = textwrap.dedent("""\
        _EXAMPLE = {
            'aaaaaaaaaaaaaa': [
                {'bbbb': 'cccccccccccccccccccccc',
                 'dddddddddddd': [
                 ]}, {'bbbb': 'ccccccccccccccccccc',
                      'dddddddddddd': [
                      ]}
            ]
        }
        """)
    uwlines = _ParseAndUnwrap(code)
    self.assertCodeEqual(code, reformatter.Reformat(uwlines))

  def testB25324261(self):
    code = textwrap.dedent("""\
        aaaaaaaaa = set(bbbb.cccc
                        for ddd in eeeeee.fffffffffff.gggggggggggggggg
                        for cccc in ddd.specification)
        """)
    uwlines = _ParseAndUnwrap(code)
    self.assertCodeEqual(code, reformatter.Reformat(uwlines))

  def testB25136704(self):
    code = textwrap.dedent("""\
        class f:

          def test(self):
            self.bbbbbbb[0][
                'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
                {'xxxxxx': 'yyyyyy'}] = cccccc.ddd('1m', '10x1+1')
        """)
    uwlines = _ParseAndUnwrap(code)
    self.assertCodeEqual(code, reformatter.Reformat(uwlines))

  def testB25165602(self):
    code = textwrap.dedent("""\
        def f():
          ids = {u: i for u, i in zip(self.aaaaa, xrange(42, 42 + len(self.aaaaaa)))}
        """)
    uwlines = _ParseAndUnwrap(code)
    self.assertCodeEqual(code, reformatter.Reformat(uwlines))

  def testB25157123(self):
    code = textwrap.dedent("""\
        def ListArgs():
          FairlyLongMethodName(
              [relatively_long_identifier_for_a_list],
              another_argument_with_a_long_identifier)
        """)
    uwlines = _ParseAndUnwrap(code)
    self.assertCodeEqual(code, reformatter.Reformat(uwlines))

  def testB25136820(self):
    unformatted_code = textwrap.dedent("""\
        def foo():
          return collections.OrderedDict({
              # Preceding comment.
              'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa':
              '$bbbbbbbbbbbbbbbbbbbbbbbb',
          })
        """)
    expected_formatted_code = textwrap.dedent("""\
        def foo():
          return collections.OrderedDict({
              # Preceding comment.
              'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa':
                  '$bbbbbbbbbbbbbbbbbbbbbbbb',
          })
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testB25131481(self):
    unformatted_code = textwrap.dedent("""\
        APPARENT_ACTIONS = ('command_type', {
            'materialize': lambda x: some_type_of_function('materialize ' + x.command_def),
            '#': lambda x: x  # do nothing
        })
        """)
    expected_formatted_code = textwrap.dedent("""\
        APPARENT_ACTIONS = (
            'command_type',
            {
                'materialize':
                    lambda x: some_type_of_function('materialize ' + x.command_def),
                '#': lambda x: x  # do nothing
            })
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testB23445244(self):
    unformatted_code = textwrap.dedent("""\
        def foo():
          if True:
            return xxxxxxxxxxxxxxxx(
                command,
                extra_env={
                    "OOOOOOOOOOOOOOOOOOOOO": FLAGS.zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz,
                    "PPPPPPPPPPPPPPPPPPPPP":
                        FLAGS.aaaaaaaaaaaaaa + FLAGS.bbbbbbbbbbbbbbbbbbb,
                })
        """)
    expected_formatted_code = textwrap.dedent("""\
        def foo():
          if True:
            return xxxxxxxxxxxxxxxx(
                command,
                extra_env={
                    "OOOOOOOOOOOOOOOOOOOOO":
                        FLAGS.zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz,
                    "PPPPPPPPPPPPPPPPPPPPP": FLAGS.aaaaaaaaaaaaaa +
                                             FLAGS.bbbbbbbbbbbbbbbbbbb,
                })
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testB20559654(self):
    unformatted_code = textwrap.dedent("""\
      class A(object):

        def foo(self):
          unused_error, result = server.Query(
              ['AA BBBB CCC DDD EEEEEEEE X YY ZZZZ FFF EEE AAAAAAAA'],
              aaaaaaaaaaa=True, bbbbbbbb=None)
        """)
    expected_formatted_code = textwrap.dedent("""\
      class A(object):

        def foo(self):
          unused_error, result = server.Query(
              ['AA BBBB CCC DDD EEEEEEEE X YY ZZZZ FFF EEE AAAAAAAA'],
              aaaaaaaaaaa=True,
              bbbbbbbb=None)
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testB23943842(self):
    unformatted_code = textwrap.dedent("""\
        class F():
          def f():
            self.assertDictEqual(
                accounts, {
                    'foo':
                    {'account': 'foo',
                     'lines': 'l1\\nl2\\nl3\\n1 line(s) were elided.'},
                    'bar': {'account': 'bar',
                            'lines': 'l5\\nl6\\nl7'},
                    'wiz': {'account': 'wiz',
                            'lines': 'l8'}
                })
        """)
    expected_formatted_code = textwrap.dedent("""\
        class F():

          def f():
            self.assertDictEqual(accounts, {
                'foo': {'account': 'foo',
                        'lines': 'l1\\nl2\\nl3\\n1 line(s) were elided.'},
                'bar': {'account': 'bar',
                        'lines': 'l5\\nl6\\nl7'},
                'wiz': {'account': 'wiz',
                        'lines': 'l8'}
            })
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testB20551180(self):
    unformatted_code = textwrap.dedent("""\
        def foo():
          if True:
            return (struct.pack('aaaa', bbbbbbbbbb, ccccccccccccccc, dddddddd) + eeeeeee)
        """)
    expected_formatted_code = textwrap.dedent("""\
        def foo():
          if True:
            return (
                struct.pack('aaaa', bbbbbbbbbb, ccccccccccccccc, dddddddd) + eeeeeee)
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testB23944849(self):
    unformatted_code = textwrap.dedent("""\
        class A(object):
          def xxxxxxxxx(self, aaaaaaa, bbbbbbb=ccccccccccc, dddddd=300, eeeeeeeeeeeeee=None, fffffffffffffff=0):
            pass
        """)
    expected_formatted_code = textwrap.dedent("""\
        class A(object):

          def xxxxxxxxx(self,
                        aaaaaaa,
                        bbbbbbb=ccccccccccc,
                        dddddd=300,
                        eeeeeeeeeeeeee=None,
                        fffffffffffffff=0):
            pass
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testB23935890(self):
    unformatted_code = textwrap.dedent("""\
        class F():
          def functioni(self, aaaaaaa, bbbbbbb, cccccc, dddddddddddddd, eeeeeeeeeeeeeee):
            pass
        """)
    expected_formatted_code = textwrap.dedent("""\
        class F():

          def functioni(self, aaaaaaa, bbbbbbb, cccccc, dddddddddddddd,
                        eeeeeeeeeeeeeee):
            pass
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testB28414371(self):
    code = textwrap.dedent("""\
        def _():
          return ((m.fffff(
              m.rrr('mmmmmmmmmmmmmmmm', 'ssssssssssssssssssssssssss'), ffffffffffffffff)
                   | m.wwwwww(m.ddddd('1h'))
                   | m.ggggggg(bbbbbbbbbbbbbbb)
                   | m.ppppp(
                       (1 - m.ffffffffffffffff(llllllllllllllllllllll * 1000000, m.vvv))
                       * m.ddddddddddddddddd(m.vvv)),
                   m.fffff(
                       m.rrr('mmmmmmmmmmmmmmmm', 'sssssssssssssssssssssss'),
                       dict(ffffffffffffffff,
                            **{
                                'mmmmmm:ssssss': m.rrrrrrrrrrr('|'.join(iiiiiiiiiiiiii),
                                                               iiiiii=True)
                            }))
                   | m.wwwwww(m.rrrr('1h'))
                   | m.ggggggg(bbbbbbbbbbbbbbb))
                  | m.jjjj()
                  | m.ppppp(m.vvv[0] + m.vvv[1]))
        """)
    uwlines = _ParseAndUnwrap(code)
    self.assertCodeEqual(code, reformatter.Reformat(uwlines))

  def testB20127686(self):
    code = textwrap.dedent("""\
        def f():
          if True:
            return ((m.fffff(
                m.rrr('xxxxxxxxxxxxxxxx',
                      'yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy'),
                mmmmmmmm)
                     | m.wwwwww(m.rrrr(self.tttttttttt, self.mmmmmmmmmmmmmmmmmmmmm))
                     | m.ggggggg(self.gggggggg, m.sss()), m.fffff('aaaaaaaaaaaaaaaa')
                     | m.wwwwww(m.ddddd(self.tttttttttt, self.mmmmmmmmmmmmmmmmmmmmm))
                     | m.ggggggg(self.gggggggg))
                    | m.jjjj()
                    | m.ppppp(m.VAL[0] / m.VAL[1]))
        """)
    uwlines = _ParseAndUnwrap(code)
    self.assertCodeEqual(code, reformatter.Reformat(uwlines))

  def testB20016122(self):
    try:
      style.SetGlobalStyle(style.CreateStyleFromConfig(
          '{based_on_style: chromium, SPLIT_BEFORE_LOGICAL_OPERATOR: True}'))
      code = textwrap.dedent("""\
          class foo():

            def __eq__(self, other):
              return (isinstance(other, type(self))
                      and self.xxxxxxxxxxx == other.xxxxxxxxxxx
                      and self.xxxxxxxx == other.xxxxxxxx
                      and self.aaaaaaaaaaaa == other.aaaaaaaaaaaa
                      and self.bbbbbbbbbbb == other.bbbbbbbbbbb
                      and self.ccccccccccccccccc == other.ccccccccccccccccc
                      and self.ddddddddddddddddddddddd == other.ddddddddddddddddddddddd
                      and self.eeeeeeeeeeee == other.eeeeeeeeeeee
                      and self.ffffffffffffff == other.time_completed
                      and self.gggggg == other.gggggg and self.hhh == other.hhh
                      and len(self.iiiiiiii) == len(other.iiiiiiii)
                      and all(jjjjjjj in other.iiiiiiii for jjjjjjj in self.iiiiiiii))
          """)
      uwlines = _ParseAndUnwrap(code)
      self.assertCodeEqual(code, reformatter.Reformat(uwlines))
    finally:
      style.SetGlobalStyle(style.CreateChromiumStyle())

  def testB22527411(self):
    unformatted_code = textwrap.dedent("""\
        def f():
          if True:
            aaaaaa.bbbbbbbbbbbbbbbbbbbb[-1].cccccccccccccc.ddd().eeeeeeee(ffffffffffffff)
        """)
    expected_formatted_code = textwrap.dedent("""\
        def f():
          if True:
            aaaaaa.bbbbbbbbbbbbbbbbbbbb[-1].cccccccccccccc.ddd().eeeeeeee(
                ffffffffffffff)
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testB20849933(self):
    code = textwrap.dedent("""\
        def main(unused_argv):
          if True:
            aaaaaaaa = {
                'xxx': '%s/cccccc/ddddddddddddddddddd.jar' %
                       (eeeeee.FFFFFFFFFFFFFFFFFF),
            }
        """)
    uwlines = _ParseAndUnwrap(code)
    self.assertCodeEqual(code, reformatter.Reformat(uwlines))

  def testB20813997(self):
    code = textwrap.dedent("""\
        def myfunc_1():
          myarray = numpy.zeros((2, 2, 2))
          print(myarray[:, 1, :])
        """)
    uwlines = _ParseAndUnwrap(code)
    self.assertCodeEqual(code, reformatter.Reformat(uwlines))

  def testB20605036(self):
    code = textwrap.dedent("""\
        foo = {
            'aaaa': {
                # A comment for no particular reason.
                'xxxxxxxx': 'bbbbbbbbb',
                'yyyyyyyyyyyyyyyyyy': 'cccccccccccccccccccccccccccccc'
                                      'dddddddddddddddddddddddddddddddddddddddddd',
            }
        }
        """)
    uwlines = _ParseAndUnwrap(code)
    self.assertCodeEqual(code, reformatter.Reformat(uwlines))

  def testB20562732(self):
    code = textwrap.dedent("""\
        foo = [
            # Comment about first list item
            'First item',
            # Comment about second list item
            'Second item',
        ]
        """)
    uwlines = _ParseAndUnwrap(code)
    self.assertCodeEqual(code, reformatter.Reformat(uwlines))

  def testB20128830(self):
    code = textwrap.dedent("""\
        a = {
            'xxxxxxxxxxxxxxxxxxxx': {
                'aaaa': 'mmmmmmm',
                'bbbbb': 'mmmmmmmmmmmmmmmmmmmmm',
                'cccccccccc': [
                    'nnnnnnnnnnn',
                    'ooooooooooo',
                    'ppppppppppp',
                    'qqqqqqqqqqq',
                ],
            },
        }
        """)
    uwlines = _ParseAndUnwrap(code)
    self.assertCodeEqual(code, reformatter.Reformat(uwlines))

  def testB20073838(self):
    code = textwrap.dedent("""\
        class DummyModel(object):

          def do_nothing(self, class_1_count):
            if True:
              class_0_count = num_votes - class_1_count
              return ('{class_0_name}={class_0_count}, {class_1_name}={class_1_count}'
                      .format(class_0_name=self.class_0_name,
                              class_0_count=class_0_count,
                              class_1_name=self.class_1_name,
                              class_1_count=class_1_count))
        """)
    uwlines = _ParseAndUnwrap(code)
    self.assertCodeEqual(code, reformatter.Reformat(uwlines))

  def testB19626808(self):
    code = textwrap.dedent("""\
        if True:
          aaaaaaaaaaaaaaaaaaaaaaa.bbbbbbbbb('ccccccccccc',
                                            ddddddddd='eeeee').fffffffff([
                                                ggggggggggggggggggggg
                                            ])
        """)
    uwlines = _ParseAndUnwrap(code)
    self.assertCodeEqual(code, reformatter.Reformat(uwlines))

  def testB19547210(self):
    code = textwrap.dedent("""\
        while True:
          if True:
            if True:
              if True:
                if xxxxxxxxxxxx.yyyyyyy(aa).zzzzzzz() not in (
                    xxxxxxxxxxxx.yyyyyyyyyyyyyy.zzzzzzzz,
                    xxxxxxxxxxxx.yyyyyyyyyyyyyy.zzzzzzzz):
                  continue
        """)
    uwlines = _ParseAndUnwrap(code)
    self.assertCodeEqual(code, reformatter.Reformat(uwlines))

  def testB19377034(self):
    code = textwrap.dedent("""\
        def f():
          if (aaaaaaaaaaaaaaa.start >= aaaaaaaaaaaaaaa.end or
              bbbbbbbbbbbbbbb.start >= bbbbbbbbbbbbbbb.end):
            return False
        """)
    uwlines = _ParseAndUnwrap(code)
    self.assertCodeEqual(code, reformatter.Reformat(uwlines))

  def testB19372573(self):
    code = textwrap.dedent("""\
        def f():
            if a: return 42
            while True:
                if b: continue
                if c: break
            return 0
        """)
    uwlines = _ParseAndUnwrap(code)
    try:
      style.SetGlobalStyle(style.CreatePEP8Style())
      self.assertCodeEqual(code, reformatter.Reformat(uwlines))
    finally:
      style.SetGlobalStyle(style.CreateChromiumStyle())

  def testB19353268(self):
    code = textwrap.dedent("""\
        a = {1, 2, 3}[x]
        b = {'foo': 42, 'bar': 37}['foo']
        """)
    uwlines = _ParseAndUnwrap(code)
    self.assertCodeEqual(code, reformatter.Reformat(uwlines))

  def testB19287512(self):
    unformatted_code = textwrap.dedent("""\
        class Foo(object):

          def bar(self):
            with xxxxxxxxxx.yyyyy(
                'aaaaaaa.bbbbbbbb.ccccccc.dddddddddddddddddddd.eeeeeeeeeee',
                fffffffffff=(aaaaaaa.bbbbbbbb.ccccccc.dddddddddddddddddddd
                             .Mmmmmmmmmmmmmmmmmm(-1, 'permission error'))):
              self.assertRaises(nnnnnnnnnnnnnnnn.ooooo, ppppp.qqqqqqqqqqqqqqqqq)
        """)
    expected_formatted_code = textwrap.dedent("""\
        class Foo(object):

          def bar(self):
            with xxxxxxxxxx.yyyyy(
                'aaaaaaa.bbbbbbbb.ccccccc.dddddddddddddddddddd.eeeeeeeeeee',
                fffffffffff=(
                    aaaaaaa.bbbbbbbb.ccccccc.dddddddddddddddddddd.Mmmmmmmmmmmmmmmmmm(
                        -1, 'permission error'))):
              self.assertRaises(nnnnnnnnnnnnnnnn.ooooo, ppppp.qqqqqqqqqqqqqqqqq)
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testB19194420(self):
    code = textwrap.dedent("""\
        method.Set(
            'long argument goes here that causes the line to break',
            lambda arg2=0.5: arg2)
        """)
    uwlines = _ParseAndUnwrap(code)
    self.assertCodeEqual(code, reformatter.Reformat(uwlines))

  def testB19073499(self):
    code = textwrap.dedent("""\
        instance = (aaaaaaa.bbbbbbb().ccccccccccccccccc().ddddddddddd(
            {'aa': 'context!'}).eeeeeeeeeeeeeeeeeee(
                {  # Inline comment about why fnord has the value 6.
                    'fnord': 6
                }))
        """)
    uwlines = _ParseAndUnwrap(code)
    self.assertCodeEqual(code, reformatter.Reformat(uwlines))

  def testB18257115(self):
    code = textwrap.dedent("""\
        if True:
          if True:
            self._Test(aaaa, bbbbbbb.cccccccccc, dddddddd, eeeeeeeeeee,
                       [ffff, ggggggggggg, hhhhhhhhhhhh, iiiiii, jjjj])
        """)
    uwlines = _ParseAndUnwrap(code)
    self.assertCodeEqual(code, reformatter.Reformat(uwlines))

  def testB18256666(self):
    code = textwrap.dedent("""\
        class Foo(object):

          def Bar(self):
            aaaaa.bbbbbbb(ccc='ddddddddddddddd',
                          eeee='ffffffffffffffffffffff-%s-%s' %
                          (gggg, int(time.time())),
                          hhhhhh={
                              'iiiiiiiiiii': iiiiiiiiiii,
                              'jjjj': jjjj.jjjjj(),
                              'kkkkkkkkkkkk': kkkkkkkkkkkk,
                          },
                          llllllllll=mmmmmm.nnnnnnnnnnnnnnnn)
        """)
    uwlines = _ParseAndUnwrap(code)
    self.assertCodeEqual(code, reformatter.Reformat(uwlines))

  def testB18256826(self):
    code = textwrap.dedent("""\
        if True:
          pass
        # A multiline comment.
        # Line two.
        elif False:
          pass

        if True:
          pass
          # A multiline comment.
          # Line two.
        elif False:
          pass
        """)
    uwlines = _ParseAndUnwrap(code)
    self.assertCodeEqual(code, reformatter.Reformat(uwlines))

  def testB18255697(self):
    code = textwrap.dedent("""\
        AAAAAAAAAAAAAAA = {
            'XXXXXXXXXXXXXX': 4242,  # Inline comment
            # Next comment
            'YYYYYYYYYYYYYYYY': ['zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz'],
        }
        """)
    uwlines = _ParseAndUnwrap(code)
    self.assertCodeEqual(code, reformatter.Reformat(uwlines))

  def testB17534869(self):
    unformatted_code = textwrap.dedent("""\
        if True:
          self.assertLess(abs(time.time()-aaaa.bbbbbbbbbbb(
                              datetime.datetime.now())), 1)
        """)
    expected_formatted_code = textwrap.dedent("""\
        if True:
          self.assertLess(
              abs(time.time() - aaaa.bbbbbbbbbbb(datetime.datetime.now())), 1)
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testB17489866(self):
    unformatted_code = textwrap.dedent("""\
        def f():
          if True:
            if True:
              return aaaa.bbbbbbbbb(ccccccc=dddddddddddddd({('eeee', \
'ffffffff'): str(j)}))
        """)
    expected_formatted_code = textwrap.dedent("""\
        def f():
          if True:
            if True:
              return aaaa.bbbbbbbbb(
                  ccccccc=dddddddddddddd({('eeee', 'ffffffff'): str(j)}))
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testB17133019(self):
    unformatted_code = textwrap.dedent("""\
        class aaaaaaaaaaaaaa(object):

          def bbbbbbbbbb(self):
            with io.open("/dev/null", "rb"):
              with io.open(os.path.join(aaaaa.bbbbb.ccccccccccc,
                                        DDDDDDDDDDDDDDD,
                                        "eeeeeeeee ffffffffff"
                                       ), "rb") as gggggggggggggggggggg:
                print(gggggggggggggggggggg)
        """)
    expected_formatted_code = textwrap.dedent("""\
        class aaaaaaaaaaaaaa(object):

          def bbbbbbbbbb(self):
            with io.open("/dev/null", "rb"):
              with io.open(
                  os.path.join(aaaaa.bbbbb.ccccccccccc, DDDDDDDDDDDDDDD,
                               "eeeeeeeee ffffffffff"), "rb") as gggggggggggggggggggg:
                print(gggggggggggggggggggg)
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testB17011869(self):
    unformatted_code = textwrap.dedent("""\
        '''blah......'''

        class SomeClass(object):
          '''blah.'''

          AAAAAAAAAAAA = {                        # Comment.
              'BBB': 1.0,
                'DDDDDDDD': 0.4811
                                      }
        """)
    expected_formatted_code = textwrap.dedent("""\
        '''blah......'''


        class SomeClass(object):
          '''blah.'''

          AAAAAAAAAAAA = {  # Comment.
              'BBB': 1.0,
              'DDDDDDDD': 0.4811
          }
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testB16783631(self):
    unformatted_code = textwrap.dedent("""\
        if True:
          with aaaaaaaaaaaaaa.bbbbbbbbbbbbb.ccccccc(ddddddddddddd,
                                                      eeeeeeeee=self.fffffffffffff
                                                      )as gggg:
            pass
        """)
    expected_formatted_code = textwrap.dedent("""\
        if True:
          with aaaaaaaaaaaaaa.bbbbbbbbbbbbb.ccccccc(
              ddddddddddddd, eeeeeeeee=self.fffffffffffff) as gggg:
            pass
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testB16572361(self):
    unformatted_code = textwrap.dedent("""\
        def foo(self):
         def bar(my_dict_name):
          self.my_dict_name['foo-bar-baz-biz-boo-baa-baa'].IncrementBy.assert_called_once_with('foo_bar_baz_boo')
        """)
    expected_formatted_code = textwrap.dedent("""\
        def foo(self):

          def bar(my_dict_name):
            self.my_dict_name[
                'foo-bar-baz-biz-boo-baa-baa'].IncrementBy.assert_called_once_with(
                    'foo_bar_baz_boo')
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testB15884241(self):
    unformatted_code = textwrap.dedent("""\
        if 1:
          if 1:
            for row in AAAA:
              self.create(aaaaaaaa="/aaa/bbbb/cccc/dddddd/eeeeeeeeeeeeeeeeeeeeeeeeee/%s" % row [0].replace(".foo", ".bar"), aaaaa=bbb[1], ccccc=bbb[2], dddd=bbb[3], eeeeeeeeeee=[s.strip() for s in bbb[4].split(",")], ffffffff=[s.strip() for s in bbb[5].split(",")], gggggg=bbb[6])
        """)
    expected_formatted_code = textwrap.dedent("""\
        if 1:
          if 1:
            for row in AAAA:
              self.create(aaaaaaaa="/aaa/bbbb/cccc/dddddd/eeeeeeeeeeeeeeeeeeeeeeeeee/%s"
                          % row[0].replace(".foo", ".bar"),
                          aaaaa=bbb[1],
                          ccccc=bbb[2],
                          dddd=bbb[3],
                          eeeeeeeeeee=[s.strip() for s in bbb[4].split(",")],
                          ffffffff=[s.strip() for s in bbb[5].split(",")],
                          gggggg=bbb[6])
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testB15697268(self):
    unformatted_code = textwrap.dedent("""\
        def main(unused_argv):
          ARBITRARY_CONSTANT_A = 10
          an_array_with_an_exceedingly_long_name = range(ARBITRARY_CONSTANT_A + 1)
          ok = an_array_with_an_exceedingly_long_name[:ARBITRARY_CONSTANT_A]
          bad_slice = map(math.sqrt, an_array_with_an_exceedingly_long_name[:ARBITRARY_CONSTANT_A])
          a_long_name_slicing = an_array_with_an_exceedingly_long_name[:ARBITRARY_CONSTANT_A]
          bad_slice = ("I am a crazy, no good, string whats too long, etc." + " no really ")[:ARBITRARY_CONSTANT_A]
        """)
    expected_formatted_code = textwrap.dedent("""\
        def main(unused_argv):
          ARBITRARY_CONSTANT_A = 10
          an_array_with_an_exceedingly_long_name = range(ARBITRARY_CONSTANT_A + 1)
          ok = an_array_with_an_exceedingly_long_name[:ARBITRARY_CONSTANT_A]
          bad_slice = map(math.sqrt,
                          an_array_with_an_exceedingly_long_name[:ARBITRARY_CONSTANT_A])
          a_long_name_slicing = an_array_with_an_exceedingly_long_name[:
                                                                       ARBITRARY_CONSTANT_A]
          bad_slice = ("I am a crazy, no good, string whats too long, etc." +
                       " no really ")[:ARBITRARY_CONSTANT_A]
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testB15597568(self):
    unformatted_code = textwrap.dedent("""\
        if True:
          if True:
            if True:
              print(("Return code was %d" + (", and the process timed out." if did_time_out else ".")) % errorcode)
        """)
    expected_formatted_code = textwrap.dedent("""\
        if True:
          if True:
            if True:
              print(("Return code was %d" + (", and the process timed out."
                                             if did_time_out else ".")) % errorcode)
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testB15542157(self):
    unformatted_code = textwrap.dedent("""\
        aaaaaaaaaaaa = bbbb.ccccccccccccccc(dddddd.eeeeeeeeeeeeee, ffffffffffffffffff, gggggg.hhhhhhhhhhhhhhhhh)
        """)
    expected_formatted_code = textwrap.dedent("""\
        aaaaaaaaaaaa = bbbb.ccccccccccccccc(dddddd.eeeeeeeeeeeeee, ffffffffffffffffff,
                                            gggggg.hhhhhhhhhhhhhhhhh)
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testB15438132(self):
    unformatted_code = textwrap.dedent("""\
        if aaaaaaa.bbbbbbbbbb:
           cccccc.dddddddddd(eeeeeeeeeee=fffffffffffff.gggggggggggggggggg)
           if hhhhhh.iiiii.jjjjjjjjjjjjj:
             # This is a comment in the middle of it all.
             kkkkkkk.llllllllll.mmmmmmmmmmmmm = True
           if (aaaaaa.bbbbb.ccccccccccccc != ddddddd.eeeeeeeeee.fffffffffffff or
               eeeeee.fffff.ggggggggggggggggggggggggggg() != hhhhhhh.iiiiiiiiii.jjjjjjjjjjjj):
             aaaaaaaa.bbbbbbbbbbbb(
                 aaaaaa.bbbbb.cc,
                 dddddddddddd=eeeeeeeeeeeeeeeeeee.fffffffffffffffff(
                     gggggg.hh,
                     iiiiiiiiiiiiiiiiiii.jjjjjjjjjj.kkkkkkk,
                     lllll.mm),
                 nnnnnnnnnn=ooooooo.pppppppppp)
        """)
    expected_formatted_code = textwrap.dedent("""\
        if aaaaaaa.bbbbbbbbbb:
          cccccc.dddddddddd(eeeeeeeeeee=fffffffffffff.gggggggggggggggggg)
          if hhhhhh.iiiii.jjjjjjjjjjjjj:
            # This is a comment in the middle of it all.
            kkkkkkk.llllllllll.mmmmmmmmmmmmm = True
          if (aaaaaa.bbbbb.ccccccccccccc != ddddddd.eeeeeeeeee.fffffffffffff or
              eeeeee.fffff.ggggggggggggggggggggggggggg() !=
              hhhhhhh.iiiiiiiiii.jjjjjjjjjjjj):
            aaaaaaaa.bbbbbbbbbbbb(aaaaaa.bbbbb.cc,
                                  dddddddddddd=eeeeeeeeeeeeeeeeeee.fffffffffffffffff(
                                      gggggg.hh, iiiiiiiiiiiiiiiiiii.jjjjjjjjjj.kkkkkkk,
                                      lllll.mm),
                                  nnnnnnnnnn=ooooooo.pppppppppp)
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testB14468247(self):
    unformatted_code = textwrap.dedent("""\
        call(a=1,
            b=2,
        )
        """)
    expected_formatted_code = textwrap.dedent("""\
        call(a=1, b=2,)
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testB14406499(self):
    unformatted_code = textwrap.dedent("""\
        def foo1(parameter_1, parameter_2, parameter_3, parameter_4, \
parameter_5, parameter_6): pass
        """)
    expected_formatted_code = textwrap.dedent("""\
        def foo1(parameter_1, parameter_2, parameter_3, parameter_4, parameter_5,
                 parameter_6):
          pass
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testB13900309(self):
    unformatted_code = textwrap.dedent("""\
        self.aaaaaaaaaaa(  # A comment in the middle of it all.
               948.0/3600, self.bbb.ccccccccccccccccccccc(dddddddddddddddd.eeee, True))
        """)
    expected_formatted_code = textwrap.dedent("""\
        self.aaaaaaaaaaa(  # A comment in the middle of it all.
            948.0 / 3600, self.bbb.ccccccccccccccccccccc(dddddddddddddddd.eeee, True))
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

    code = textwrap.dedent("""\
        aaaaaaaaaa.bbbbbbbbbbbbbbbbbbbbbbbb.cccccccccccccccccccccccccccccc(
            DC_1, (CL - 50, CL), AAAAAAAA, BBBBBBBBBBBBBBBB, 98.0,
            CCCCCCC).ddddddddd(  # Look! A comment is here.
                AAAAAAAA - (20 * 60 - 5))
        """)
    uwlines = _ParseAndUnwrap(code)
    self.assertCodeEqual(code, reformatter.Reformat(uwlines))

    unformatted_code = textwrap.dedent("""\
        aaaaaaaaaaaaaaaaaaaaaaaa.bbbbbbbbbbbbb.ccccccccccccccccccccccccc().dddddddddddddddddddddddddd(1, 2, 3, 4)
        """)
    expected_formatted_code = textwrap.dedent("""\
        aaaaaaaaaaaaaaaaaaaaaaaa.bbbbbbbbbbbbb.ccccccccccccccccccccccccc(
        ).dddddddddddddddddddddddddd(1, 2, 3, 4)
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

    unformatted_code = textwrap.dedent("""\
        aaaaaaaaaaaaaaaaaaaaaaaa.bbbbbbbbbbbbb.ccccccccccccccccccccccccc(x).dddddddddddddddddddddddddd(1, 2, 3, 4)
        """)
    expected_formatted_code = textwrap.dedent("""\
        aaaaaaaaaaaaaaaaaaaaaaaa.bbbbbbbbbbbbb.ccccccccccccccccccccccccc(
            x).dddddddddddddddddddddddddd(1, 2, 3, 4)
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

    unformatted_code = textwrap.dedent("""\
        aaaaaaaaaaaaaaaaaaaaaaaa(xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx).dddddddddddddddddddddddddd(1, 2, 3, 4)
        """)
    expected_formatted_code = textwrap.dedent("""\
        aaaaaaaaaaaaaaaaaaaaaaaa(
            xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx).dddddddddddddddddddddddddd(1, 2, 3, 4)
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

    unformatted_code = textwrap.dedent("""\
        aaaaaaaaaaaaaaaaaaaaaaaa().bbbbbbbbbbbbbbbbbbbbbbbb().ccccccccccccccccccc().\
dddddddddddddddddd().eeeeeeeeeeeeeeeeeeeee().fffffffffffffffff().gggggggggggggggggg()
        """)
    expected_formatted_code = textwrap.dedent("""\
        aaaaaaaaaaaaaaaaaaaaaaaa().bbbbbbbbbbbbbbbbbbbbbbbb().ccccccccccccccccccc(
        ).dddddddddddddddddd().eeeeeeeeeeeeeeeeeeeee().fffffffffffffffff(
        ).gggggggggggggggggg()
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))


class TestsForPEP8Style(ReformatterTest):

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
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testSingleLineIfStatements(self):
    code = textwrap.dedent("""\
        if True: a = 42
        elif False: b = 42
        else: c = 42
        """)
    uwlines = _ParseAndUnwrap(code)
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
    uwlines = _ParseAndUnwrap(unformatted_code)
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
    uwlines = _ParseAndUnwrap(unformatted_code)
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
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testSpaceBetweenEndingCommandAndClosingBracket(self):
    unformatted_code = textwrap.dedent("""\
        a = [
            1,
        ]
        """)
    expected_formatted_code = textwrap.dedent("""\
        a = [1, ]
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testContinuedNonOudentedLine(self):
    code = textwrap.dedent("""\
        class eld(d):
            if str(geom.geom_type).upper(
            ) != self.geom_type and not self.geom_type == 'GEOMETRY':
                ror(code='om_type')
        """)
    uwlines = _ParseAndUnwrap(code)
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
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testAlignClosingBracketWithVisualIndentation(self):
    unformatted_code = textwrap.dedent("""\
        TEST_LIST = ('foo', 'bar',  # first comment
                     'baz'  # second comment
                    )
        """)
    expected_formatted_code = textwrap.dedent("""\
        TEST_LIST = ('foo',
                     'bar',  # first comment
                     'baz'  # second comment
                     )
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
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
                       xxxxxxxxxxxxxxxxxxxx(yyyyyyyyyyyyy[zzzzz].aaaaaaaa[0]) ==
                       'bbbbbbb'):
                    pass
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
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
    uwlines = _ParseAndUnwrap(unformatted_code)
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
        elif (xxxxxxxxxxxxxxx(aaaaaaaaaaa,
                              bbbbbbbbbbbbbb,
                              cccccccccccc,
                              dddddddddd=None)):
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
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testB20016122(self):
    try:
      style.SetGlobalStyle(style.CreateStyleFromConfig(
          '{based_on_style: pep8, SPLIT_PENALTY_IMPORT_NAMES: 35}'))
      unformatted_code = textwrap.dedent("""\
          from a_very_long_or_indented_module_name_yada_yada import (long_argument_1,
                                                                     long_argument_2)
          """)
      expected_formatted_code = textwrap.dedent("""\
          from a_very_long_or_indented_module_name_yada_yada import (
              long_argument_1, long_argument_2)
          """)
      uwlines = _ParseAndUnwrap(unformatted_code)
      self.assertCodeEqual(expected_formatted_code,
                           reformatter.Reformat(uwlines))
    finally:
      style.SetGlobalStyle(style.CreatePEP8Style())

  def testSplittingBeforeLogicalOperator(self):
    try:
      style.SetGlobalStyle(style.CreateStyleFromConfig(
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
      uwlines = _ParseAndUnwrap(unformatted_code)
      self.assertCodeEqual(expected_formatted_code,
                           reformatter.Reformat(uwlines))
    finally:
      style.SetGlobalStyle(style.CreatePEP8Style())


class TestingNotInParameters(unittest.TestCase):

  def testNotInParams(self):
    unformatted_code = textwrap.dedent("""\
      list("a long line to break the line. a long line to break the brk a long lin", not True)
      """)

    expected_code = textwrap.dedent("""\
      list("a long line to break the line. a long line to break the brk a long lin",
           not True)
      """)

    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertEqual(expected_code, reformatter.Reformat(uwlines))


@unittest.skipIf(py3compat.PY3, 'Requires Python 2')
class TestVerifyNoVerify(ReformatterTest):

  @classmethod
  def setUpClass(cls):
    style.SetGlobalStyle(style.CreatePEP8Style())

  def testVerifyException(self):
    unformatted_code = textwrap.dedent("""\
        class ABC(metaclass=type):
          pass
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    with self.assertRaises(verifier.InternalError):
      reformatter.Reformat(uwlines, verify=True)
    with self.assertRaises(verifier.InternalError):
      # default should be True
      reformatter.Reformat(uwlines)

  def testNoVerify(self):
    unformatted_code = textwrap.dedent("""\
        class ABC(metaclass=type):
          pass
        """)
    expected_formatted_code = textwrap.dedent("""\
        class ABC(metaclass=type):
            pass
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code,
                         reformatter.Reformat(uwlines,
                                              verify=False))

  def testVerifyFutureImport(self):
    unformatted_code = textwrap.dedent("""\
        from __future__ import print_function

        def call_my_function(the_function):
          the_function("hi")

        if __name__ == "__main__":
          call_my_function(print)
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    with self.assertRaises(verifier.InternalError):
      reformatter.Reformat(uwlines, verify=True)

    expected_formatted_code = textwrap.dedent("""\
        from __future__ import print_function


        def call_my_function(the_function):
            the_function("hi")


        if __name__ == "__main__":
            call_my_function(print)
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code,
                         reformatter.Reformat(uwlines,
                                              verify=False))

  def testContinuationLineShouldBeDistinguished(self):
    unformatted_code = textwrap.dedent("""\
        class Foo(object):

            def bar(self):
                if self.solo_generator_that_is_long is None and len(
                        self.generators + self.next_batch) == 1:
                    pass
        """)
    expected_formatted_code = textwrap.dedent("""\
        class Foo(object):
            def bar(self):
                if self.solo_generator_that_is_long is None and len(
                        self.generators + self.next_batch) == 1:
                    pass
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code,
                         reformatter.Reformat(uwlines,
                                              verify=False))


@unittest.skipUnless(py3compat.PY3, 'Requires Python 3')
class TestsForPython3Code(ReformatterTest):
  """Test a few constructs that are new Python 3 syntax."""

  @classmethod
  def setUpClass(cls):
    style.SetGlobalStyle(style.CreatePEP8Style())

  def testKeywordOnlyArgSpecifier(self):
    unformatted_code = textwrap.dedent("""\
        def foo(a, *, kw):
          return a+kw
        """)
    expected_formatted_code = textwrap.dedent("""\
        def foo(a, *, kw):
            return a + kw
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
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
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testExecAsNonKeyword(self):
    unformatted_code = 'methods.exec( sys.modules[name])\n'
    expected_formatted_code = 'methods.exec(sys.modules[name])\n'
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testAsyncFunctions(self):
    if sys.version_info[1] < 5:
      return
    code = textwrap.dedent("""\
        import asyncio
        import time


        async def slow_operation():
            await asyncio.sleep(1)
            # print("Slow operation {} complete".format(n))


        async def main():
            start = time.time()
        """)
    uwlines = _ParseAndUnwrap(code)
    self.assertCodeEqual(code, reformatter.Reformat(uwlines, verify=False))

  def testNoSpacesAroundPowerOparator(self):
    try:
      style.SetGlobalStyle(style.CreateStyleFromConfig(
          '{based_on_style: pep8, SPACES_AROUND_POWER_OPERATOR: True}'))
      unformatted_code = textwrap.dedent("""\
          a**b
          """)
      expected_formatted_code = textwrap.dedent("""\
          a ** b
          """)
      uwlines = _ParseAndUnwrap(unformatted_code)
      self.assertCodeEqual(expected_formatted_code,
                           reformatter.Reformat(uwlines))
    finally:
      style.SetGlobalStyle(style.CreatePEP8Style())


class TestsForFBStyle(ReformatterTest):

  @classmethod
  def setUpClass(cls):
    style.SetGlobalStyle(style.CreateFacebookStyle())

  def testNoNeedForLineBreaks(self):
    unformatted_code = textwrap.dedent("""\
        def overly_long_function_name(
          just_one_arg, **kwargs):
          pass
        """)
    expected_formatted_code = textwrap.dedent("""\
        def overly_long_function_name(just_one_arg, **kwargs):
            pass
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testDedentClosingBracket(self):
    unformatted_code = textwrap.dedent("""\
        def overly_long_function_name(
          first_argument_on_the_same_line,
          second_argument_makes_the_line_too_long):
          pass
        """)
    expected_formatted_code = textwrap.dedent("""\
        def overly_long_function_name(
            first_argument_on_the_same_line, \
second_argument_makes_the_line_too_long
        ):
            pass
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testBreakAfterOpeningBracketIfContentsTooBig(self):
    unformatted_code = textwrap.dedent("""\
        def overly_long_function_name(a, b, c, d, e, f, g, h, i, j, k, l, m,
          n, o, p, q, r, s, t, u, v, w, x, y, z):
          pass
        """)
    expected_formatted_code = textwrap.dedent("""\
        def overly_long_function_name(
            a, b, c, d, e, f, g, h, i, j, k, l, m, n, o, p, q, r, s, t, u, \
v, w, x, y, z
        ):
            pass
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testDedentClosingBracketWithComments(self):
    unformatted_code = textwrap.dedent("""\
        def overly_long_function_name(
          # comment about the first argument
          first_argument_with_a_very_long_name_or_so,
          # comment about the second argument
          second_argument_makes_the_line_too_long):
          pass
        """)
    expected_formatted_code = textwrap.dedent("""\
        def overly_long_function_name(
            # comment about the first argument
            first_argument_with_a_very_long_name_or_so,
            # comment about the second argument
            second_argument_makes_the_line_too_long
        ):
            pass
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testDedentImportAsNames(self):
    unformatted_code = textwrap.dedent("""\
    from module import (
        internal_function as function,
        SOME_CONSTANT_NUMBER1,
        SOME_CONSTANT_NUMBER2,
        SOME_CONSTANT_NUMBER3,
    )
    """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(unformatted_code, reformatter.Reformat(uwlines))

  def testDedentTestListGexp(self):
    # TODO(ambv): Arguably _DetermineMustSplitAnnotation shouldn't enforce
    # breaks only on the basis of a trailing comma if the entire thing fits
    # in a single line.
    unformatted_code = textwrap.dedent("""\
    try:
        pass
    except (
        IOError, OSError, LookupError, RuntimeError, OverflowError
    ) as exception:
        pass

    try:
        pass
    except (
        IOError,
        OSError,
        LookupError,
        RuntimeError,
        OverflowError,
    ) as exception:
        pass
    """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(unformatted_code, reformatter.Reformat(uwlines))

  def testBrokenIdempotency(self):
    # TODO(ambv): The following behaviour should be fixed.
    pass0_code = textwrap.dedent("""\
    try:
        pass
    except (IOError, OSError, LookupError, RuntimeError, OverflowError) as exception:
        pass
    """)
    pass1_code = textwrap.dedent("""\
    try:
        pass
    except (
        IOError, OSError, LookupError, RuntimeError, OverflowError
    ) as exception:
        pass
    """)
    uwlines = _ParseAndUnwrap(pass0_code)
    self.assertCodeEqual(pass1_code, reformatter.Reformat(uwlines))

    pass2_code = textwrap.dedent("""\
    try:
        pass
    except (
        IOError, OSError, LookupError, RuntimeError, OverflowError
    ) as exception:
        pass
    """)
    uwlines = _ParseAndUnwrap(pass1_code)
    self.assertCodeEqual(pass2_code, reformatter.Reformat(uwlines))

  def testIfExprHangingIndent(self):
    unformatted_code = textwrap.dedent("""\
    if True:
        if True:
            if True:
                if not self.frobbies and (
                   self.foobars.counters['db.cheeses'] != 1 or
                   self.foobars.counters['db.marshmellow_skins'] != 1):
                    pass
    """)
    expected_formatted_code = textwrap.dedent("""\
    if True:
        if True:
            if True:
                if not self.frobbies and (
                    self.foobars.counters['db.cheeses'] != 1 or
                    self.foobars.counters['db.marshmellow_skins'] != 1
                ):
                    pass
    """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testSimpleDedenting(self):
    unformatted_code = textwrap.dedent("""\
    if True:
        self.assertEqual(result.reason_not_added, "current preflight is still running")
    """)
    expected_formatted_code = textwrap.dedent("""\
    if True:
        self.assertEqual(
            result.reason_not_added, "current preflight is still running"
        )
    """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testDedentingWithSubscripts(self):
    unformatted_code = textwrap.dedent("""\
    class Foo:
        class Bar:
            @classmethod
            def baz(cls, clues_list, effect, constraints, constraint_manager):
                if clues_lists:
                   return cls.single_constraint_not(clues_lists, effect, constraints[0], constraint_manager)

    """)
    expected_formatted_code = textwrap.dedent("""\
    class Foo:
        class Bar:
            @classmethod
            def baz(cls, clues_list, effect, constraints, constraint_manager):
                if clues_lists:
                    return cls.single_constraint_not(
                        clues_lists, effect, constraints[0], constraint_manager
                    )
    """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertCodeEqual(expected_formatted_code, reformatter.Reformat(uwlines))


def _ParseAndUnwrap(code, dumptree=False):
  """Produces unwrapped lines from the given code.

  Parses the code into a tree, performs comment splicing and runs the
  unwrapper.

  Arguments:
    code: code to parse as a string
    dumptree: if True, the parsed pytree (after comment splicing) is dumped
              to stderr. Useful for debugging.

  Returns:
    List of unwrapped lines.
  """
  tree = pytree_utils.ParseCodeToTree(code)
  comment_splicer.SpliceComments(tree)
  continuation_splicer.SpliceContinuations(tree)
  subtype_assigner.AssignSubtypes(tree)
  split_penalty.ComputeSplitPenalties(tree)
  blank_line_calculator.CalculateBlankLines(tree)

  if dumptree:
    pytree_visitor.DumpPyTree(tree, target_stream=sys.stderr)

  uwlines = pytree_unwrapper.UnwrapPyTree(tree)
  for uwl in uwlines:
    uwl.CalculateFormattingInformation()

  return uwlines


if __name__ == '__main__':
  unittest.main()
