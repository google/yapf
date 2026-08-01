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
"""Tests for yapf_third_party._ylib2to3.pgen2.grammar."""

import os
import shutil
import stat
import tempfile
import unittest

from yapf_third_party._ylib2to3.pgen2 import grammar

from yapftests import yapf_test_helper


class GrammarDumpTest(yapf_test_helper.YAPFTest):

  def setUp(self):
    self.test_tmpdir = tempfile.mkdtemp()

  def tearDown(self):
    shutil.rmtree(self.test_tmpdir, ignore_errors=True)

  def testDumpAndLoadRoundTrip(self):
    g = grammar.Grammar()
    target = os.path.join(self.test_tmpdir, 'test.pickle')
    g.dump(target)
    self.assertTrue(os.path.exists(target))

    loaded = grammar.Grammar()
    loaded.load(target)
    self.assertEqual(g.__dict__, loaded.__dict__)

  @unittest.skipIf(
      os.name == 'nt' or os.geteuid() == 0,
      'permission bits are not enforced for root or on Windows')
  def testDumpFailsImmediatelyWhenDirectoryIsUnwritable(self):
    # Regression test for #1311: a denied cache write must raise promptly
    # instead of retrying (potentially for a very long time, as observed on
    # Windows with the stdlib tempfile module).
    unwritable_dir = os.path.join(self.test_tmpdir, 'unwritable')
    os.mkdir(unwritable_dir)
    os.chmod(unwritable_dir, stat.S_IRUSR | stat.S_IXUSR)

    g = grammar.Grammar()
    target = os.path.join(unwritable_dir, 'test.pickle')
    with self.assertRaises(OSError):
      g.dump(target)

    self.assertEqual([], os.listdir(unwritable_dir))


if __name__ == '__main__':
  unittest.main()
