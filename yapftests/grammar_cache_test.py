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
"""Grammar cache entries must follow the contents, not checkout timestamps."""

import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from yapf.pytree import pytree_utils

# Initialize YAPF before accessing its vendored driver (the driver imports YAPF).
driver = pytree_utils.driver


class GrammarCacheTest(unittest.TestCase):

  def testDifferentCheckoutsWithSameBasenameAndTimestamp(self):
    with tempfile.TemporaryDirectory() as directory:
      root = Path(directory)
      cache = root / 'cache'
      with mock.patch.object(driver, 'user_cache_dir', return_value=str(cache)):
        grammars = []
        for i, keyword in enumerate(('first', 'second', 'first')):
          source = root / str(i) / 'Grammar.txt'
          source.parent.mkdir()
          source.write_text("start: '%s' NEWLINE ENDMARKER\n" % keyword)
          os.utime(str(source), (1, 1))
          grammars.append(driver.load_grammar(str(source)))
        self.assertIn('first', grammars[0].keywords)
        self.assertIn('second', grammars[1].keywords)
        self.assertNotIn('first', grammars[1].keywords)
        self.assertIn('first', grammars[2].keywords)
        self.assertEqual(2, len(list(cache.glob('*.pickle'))))

  def testSourceChangesWithPreservedTimestamp(self):
    with tempfile.TemporaryDirectory() as directory:
      root = Path(directory)
      source = root / 'Grammar.txt'
      with mock.patch.object(driver, 'user_cache_dir', return_value=str(root)):
        for keyword in ('before', 'after'):
          source.write_text("start: '%s' NEWLINE ENDMARKER\n" % keyword)
          os.utime(str(source), (1, 1))
          grammar = driver.load_grammar(str(source))
          self.assertIn(keyword, grammar.keywords)

  def testPackageSourceIsAlsoFingerprintIsolated(self):
    with tempfile.TemporaryDirectory() as directory:
      with mock.patch.object(driver, 'user_cache_dir', return_value=directory):
        for keyword in ('first', 'second'):
          source = ("start: '%s' NEWLINE ENDMARKER\n" % keyword).encode()
          with mock.patch.object(
              driver.pkgutil, 'get_data', return_value=source):
            grammar = driver.load_grammar(
                os.path.join(directory, 'missing.txt'))
          self.assertIn(keyword, grammar.keywords)

  def testExplicitCacheAndForceStillWork(self):
    with tempfile.TemporaryDirectory() as directory:
      root = Path(directory)
      source = root / 'Grammar.txt'
      target = root / 'explicit.pickle'
      source.write_text("start: 'original' NEWLINE ENDMARKER\n")
      driver.load_grammar(str(source), gp=str(target))
      self.assertTrue(target.is_file())
      source.write_text("start: 'changed' NEWLINE ENDMARKER\n")
      grammar = driver.load_grammar(str(source), gp=str(target), force=True)
      self.assertIn('changed', grammar.keywords)


if __name__ == '__main__':
  unittest.main()
