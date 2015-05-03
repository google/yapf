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
import sys
import tempfile
import unittest

from yapf.yapflib import file_resources
from yapf.yapflib import py3compat


@contextlib.contextmanager
def stdout_redirector(stream):  # pylint: disable=invalid-name
  old_stdout = sys.stdout
  sys.stdout = stream
  try:
    yield
  finally:
    sys.stdout = old_stdout


class GetDefaultStyleForDirTest(unittest.TestCase):

  def setUp(self):
    self.test_tmpdir = tempfile.mkdtemp()

  def tearDown(self):
    shutil.rmtree(self.test_tmpdir)

  def test_no_local_style(self):
    test_file = os.path.join(self.test_tmpdir, 'file.py')
    style_name = file_resources.GetDefaultStyleForDir(test_file)
    self.assertEqual(style_name, 'pep8')

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


def _touch_files(filenames):
  for name in filenames:
    open(name, 'a').close()


class GetCommandLineFilesTest(unittest.TestCase):

  def setUp(self):
    self.test_tmpdir = tempfile.mkdtemp()

  def tearDown(self):
    shutil.rmtree(self.test_tmpdir)

  def _make_test_dir(self, name):
    fullpath = os.path.join(self.test_tmpdir, name)
    os.makedirs(fullpath)
    return fullpath

  def test_find_files_not_dirs(self):
    tdir1 = self._make_test_dir('test1')
    tdir2 = self._make_test_dir('test2')
    file1 = os.path.join(tdir1, 'testfile1.py')
    file2 = os.path.join(tdir2, 'testfile2.py')
    _touch_files([file1, file2])

    self.assertEqual(file_resources.GetCommandLineFiles([file1, file2],
                                                        recursive=False),
                     [file1, file2])
    self.assertEqual(file_resources.GetCommandLineFiles([file1, file2],
                                                        recursive=True),
                     [file1, file2])

  def test_nonrecursive_find_in_dir(self):
    tdir1 = self._make_test_dir('test1')
    tdir2 = self._make_test_dir('test1/foo')
    file1 = os.path.join(tdir1, 'testfile1.py')
    file2 = os.path.join(tdir2, 'testfile2.py')
    _touch_files([file1, file2])

    self.assertEqual(file_resources.GetCommandLineFiles([tdir1],
                                                        recursive=False),
                     [file1])

  def test_recursive_find_in_dir(self):
    tdir1 = self._make_test_dir('test1')
    tdir2 = self._make_test_dir('test2/testinner/')
    tdir3 = self._make_test_dir('test3/foo/bar/bas/kkk')
    files = [os.path.join(tdir1, 'testfile1.py'),
             os.path.join(tdir2, 'testfile2.py'),
             os.path.join(tdir3, 'testfile3.py')]
    _touch_files(files)

    self.assertEqual(
        sorted(file_resources.GetCommandLineFiles([self.test_tmpdir],
                                                  recursive=True)),
        sorted(files))


class IsPythonFileTest(unittest.TestCase):

  def setUp(self):
    self.test_tmpdir = tempfile.mkdtemp()

  def tearDown(self):
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
  def setUpClass(cls):
    cls.test_tmpdir = tempfile.mkdtemp()

  @classmethod
  def tearDownClass(cls):
    shutil.rmtree(cls.test_tmpdir)

  def test_write_to_file(self):
    s = u'foobar'
    with tempfile.NamedTemporaryFile(dir=self.test_tmpdir) as testfile:
      file_resources.WriteReformattedCode(testfile.name, s,
                                          in_place=True,
                                          encoding='utf-8')
      testfile.flush()

      with open(testfile.name) as f:
        self.assertEqual(f.read(), s)

  def test_write_to_stdout(self):
    s = u'foobar'
    stream = BufferedByteStream() if py3compat.PY3 else py3compat.StringIO()
    with stdout_redirector(stream):
      file_resources.WriteReformattedCode(None, s,
                                          in_place=False,
                                          encoding='utf-8')
    self.assertEqual(stream.getvalue(), s)

  def test_write_encoded_to_stdout(self):
    s = '\ufeff# -*- coding: utf-8 -*-\nresult = "passed"\n'  # pylint: disable=anomalous-unicode-escape-in-string
    stream = BufferedByteStream() if py3compat.PY3 else py3compat.StringIO()
    with stdout_redirector(stream):
      file_resources.WriteReformattedCode(None, s,
                                          in_place=False,
                                          encoding='utf-8')
    self.assertEqual(stream.getvalue(), s)


if __name__ == '__main__':
  unittest.main()
