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
"""Tests for yapf.style."""

import contextlib
import shutil
import tempfile
import textwrap
import unittest

from yapf.yapflib import style


class UtilsTest(unittest.TestCase):

  def testStringListConverter(self):
    self.assertEqual(style._StringListConverter('foo, bar'), ['foo', 'bar'])
    self.assertEqual(style._StringListConverter('foo,bar'), ['foo', 'bar'])
    self.assertEqual(style._StringListConverter('  foo'), ['foo'])
    self.assertEqual(style._StringListConverter('joe  ,foo,  bar'),
                     ['joe', 'foo', 'bar'])

  def testBoolConverter(self):
    self.assertEqual(style._BoolConverter('true'), True)
    self.assertEqual(style._BoolConverter('1'), True)
    self.assertEqual(style._BoolConverter('false'), False)
    self.assertEqual(style._BoolConverter('0'), False)


def _LooksLikeYapfStyle(cfg):
  return (cfg['INDENT_WIDTH'] == 2 and
          cfg['BLANK_LINE_BEFORE_NESTED_CLASS_OR_DEF'])


def _LooksLikeGoogleStyle(cfg):
  return (cfg['INDENT_WIDTH'] == 4 and
          cfg['BLANK_LINE_BEFORE_NESTED_CLASS_OR_DEF'])


def _LooksLikePEP8Style(cfg):
  return (cfg['INDENT_WIDTH'] == 4 and
          not cfg['BLANK_LINE_BEFORE_NESTED_CLASS_OR_DEF'])


class PredefinedStylesByNameTest(unittest.TestCase):

  def testDefault(self):
    # default is PEP8
    cfg = style.CreateStyleFromConfig(None)
    self.assertTrue(_LooksLikePEP8Style(cfg))

  def testGoogleByName(self):
    for google_name in ('yapf', 'Yapf', 'YAPF'):
      cfg = style.CreateStyleFromConfig(google_name)
      self.assertTrue(_LooksLikeYapfStyle(cfg))

  def testPEP8ByName(self):
    for pep8_name in ('PEP8', 'pep8', 'Pep8'):
      cfg = style.CreateStyleFromConfig(pep8_name)
      self.assertTrue(_LooksLikePEP8Style(cfg))


@contextlib.contextmanager
def _TempFileContents(dirname, contents):
  with tempfile.NamedTemporaryFile(dir=dirname, mode='w') as f:
    f.write(contents)
    f.flush()
    yield f


class StyleFromFileTest(unittest.TestCase):

  @classmethod
  def setUpClass(cls):
    cls.test_tmpdir = tempfile.mkdtemp()

  @classmethod
  def tearDownClass(cls):
    shutil.rmtree(cls.test_tmpdir)

  def testDefaultBasedOnStyle(self):
    cfg = textwrap.dedent('''\
        [style]
        continuation_indent_width = 20
        ''')
    with _TempFileContents(self.test_tmpdir, cfg) as f:
      cfg = style.CreateStyleFromConfig(f.name)
      self.assertTrue(_LooksLikePEP8Style(cfg))
      self.assertEqual(cfg['CONTINUATION_INDENT_WIDTH'], 20)

  def testDefaultBasedOnPEP8Style(self):
    cfg = textwrap.dedent('''\
        [style]
        based_on_style = pep8
        continuation_indent_width = 40
        ''')
    with _TempFileContents(self.test_tmpdir, cfg) as f:
      cfg = style.CreateStyleFromConfig(f.name)
      self.assertTrue(_LooksLikePEP8Style(cfg))
      self.assertEqual(cfg['CONTINUATION_INDENT_WIDTH'], 40)

  def testDefaultBasedOnYapfStyle(self):
    cfg = textwrap.dedent('''\
        [style]
        based_on_style = yapf
        split_penalty_matching_bracket = 33
        ''')
    with _TempFileContents(self.test_tmpdir, cfg) as f:
      cfg = style.CreateStyleFromConfig(f.name)
      self.assertTrue(_LooksLikeYapfStyle(cfg))
      self.assertEqual(cfg['SPLIT_PENALTY_MATCHING_BRACKET'], 33)

  def testDefaultBasedOnGoogleStyle(self):
    cfg = textwrap.dedent('''\
        [style]
        based_on_style = google
        split_penalty_matching_bracket = 33
        ''')
    with _TempFileContents(self.test_tmpdir, cfg) as f:
      cfg = style.CreateStyleFromConfig(f.name)
      self.assertTrue(_LooksLikeGoogleStyle(cfg))
      self.assertEqual(cfg['SPLIT_PENALTY_MATCHING_BRACKET'], 33)

  def testBoolOptionValue(self):
    cfg = textwrap.dedent('''\
        [style]
        based_on_style = yapf
        SPLIT_BEFORE_NAMED_ASSIGNS=False
        split_before_logical_operator = true
        ''')
    with _TempFileContents(self.test_tmpdir, cfg) as f:
      cfg = style.CreateStyleFromConfig(f.name)
      self.assertTrue(_LooksLikeYapfStyle(cfg))
      self.assertEqual(cfg['SPLIT_BEFORE_NAMED_ASSIGNS'], False)
      self.assertEqual(cfg['SPLIT_BEFORE_LOGICAL_OPERATOR'], True)

  def testStringListOptionValue(self):
    cfg = textwrap.dedent('''\
        [style]
        based_on_style = yapf
        I18N_FUNCTION_CALL = N_, V_, T_
        ''')
    with _TempFileContents(self.test_tmpdir, cfg) as f:
      cfg = style.CreateStyleFromConfig(f.name)
      self.assertTrue(_LooksLikeYapfStyle(cfg))
      self.assertEqual(cfg['I18N_FUNCTION_CALL'], ['N_', 'V_', 'T_'])

  def testErrorNoStyleFile(self):
    with self.assertRaisesRegexp(style.StyleConfigError,
                                 'is not a valid style or file path'):
      style.CreateStyleFromConfig('/8822/xyznosuchfile')

  def testErrorNoStyleSection(self):
    cfg = textwrap.dedent('''\
        [s]
        indent_width=2
        ''')
    with _TempFileContents(self.test_tmpdir, cfg) as f:
      with self.assertRaisesRegexp(style.StyleConfigError,
                                   'Unable to find section'):
        style.CreateStyleFromConfig(f.name)

  def testErrorUnknownStyleOption(self):
    cfg = textwrap.dedent('''\
        [style]
        indent_width=2
        hummus=2
        ''')
    with _TempFileContents(self.test_tmpdir, cfg) as f:
      with self.assertRaisesRegexp(style.StyleConfigError,
                                   'Unknown style option'):
        style.CreateStyleFromConfig(f.name)


class StyleFromCommandLine(unittest.TestCase):

  def testDefaultBasedOnStyle(self):
    cfg = style.CreateStyleFromConfig(
        '{based_on_style: pep8,'
        ' indent_width: 2,'
        ' blank_line_before_nested_class_or_def: True}')
    self.assertTrue(_LooksLikeYapfStyle(cfg))
    self.assertEqual(cfg['INDENT_WIDTH'], 2)


class StyleSettings(unittest.TestCase):

  def testSettings(self):
    settings = sorted(style.Settings())
    expected = sorted(list(style._style) + ['BASED_ON_STYLE'])
    self.assertListEqual(settings, expected)


if __name__ == '__main__':
  unittest.main()
