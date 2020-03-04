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
"""Tests for yapf.file_resources."""

import contextlib
import os
import shutil
import tempfile
import unittest

from yapf.yapflib import errors
from yapf.yapflib import file_resources
from yapf.yapflib import py3compat

from yapftests import utils


@contextlib.contextmanager
def _restore_working_dir():
  curdir = os.getcwd()
  try:
    yield
  finally:
    os.chdir(curdir)


@contextlib.contextmanager
def _exists_mocked_in_module(module, mock_implementation):
  unmocked_exists = getattr(module, 'exists')
  setattr(module, 'exists', mock_implementation)
  try:
    yield
  finally:
    setattr(module, 'exists', unmocked_exists)


class GetExcludePatternsForDir(unittest.TestCase):

  def setUp(self):  # pylint: disable=g-missing-super-call
    self.test_tmpdir = tempfile.mkdtemp()

  def tearDown(self):  # pylint: disable=g-missing-super-call
    shutil.rmtree(self.test_tmpdir)

  def _make_test_dir(self, name):
    fullpath = os.path.normpath(os.path.join(self.test_tmpdir, name))
    os.makedirs(fullpath)
    return fullpath

  def test_get_exclude_file_patterns(self):
    local_ignore_file = os.path.join(self.test_tmpdir, '.yapfignore')
    ignore_patterns = ['temp/**/*.py', 'temp2/*.py']
    with open(local_ignore_file, 'w') as f:
      f.writelines('\n'.join(ignore_patterns))

    self.assertEqual(
        sorted(file_resources.GetExcludePatternsForDir(self.test_tmpdir)),
        sorted(ignore_patterns))


class GetDefaultStyleForDirTest(unittest.TestCase):

  def setUp(self):  # pylint: disable=g-missing-super-call
    self.test_tmpdir = tempfile.mkdtemp()

  def tearDown(self):  # pylint: disable=g-missing-super-call
    shutil.rmtree(self.test_tmpdir)

  def test_no_local_style(self):
    test_file = os.path.join(self.test_tmpdir, 'file.py')
    style_name = file_resources.GetDefaultStyleForDir(test_file)
    self.assertEqual(style_name, 'pep8')

  def test_no_local_style_custom_default(self):
    test_file = os.path.join(self.test_tmpdir, 'file.py')
    style_name = file_resources.GetDefaultStyleForDir(
        test_file, default_style='custom-default')
    self.assertEqual(style_name, 'custom-default')

  def test_with_local_style(self):
    # Create an empty .style.yapf file in test_tmpdir
    style_file = os.path.join(self.test_tmpdir, '.style.yapf')
    open(style_file, 'w').close()

    test_filename = os.path.join(self.test_tmpdir, 'file.py')
    self.assertEqual(style_file,
                     file_resources.GetDefaultStyleForDir(test_filename))

    test_filename = os.path.join(self.test_tmpdir, 'dir1', 'file.py')
    self.assertEqual(style_file,
                     file_resources.GetDefaultStyleForDir(test_filename))

  def test_setup_config(self):
    # An empty setup.cfg file should not be used
    setup_config = os.path.join(self.test_tmpdir, 'setup.cfg')
    open(setup_config, 'w').close()

    test_dir = os.path.join(self.test_tmpdir, 'dir1')
    style_name = file_resources.GetDefaultStyleForDir(test_dir)
    self.assertEqual(style_name, 'pep8')

    # One with a '[yapf]' section should be used
    with open(setup_config, 'w') as f:
      f.write('[yapf]\n')
    self.assertEqual(setup_config,
                     file_resources.GetDefaultStyleForDir(test_dir))

  def test_local_style_at_root(self):
    # Test behavior of files located on the root, and under root.
    rootdir = os.path.abspath(os.path.sep)
    test_dir_at_root = os.path.join(rootdir, 'dir1')
    test_dir_under_root = os.path.join(rootdir, 'dir1', 'dir2')

    # Fake placing only a style file at the root by mocking `os.path.exists`.
    style_file = os.path.join(rootdir, '.style.yapf')

    def mock_exists_implementation(path):
      return path == style_file

    with _exists_mocked_in_module(file_resources.os.path,
                                  mock_exists_implementation):
      # Both files should find the style file at the root.
      default_style_at_root = file_resources.GetDefaultStyleForDir(
          test_dir_at_root)
      self.assertEqual(style_file, default_style_at_root)
      default_style_under_root = file_resources.GetDefaultStyleForDir(
          test_dir_under_root)
      self.assertEqual(style_file, default_style_under_root)


def _touch_files(filenames):
  for name in filenames:
    open(name, 'a').close()


class GetCommandLineFilesTest(unittest.TestCase):

  def setUp(self):  # pylint: disable=g-missing-super-call
    self.test_tmpdir = tempfile.mkdtemp()
    self.old_dir = os.getcwd()

  def tearDown(self):  # pylint: disable=g-missing-super-call
    shutil.rmtree(self.test_tmpdir)
    os.chdir(self.old_dir)

  def _make_test_dir(self, name):
    fullpath = os.path.normpath(os.path.join(self.test_tmpdir, name))
    os.makedirs(fullpath)
    return fullpath

  def test_find_files_not_dirs(self):
    tdir1 = self._make_test_dir('test1')
    tdir2 = self._make_test_dir('test2')
    file1 = os.path.join(tdir1, 'testfile1.py')
    file2 = os.path.join(tdir2, 'testfile2.py')
    _touch_files([file1, file2])

    self.assertEqual(
        file_resources.GetCommandLineFiles([file1, file2],
                                           recursive=False,
                                           exclude=None), [file1, file2])
    self.assertEqual(
        file_resources.GetCommandLineFiles([file1, file2],
                                           recursive=True,
                                           exclude=None), [file1, file2])

  def test_nonrecursive_find_in_dir(self):
    tdir1 = self._make_test_dir('test1')
    tdir2 = self._make_test_dir('test1/foo')
    file1 = os.path.join(tdir1, 'testfile1.py')
    file2 = os.path.join(tdir2, 'testfile2.py')
    _touch_files([file1, file2])

    self.assertRaises(
        errors.YapfError,
        file_resources.GetCommandLineFiles,
        command_line_file_list=[tdir1],
        recursive=False,
        exclude=None)

  def test_recursive_find_in_dir(self):
    tdir1 = self._make_test_dir('test1')
    tdir2 = self._make_test_dir('test2/testinner/')
    tdir3 = self._make_test_dir('test3/foo/bar/bas/xxx')
    files = [
        os.path.join(tdir1, 'testfile1.py'),
        os.path.join(tdir2, 'testfile2.py'),
        os.path.join(tdir3, 'testfile3.py'),
    ]
    _touch_files(files)

    self.assertEqual(
        sorted(
            file_resources.GetCommandLineFiles([self.test_tmpdir],
                                               recursive=True,
                                               exclude=None)), sorted(files))

  def test_recursive_find_in_dir_with_exclude(self):
    tdir1 = self._make_test_dir('test1')
    tdir2 = self._make_test_dir('test2/testinner/')
    tdir3 = self._make_test_dir('test3/foo/bar/bas/xxx')
    files = [
        os.path.join(tdir1, 'testfile1.py'),
        os.path.join(tdir2, 'testfile2.py'),
        os.path.join(tdir3, 'testfile3.py'),
    ]
    _touch_files(files)

    self.assertEqual(
        sorted(
            file_resources.GetCommandLineFiles([self.test_tmpdir],
                                               recursive=True,
                                               exclude=['*test*3.py'])),
        sorted([
            os.path.join(tdir1, 'testfile1.py'),
            os.path.join(tdir2, 'testfile2.py'),
        ]))

  def test_find_with_excluded_hidden_dirs(self):
    tdir1 = self._make_test_dir('.test1')
    tdir2 = self._make_test_dir('test_2')
    tdir3 = self._make_test_dir('test.3')
    files = [
        os.path.join(tdir1, 'testfile1.py'),
        os.path.join(tdir2, 'testfile2.py'),
        os.path.join(tdir3, 'testfile3.py'),
    ]
    _touch_files(files)

    actual = file_resources.GetCommandLineFiles([self.test_tmpdir],
                                                recursive=True,
                                                exclude=['*.test1*'])

    self.assertEqual(
        sorted(actual),
        sorted([
            os.path.join(tdir2, 'testfile2.py'),
            os.path.join(tdir3, 'testfile3.py'),
        ]))

  def test_find_with_excluded_hidden_dirs_relative(self):
    """Test find with excluded hidden dirs.

    A regression test against a specific case where a hidden directory (one
    beginning with a period) is being excluded, but it is also an immediate
    child of the current directory which has been specified in a relative
    manner.

    At its core, the bug has to do with overzelous stripping of "./foo" so that
    it removes too much from "./.foo" .
    """
    tdir1 = self._make_test_dir('.test1')
    tdir2 = self._make_test_dir('test_2')
    tdir3 = self._make_test_dir('test.3')
    files = [
        os.path.join(tdir1, 'testfile1.py'),
        os.path.join(tdir2, 'testfile2.py'),
        os.path.join(tdir3, 'testfile3.py'),
    ]
    _touch_files(files)

    # We must temporarily change the current directory, so that we test against
    # patterns like ./.test1/file instead of /tmp/foo/.test1/file
    with _restore_working_dir():

      os.chdir(self.test_tmpdir)
      actual = file_resources.GetCommandLineFiles(
          [os.path.relpath(self.test_tmpdir)],
          recursive=True,
          exclude=['*.test1*'])

      self.assertEqual(
          sorted(actual),
          sorted([
              os.path.join(
                  os.path.relpath(self.test_tmpdir), os.path.basename(tdir2),
                  'testfile2.py'),
              os.path.join(
                  os.path.relpath(self.test_tmpdir), os.path.basename(tdir3),
                  'testfile3.py'),
          ]))

  def test_find_with_excluded_dirs(self):
    tdir1 = self._make_test_dir('test1')
    tdir2 = self._make_test_dir('test2/testinner/')
    tdir3 = self._make_test_dir('test3/foo/bar/bas/xxx')
    files = [
        os.path.join(tdir1, 'testfile1.py'),
        os.path.join(tdir2, 'testfile2.py'),
        os.path.join(tdir3, 'testfile3.py'),
    ]
    _touch_files(files)

    os.chdir(self.test_tmpdir)

    found = sorted(
        file_resources.GetCommandLineFiles(['test1', 'test2', 'test3'],
                                           recursive=True,
                                           exclude=[
                                               'test1',
                                               'test2/testinner/',
                                           ]))

    self.assertEqual(found, ['test3/foo/bar/bas/xxx/testfile3.py'])

    found = sorted(
        file_resources.GetCommandLineFiles(['.'],
                                           recursive=True,
                                           exclude=[
                                               'test1',
                                               'test3',
                                           ]))

    self.assertEqual(found, ['./test2/testinner/testfile2.py'])

  def test_find_with_excluded_current_dir(self):
    with self.assertRaises(errors.YapfError):
      file_resources.GetCommandLineFiles([], False, exclude=['./z'])


class IsPythonFileTest(unittest.TestCase):

  def setUp(self):  # pylint: disable=g-missing-super-call
    self.test_tmpdir = tempfile.mkdtemp()

  def tearDown(self):  # pylint: disable=g-missing-super-call
    shutil.rmtree(self.test_tmpdir)

  def test_with_py_extension(self):
    file1 = os.path.join(self.test_tmpdir, 'testfile1.py')
    self.assertTrue(file_resources.IsPythonFile(file1))

  def test_empty_without_py_extension(self):
    file1 = os.path.join(self.test_tmpdir, 'testfile1')
    self.assertFalse(file_resources.IsPythonFile(file1))
    file2 = os.path.join(self.test_tmpdir, 'testfile1.rb')
    self.assertFalse(file_resources.IsPythonFile(file2))

  def test_python_shebang(self):
    file1 = os.path.join(self.test_tmpdir, 'testfile1')
    with open(file1, 'w') as f:
      f.write(u'#!/usr/bin/python\n')
    self.assertTrue(file_resources.IsPythonFile(file1))

    file2 = os.path.join(self.test_tmpdir, 'testfile2.run')
    with open(file2, 'w') as f:
      f.write(u'#! /bin/python2\n')
    self.assertTrue(file_resources.IsPythonFile(file1))

  def test_with_latin_encoding(self):
    file1 = os.path.join(self.test_tmpdir, 'testfile1')
    with py3compat.open_with_encoding(file1, mode='w', encoding='latin-1') as f:
      f.write(u'#! /bin/python2\n')
    self.assertTrue(file_resources.IsPythonFile(file1))

  def test_with_invalid_encoding(self):
    file1 = os.path.join(self.test_tmpdir, 'testfile1')
    with open(file1, 'w') as f:
      f.write(u'#! /bin/python2\n')
      f.write(u'# -*- coding: iso-3-14159 -*-\n')
    self.assertFalse(file_resources.IsPythonFile(file1))


class IsIgnoredTest(unittest.TestCase):

  def test_root_path(self):
    self.assertTrue(file_resources.IsIgnored('media', ['media']))
    self.assertFalse(file_resources.IsIgnored('media', ['media/*']))

  def test_sub_path(self):
    self.assertTrue(file_resources.IsIgnored('media/a', ['*/a']))
    self.assertTrue(file_resources.IsIgnored('media/b', ['media/*']))
    self.assertTrue(file_resources.IsIgnored('media/b/c', ['*/*/c']))

  def test_trailing_slash(self):
    self.assertTrue(file_resources.IsIgnored('z', ['z']))
    self.assertTrue(file_resources.IsIgnored('z', ['z/']))


class BufferedByteStream(object):

  def __init__(self):
    self.stream = py3compat.BytesIO()

  def getvalue(self):  # pylint: disable=invalid-name
    return self.stream.getvalue().decode('utf-8')

  @property
  def buffer(self):
    return self.stream


class WriteReformattedCodeTest(unittest.TestCase):

  @classmethod
  def setUpClass(cls):  # pylint: disable=g-missing-super-call
    cls.test_tmpdir = tempfile.mkdtemp()

  @classmethod
  def tearDownClass(cls):  # pylint: disable=g-missing-super-call
    shutil.rmtree(cls.test_tmpdir)

  def test_write_to_file(self):
    s = u'foobar\n'
    with utils.NamedTempFile(dirname=self.test_tmpdir) as (f, fname):
      file_resources.WriteReformattedCode(
          fname, s, in_place=True, encoding='utf-8')
      f.flush()

      with open(fname) as f2:
        self.assertEqual(f2.read(), s)

  def test_write_to_stdout(self):
    s = u'foobar'
    stream = BufferedByteStream() if py3compat.PY3 else py3compat.StringIO()
    with utils.stdout_redirector(stream):
      file_resources.WriteReformattedCode(
          None, s, in_place=False, encoding='utf-8')
    self.assertEqual(stream.getvalue(), s)

  def test_write_encoded_to_stdout(self):
    s = '\ufeff# -*- coding: utf-8 -*-\nresult = "passed"\n'  # pylint: disable=anomalous-unicode-escape-in-string
    stream = BufferedByteStream() if py3compat.PY3 else py3compat.StringIO()
    with utils.stdout_redirector(stream):
      file_resources.WriteReformattedCode(
          None, s, in_place=False, encoding='utf-8')
    self.assertEqual(stream.getvalue(), s)


class LineEndingTest(unittest.TestCase):

  def test_line_ending_linefeed(self):
    lines = ['spam\n', 'spam\n']
    actual = file_resources.LineEnding(lines)
    self.assertEqual(actual, '\n')

  def test_line_ending_carriage_return(self):
    lines = ['spam\r', 'spam\r']
    actual = file_resources.LineEnding(lines)
    self.assertEqual(actual, '\r')

  def test_line_ending_combo(self):
    lines = ['spam\r\n', 'spam\r\n']
    actual = file_resources.LineEnding(lines)
    self.assertEqual(actual, '\r\n')

  def test_line_ending_weighted(self):
    lines = [
        'spam\n',
        'spam\n',
        'spam\r',
        'spam\r\n',
    ]
    actual = file_resources.LineEnding(lines)
    self.assertEqual(actual, '\n')


if __name__ == '__main__':
  unittest.main()
