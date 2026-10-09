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
"""Visitors and diagnostic dumping for mutable layout groups and leaves.

Method names correspond to semantic layout roles, not LibCST node classes.
The source CST is never mutated by these visitors.
"""

import sys

from yapf.layout import tree as layout_tree
from yapf.layout import utils


class LayoutVisitor(object):
  """Visitor pattern for layout groups and tokens.

  Methods named Visit_XXX will be invoked when a node with type XXX is
  encountered in the tree. The type is either a token type (for Leaf nodes) or
  layout categories (for Node nodes). The return value of Visit_XXX methods is
  ignored by the visitor.

  Visitors can modify node contents but must not change the tree structure
  (e.g. add/remove children and move nodes around).

  This is a very common visitor pattern in Python code; it's also used in the
  Python standard library ast module for providing AST visitors.

  For more complex behavior, the visit, DefaultNodeVisit and DefaultLeafVisit
  methods can be overridden. Don't forget to invoke DefaultNodeVisit for nodes
  that may have children - otherwise the children will not be visited.
  """

  def Visit(self, node):
    """Visit a node."""
    method = 'Visit_{0}'.format(utils.NodeName(node))
    if hasattr(self, method):
      # Found a specific visitor for this node
      getattr(self, method)(node)
    else:
      if isinstance(node, layout_tree.Leaf):
        self.DefaultLeafVisit(node)
      else:
        self.DefaultNodeVisit(node)

  def DefaultNodeVisit(self, node):
    """Default visitor for Node: visits the node's children depth-first.

    This method is invoked when no specific visitor for the node is defined.

    Arguments:
      node: the node to visit
    """
    for child in node.children:
      self.Visit(child)

  def DefaultLeafVisit(self, leaf):
    """Default visitor for Leaf: no-op.

    This method is invoked when no specific visitor for the leaf is defined.

    Arguments:
      leaf: the leaf to visit
    """
    pass


def DumpLayout(tree, target_stream=sys.stdout):
  """Convenience function for dumping a given tree.

  This function presents a very minimal interface. For more configurability (for
  example, controlling how specific node types are displayed), use LayoutDumper
  directly.

  Arguments:
    tree: the tree to dump.
    target_stream: the stream to dump the tree to. A file-like object. By
      default will dump into stdout.
  """
  dumper = LayoutDumper(target_stream)
  dumper.Visit(tree)


class LayoutDumper(LayoutVisitor):
  """Visitor that dumps the tree to a stream.

  Implements the LayoutVisitor interface.
  """

  def __init__(self, target_stream=sys.stdout):
    """Create a tree dumper.

    Arguments:
      target_stream: the stream to dump the tree to. A file-like object. By
        default will dump into stdout.
    """
    self._target_stream = target_stream
    self._current_indent = 0

  def _DumpString(self, s):
    self._target_stream.write('{0}{1}\n'.format(' ' * self._current_indent, s))

  def DefaultNodeVisit(self, node):
    # Dump information about the current node, and then use the generic
    # DefaultNodeVisit visitor to dump each of its children.
    self._DumpString(utils.DumpNodeToString(node))
    self._current_indent += 2
    super(LayoutDumper, self).DefaultNodeVisit(node)
    self._current_indent -= 2

  def DefaultLeafVisit(self, leaf):
    self._DumpString(utils.DumpNodeToString(leaf))
