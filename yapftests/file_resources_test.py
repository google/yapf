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

  def testWriteToFile(self):
    s = u'foobar'
    with tempfile.NamedTemporaryFile(dir=self.test_tmpdir) as testfile:
      file_resources.WriteReformattedCode(testfile.name, s,
                                          in_place=True,
                                          encoding='utf-8')
      testfile.flush()

      with open(testfile.name) as f:
        self.assertEqual(f.read(), s)

  def testWriteToStdout(self):
    s = u'foobar'
    stream = BufferedByteStream() if py3compat.PY3 else py3compat.StringIO()
    with stdout_redirector(stream):
      file_resources.WriteReformattedCode(None, s,
                                          in_place=False,
                                          encoding='utf-8')
    self.assertEqual(stream.getvalue(), s)

  def testWriteEncodedToStdout(self):
    s = '\ufeff# -*- coding: utf-8 -*-\nresult = "passed"\n'  # pylint: disable=anomalous-unicode-escape-in-string
    stream = BufferedByteStream() if py3compat.PY3 else py3compat.StringIO()
    with stdout_redirector(stream):
      file_resources.WriteReformattedCode(None, s,
                                          in_place=False,
                                          encoding='utf-8')
    self.assertEqual(stream.getvalue(), s)


if __name__ == '__main__':
  unittest.main()
