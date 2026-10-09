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
"""Layout-tree navigation, annotation, insertion, and debugging helpers."""

from yapf.layout import tokens as token
from yapf.layout import tree as layout_tree
from yapf.layout.roles import Kind

# TODO(eliben): We may want to get rid of this filtering at some point once we
# have a better understanding of what information we need from the tree. Then,
# these tokens may be filtered out from the tree before the tree gets to the
# unwrapper.
NONSEMANTIC_TOKENS = frozenset(['DEDENT', 'INDENT', 'NEWLINE', 'ENDMARKER'])


class Annotation(object):
  """Annotation names associated with layout trees."""
  CHILD_INDENT = 'child_indent'
  NEWLINES = 'newlines'
  MUST_SPLIT = 'must_split'
  SPLIT_PENALTY = 'split_penalty'
  SUBTYPE = 'subtype'


def NodeName(node):
  """Produce a string name for a given node.

  For a Leaf this is the token name, and for a Node this is the type.

  Arguments:
    node: a tree node

  Returns:
    Name as a string.
  """
  # Nodes with values < 256 are tokens. Values >= 256 are layout categories.
  if node.type < 256:
    return 'CONTINUATION' if node.type == token.N_TOKENS else token.tok_name[
        node.type]
  else:
    return Kind(node.type).name


def FirstLeafNode(node):
  if isinstance(node, layout_tree.Leaf):
    return node
  return FirstLeafNode(node.children[0])


def LastLeafNode(node):
  if isinstance(node, layout_tree.Leaf):
    return node
  return LastLeafNode(node.children[-1])


def ParseCodeToTree(code):
  """Parse with LibCST and lower to the mutable formatting representation."""
  from yapf.layout.frontend import ParseCode
  return ParseCode(code)


def InsertNodesBefore(new_nodes, target):
  """Insert new_nodes before the given target location in the tree.

  Arguments:
    new_nodes: a sequence of new nodes to insert (the nodes should not be in the
      tree).
    target: the target node before which the new node node will be inserted.

  Raises:
    RuntimeError: if the tree is corrupted, or the insertion would corrupt it.
  """
  for node in new_nodes:
    _InsertNodeAt(node, target, after=False)


def InsertNodesAfter(new_nodes, target):
  """Insert new_nodes after the given target location in the tree.

  Arguments:
    new_nodes: a sequence of new nodes to insert (the nodes should not be in the
      tree).
    target: the target node after which the new node node will be inserted.

  Raises:
    RuntimeError: if the tree is corrupted, or the insertion would corrupt it.
  """
  for node in reversed(new_nodes):
    _InsertNodeAt(node, target, after=True)


def _InsertNodeAt(new_node, target, after=False):
  """Underlying implementation for node insertion.

  Arguments:
    new_node: a new node to insert (this node should not be in the tree).
    target: the target node.
    after: if True, new_node is inserted after target. Otherwise, it's inserted
      before target.

  Returns:
    nothing

  Raises:
    RuntimeError: if the tree is corrupted, or the insertion would corrupt it.
  """

  # Protect against attempts to insert nodes which already belong to some tree.
  if new_node.parent is not None:
    raise RuntimeError('inserting node which already has a parent',
                       (new_node, new_node.parent))

  # The code here is based on tree.Base.next_sibling
  parent_of_target = target.parent
  if parent_of_target is None:
    raise RuntimeError('expected target node to have a parent', (target,))

  for i, child in enumerate(parent_of_target.children):
    if child is target:
      insertion_index = i + 1 if after else i
      parent_of_target.insert_child(insertion_index, new_node)
      return

  raise RuntimeError('unable to find insertion point for target node',
                     (target,))


# The following constant and functions implement a simple custom annotation
# mechanism for layout nodes. Each new attribute attached to a node
# is prefixed with _NODE_ANNOTATION_PREFIX. These annotations should only be
# managed through GetNodeAnnotation and SetNodeAnnotation.
_NODE_ANNOTATION_PREFIX = '_yapf_annotation_'


def CopyYapfAnnotations(src, dst):
  """Copy all YAPF annotations from the source node to the destination node.

  Arguments:
    src: the source node.
    dst: the destination node.
  """
  for annotation in dir(src):
    if annotation.startswith(_NODE_ANNOTATION_PREFIX):
      setattr(dst, annotation, getattr(src, annotation, None))


def GetNodeAnnotation(node, annotation, default=None):
  """Get annotation value from a node.

  Arguments:
    node: the node.
    annotation: annotation name - a string.
    default: the default value to return if there's no annotation.

  Returns:
    Value of the annotation in the given node. If the node doesn't have this
    particular annotation name yet, returns default.
  """
  return getattr(node, _NODE_ANNOTATION_PREFIX + annotation, default)


def SetNodeAnnotation(node, annotation, value):
  """Set annotation value on a node.

  Arguments:
    node: the node.
    annotation: annotation name - a string.
    value: annotation value to set.
  """
  setattr(node, _NODE_ANNOTATION_PREFIX + annotation, value)


def AppendNodeAnnotation(node, annotation, value):
  """Appends an annotation value to a list of annotations on the node.

  Arguments:
    node: the node.
    annotation: annotation name - a string.
    value: annotation value to set.
  """
  attr = GetNodeAnnotation(node, annotation, set())
  attr.add(value)
  SetNodeAnnotation(node, annotation, attr)


def RemoveSubtypeAnnotation(node, value):
  """Removes an annotation value from the subtype annotations on the node.

  Arguments:
    node: the node.
    value: annotation value to remove.
  """
  attr = GetNodeAnnotation(node, Annotation.SUBTYPE)
  if attr and value in attr:
    attr.remove(value)
    SetNodeAnnotation(node, Annotation.SUBTYPE, attr)


def GetOpeningBracket(node):
  """Get opening bracket value from a node.

  Arguments:
    node: the node.

  Returns:
    The opening bracket node or None if it couldn't find one.
  """
  return getattr(node, _NODE_ANNOTATION_PREFIX + 'container_bracket', None)


def SetOpeningBracket(node, bracket):
  """Set opening bracket value for a node.

  Arguments:
    node: the node.
    bracket: opening bracket to set.
  """
  setattr(node, _NODE_ANNOTATION_PREFIX + 'container_bracket', bracket)


def DumpNodeToString(node):
  """Dump a string representation of the given node. For debugging.

  Arguments:
    node: the node.

  Returns:
    The string representation.
  """
  if isinstance(node, layout_tree.Leaf):
    fmt = ('{name}({value}) [lineno={lineno}, column={column}, '
           'prefix={prefix}, penalty={penalty}]')
    return fmt.format(
        name=NodeName(node),
        value=_PytreeNodeRepr(node),
        lineno=node.lineno,
        column=node.column,
        prefix=repr(node.prefix),
        penalty=GetNodeAnnotation(node, Annotation.SPLIT_PENALTY, None))
  else:
    fmt = '{node} [{len} children] [child_indent="{indent}"]'
    return fmt.format(
        node=NodeName(node),
        len=len(node.children),
        indent=GetNodeAnnotation(node, Annotation.CHILD_INDENT))


def _PytreeNodeRepr(node):
  """Like layout_tree.Node.__repr__, but names instead of numbers for tokens."""
  if isinstance(node, layout_tree.Node):
    return '%s(%s, %r)' % (node.__class__.__name__, NodeName(node),
                           [_PytreeNodeRepr(c) for c in node.children])
  if isinstance(node, layout_tree.Leaf):
    return '%s(%s, %r)' % (node.__class__.__name__, NodeName(node), node.value)


def IsCommentStatement(node):
  return (NodeName(node) == 'simple_stmt' and
          node.children[0].type == token.COMMENT)
