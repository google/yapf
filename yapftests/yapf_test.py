# -*- coding: utf-8 -*-
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
"""Tests for yapf.yapf."""

import io
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest

from yapf.yapflib import yapf_api

ROOT_DIR = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))

# Verification is turned off by default, but want to enable it for testing.
YAPF_BINARY = [sys.executable, '-m', 'yapf', '--verify', '--no-local-style']


class FormatCodeTest(unittest.TestCase):

  def _Check(self, unformatted_code, expected_formatted_code):
    formatted_code, _ = yapf_api.FormatCode(unformatted_code,
                                            style_config='chromium')
    self.assertEqual(expected_formatted_code, formatted_code)

  def testSimple(self):
    unformatted_code = textwrap.dedent(u"""\
        print('foo')
        """)
    self._Check(unformatted_code, unformatted_code)

  def testNoEndingNewline(self):
    unformatted_code = textwrap.dedent(u"""\
        if True:
          pass""")
    expected_formatted_code = textwrap.dedent(u"""\
        if True:
          pass
        """)
    self._Check(unformatted_code, expected_formatted_code)


class FormatFileTest(unittest.TestCase):

  def setUp(self):
    self.test_tmpdir = tempfile.mkdtemp()

  def tearDown(self):
    shutil.rmtree(self.test_tmpdir)

  def assertCodeEqual(self, expected_code, code):
    if code != expected_code:
      msg = 'Code format mismatch:\n'
      msg += 'Expected:\n >'
      msg += '\n > '.join(expected_code.splitlines())
      msg += '\nActual:\n >'
      msg += '\n > '.join(code.splitlines())
      # TODO(sbc): maybe using difflib here to produce easy to read deltas?
      self.fail(msg)

  def _MakeTempFileWithContents(self, filename, contents):
    path = os.path.join(self.test_tmpdir, filename)
    with open(path, 'w') as f:
      f.write(contents)
    return path

  def testFormatFile(self):
    unformatted_code = textwrap.dedent(u"""\
        if True:
         pass
        """)
    file1 = self._MakeTempFileWithContents('testfile1.py', unformatted_code)

    expected_formatted_code_pep8 = textwrap.dedent(u"""\
        if True:
            pass
        """)
    expected_formatted_code_chromium = textwrap.dedent(u"""\
        if True:
          pass
        """)

    formatted_code = yapf_api.FormatFile(file1, style_config='pep8')[0]
    self.assertCodeEqual(expected_formatted_code_pep8, formatted_code)

    formatted_code = yapf_api.FormatFile(file1, style_config='chromium')[0]
    self.assertCodeEqual(expected_formatted_code_chromium, formatted_code)

  def testDisableLinesPattern(self):
    unformatted_code = textwrap.dedent(u"""\
        if a:    b

        # yapf: disable
        if f:    g

        if h:    i
        """)
    file1 = self._MakeTempFileWithContents('testfile1.py', unformatted_code)

    expected_formatted_code = textwrap.dedent(u"""\
        if a: b

        # yapf: disable
        if f:    g

        if h:    i
        """)
    formatted_code = yapf_api.FormatFile(file1, style_config='pep8')[0]
    self.assertCodeEqual(expected_formatted_code, formatted_code)

  def testDisableAndReenableLinesPattern(self):
    unformatted_code = textwrap.dedent(u"""\
        if a:    b

        # yapf: disable
        if f:    g
        # yapf: enable

        if h:    i
        """)
    file1 = self._MakeTempFileWithContents('testfile1.py', unformatted_code)

    expected_formatted_code = textwrap.dedent(u"""\
        if a: b

        # yapf: disable
        if f:    g
        # yapf: enable

        if h: i
        """)
    formatted_code = yapf_api.FormatFile(file1, style_config='pep8')[0]
    self.assertCodeEqual(expected_formatted_code, formatted_code)

  def testDisablePartOfMultilineComment(self):
    unformatted_code = textwrap.dedent(u"""\
        if a:    b

        # This is a multiline comment that disables YAPF.
        # yapf: disable
        if f:    g
        # yapf: enable
        # This is a multiline comment that enables YAPF.

        if h:    i
        """)
    file1 = self._MakeTempFileWithContents('testfile1.py', unformatted_code)

    expected_formatted_code = textwrap.dedent(u"""\
        if a: b

        # This is a multiline comment that disables YAPF.
        # yapf: disable
        if f:    g
        # yapf: enable
        # This is a multiline comment that enables YAPF.

        if h: i
        """)
    formatted_code = yapf_api.FormatFile(file1, style_config='pep8')[0]
    self.assertCodeEqual(expected_formatted_code, formatted_code)

  def testFormatFileLinesSelection(self):
    unformatted_code = textwrap.dedent(u"""\
        if a:    b

        if f:    g

        if h:    i
        """)
    file1 = self._MakeTempFileWithContents('testfile1.py', unformatted_code)

    expected_formatted_code_lines1and2 = textwrap.dedent(u"""\
        if a: b

        if f:    g

        if h:    i
        """)
    formatted_code = yapf_api.FormatFile(file1, style_config='pep8',
                                         lines=[(1, 2)])[0]
    self.assertCodeEqual(expected_formatted_code_lines1and2, formatted_code)

    expected_formatted_code_lines3 = textwrap.dedent(u"""\
        if a:    b

        if f: g

        if h:    i
        """)
    formatted_code = yapf_api.FormatFile(file1, style_config='pep8',
                                         lines=[(3, 3)])[0]
    self.assertCodeEqual(expected_formatted_code_lines3, formatted_code)

  def testFormatFileDiff(self):
    unformatted_code = textwrap.dedent(u"""\
        if True:
         pass
        """)
    file1 = self._MakeTempFileWithContents('testfile1.py', unformatted_code)
    diff = yapf_api.FormatFile(file1, print_diff=True)[0]
    self.assertTrue(u'+    pass' in diff)

  def testFormatFileInPlace(self):
    unformatted_code = 'True==False\n'
    formatted_code = 'True == False\n'
    file1 = self._MakeTempFileWithContents('testfile1.py', unformatted_code)
    result, _, _ = yapf_api.FormatFile(file1, in_place=True)
    self.assertEqual(result, None)
    with open(file1) as f:
      self.assertCodeEqual(formatted_code, f.read())

    self.assertRaises(ValueError, yapf_api.FormatFile, file1,
                      in_place=True, print_diff=True)

  def testNoFile(self):
    self.assertRaises(IOError, yapf_api.FormatFile, 'not_a_file.py')

  def testCommentsUnformatted(self):
    code = textwrap.dedent("""\
        foo = [# A list of things
               # bork
            'one',
            # quark
            'two'] # yapf: disable
        """)
    file1 = self._MakeTempFileWithContents('testfile1.py', code)
    formatted_code = yapf_api.FormatFile(file1, style_config='pep8')[0]
    self.assertCodeEqual(code, formatted_code)


class CommandLineTest(unittest.TestCase):
  """Test how calling yapf from the command line acts."""

  @classmethod
  def setUpClass(cls):
    cls.test_tmpdir = tempfile.mkdtemp()

  @classmethod
  def tearDownClass(cls):
    shutil.rmtree(cls.test_tmpdir)

  def assertYapfReformats(self, unformatted, expected, extra_options=None):
    """Check that yapf reformats the given code as expected.

    Invokes yapf in a subprocess, piping the unformatted code into its stdin.
    Checks that the formatted output is as expected.

    Arguments:
      unformatted: unformatted code - input to yapf
      expected: expected formatted code at the output of yapf
      extra_options: iterable of extra command-line options to pass to yapf
    """
    cmdline = YAPF_BINARY + (extra_options or [])
    p = subprocess.Popen(cmdline,
                         stdout=subprocess.PIPE,
                         stdin=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    reformatted_code, stderrdata = p.communicate(unformatted.encode('utf-8'))
    self.assertEqual(stderrdata, b'')
    self.assertEqual(reformatted_code.decode('utf-8'), expected)

  def testUnicodeEncodingPipedToFile(self):
    unformatted_code = textwrap.dedent(u"""\
        def foo():
            print('⇒')
        """)

    with tempfile.NamedTemporaryFile(suffix='.py',
                                     dir=self.test_tmpdir) as outfile:
      with tempfile.NamedTemporaryFile(suffix='.py',
                                       dir=self.test_tmpdir) as testfile:
        testfile.write(unformatted_code.encode('UTF-8'))
        subprocess.check_call(YAPF_BINARY + ['--diff', testfile.name],
                              stdout=outfile)

  def testInPlaceReformatting(self):
    unformatted_code = textwrap.dedent(u"""\
        def foo():
          x = 37
        """)
    expected_formatted_code = textwrap.dedent(u"""\
        def foo():
            x = 37
        """)

    with tempfile.NamedTemporaryFile(suffix='.py',
                                     dir=self.test_tmpdir) as testfile:
      testfile.write(unformatted_code.encode('UTF-8'))
      testfile.seek(0)

      p = subprocess.Popen(YAPF_BINARY + ['--in-place', testfile.name])
      p.wait()

      with io.open(testfile.name, mode='r', newline='') as fd:
        reformatted_code = fd.read()

    self.assertEqual(reformatted_code, expected_formatted_code)

  def testInPlaceReformattingBlank(self):
    unformatted_code = u'\n\n'
    expected_formatted_code = u'\n'

    with tempfile.NamedTemporaryFile(suffix='.py',
                                     dir=self.test_tmpdir) as testfile:
      testfile.write(unformatted_code.encode('UTF-8'))
      testfile.seek(0)

      p = subprocess.Popen(YAPF_BINARY + ['--in-place', testfile.name])
      p.wait()

      with io.open(testfile.name, mode='r', newline='') as fd:
        reformatted_code = fd.read()

    self.assertEqual(reformatted_code, expected_formatted_code)

  def testReadFromStdin(self):
    unformatted_code = textwrap.dedent(u"""\
        def foo():
          x = 37
        """)
    expected_formatted_code = textwrap.dedent(u"""\
        def foo():
            x = 37
        """)
    self.assertYapfReformats(unformatted_code, expected_formatted_code)

  def testReadFromStdinWithEscapedStrings(self):
    unformatted_code = textwrap.dedent(u"""\
        s =   "foo\\nbar"
        """)
    expected_formatted_code = textwrap.dedent(u"""\
        s = "foo\\nbar"
        """)
    self.assertYapfReformats(unformatted_code, expected_formatted_code)

  def testSetChromiumStyle(self):
    unformatted_code = textwrap.dedent(u"""\
        def foo(): # trail
            x = 37
        """)
    expected_formatted_code = textwrap.dedent(u"""\
        def foo():  # trail
          x = 37
        """)
    self.assertYapfReformats(unformatted_code, expected_formatted_code,
                             extra_options=['--style=chromium'])

  def testSetCustomStyleBasedOnChromium(self):
    unformatted_code = textwrap.dedent(u"""\
        def foo(): # trail
            x = 37
        """)
    expected_formatted_code = textwrap.dedent(u"""\
        def foo():    # trail
          x = 37
        """)

    with tempfile.NamedTemporaryFile(dir=self.test_tmpdir, mode='w') as f:
      f.write(textwrap.dedent('''\
          [style]
          based_on_style = chromium
          SPACES_BEFORE_COMMENT = 4
          '''))
      f.flush()
      self.assertYapfReformats(unformatted_code, expected_formatted_code,
                               extra_options=['--style={0}'.format(f.name)])

  def testReadSingleLineCodeFromStdin(self):
    unformatted_code = textwrap.dedent(u"""\
        if True: pass
        """)
    expected_formatted_code = textwrap.dedent(u"""\
        if True: pass
        """)
    self.assertYapfReformats(unformatted_code, expected_formatted_code)

  def testEncodingVerification(self):
    unformatted_code = textwrap.dedent(u"""\
        '''The module docstring.'''
        # -*- coding: utf-8 -*-
        def f():
            x = 37
        """)

    with tempfile.NamedTemporaryFile(suffix='.py',
                                     dir=self.test_tmpdir) as outfile:
      with tempfile.NamedTemporaryFile(suffix='.py',
                                       dir=self.test_tmpdir) as testfile:
        testfile.write(unformatted_code.encode('utf-8'))
        subprocess.check_call(YAPF_BINARY + ['--diff', testfile.name],
                              stdout=outfile)

  def testReformattingSpecificLines(self):
    unformatted_code = textwrap.dedent(u"""\
        def h():
            if (xxxxxxxxxxxx.yyyyyyyy(zzzzzzzzzzzzz[0]) == 'aaaaaaaaaaa' and xxxxxxxxxxxx.yyyyyyyy(zzzzzzzzzzzzz[0].mmmmmmmm[0]) == 'bbbbbbb'):
                pass


        def g():
            if (xxxxxxxxxxxx.yyyyyyyy(zzzzzzzzzzzzz[0]) == 'aaaaaaaaaaa' and xxxxxxxxxxxx.yyyyyyyy(zzzzzzzzzzzzz[0].mmmmmmmm[0]) == 'bbbbbbb'):
                pass
        """)
    expected_formatted_code = textwrap.dedent(u"""\
        def h():
            if (xxxxxxxxxxxx.yyyyyyyy(zzzzzzzzzzzzz[0]) == 'aaaaaaaaaaa' and
                xxxxxxxxxxxx.yyyyyyyy(zzzzzzzzzzzzz[0].mmmmmmmm[0]) == 'bbbbbbb'):
                pass


        def g():
            if (xxxxxxxxxxxx.yyyyyyyy(zzzzzzzzzzzzz[0]) == 'aaaaaaaaaaa' and xxxxxxxxxxxx.yyyyyyyy(zzzzzzzzzzzzz[0].mmmmmmmm[0]) == 'bbbbbbb'):
                pass
        """)
    self.assertYapfReformats(unformatted_code, expected_formatted_code,
                             extra_options=['--lines', '1-2'])

  def testReformattingSkippingLines(self):
    unformatted_code = textwrap.dedent(u"""\
        def h():
            if (xxxxxxxxxxxx.yyyyyyyy(zzzzzzzzzzzzz[0]) == 'aaaaaaaaaaa' and xxxxxxxxxxxx.yyyyyyyy(zzzzzzzzzzzzz[0].mmmmmmmm[0]) == 'bbbbbbb'):
                pass

        # yapf: disable
        def g():
            if (xxxxxxxxxxxx.yyyyyyyy(zzzzzzzzzzzzz[0]) == 'aaaaaaaaaaa' and xxxxxxxxxxxx.yyyyyyyy(zzzzzzzzzzzzz[0].mmmmmmmm[0]) == 'bbbbbbb'):
                pass
        # yapf: enable
        """)
    expected_formatted_code = textwrap.dedent(u"""\
        def h():
            if (xxxxxxxxxxxx.yyyyyyyy(zzzzzzzzzzzzz[0]) == 'aaaaaaaaaaa' and
                xxxxxxxxxxxx.yyyyyyyy(zzzzzzzzzzzzz[0].mmmmmmmm[0]) == 'bbbbbbb'):
                pass


        # yapf: disable
        def g():
            if (xxxxxxxxxxxx.yyyyyyyy(zzzzzzzzzzzzz[0]) == 'aaaaaaaaaaa' and xxxxxxxxxxxx.yyyyyyyy(zzzzzzzzzzzzz[0].mmmmmmmm[0]) == 'bbbbbbb'):
                pass
        # yapf: enable
        """)
    self.assertYapfReformats(unformatted_code, expected_formatted_code)

  def testReformattingSkippingToEndOfFile(self):
    unformatted_code = textwrap.dedent(u"""\
        def h():
            if (xxxxxxxxxxxx.yyyyyyyy(zzzzzzzzzzzzz[0]) == 'aaaaaaaaaaa' and xxxxxxxxxxxx.yyyyyyyy(zzzzzzzzzzzzz[0].mmmmmmmm[0]) == 'bbbbbbb'):
                pass

        # yapf: disable
        def g():
            if (xxxxxxxxxxxx.yyyyyyyy(zzzzzzzzzzzzz[0]) == 'aaaaaaaaaaa' and xxxxxxxxxxxx.yyyyyyyy(zzzzzzzzzzzzz[0].mmmmmmmm[0]) == 'bbbbbbb'):
                pass

        def f():
            def e():
                while (xxxxxxxxxxxxxxxxxxxxx(yyyyyyyyyyyyy[zzzzz]) == 'aaaaaaaaaaa' and
                       xxxxxxxxxxxxxxxxxxxxx(yyyyyyyyyyyyy[zzzzz].aaaaaaaa[0]) ==
                       'bbbbbbb'):
                    pass
        """)
    expected_formatted_code = textwrap.dedent(u"""\
        def h():
            if (xxxxxxxxxxxx.yyyyyyyy(zzzzzzzzzzzzz[0]) == 'aaaaaaaaaaa' and
                xxxxxxxxxxxx.yyyyyyyy(zzzzzzzzzzzzz[0].mmmmmmmm[0]) == 'bbbbbbb'):
                pass


        # yapf: disable
        def g():
            if (xxxxxxxxxxxx.yyyyyyyy(zzzzzzzzzzzzz[0]) == 'aaaaaaaaaaa' and xxxxxxxxxxxx.yyyyyyyy(zzzzzzzzzzzzz[0].mmmmmmmm[0]) == 'bbbbbbb'):
                pass

        def f():
            def e():
                while (xxxxxxxxxxxxxxxxxxxxx(yyyyyyyyyyyyy[zzzzz]) == 'aaaaaaaaaaa' and
                       xxxxxxxxxxxxxxxxxxxxx(yyyyyyyyyyyyy[zzzzz].aaaaaaaa[0]) ==
                       'bbbbbbb'):
                    pass
        """)
    self.assertYapfReformats(unformatted_code, expected_formatted_code)

  def testReformattingSkippingSingleLine(self):
    unformatted_code = textwrap.dedent(u"""\
        def h():
            if (xxxxxxxxxxxx.yyyyyyyy(zzzzzzzzzzzzz[0]) == 'aaaaaaaaaaa' and xxxxxxxxxxxx.yyyyyyyy(zzzzzzzzzzzzz[0].mmmmmmmm[0]) == 'bbbbbbb'):
                pass

        def g():
            if (xxxxxxxxxxxx.yyyyyyyy(zzzzzzzzzzzzz[0]) == 'aaaaaaaaaaa' and xxxxxxxxxxxx.yyyyyyyy(zzzzzzzzzzzzz[0].mmmmmmmm[0]) == 'bbbbbbb'):  # yapf: disable
                pass
        """)
    expected_formatted_code = textwrap.dedent(u"""\
        def h():
            if (xxxxxxxxxxxx.yyyyyyyy(zzzzzzzzzzzzz[0]) == 'aaaaaaaaaaa' and
                xxxxxxxxxxxx.yyyyyyyy(zzzzzzzzzzzzz[0].mmmmmmmm[0]) == 'bbbbbbb'):
                pass


        def g():
            if (xxxxxxxxxxxx.yyyyyyyy(zzzzzzzzzzzzz[0]) == 'aaaaaaaaaaa' and xxxxxxxxxxxx.yyyyyyyy(zzzzzzzzzzzzz[0].mmmmmmmm[0]) == 'bbbbbbb'):  # yapf: disable
                pass
        """)
    self.assertYapfReformats(unformatted_code, expected_formatted_code)

  def testDisableWholeDataStructure(self):
    unformatted_code = textwrap.dedent(u"""\
        A = set([
            'hello',
            'world',
        ])  # yapf: disable
        """)
    expected_formatted_code = textwrap.dedent(u"""\
        A = set([
            'hello',
            'world',
        ])  # yapf: disable
        """)
    self.assertYapfReformats(unformatted_code, expected_formatted_code)

  def testDisableButAdjustIndentations(self):
    unformatted_code = textwrap.dedent(u"""\
        class SplitPenaltyTest(unittest.TestCase):
          def testUnbreakable(self):
            self._CheckPenalties(tree, [
            ])  # yapf: disable
        """)
    expected_formatted_code = textwrap.dedent(u"""\
        class SplitPenaltyTest(unittest.TestCase):
            def testUnbreakable(self):
                self._CheckPenalties(tree, [
                ])  # yapf: disable
        """)
    self.assertYapfReformats(unformatted_code, expected_formatted_code)

  def testRetainingHorizontalWhitespace(self):
    unformatted_code = textwrap.dedent(u"""\
        def h():
            if (xxxxxxxxxxxx.yyyyyyyy(zzzzzzzzzzzzz[0]) == 'aaaaaaaaaaa' and xxxxxxxxxxxx.yyyyyyyy(zzzzzzzzzzzzz[0].mmmmmmmm[0]) == 'bbbbbbb'):
                pass

        def g():
            if (xxxxxxxxxxxx.yyyyyyyy        (zzzzzzzzzzzzz  [0]) ==     'aaaaaaaaaaa' and    xxxxxxxxxxxx.yyyyyyyy(zzzzzzzzzzzzz[0].mmmmmmmm[0]) == 'bbbbbbb'):  # yapf: disable
                pass
        """)
    expected_formatted_code = textwrap.dedent(u"""\
        def h():
            if (xxxxxxxxxxxx.yyyyyyyy(zzzzzzzzzzzzz[0]) == 'aaaaaaaaaaa' and
                xxxxxxxxxxxx.yyyyyyyy(zzzzzzzzzzzzz[0].mmmmmmmm[0]) == 'bbbbbbb'):
                pass


        def g():
            if (xxxxxxxxxxxx.yyyyyyyy        (zzzzzzzzzzzzz  [0]) ==     'aaaaaaaaaaa' and    xxxxxxxxxxxx.yyyyyyyy(zzzzzzzzzzzzz[0].mmmmmmmm[0]) == 'bbbbbbb'):  # yapf: disable
                pass
        """)
    self.assertYapfReformats(unformatted_code, expected_formatted_code)

  def testREtainingVerticalWhitespace(self):
    unformatted_code = textwrap.dedent(u"""\
        def h():
            if (xxxxxxxxxxxx.yyyyyyyy(zzzzzzzzzzzzz[0]) == 'aaaaaaaaaaa' and xxxxxxxxxxxx.yyyyyyyy(zzzzzzzzzzzzz[0].mmmmmmmm[0]) == 'bbbbbbb'):
                pass

        def g():


            if (xxxxxxxxxxxx.yyyyyyyy(zzzzzzzzzzzzz[0]) == 'aaaaaaaaaaa' and xxxxxxxxxxxx.yyyyyyyy(zzzzzzzzzzzzz[0].mmmmmmmm[0]) == 'bbbbbbb'):

                pass
        """)
    expected_formatted_code = textwrap.dedent(u"""\
        def h():
            if (xxxxxxxxxxxx.yyyyyyyy(zzzzzzzzzzzzz[0]) == 'aaaaaaaaaaa' and
                xxxxxxxxxxxx.yyyyyyyy(zzzzzzzzzzzzz[0].mmmmmmmm[0]) == 'bbbbbbb'):
                pass

        def g():


            if (xxxxxxxxxxxx.yyyyyyyy(zzzzzzzzzzzzz[0]) == 'aaaaaaaaaaa' and xxxxxxxxxxxx.yyyyyyyy(zzzzzzzzzzzzz[0].mmmmmmmm[0]) == 'bbbbbbb'):

                pass
        """)
    self.assertYapfReformats(unformatted_code, expected_formatted_code,
                             extra_options=['--lines', '1-2'])

    unformatted_code = textwrap.dedent(u"""\


        if a:     b


        if c:
            to_much      + indent

            same



        #comment

        #   trailing whitespace
        """)
    expected_formatted_code = textwrap.dedent(u"""\
        if a: b


        if c:
            to_much      + indent

            same



        #comment

        #   trailing whitespace
        """)
    self.assertYapfReformats(unformatted_code, expected_formatted_code,
                             extra_options=['--lines', '3-3',
                                            '--lines', '13-13'])

    unformatted_code = textwrap.dedent(u"""\
        '''
        docstring

        '''

        import blah
        """)

    self.assertYapfReformats(unformatted_code, unformatted_code,
                             extra_options=['--lines', '2-2'])

  def testRetainingSemicolonsWhenSpecifyingLines(self):
    unformatted_code = textwrap.dedent("""\
        a = line_to_format
        def f():
            x = y + 42; z = n * 42
            if True: a += 1 ; b += 1 ; c += 1
        """)
    expected_formatted_code = textwrap.dedent("""\
        a = line_to_format
        def f():
            x = y + 42; z = n * 42
            if True: a += 1 ; b += 1 ; c += 1
        """)
    self.assertYapfReformats(unformatted_code, expected_formatted_code,
                             extra_options=['--lines', '1-1'])

  def testDisabledMultilineStrings(self):
    unformatted_code = textwrap.dedent('''\
        foo=42
        def f():
            email_text += """<html>This is a really long docstring that goes over the column limit and is multi-line.<br><br>
        <b>Czar: </b>"""+despot["Nicholas"]+"""<br>
        <b>Minion: </b>"""+serf["Dmitri"]+"""<br>
        <b>Residence: </b>"""+palace["Winter"]+"""<br>
        </body>
        </html>"""
        ''')
    expected_formatted_code = textwrap.dedent('''\
        foo = 42
        def f():
            email_text += """<html>This is a really long docstring that goes over the column limit and is multi-line.<br><br>
        <b>Czar: </b>"""+despot["Nicholas"]+"""<br>
        <b>Minion: </b>"""+serf["Dmitri"]+"""<br>
        <b>Residence: </b>"""+palace["Winter"]+"""<br>
        </body>
        </html>"""
        ''')
    self.assertYapfReformats(unformatted_code, expected_formatted_code,
                             extra_options=['--lines', '1-1'])

  def testDisableWhenSpecifyingLines(self):
    unformatted_code = textwrap.dedent(u"""\
        # yapf: disable
        A = set([
            'hello',
            'world',
        ])
        # yapf: enable
        B = set([
            'hello',
            'world',
        ])  # yapf: disable
        """)
    expected_formatted_code = textwrap.dedent(u"""\
        # yapf: disable
        A = set([
            'hello',
            'world',
        ])
        # yapf: enable
        B = set([
            'hello',
            'world',
        ])  # yapf: disable
        """)
    self.assertYapfReformats(unformatted_code, expected_formatted_code,
                             extra_options=['--lines', '1-10'])

  def testDisableFormattingInDataLiteral(self):
    unformatted_code = textwrap.dedent(u"""\
        def horrible():
          oh_god()
          why_would_you()
          [
             'do',

              'that',
          ]

        def still_horrible():
            oh_god()
            why_would_you()
            [
                'do',

                'that',
            ]
        """)
    expected_formatted_code = textwrap.dedent(u"""\
        def horrible():
            oh_god()
            why_would_you()
            [
               'do',

                'that',
            ]

        def still_horrible():
            oh_god()
            why_would_you()
            ['do', 'that', ]
        """)
    self.assertYapfReformats(unformatted_code, expected_formatted_code,
                             extra_options=['--lines', '10-18'])

  def testRetainVerticalFormattingBetweenDisabledAndEnabledLines(self):
    unformatted_code = textwrap.dedent(u"""\
        class A(object):
            def aaaaaaaaaaaaa(self):
                c = bbbbbbbbb.ccccccccc('challenge', 0, 1, 10)
                self.assertEqual(
                    ('ddddddddddddddddddddddddd',
             'eeeeeeeeeeeeeeeeeeeeeeeee.%s' %
                     c.ffffffffffff),
             gggggggggggg.hhhhhhhhh(c, c.ffffffffffff))
                iiiii = jjjjjjjjjjjjjj.iiiii
        """)
    expected_formatted_code = textwrap.dedent(u"""\
        class A(object):
            def aaaaaaaaaaaaa(self):
                c = bbbbbbbbb.ccccccccc('challenge', 0, 1, 10)
                self.assertEqual(
                    ('ddddddddddddddddddddddddd', 'eeeeeeeeeeeeeeeeeeeeeeeee.%s' %
                     c.ffffffffffff), gggggggggggg.hhhhhhhhh(c, c.ffffffffffff))
                iiiii = jjjjjjjjjjjjjj.iiiii
        """)
    self.assertYapfReformats(unformatted_code, expected_formatted_code,
                             extra_options=['--lines', '4-7'])

  def testFormatLinesSpecifiedInMiddleOfExpression(self):
    unformatted_code = textwrap.dedent(u"""\
        class A(object):
            def aaaaaaaaaaaaa(self):
                c = bbbbbbbbb.ccccccccc('challenge', 0, 1, 10)
                self.assertEqual(
                    ('ddddddddddddddddddddddddd',
             'eeeeeeeeeeeeeeeeeeeeeeeee.%s' %
                     c.ffffffffffff),
             gggggggggggg.hhhhhhhhh(c, c.ffffffffffff))
                iiiii = jjjjjjjjjjjjjj.iiiii
        """)
    expected_formatted_code = textwrap.dedent(u"""\
        class A(object):
            def aaaaaaaaaaaaa(self):
                c = bbbbbbbbb.ccccccccc('challenge', 0, 1, 10)
                self.assertEqual(
                    ('ddddddddddddddddddddddddd', 'eeeeeeeeeeeeeeeeeeeeeeeee.%s' %
                     c.ffffffffffff), gggggggggggg.hhhhhhhhh(c, c.ffffffffffff))
                iiiii = jjjjjjjjjjjjjj.iiiii
        """)
    self.assertYapfReformats(unformatted_code, expected_formatted_code,
                             extra_options=['--lines', '5-6'])


class BadInputTest(unittest.TestCase):
  """Test yapf's behaviour when passed bad input."""

  def testBadSyntax(self):
    code = '  a = 1\n'
    self.assertRaises(SyntaxError, yapf_api.FormatCode, code)


if __name__ == '__main__':
  unittest.main()
