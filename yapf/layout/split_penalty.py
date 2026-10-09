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
"""Computation of split penalties before/between tokens."""

import re

from yapf.layout import tokens as layout_token
from yapf.layout import tree as layout_tree
from yapf.layout import utils
from yapf.layout import visitor
from yapf.yapflib import style
from yapf.yapflib import subtypes

# TODO(morbo): Document the annotations in a centralized place. E.g., the
# README file.
UNBREAKABLE = 1000 * 1000
NAMED_ASSIGN = 15000
DOTTED_NAME = 4000
VERY_STRONGLY_CONNECTED = 3500
STRONGLY_CONNECTED = 3000
CONNECTED = 500
TOGETHER = 100

OR_TEST = 1000
AND_TEST = 1100
NOT_TEST = 1200
COMPARISON = 1300
STAR_EXPR = 1300
EXPR = 1400
XOR_EXPR = 1500
AND_EXPR = 1700
SHIFT_EXPR = 1800
ARITH_EXPR = 1900
TERM = 2000
FACTOR = 2100
POWER = 2200
ATOM = 2300
ONE_ELEMENT_ARGUMENT = 500
SUBSCRIPT = 6000


def ComputeSplitPenalties(tree):
  """Compute split penalties on tokens in the given parse tree.

  Arguments:
    tree: the top-level layout tree node to annotate with penalties.
  """
  _SplitPenaltyAssigner().Visit(tree)


class _SplitPenaltyAssigner(visitor.LayoutVisitor):
  """Assigns split penalties to tokens, based on parse tree structure.

  Split penalties are attached as annotations to tokens.
  """

  def Visit(self, node):
    if not hasattr(node, 'is_pseudo'):  # Ignore pseudo tokens.
      super(_SplitPenaltyAssigner, self).Visit(node)

  def Visit_import_as_names(self, node):  # pyline: disable=invalid-name
    self.DefaultNodeVisit(node)
    prev_child = None
    for child in node.children:
      if (prev_child and isinstance(prev_child, layout_tree.Leaf) and
          prev_child.value == ','):
        _SetSplitPenalty(child, style.Get('SPLIT_PENALTY_IMPORT_NAMES'))
      prev_child = child

  def Visit_classdef(self, node):  # pylint: disable=invalid-name
    #
    # NAME
    _SetUnbreakable(node.children[1])
    if len(node.children) > 4:
      # opening '('
      _SetUnbreakable(node.children[2])
    # ':'
    _SetUnbreakable(node.children[-2])
    self.DefaultNodeVisit(node)

  def Visit_funcdef(self, node):  # pylint: disable=invalid-name
    #
    # Can't break before the function name and before the colon. The parameters
    # are handled by child iteration.
    colon_idx = 1
    while utils.NodeName(node.children[colon_idx]) == 'simple_stmt':
      colon_idx += 1
    _SetUnbreakable(node.children[colon_idx])
    arrow_idx = -1
    while colon_idx < len(node.children):
      if isinstance(node.children[colon_idx], layout_tree.Leaf):
        if node.children[colon_idx].value == ':':
          break
        if node.children[colon_idx].value == '->':
          arrow_idx = colon_idx
      colon_idx += 1
    _SetUnbreakable(node.children[colon_idx])
    self.DefaultNodeVisit(node)
    if arrow_idx > 0:
      _SetSplitPenalty(utils.LastLeafNode(node.children[arrow_idx - 1]), 0)
      _SetUnbreakable(node.children[arrow_idx])
      _SetStronglyConnected(node.children[arrow_idx + 1])

  def Visit_lambdef(self, node):  # pylint: disable=invalid-name
    # Loop over the lambda up to and including the colon.
    allow_multiline_lambdas = style.Get('ALLOW_MULTILINE_LAMBDAS')
    if not allow_multiline_lambdas:
      for child in node.children:
        if child.type == layout_token.COMMENT:
          if re.search(r'pylint:.*disable=.*\bg-long-lambda', child.value):
            allow_multiline_lambdas = True
            break

    if allow_multiline_lambdas:
      _SetExpressionPenalty(node, STRONGLY_CONNECTED)
    else:
      _SetExpressionPenalty(node, VERY_STRONGLY_CONNECTED)

  def Visit_parameters(self, node):  # pylint: disable=invalid-name
    self.DefaultNodeVisit(node)

    # Can't break before the opening paren of a parameter list.
    _SetUnbreakable(node.children[0])
    if not (style.Get('INDENT_CLOSING_BRACKETS') or
            style.Get('DEDENT_CLOSING_BRACKETS')):
      _SetStronglyConnected(node.children[-1])

  def Visit_arglist(self, node):  # pylint: disable=invalid-name
    if node.children[0].type == layout_token.STAR:
      # Python 3 treats a star expression as a specific expression type.
      # Process it in that method.
      self.Visit_star_expr(node)
      return

    self.DefaultNodeVisit(node)

    for index in range(1, len(node.children)):
      child = node.children[index]
      if isinstance(child, layout_tree.Leaf) and child.value == ',':
        _SetUnbreakable(child)

    for child in node.children:
      if utils.NodeName(child) == 'atom':
        _IncreasePenalty(child, CONNECTED)

  def Visit_argument(self, node):  # pylint: disable=invalid-name
    self.DefaultNodeVisit(node)

    for index in range(1, len(node.children) - 1):
      child = node.children[index]
      if isinstance(child, layout_tree.Leaf) and child.value == '=':
        _SetSplitPenalty(
            utils.FirstLeafNode(node.children[index]), NAMED_ASSIGN)
        _SetSplitPenalty(
            utils.FirstLeafNode(node.children[index + 1]), NAMED_ASSIGN)

  def Visit_tname(self, node):  # pylint: disable=invalid-name
    self.DefaultNodeVisit(node)

    for index in range(1, len(node.children) - 1):
      child = node.children[index]
      if isinstance(child, layout_tree.Leaf) and child.value == ':':
        _SetSplitPenalty(
            utils.FirstLeafNode(node.children[index]), NAMED_ASSIGN)
        _SetSplitPenalty(
            utils.FirstLeafNode(node.children[index + 1]), NAMED_ASSIGN)

  def Visit_dotted_name(self, node):  # pylint: disable=invalid-name
    for child in node.children:
      self.Visit(child)
    start = 2 if hasattr(node.children[0], 'is_pseudo') else 1
    for i in range(start, len(node.children)):
      _SetUnbreakable(node.children[i])

  def Visit_dictsetmaker(self, node):  # pylint: disable=invalid-name
    for child in node.children:
      self.Visit(child)
      if child.type == layout_token.COLON:
        # This is a key to a dictionary. We don't want to split the key if at
        # all possible.
        _SetStronglyConnected(child)

  def Visit_trailer(self, node):  # pylint: disable=invalid-name
    if node.children[0].value == '.':
      before = style.Get('SPLIT_BEFORE_DOT')
      _SetSplitPenalty(node.children[0],
                       VERY_STRONGLY_CONNECTED if before else DOTTED_NAME)
      _SetSplitPenalty(node.children[1],
                       DOTTED_NAME if before else VERY_STRONGLY_CONNECTED)
    elif len(node.children) == 2:
      # Don't split an empty argument list if at all possible.
      _SetSplitPenalty(node.children[1], VERY_STRONGLY_CONNECTED)
    elif len(node.children) == 3:
      name = utils.NodeName(node.children[1])
      if name in {'argument', 'comparison'}:
        # Don't split an argument list with one element if at all possible.
        _SetStronglyConnected(node.children[1])
        if (len(node.children[1].children) > 1 and
            utils.NodeName(node.children[1].children[1]) == 'comp_for'):
          # Don't penalize splitting before a comp_for expression.
          _SetSplitPenalty(utils.FirstLeafNode(node.children[1]), 0)
        else:
          _SetSplitPenalty(
              utils.FirstLeafNode(node.children[1]), ONE_ELEMENT_ARGUMENT)
      elif (node.children[0].type == layout_token.LSQB and
            len(node.children[1].children) > 2 and
            (name.endswith('_test') or name.endswith('_expr'))):
        _SetStronglyConnected(node.children[1].children[0])
        _SetStronglyConnected(node.children[1].children[2])

        # Still allow splitting around the operator.
        split_before = ((name.endswith('_test') and
                         style.Get('SPLIT_BEFORE_LOGICAL_OPERATOR')) or
                        (name.endswith('_expr') and
                         style.Get('SPLIT_BEFORE_BITWISE_OPERATOR')))
        if split_before:
          _SetSplitPenalty(utils.LastLeafNode(node.children[1].children[1]), 0)
        else:
          _SetSplitPenalty(utils.FirstLeafNode(node.children[1].children[2]), 0)

        # Don't split the ending bracket of a subscript list.
        _RecAnnotate(node.children[-1], utils.Annotation.SPLIT_PENALTY,
                     VERY_STRONGLY_CONNECTED)
      elif name not in {
          'arglist', 'argument', 'term', 'or_test', 'and_test', 'comparison',
          'atom', 'power'
      }:
        # Don't split an argument list with one element if at all possible.
        stypes = utils.GetNodeAnnotation(
            utils.FirstLeafNode(node), utils.Annotation.SUBTYPE)
        if stypes and subtypes.SUBSCRIPT_BRACKET in stypes:
          _IncreasePenalty(node, SUBSCRIPT)

          # Bump up the split penalty for the first part of a subscript. We
          # would rather not split there.
          _IncreasePenalty(node.children[1], CONNECTED)
        else:
          _SetStronglyConnected(node.children[1], node.children[2])

      if name == 'arglist':
        _SetStronglyConnected(node.children[-1])

    self.DefaultNodeVisit(node)

  def Visit_power(self, node):  # pylint: disable=invalid-name,missing-docstring
    self.DefaultNodeVisit(node)

    # When atom is followed by a trailer, we can not break between them.
    # E.g. arr[idx] - no break allowed between 'arr' and '['.
    if (len(node.children) > 1 and
        utils.NodeName(node.children[1]) == 'trailer'):
      # children[1] itself is a whole trailer: we don't want to
      # mark all of it as unbreakable, only its first token: (, [ or .
      first = utils.FirstLeafNode(node.children[1])
      if first.value != '.':
        _SetUnbreakable(node.children[1].children[0])

      # A special case when there are more trailers in the sequence. Given:
      #   atom tr1 tr2
      # The last token of tr1 and the first token of tr2 comprise an unbreakable
      # region. For example: foo.bar.baz(1)
      # We can't put breaks between either of the '.', '(', or '[' and the names
      # *preceding* them.
      prev_trailer_idx = 1
      while prev_trailer_idx < len(node.children) - 1:
        cur_trailer_idx = prev_trailer_idx + 1
        cur_trailer = node.children[cur_trailer_idx]
        if utils.NodeName(cur_trailer) != 'trailer':
          break

        # Now we know we have two trailers one after the other
        prev_trailer = node.children[prev_trailer_idx]
        if prev_trailer.children[-1].value != ')':
          # Set the previous node unbreakable if it's not a function call:
          #   atom tr1() tr2
          # It may be necessary (though undesirable) to split up a previous
          # function call's parentheses to the next line.
          _SetStronglyConnected(prev_trailer.children[-1])
        _SetStronglyConnected(cur_trailer.children[0])
        prev_trailer_idx = cur_trailer_idx

    # We don't want to split before the last ')' of a function call. This also
    # takes care of the special case of:
    #   atom tr1 tr2 ... trn
    # where the 'tr#' are trailers that may end in a ')'.
    for trailer in node.children[1:]:
      if utils.NodeName(trailer) != 'trailer':
        break
      if trailer.children[0].value in '([':
        if len(trailer.children) > 2:
          stypes = utils.GetNodeAnnotation(trailer.children[0],
                                           utils.Annotation.SUBTYPE)
          if stypes and subtypes.SUBSCRIPT_BRACKET in stypes:
            _SetStronglyConnected(utils.FirstLeafNode(trailer.children[1]))

          last_child_node = utils.LastLeafNode(trailer)
          if last_child_node.value.strip().startswith('#'):
            last_child_node = last_child_node.prev_sibling
          if not (style.Get('INDENT_CLOSING_BRACKETS') or
                  style.Get('DEDENT_CLOSING_BRACKETS')):
            last = utils.LastLeafNode(last_child_node.prev_sibling)
            if last.value != ',':
              if last_child_node.value == ']':
                _SetUnbreakable(last_child_node)
              else:
                _SetSplitPenalty(last_child_node, VERY_STRONGLY_CONNECTED)
        else:
          # If the trailer's children are '()', then make it a strongly
          # connected region.  It's sometimes necessary, though undesirable, to
          # split the two.
          _SetStronglyConnected(trailer.children[-1])

  def Visit_subscriptlist(self, node):  # pylint: disable=invalid-name
    self.DefaultNodeVisit(node)
    _SetSplitPenalty(utils.FirstLeafNode(node), 0)
    prev_child = None
    for child in node.children:
      if prev_child and prev_child.type == layout_token.COMMA:
        _SetSplitPenalty(utils.FirstLeafNode(child), 0)
      prev_child = child

  def Visit_subscript(self, node):  # pylint: disable=invalid-name
    _SetStronglyConnected(*node.children)
    self.DefaultNodeVisit(node)

  def Visit_comp_for(self, node):  # pylint: disable=invalid-name
    _SetSplitPenalty(utils.FirstLeafNode(node), 0)
    _SetStronglyConnected(*node.children[1:])
    self.DefaultNodeVisit(node)

  def Visit_comp_if(self, node):  # pylint: disable=invalid-name
    _SetSplitPenalty(node.children[0],
                     style.Get('SPLIT_PENALTY_BEFORE_IF_EXPR'))
    _SetStronglyConnected(*node.children[1:])
    self.DefaultNodeVisit(node)

  def Visit_test(self, node):  # pylint: disable=invalid-name
    _IncreasePenalty(node, OR_TEST)
    self.DefaultNodeVisit(node)

  def Visit_or_test(self, node):  # pylint: disable=invalid-name
    self.DefaultNodeVisit(node)
    _IncreasePenalty(node, OR_TEST)
    index = 1
    while index + 1 < len(node.children):
      if style.Get('SPLIT_BEFORE_LOGICAL_OPERATOR'):
        _DecrementSplitPenalty(
            utils.FirstLeafNode(node.children[index]), OR_TEST)
      else:
        _DecrementSplitPenalty(
            utils.FirstLeafNode(node.children[index + 1]), OR_TEST)
      index += 2

  def Visit_and_test(self, node):  # pylint: disable=invalid-name
    self.DefaultNodeVisit(node)
    _IncreasePenalty(node, AND_TEST)
    index = 1
    while index + 1 < len(node.children):
      if style.Get('SPLIT_BEFORE_LOGICAL_OPERATOR'):
        _DecrementSplitPenalty(
            utils.FirstLeafNode(node.children[index]), AND_TEST)
      else:
        _DecrementSplitPenalty(
            utils.FirstLeafNode(node.children[index + 1]), AND_TEST)
      index += 2

  def Visit_not_test(self, node):  # pylint: disable=invalid-name
    self.DefaultNodeVisit(node)
    _IncreasePenalty(node, NOT_TEST)

  def Visit_comparison(self, node):  # pylint: disable=invalid-name
    self.DefaultNodeVisit(node)
    if len(node.children) == 3 and _StronglyConnectedCompOp(node):
      _IncreasePenalty(node.children[1], VERY_STRONGLY_CONNECTED)
      _SetSplitPenalty(
          utils.FirstLeafNode(node.children[2]), STRONGLY_CONNECTED)
    else:
      _IncreasePenalty(node, COMPARISON)

  def Visit_star_expr(self, node):  # pylint: disable=invalid-name
    self.DefaultNodeVisit(node)
    _IncreasePenalty(node, STAR_EXPR)

  def Visit_expr(self, node):  # pylint: disable=invalid-name
    self.DefaultNodeVisit(node)
    _IncreasePenalty(node, EXPR)
    _SetBitwiseOperandPenalty(node, '|')

  def Visit_xor_expr(self, node):  # pylint: disable=invalid-name
    self.DefaultNodeVisit(node)
    _IncreasePenalty(node, XOR_EXPR)
    _SetBitwiseOperandPenalty(node, '^')

  def Visit_and_expr(self, node):  # pylint: disable=invalid-name
    self.DefaultNodeVisit(node)
    _IncreasePenalty(node, AND_EXPR)
    _SetBitwiseOperandPenalty(node, '&')

  def Visit_shift_expr(self, node):  # pylint: disable=invalid-name
    self.DefaultNodeVisit(node)
    _IncreasePenalty(node, SHIFT_EXPR)

  _ARITH_OPS = frozenset({'PLUS', 'MINUS'})

  def Visit_arith_expr(self, node):  # pylint: disable=invalid-name
    self.DefaultNodeVisit(node)
    _IncreasePenalty(node, ARITH_EXPR)
    _SetExpressionOperandPenalty(node, self._ARITH_OPS)

  _TERM_OPS = frozenset({'STAR', 'AT', 'SLASH', 'PERCENT', 'DOUBLESLASH'})

  def Visit_term(self, node):  # pylint: disable=invalid-name
    self.DefaultNodeVisit(node)
    _IncreasePenalty(node, TERM)
    _SetExpressionOperandPenalty(node, self._TERM_OPS)

  def Visit_factor(self, node):  # pyline: disable=invalid-name
    self.DefaultNodeVisit(node)
    _IncreasePenalty(node, FACTOR)

  def Visit_atom(self, node):  # pylint: disable=invalid-name
    self.DefaultNodeVisit(node)
    if (node.children[0].value == '(' and
        not hasattr(node.children[0], 'is_pseudo')):
      if node.children[-1].value == ')':
        if utils.NodeName(node.parent) == 'if_stmt':
          _SetSplitPenalty(node.children[-1], STRONGLY_CONNECTED)
        else:
          if len(node.children) > 2:
            _SetSplitPenalty(utils.FirstLeafNode(node.children[1]), EXPR)
          _SetSplitPenalty(node.children[-1], ATOM)
    elif node.children[0].value in '[{' and len(node.children) == 2:
      # Keep empty containers together if we can.
      _SetUnbreakable(node.children[-1])

  def Visit_testlist_gexp(self, node):  # pylint: disable=invalid-name
    self.DefaultNodeVisit(node)
    prev_was_comma = False
    for child in node.children:
      if isinstance(child, layout_tree.Leaf) and child.value == ',':
        _SetUnbreakable(child)
        prev_was_comma = True
      else:
        if prev_was_comma:
          _SetSplitPenalty(utils.FirstLeafNode(child), TOGETHER)
        prev_was_comma = False


def _SetUnbreakable(node):
  """Set an UNBREAKABLE penalty annotation for the given node."""
  _RecAnnotate(node, utils.Annotation.SPLIT_PENALTY, UNBREAKABLE)


def _SetStronglyConnected(*nodes):
  """Set a STRONGLY_CONNECTED penalty annotation for the given nodes."""
  for node in nodes:
    _RecAnnotate(node, utils.Annotation.SPLIT_PENALTY, STRONGLY_CONNECTED)


def _SetExpressionPenalty(node, penalty):
  """Set a penalty annotation on children nodes."""

  def RecExpression(node, first_child_leaf):
    if node is first_child_leaf:
      return

    if isinstance(node, layout_tree.Leaf):
      if node.value in {'(', 'for', 'if'}:
        return
      penalty_annotation = utils.GetNodeAnnotation(
          node, utils.Annotation.SPLIT_PENALTY, default=0)
      if penalty_annotation < penalty:
        _SetSplitPenalty(node, penalty)
    else:
      for child in node.children:
        RecExpression(child, first_child_leaf)

  RecExpression(node, utils.FirstLeafNode(node))


def _SetBitwiseOperandPenalty(node, op):
  for index in range(1, len(node.children) - 1):
    child = node.children[index]
    if isinstance(child, layout_tree.Leaf) and child.value == op:
      if style.Get('SPLIT_BEFORE_BITWISE_OPERATOR'):
        _SetSplitPenalty(child, style.Get('SPLIT_PENALTY_BITWISE_OPERATOR'))
      else:
        _SetSplitPenalty(
            utils.FirstLeafNode(node.children[index + 1]),
            style.Get('SPLIT_PENALTY_BITWISE_OPERATOR'))


def _SetExpressionOperandPenalty(node, ops):
  for index in range(1, len(node.children) - 1):
    child = node.children[index]
    if utils.NodeName(child) in ops:
      if style.Get('SPLIT_BEFORE_ARITHMETIC_OPERATOR'):
        _SetSplitPenalty(child, style.Get('SPLIT_PENALTY_ARITHMETIC_OPERATOR'))
      else:
        _SetSplitPenalty(
            utils.FirstLeafNode(node.children[index + 1]),
            style.Get('SPLIT_PENALTY_ARITHMETIC_OPERATOR'))


def _IncreasePenalty(node, amt):
  """Increase a penalty annotation on children nodes."""

  def RecExpression(node, first_child_leaf):
    if node is first_child_leaf:
      return

    if isinstance(node, layout_tree.Leaf):
      if node.value in {'(', 'for'}:
        return
      penalty = utils.GetNodeAnnotation(
          node, utils.Annotation.SPLIT_PENALTY, default=0)
      _SetSplitPenalty(node, penalty + amt)
    else:
      for child in node.children:
        RecExpression(child, first_child_leaf)

  RecExpression(node, utils.FirstLeafNode(node))


def _RecAnnotate(tree, annotate_name, annotate_value):
  """Recursively set the given annotation on all leafs of the subtree.

  Takes care to only increase the penalty. If the node already has a higher
  or equal penalty associated with it, this is a no-op.

  Args:
    tree: subtree to annotate
    annotate_name: name of the annotation to set
    annotate_value: value of the annotation to set
  """
  for child in tree.children:
    _RecAnnotate(child, annotate_name, annotate_value)
  if isinstance(tree, layout_tree.Leaf):
    cur_annotate = utils.GetNodeAnnotation(tree, annotate_name, default=0)
    if cur_annotate < annotate_value:
      utils.SetNodeAnnotation(tree, annotate_name, annotate_value)


_COMP_OPS = frozenset({'==', '!=', '<=', '<', '>', '>=', '<>', 'in', 'is'})


def _StronglyConnectedCompOp(op):
  if (len(op.children[1].children) == 2 and
      utils.NodeName(op.children[1]) == 'comp_op'):
    if (utils.FirstLeafNode(op.children[1]).value == 'not' and
        utils.LastLeafNode(op.children[1]).value == 'in'):
      return True
    if (utils.FirstLeafNode(op.children[1]).value == 'is' and
        utils.LastLeafNode(op.children[1]).value == 'not'):
      return True
  if (isinstance(op.children[1], layout_tree.Leaf) and
      op.children[1].value in _COMP_OPS):
    return True
  return False


def _DecrementSplitPenalty(node, amt):
  penalty = utils.GetNodeAnnotation(
      node, utils.Annotation.SPLIT_PENALTY, default=amt)
  penalty = penalty - amt if amt < penalty else 0
  _SetSplitPenalty(node, penalty)


def _SetSplitPenalty(node, penalty):
  utils.SetNodeAnnotation(node, utils.Annotation.SPLIT_PENALTY, penalty)
