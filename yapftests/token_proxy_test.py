# Copyright 2026 The YAPF Authors. All Rights Reserved.
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
"""Lookahead must be replayable, nestable, and bounded by unread tokens."""

import ast
import sys
import unittest

from yapf.pytree import pytree_utils
from yapf.yapflib.yapf_api import FormatCode

TokenProxy = pytree_utils.driver.TokenProxy


class TokenProxyTest(unittest.TestCase):

  def testLookaheadDoesNotConsumeOrReadTokensTwice(self):
    reads = []

    def tokens():
      for value in range(6):
        reads.append(value)
        yield value

    proxy = TokenProxy(tokens())
    self.assertEqual(0, next(proxy))
    with proxy.release():
      self.assertEqual(3, proxy.eat(2))
      self.assertEqual(1, proxy.eat(0))
      self.assertEqual(3, proxy.eat(2))
    self.assertEqual([0, 1, 2, 3], reads)
    self.assertEqual([1, 2, 3, 4, 5], list(proxy))
    self.assertEqual(list(range(6)), reads)

  def testNestedLookaheadRestoresParentCursor(self):
    proxy = TokenProxy(iter(range(6)))
    self.assertEqual(0, next(proxy))
    with proxy.release():
      self.assertEqual(1, proxy.eat(0))
      with proxy.release():
        self.assertEqual(2, proxy.eat(0))
        self.assertEqual(3, proxy.eat(1))
      self.assertEqual(2, proxy.eat(1))
      with proxy.release():
        self.assertEqual(3, proxy.eat(0))
      self.assertEqual(3, proxy.eat(2))
    self.assertEqual([1, 2, 3, 4, 5], list(proxy))

  def testCompetingLookaheadsSeeTheSameStream(self):
    proxy = TokenProxy(iter(range(8)))
    next(proxy)
    with proxy.release():
      self.assertEqual(1, proxy.eat(0))
      for _ in range(3):
        with proxy.release():
          self.assertEqual(2, proxy.eat(0))
          self.assertEqual(5, proxy.eat(3))
      self.assertEqual(2, proxy.eat(1))
    self.assertEqual(list(range(1, 8)), list(proxy))

  def testUnwindingAfterErrorPreservesBufferedTokens(self):
    proxy = TokenProxy(iter(range(5)))
    with self.assertRaises(ValueError):
      with proxy.release():
        proxy.eat(0)
        with proxy.release():
          proxy.eat(2)
          raise ValueError('rejected parser route')
    self.assertEqual(list(range(5)), list(proxy))
    self.assertFalse(proxy._lookahead)

  def testLookaheadPastEofDoesNotLoseAvailableTokens(self):
    proxy = TokenProxy(iter(range(3)))
    with proxy.release():
      self.assertFalse(proxy.can_advance(8))
      self.assertTrue(proxy.can_advance(2))
    self.assertEqual([0, 1, 2], list(proxy))

  def testConsumedTokensAndScopesAreDiscarded(self):
    # A structural complexity check, not a timing assertion. The old proxy
    # retained one scope per keyword and rescanned all scopes for every token.
    proxy = TokenProxy(iter(range(4000)))
    for value in range(4000):
      with proxy.release():
        self.assertEqual(value, proxy.eat(0))
      self.assertEqual(value, next(proxy))
      self.assertFalse(proxy._buffer)
      self.assertFalse(proxy._lookahead)

  def testNegativeLookaheadIsRejected(self):
    proxy = TokenProxy(iter(range(2)))
    with proxy.release():
      with self.assertRaises(IndexError):
        proxy.eat(-1)


class NestedSoftKeywordTest(unittest.TestCase):

  def testSoftKeywordsInsideAmbiguousMatchExpressions(self):
    for name in ('match', 'case', 'type', 'lazy'):
      for subject in (name, name + '(value)', name + ', other',
                      'lambda ' + name + ': ' + name):
        for brackets in ('(%s)', '[%s]'):
          expression = brackets % subject
          for source in ('match' + expression + '\n',
                         'match ' + expression + ':\n case _: pass\n'):
            with self.subTest(source=source):
              output, _ = FormatCode(source, style_config='pep8')
              self.assertEqual((output, False),
                               FormatCode(output, style_config='pep8'))
              if sys.version_info >= (3, 10):
                self.assertEqual(
                    ast.dump(ast.parse(source)), ast.dump(ast.parse(output)))

  def testNestedAmbiguityAndComments(self):
    sources = [
        'match(match(type), lazy, case)\n',
        'match[match[case]]\n',
        'match (type # comment\n, lazy):\n case _: pass\n',
        'match (match(case),type(lazy)):\n case _: pass\n',
    ]
    for source in sources:
      with self.subTest(source=source):
        output, _ = FormatCode(source, style_config='pep8')
        self.assertEqual((output, False),
                         FormatCode(output, style_config='pep8'))
        if sys.version_info >= (3, 10):
          self.assertEqual(
              ast.dump(ast.parse(source)), ast.dump(ast.parse(output)))


if __name__ == '__main__':
  unittest.main()
