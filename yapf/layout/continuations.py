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
"""Insert "continuation" nodes into layout groups.

The "backslash-newline" continuation marker is preserved in the node's prefix.
Pull them out and make it into nodes of their own.

  AttachContinuations(): the main function exported by this module.
"""

from yapf.layout import tree as layout_tree

from yapf.yapflib import format_token


def AttachContinuations(tree):
  """Given a layout tree, splice the continuation marker into nodes.

  Arguments:
    tree: (layout_tree.Node) The tree to work on. The tree is modified by this
      function.
  """

  def RecSplicer(node):
    """Inserts a continuation marker into the node."""
    if isinstance(node, layout_tree.Leaf):
      if node.prefix.lstrip().startswith('\\\n'):
        new_lineno = node.lineno - node.prefix.count('\n')
        return layout_tree.Leaf(
            type=format_token.CONTINUATION,
            value=node.prefix,
            context=('', (new_lineno, 0)))
      return None
    num_inserted = 0
    for index, child in enumerate(node.children[:]):
      continuation_node = RecSplicer(child)
      if continuation_node:
        node.children.insert(index + num_inserted, continuation_node)
        num_inserted += 1

  RecSplicer(tree)
