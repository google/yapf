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
"""Tests for yapf.layout.utils."""

import unittest

from yapf.layout import tokens as token
from yapf.layout import tree as layout_tree
from yapf.layout import utils
from yapf.layout.roles import Kind

from yapftests import yapf_test_helper

# Semantic layout categories used by the formatting representation
# module.
_GRAMMAR_SYMBOL2NUMBER = {k.name: k.value for k in Kind}

_FOO = 'foo'
_FOO1 = 'foo1'
_FOO2 = 'foo2'
_FOO3 = 'foo3'
_FOO4 = 'foo4'
_FOO5 = 'foo5'


class NodeNameTest(yapf_test_helper.YAPFTest):

  def testNodeNameForLeaf(self):
    leaf = layout_tree.Leaf(token.LPAR, '(')
    self.assertEqual('LPAR', utils.NodeName(leaf))

  def testNodeNameForNode(self):
    leaf = layout_tree.Leaf(token.LPAR, '(')
    node = layout_tree.Node({k.name: k.value for k in Kind}['suite'], [leaf])
    self.assertEqual('suite', utils.NodeName(node))


class ParseCodeToTreeTest(yapf_test_helper.YAPFTest):

  def testParseCodeToTree(self):
    # Since ParseCodeToTree is a thin wrapper around the LibCST frontend and layout
    # functionality, only a sanity test here...
    tree = utils.ParseCodeToTree('foo = 2\n')
    self.assertEqual('file_input', utils.NodeName(tree))
    self.assertEqual(2, len(tree.children))
    self.assertEqual('simple_stmt', utils.NodeName(tree.children[0]))

  def testPrintFunctionToTree(self):
    tree = utils.ParseCodeToTree('print("hello world", file=sys.stderr)\n')
    self.assertEqual('file_input', utils.NodeName(tree))
    self.assertEqual(2, len(tree.children))
    self.assertEqual('simple_stmt', utils.NodeName(tree.children[0]))

  def testPrintStatementToTree(self):
    with self.assertRaises(SyntaxError):
      utils.ParseCodeToTree('print "hello world"\n')

  def testClassNotLocal(self):
    with self.assertRaises(SyntaxError):
      utils.ParseCodeToTree('class nonlocal: pass\n')


class InsertNodesBeforeAfterTest(yapf_test_helper.YAPFTest):

  def _BuildSimpleTree(self):
    # Builds a simple tree we can play with in the tests.
    # The tree looks like this:
    #
    #   suite:
    #     LPAR
    #     LPAR
    #     simple_stmt:
    #       NAME('foo')
    #
    lpar1 = layout_tree.Leaf(token.LPAR, '(')
    lpar2 = layout_tree.Leaf(token.LPAR, '(')
    simple_stmt = layout_tree.Node(_GRAMMAR_SYMBOL2NUMBER['simple_stmt'],
                                   [layout_tree.Leaf(token.NAME, 'foo')])
    return layout_tree.Node(_GRAMMAR_SYMBOL2NUMBER['suite'],
                            [lpar1, lpar2, simple_stmt])

  def _MakeNewNodeRPAR(self):
    return layout_tree.Leaf(token.RPAR, ')')

  def setUp(self):
    self._simple_tree = self._BuildSimpleTree()

  def testInsertNodesBefore(self):
    # Insert before simple_stmt and make sure it went to the right place
    utils.InsertNodesBefore([self._MakeNewNodeRPAR()],
                            self._simple_tree.children[2])
    self.assertEqual(4, len(self._simple_tree.children))
    self.assertEqual('RPAR', utils.NodeName(self._simple_tree.children[2]))
    self.assertEqual('simple_stmt',
                     utils.NodeName(self._simple_tree.children[3]))

  def testInsertNodesBeforeFirstChild(self):
    # Insert before the first child of its parent
    simple_stmt = self._simple_tree.children[2]
    foo_child = simple_stmt.children[0]
    utils.InsertNodesBefore([self._MakeNewNodeRPAR()], foo_child)
    self.assertEqual(3, len(self._simple_tree.children))
    self.assertEqual(2, len(simple_stmt.children))
    self.assertEqual('RPAR', utils.NodeName(simple_stmt.children[0]))
    self.assertEqual('NAME', utils.NodeName(simple_stmt.children[1]))

  def testInsertNodesAfter(self):
    # Insert after and make sure it went to the right place
    utils.InsertNodesAfter([self._MakeNewNodeRPAR()],
                           self._simple_tree.children[2])
    self.assertEqual(4, len(self._simple_tree.children))
    self.assertEqual('simple_stmt',
                     utils.NodeName(self._simple_tree.children[2]))
    self.assertEqual('RPAR', utils.NodeName(self._simple_tree.children[3]))

  def testInsertNodesAfterLastChild(self):
    # Insert after the last child of its parent
    simple_stmt = self._simple_tree.children[2]
    foo_child = simple_stmt.children[0]
    utils.InsertNodesAfter([self._MakeNewNodeRPAR()], foo_child)
    self.assertEqual(3, len(self._simple_tree.children))
    self.assertEqual(2, len(simple_stmt.children))
    self.assertEqual('NAME', utils.NodeName(simple_stmt.children[0]))
    self.assertEqual('RPAR', utils.NodeName(simple_stmt.children[1]))

  def testInsertNodesWhichHasParent(self):
    # Try to insert an existing tree node into another place and fail.
    with self.assertRaises(RuntimeError):
      utils.InsertNodesAfter([self._simple_tree.children[1]],
                             self._simple_tree.children[0])


class AnnotationsTest(yapf_test_helper.YAPFTest):

  def setUp(self):
    self._leaf = layout_tree.Leaf(token.LPAR, '(')
    self._node = layout_tree.Node(_GRAMMAR_SYMBOL2NUMBER['simple_stmt'],
                                  [layout_tree.Leaf(token.NAME, 'foo')])

  def testGetWhenNone(self):
    self.assertIsNone(utils.GetNodeAnnotation(self._leaf, _FOO))

  def testSetWhenNone(self):
    utils.SetNodeAnnotation(self._leaf, _FOO, 20)
    self.assertEqual(utils.GetNodeAnnotation(self._leaf, _FOO), 20)

  def testSetAgain(self):
    utils.SetNodeAnnotation(self._leaf, _FOO, 20)
    self.assertEqual(utils.GetNodeAnnotation(self._leaf, _FOO), 20)
    utils.SetNodeAnnotation(self._leaf, _FOO, 30)
    self.assertEqual(utils.GetNodeAnnotation(self._leaf, _FOO), 30)

  def testMultiple(self):
    utils.SetNodeAnnotation(self._leaf, _FOO, 20)
    utils.SetNodeAnnotation(self._leaf, _FOO1, 1)
    utils.SetNodeAnnotation(self._leaf, _FOO2, 2)
    utils.SetNodeAnnotation(self._leaf, _FOO3, 3)
    utils.SetNodeAnnotation(self._leaf, _FOO4, 4)
    utils.SetNodeAnnotation(self._leaf, _FOO5, 5)

    self.assertEqual(utils.GetNodeAnnotation(self._leaf, _FOO), 20)
    self.assertEqual(utils.GetNodeAnnotation(self._leaf, _FOO1), 1)
    self.assertEqual(utils.GetNodeAnnotation(self._leaf, _FOO2), 2)
    self.assertEqual(utils.GetNodeAnnotation(self._leaf, _FOO3), 3)
    self.assertEqual(utils.GetNodeAnnotation(self._leaf, _FOO4), 4)
    self.assertEqual(utils.GetNodeAnnotation(self._leaf, _FOO5), 5)

  def testSubtype(self):
    utils.AppendNodeAnnotation(self._leaf, utils.Annotation.SUBTYPE, _FOO)

    self.assertSetEqual(
        utils.GetNodeAnnotation(self._leaf, utils.Annotation.SUBTYPE), {_FOO})

    utils.RemoveSubtypeAnnotation(self._leaf, _FOO)

    self.assertSetEqual(
        utils.GetNodeAnnotation(self._leaf, utils.Annotation.SUBTYPE), set())

  def testSetOnNode(self):
    utils.SetNodeAnnotation(self._node, _FOO, 20)
    self.assertEqual(utils.GetNodeAnnotation(self._node, _FOO), 20)


if __name__ == '__main__':
  unittest.main()
