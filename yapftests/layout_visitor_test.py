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
"""Tests for yapf.layout.visitor."""

import unittest
from io import StringIO

from yapf.layout import utils
from yapf.layout import visitor

from yapftests import yapf_test_helper


class _NodeNameCollector(visitor.LayoutVisitor):
  """A tree visitor that collects the names of all tree nodes into a list.

  Attributes:
    all_node_names: collected list of the names, available when the traversal
      is over.
    name_node_values: collects a list of NAME leaves (in addition to those going
      into all_node_names).
  """

  def __init__(self):
    self.all_node_names = []
    self.name_node_values = []

  def DefaultNodeVisit(self, node):
    self.all_node_names.append(utils.NodeName(node))
    super(_NodeNameCollector, self).DefaultNodeVisit(node)

  def DefaultLeafVisit(self, leaf):
    self.all_node_names.append(utils.NodeName(leaf))

  def Visit_NAME(self, leaf):
    self.name_node_values.append(leaf.value)
    self.DefaultLeafVisit(leaf)


_VISITOR_TEST_SIMPLE_CODE = """\
foo = bar
baz = x
"""

_VISITOR_TEST_NESTED_CODE = """\
if x:
  if y:
    return z
"""


class LayoutVisitorTest(yapf_test_helper.YAPFTest):

  def testCollectAllNodeNamesSimpleCode(self):
    tree = utils.ParseCodeToTree(_VISITOR_TEST_SIMPLE_CODE)
    collector = _NodeNameCollector()
    collector.Visit(tree)
    expected_names = [
        'file_input',
        'simple_stmt', 'expr_stmt', 'NAME', 'EQUAL', 'NAME', 'NEWLINE',
        'simple_stmt', 'expr_stmt', 'NAME', 'EQUAL', 'NAME', 'NEWLINE',
        'ENDMARKER',
    ]  # yapf: disable
    self.assertEqual(expected_names, collector.all_node_names)

    expected_name_node_values = ['foo', 'bar', 'baz', 'x']
    self.assertEqual(expected_name_node_values, collector.name_node_values)

  def testCollectAllNodeNamesNestedCode(self):
    tree = utils.ParseCodeToTree(_VISITOR_TEST_NESTED_CODE)
    collector = _NodeNameCollector()
    collector.Visit(tree)
    expected_names = [
        'file_input',
        'if_stmt', 'NAME', 'NAME', 'COLON',
        'suite', 'NEWLINE',
        'INDENT', 'if_stmt', 'NAME', 'NAME', 'COLON', 'suite', 'NEWLINE',
        'INDENT', 'simple_stmt', 'return_stmt', 'NAME', 'NAME', 'NEWLINE',
        'DEDENT', 'DEDENT', 'ENDMARKER',
    ]  # yapf: disable
    self.assertEqual(expected_names, collector.all_node_names)

    expected_name_node_values = ['if', 'x', 'if', 'y', 'return', 'z']
    self.assertEqual(expected_name_node_values, collector.name_node_values)

  def testDumper(self):
    # LayoutDumper is mainly a debugging utility, so only do basic sanity
    # checking.
    tree = utils.ParseCodeToTree(_VISITOR_TEST_SIMPLE_CODE)
    stream = StringIO()
    visitor.LayoutDumper(target_stream=stream).Visit(tree)

    dump_output = stream.getvalue()
    self.assertIn('file_input [3 children]', dump_output)
    self.assertIn("NAME(Leaf(NAME, 'foo'))", dump_output)
    self.assertIn("EQUAL(Leaf(EQUAL, '='))", dump_output)

  def testDumpLayout(self):
    # Similar sanity checking for the convenience wrapper DumpLayout
    tree = utils.ParseCodeToTree(_VISITOR_TEST_SIMPLE_CODE)
    stream = StringIO()
    visitor.DumpLayout(tree, target_stream=stream)

    dump_output = stream.getvalue()
    self.assertIn('file_input [3 children]', dump_output)
    self.assertIn("NAME(Leaf(NAME, 'foo'))", dump_output)
    self.assertIn("EQUAL(Leaf(EQUAL, '='))", dump_output)


if __name__ == '__main__':
  unittest.main()
