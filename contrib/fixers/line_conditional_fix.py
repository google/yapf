# Copyright 2020 Google Inc. All Rights Reserved.
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
"""Fixer base for skipping nodes not within a line range."""

import collections
import re

from lib2to3 import fixer_base
from lib2to3 import pytree


class LineConditionalFix(fixer_base.BaseFix):
  """Base class for fixers which only want to execute on certain lines."""

  def __init__(self, options, log):
    super(LineConditionalFix, self).__init__(options, log)
    # Note that for both _skip_nodes and _line_elems, we have to store the
    # pytree node's "id" in the set, because pytree nodes aren't hashable.
    self._skip_nodes = set()
    self._line_elems = collections.defaultdict(set)

  def start_tree(self, tree, filename):
    """Record the initial position of nodes and determine which to skip."""
    super(LineConditionalFix, self).start_tree(tree, filename)

    disabled_region = False
    for node in tree.pre_order():
      if _IsYapfEnableNode(node):
        disabled_region = False

      if disabled_region:
        self._skip_nodes.add(id(node))

      start_leaf, stop_leaf = _GetLeaf(node, 0), _GetLeaf(node, -1)
      if start_leaf is None or stop_leaf is None:
        self._skip_nodes.add(id(node))  # cannot determine line numbers, so skip
      elif _OutsideOfLineRanges(start_leaf.lineno, stop_leaf.lineno,
                                self.options.get('lines')):
        self._skip_nodes.add(id(node))

      if _IsYapfDisableNode(node):
        num_newlines = node.prefix.count('\n')
        # A tailing comment that disables yapf acts on the previous line.
        # lib2to3 helpfully adds that comment to the first node of the next
        # line. Therefore, when we see a trailing comment, we need to go back to
        # the previous line and add those elements to the "self._skip_nodes"
        # set.
        if (not node.prefix.startswith('\n') and
            self._line_elems[node.get_lineno() - num_newlines]):
          for elem in self._line_elems[node.get_lineno() - num_newlines]:
            self._skip_nodes.add(elem)
        else:
          disabled_region = True

      self._line_elems[node.get_lineno()].add(id(node))

  def should_skip(self, node):
    """Returns true if this node isn't in the specified line range."""
    return id(node) in self._skip_nodes


_DISABLE_PATTERN = r'^\s*#.+yapf:\s*disable\b'
_ENABLE_PATTERN = r'^\s*#.+yapf:\s*enable\b'


def _OutsideOfLineRanges(start_lineno, stop_lineno, lines):
  if not lines:
    return False

  for start, stop in reversed(lines):
    if start_lineno >= start and stop_lineno <= stop:
      return False

  return True


def _IsYapfDisableNode(node):
  return re.search(_DISABLE_PATTERN, node.prefix.strip(), re.I | re.M)


def _IsYapfEnableNode(node):
  return re.search(_ENABLE_PATTERN, node.prefix.strip(), re.I | re.M)


def _GetLeaf(node, index):
  """A helper method to get the left-most or right-most child of a node."""
  while not isinstance(node, pytree.Leaf):
    if not node.children:
      return None
    node = node.children[index]
  return node
