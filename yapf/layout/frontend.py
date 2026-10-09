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
"""LibCST front end for YAPF's token-oriented layout engine.

LibCST alone recognizes Python syntax. Its code generator supplies punctuation
and exact source spelling; the lowering below attaches formatting contexts to
those emissions. It does not tokenize source or maintain a Python grammar.

The code-generation hook is the one intentionally private LibCST dependency.
Keep it isolated here and test lossless reconstruction when updating LibCST.
"""

from contextlib import contextmanager

import libcst as cst
from libcst._nodes.internal import CodegenState

from yapf.layout import tokens as token
from yapf.layout.roles import Kind
from yapf.layout.tree import Leaf
from yapf.layout.tree import Node


class UnsupportedSyntaxError(SyntaxError):
  """A valid LibCST construct without a YAPF layout rule."""


_OPERATORS = tuple(sorted(token.EXACT_TOKEN_TYPES, key=len, reverse=True))
_NAME_TYPES = {'async': token.ASYNC, 'await': token.AWAIT}


class _Emissions(CodegenState):
  """Observe LibCST serialization without lexing its original input."""

  def __init__(self, module):
    super().__init__(module.default_indent, module.default_newline)
    self.leaves = []
    self.spans = {}
    self.stack = []
    self.starts = {}
    self.line = 1
    self.column = 0
    self.pending = ''
    self.opaque = 0
    self.pending_indent = None
    self.shared_nodes = False

  def before_codegen(self, node):
    if id(node) in self.starts:
      self.shared_nodes = True
    self.stack.append(node)
    self.starts[id(node)] = len(self.leaves)

  def after_codegen(self, node):
    self.spans[id(node)] = (self.starts[id(node)], len(self.leaves))
    self.stack.pop()

  def _position(self, text):
    if '\n' in text:
      self.line += text.count('\n')
      self.column = len(text.rsplit('\n', 1)[-1])
    else:
      self.column += len(text)

  def _leaf(self, kind, text, position=None):
    if kind not in (token.INDENT, token.DEDENT, token.NEWLINE):
      if self.pending_indent is not None:
        indent = self.pending_indent
        indent.prefix, self.pending = self.pending, ''
        indent.lineno, indent.column = self.line, 0
        self.pending_indent = None
      elif self.leaves and self.leaves[
          -1].type == token.DEDENT and '#' in self.pending:
        dedent = self.leaves[-1]
        dedent.prefix += self.pending
        dedent.lineno, dedent.column = self.line, self.column
        self.pending = ''
    leaf = Leaf(kind, text, (self.pending, position or
                             (self.line, self.column)))
    leaf._start = len(self.leaves)
    leaf._end = leaf._start + 1
    self.leaves.append(leaf)
    self.pending = ''
    return leaf

  def add_token(self, value):
    self.tokens.append(value)
    if self.opaque:
      self._position(value)
      return
    owner = self.stack[-1] if self.stack else None
    if isinstance(owner, cst.Comment):
      self.pending += value
      self._position(value)
      return
    if isinstance(owner, cst.Newline):
      # Only a statement/block header's trailing newline ends a logical line.
      significant = (
          len(self.stack) >= 3 and
          isinstance(self.stack[-2], cst.TrailingWhitespace) and not any(
              isinstance(n, (cst.ParenthesizedWhitespace, cst.EmptyLine))
              for n in self.stack))
      if significant:
        self._leaf(token.NEWLINE, value)
      else:
        self.pending += value
      self._position(value)
      return
    if isinstance(owner,
                  (cst.SimpleWhitespace, cst.EmptyLine)) or not value.strip():
      self.pending += value
      self._position(value)
      return
    if isinstance(owner, cst.Name):
      kind = _NAME_TYPES.get(value, token.NAME)
      self._leaf(kind, value)
      self._position(value)
      return
    if isinstance(owner, (cst.Integer, cst.Float, cst.Imaginary)):
      self._leaf(token.NUMBER, value)
      self._position(value)
      return
    # These are fixed syntax fragments emitted by LibCST (e.g. " = ",
    # "not", or "*, "), never arbitrary source, literals, or identifiers.
    # Split only the finite vocabulary of punctuation/keywords in emissions.
    offset = 0
    while offset < len(value):
      if value[offset].isspace():
        end = offset + 1
        while end < len(value) and value[end].isspace():
          end += 1
        text = value[offset:end]
        self.pending += text
      elif value[offset].isalpha() or value[offset] == '_':
        end = offset + 1
        while end < len(value) and (value[end].isalnum() or value[end] == '_'):
          end += 1
        text = value[offset:end]
        kind = _NAME_TYPES.get(text, token.NAME)
        self._leaf(kind, text)
      else:
        text = next((op for op in _OPERATORS if value.startswith(op, offset)),
                    None)
        if text is None:
          raise RuntimeError('Unexpected LibCST code-generation fragment: %r' %
                             value)
        end = offset + len(text)
        # The layout engine treats ellipsis as three connected dot tokens.
        if text == '...':
          for i in range(3):
            self._leaf(token.DOT, '.', (self.line, self.column + i))
        else:
          self._leaf(token.EXACT_TOKEN_TYPES[text], text)
      self._position(text)
      offset = end

  def add_indent_tokens(self):
    for indent in self.indent_tokens:
      self.add_token(indent)

  def increase_indent(self, value):
    super().increase_indent(value)
    self.pending_indent = self._leaf(token.INDENT, ''.join(self.indent_tokens),
                                     (self.line, 0))

  def decrease_indent(self):
    super().decrease_indent()
    self._leaf(token.DEDENT, '', (self.line, self.column))

  @contextmanager
  def record_syntactic_position(self, node, **kwargs):
    if isinstance(node, (cst.SimpleString, cst.FormattedString,
                         cst.TemplatedString)) and not self.opaque:
      start = len(self.tokens)
      position = (self.line, self.column)
      self.opaque += 1
      try:
        yield
      finally:
        self.opaque -= 1
      self._leaf(token.STRING, ''.join(self.tokens[start:]), position)
    else:
      yield


def ParseModule(code):
  """Parse source with LibCST and expose conventional SyntaxError positions."""
  if not code.endswith('\n'):
    code += '\n'
  try:
    module = cst.parse_module(code)
    if module.code != code:
      # LibCST 1.9.0 can omit indented module-footer comments. Giving those
      # comments a following statement makes them leading_lines instead.
      # Remove only that synthetic statement, then verify exact reconstruction.
      envelope = cst.parse_module(code + 'pass\n')
      sentinel = envelope.body[-1]
      if not (isinstance(sentinel, cst.SimpleStatementLine) and len(
          sentinel.body) == 1 and isinstance(sentinel.body[0], cst.Pass)):
        raise SyntaxError('LibCST did not preserve the source boundary')
      module = envelope.with_changes(
          body=envelope.body[:-1], footer=sentinel.leading_lines)
      if module.code != code:
        raise SyntaxError('LibCST could not preserve the original source')
    return module
  except cst.ParserSyntaxError as exc:
    lines = code.splitlines(keepends=True)
    line = exc.raw_line
    text = lines[line - 1] if 0 < line <= len(lines) else ''
    raise SyntaxError(exc.message,
                      ('<unknown>', line, exc.raw_column + 1, text)) from exc
  except cst.CSTValidationError as exc:
    raise SyntaxError(
        str(exc),
        ('<unknown>', 1, 1, next(iter(code.splitlines()), ''))) from exc


def ParseCode(code):
  return LowerModule(ParseModule(code))


def LowerModule(module):
  if not isinstance(module, cst.Module):
    raise TypeError('FormatTree requires a libcst.Module')
  # FormatTree must not mutate its input, and an implicit final newline must
  # be represented in the layout just as for FormatCode.
  module = module.with_changes(has_trailing_newline=True)
  state = _Emissions(module)
  module._codegen(state)
  if state.shared_nodes:
    # Hand-built CSTs can reuse immutable nodes in several source positions.
    # Parsed modules normally have unique identities; clone only when needed.
    module = module.deep_clone()
    state = _Emissions(module)
    module._codegen(state)
  state._leaf(token.ENDMARKER, '')
  try:
    result = _Lowering(state).lower(module)
  except UnsupportedSyntaxError as exc:
    exc.filename = '<unknown>'
    if exc.lineno is None:
      exc.lineno, exc.offset = 1, 1
    raise
  if list(result.leaves()) != state.leaves:
    raise RuntimeError('LibCST lowering changed token identity or order')
  return result


class _Lowering:
  """Translate typed CST constructs into layout groups, never parse tokens."""

  def __init__(self, state):
    self.tokens = state.leaves
    self.spans = state.spans

  def span(self, node):
    return self.spans[id(node)]

  def group(self, name, start, end, parts=(), force=False, flatten=()):
    children = []
    cursor = start
    for part in sorted((p for p in parts if p is not None),
                       key=lambda p: p._start):
      if part._end <= start or part._start >= end:
        continue
      if part._start < cursor or part._end > end:
        raise RuntimeError('Overlapping LibCST layout spans in %s' % name)
      children.extend(self.tokens[cursor:part._start])
      if isinstance(part, Node) and part.type.name in flatten:
        children.extend(part.children)
      else:
        children.append(part)
      cursor = part._end
    children.extend(self.tokens[cursor:end])
    if len(children) == 1 and not force:
      return children[0]
    if not children:
      return None
    result = Node(Kind[name], children)
    result._start, result._end = start, end
    return result

  def combine(self, name, node, parts=(), force=False, flatten=()):
    return self.group(name, *self.span(node), parts, force, flatten)

  def lower(self, node, tuple_kind='testlist_star_expr'):
    if node is None:
      return None
    if isinstance(node, cst.Module):
      return self.lower_Module(node)
    start, end = self.span(node)
    if start == end:
      return None
    method = getattr(self, 'lower_' + type(node).__name__, None)
    # All expression parentheses are explicit LibCST fields. Preserve each
    # pair as a separate bracket group; this does not inspect source grammar.
    lpar = getattr(node, 'lpar', ())
    rpar = getattr(node, 'rpar', ())
    parens = len(lpar) if isinstance(lpar, (tuple, list)) else 0
    if parens and isinstance(node, (cst.BaseExpression, cst.MatchPattern)):
      inner_start = self.span(lpar[-1])[1]
      inner_end = self.span(rpar[0])[0]
      self.spans[id(node)] = (inner_start, inner_end)
      try:
        result = self._lower_core(
            node, method,
            'testlist_gexp' if isinstance(node, cst.Tuple) else tuple_kind)
      finally:
        self.spans[id(node)] = (start, end)
      for left, right in zip(reversed(lpar), rpar):
        result = self.group('atom',
                            self.span(left)[0],
                            self.span(right)[1], [result], True)
      return result
    return self._lower_core(node, method, tuple_kind)

  def _lower_core(self, node, method, tuple_kind):
    if isinstance(node, cst.Tuple):
      return self.sequence(node, node.elements, tuple_kind)
    if method is not None:
      return method(node)
    if isinstance(node,
                  (cst.Name, cst.Integer, cst.Float, cst.Imaginary,
                   cst.SimpleString, cst.FormattedString, cst.TemplatedString,
                   cst.Ellipsis, cst.Pass, cst.Break, cst.Continue)):
      return self.combine('atom', node)
    leaf = self.tokens[self.span(node)[0]]
    raise UnsupportedSyntaxError(
        'No layout rule for LibCST %s' % type(node).__name__,
        ('<unknown>', leaf.lineno, leaf.column + 1, None))

  def lower_Module(self, node):
    return self.group('file_input', 0, len(self.tokens),
                      [self.lower(s) for s in node.body], True)

  def lower_SimpleStatementLine(self, node):
    return self.combine('simple_stmt', node, [self.lower(s) for s in node.body],
                        True)

  lower_SimpleStatementSuite = lower_SimpleStatementLine

  def lower_IndentedBlock(self, node):
    return self.combine('suite', node, [self.lower(s) for s in node.body], True)

  def statement(self, name, node, parts=()):
    start, end = self.span(node)
    # Semicolons belong to the enclosing simple statement, not its expression.
    semi = getattr(node, 'semicolon', None)
    if isinstance(semi, cst.Semicolon):
      end = self.span(semi)[0]
    return self.group(name, start, end, parts)

  def lower_Expr(self, node):
    return self.lower(node.value)

  def lower_Assign(self, node):
    return self.statement('expr_stmt', node,
                          [self.lower(t.target) for t in node.targets] +
                          [self.lower(node.value)])

  def lower_AnnAssign(self, node):
    ann = self.group(
        'annassign',
        self.span(node.annotation)[0],
        self.span(node.value or node.annotation)[1],
        [self.lower(node.annotation.annotation),
         self.lower(node.value)])
    return self.statement('expr_stmt', node, [self.lower(node.target), ann])

  def lower_AugAssign(self, node):
    return self.statement('expr_stmt', node,
                          [self.lower(node.target),
                           self.lower(node.value)])

  def lower_Del(self, node):
    return self.statement('del_stmt', node,
                          [self.lower(node.target, 'exprlist')])

  def lower_Return(self, node):
    return self.statement('return_stmt', node, [self.lower(node.value)])

  def lower_Raise(self, node):
    return self.statement('raise_stmt', node, [
        self.lower(node.exc),
        self.lower(node.cause.item) if node.cause else None
    ])

  def lower_Assert(self, node):
    return self.statement(
        'assert_stmt', node,
        [self.lower(node.test), self.lower(node.msg)])

  def lower_Global(self, node):
    return self.statement('global_stmt', node)

  lower_Nonlocal = lower_Global

  def dotted(self, node):
    if isinstance(node, cst.Attribute):
      return self.combine(
          'dotted_name',
          node, [self.dotted(node.value),
                 self.lower(node.attr)],
          flatten=('dotted_name',))
    return self.lower(node)

  def alias(self, node, dotted):
    start, end = self.span(node)
    if isinstance(node.comma, cst.Comma):
      end = self.span(node.comma)[0]
    return self.group('dotted_as_name' if dotted else 'import_as_name', start,
                      end, [
                          self.dotted(node.name),
                          self.lower(node.asname.name) if node.asname else None
                      ])

  def lower_Import(self, node):
    parts = [self.alias(a, True) for a in node.names]
    names = self.group('dotted_as_names', parts[0]._start, parts[-1]._end,
                       parts)
    return self.statement('import_name', node, [names])

  def lower_ImportFrom(self, node):
    parts = [self.dotted(node.module)] if node.module else []
    if not isinstance(node.names, cst.ImportStar):
      aliases = [self.alias(a, False) for a in node.names]
      end = self.span(node.names[-1])[1]
      parts.append(
          self.group('import_as_names', aliases[0]._start, end, aliases))
    return self.statement('import_from', node, parts)

  def lower_If(self, node):
    parts = [self.lower(node.test), self.lower(node.body)]
    if node.orelse:
      parts.append(self.lower(node.orelse))
    return self.combine('if_stmt', node, parts, flatten=('if_stmt',))

  def lower_Else(self, node):
    return self.combine('if_stmt', node, [self.lower(node.body)])

  def lower_While(self, node):
    return self.combine(
        'while_stmt',
        node,
        [self.lower(node.test),
         self.lower(node.body),
         self.lower(node.orelse)],
        flatten=('if_stmt',))

  def asynchronous(self, name, node, parts):
    start, end = self.span(node)
    if node.asynchronous:
      inner = self.group(name, self.span(node.asynchronous)[1], end, parts)
      return self.group('async_stmt', start, end, [inner])
    return self.group(name, start, end, parts, flatten=('if_stmt',))

  def lower_For(self, node):
    return self.asynchronous('for_stmt', node, [
        self.lower(node.target, 'exprlist'),
        self.lower(node.iter),
        self.lower(node.body),
        self.lower(node.orelse)
    ])

  def lower_With(self, node):
    items = []
    for item in node.items:
      start, end = self.span(item)
      if isinstance(item.comma, cst.Comma):
        end = self.span(item.comma)[0]
      items.append(
          self.group('asexpr_test', start, end, [
              self.lower(item.item),
              self.lower(item.asname.name) if item.asname else None
          ]))
    if node.lpar is not cst.MaybeSentinel.DEFAULT:
      # Parenthesized with-items are a comma-separated bracket container.
      inner = self.group('testlist_gexp', items[0]._start,
                         self.span(node.items[-1])[1], items)
      items = [
          self.group('atom',
                     self.span(node.lpar)[0],
                     self.span(node.rpar)[1], [inner])
      ]
    return self.asynchronous('with_stmt', node, items + [self.lower(node.body)])

  def lower_Try(self, node):
    parts = [self.lower(node.body)]
    for handler in node.handlers:
      s, e = self.span(handler)
      colon = self.span(handler.body)[0] - 1
      parts.append(
          self.group('except_clause', s, colon, [
              self.lower(handler.type),
              self.lower(handler.name.name) if handler.name else None
          ]))
      parts.append(self.lower(handler.body))
    parts.extend([self.lower(node.orelse), self.lower(node.finalbody)])
    return self.combine('try_stmt', node, parts, flatten=('if_stmt',))

  lower_TryStar = lower_Try

  def lower_Finally(self, node):
    return self.combine('if_stmt', node, [self.lower(node.body)])

  def parameters(self, node, kind='typedargslist'):
    params = list(node.posonly_params) + list(node.params)
    if isinstance(node.star_arg, cst.Param):
      params.append(node.star_arg)
    params.extend(node.kwonly_params)
    if node.star_kwarg:
      params.append(node.star_kwarg)
    parts = []
    for param in params:
      if param.annotation:
        part = self.group(
            'tname',
            self.span(param.name)[0],
            self.span(param.annotation)[1],
            [self.lower(param.name),
             self.lower(param.annotation.annotation)])
        parts.append(part)
      else:
        parts.append(self.lower(param.name))
      if param.default:
        parts.append(self.lower(param.default))
    return self.combine(kind, node, parts)

  def lower_FunctionDef(self, node):
    if node.type_parameters is not None:
      raise UnsupportedSyntaxError(
          'Type parameters are outside this main-branch migration')
    params = self.parameters(node.params)
    left = self.span(node.name)[1]
    right = self.span(node.params)[1] + 1
    parameters = self.group('parameters', left, right, [params], True)
    parts = [
        self.lower(node.name), parameters,
        self.lower(node.returns.annotation) if node.returns else None,
        self.lower(node.body)
    ]
    start, end = self.span(node)
    def_start = self.span(node.name)[0] - 1
    result = self.group('funcdef', def_start, end, parts, True)
    if node.asynchronous:
      result = self.group('async_funcdef' if node.decorators else 'async_stmt',
                          self.span(node.asynchronous)[0], end, [result])
    if node.decorators:
      decorators = [self.lower(d) for d in node.decorators]
      deco = self.group('decorators', decorators[0]._start, decorators[-1]._end,
                        decorators)
      result = self.group('decorated', start, end, [deco, result])
    return result

  def lower_ClassDef(self, node):
    if node.type_parameters is not None:
      raise UnsupportedSyntaxError(
          'Type parameters are outside this main-branch migration')
    args = [self.argument(a) for a in tuple(node.bases) + tuple(node.keywords)]
    parts = [self.lower(node.name), self.lower(node.body)]
    if args:
      parts.append(
          self.group(
              'arglist', args[0]._start,
              self.span((tuple(node.bases) + tuple(node.keywords))[-1])[1],
              args))
    start, end = self.span(node)
    result = self.group('classdef',
                        self.span(node.name)[0] - 1, end, parts, True)
    if node.decorators:
      decorators = [self.lower(d) for d in node.decorators]
      deco = self.group('decorators', decorators[0]._start, decorators[-1]._end,
                        decorators)
      result = self.group('decorated', start, end, [deco, result])
    return result

  def lower_Decorator(self, node):
    return self.combine('decorator', node, [self.lower(node.decorator)])

  def lower_Lambda(self, node):
    return self.combine(
        'lambdef', node,
        [self.parameters(node.params, 'varargslist'),
         self.lower(node.body)])

  def lower_IfExp(self, node):
    return self.combine(
        'test', node,
        [self.lower(node.body),
         self.lower(node.test),
         self.lower(node.orelse)])

  def lower_NamedExpr(self, node):
    return self.combine('namedexpr_test', node,
                        [self.lower(node.target),
                         self.lower(node.value)])

  def lower_Yield(self, node):
    if isinstance(node.value, cst.From):
      arg = self.combine('yield_arg', node.value, [self.lower(node.value.item)])
    else:
      arg = self.lower(node.value)
    return self.combine('yield_expr', node, [arg])

  def lower_Await(self, node):
    return self.combine(
        'power', node, [self.lower(node.expression)], flatten=('power',))

  _binary_roles = {
      cst.Add: 'arith_expr',
      cst.Subtract: 'arith_expr',
      cst.Multiply: 'term',
      cst.Divide: 'term',
      cst.FloorDivide: 'term',
      cst.Modulo: 'term',
      cst.MatrixMultiply: 'term',
      cst.LeftShift: 'shift_expr',
      cst.RightShift: 'shift_expr',
      cst.BitOr: 'expr',
      cst.BitXor: 'xor_expr',
      cst.BitAnd: 'and_expr',
      cst.Power: 'power',
      cst.And: 'and_test',
      cst.Or: 'or_test',
  }

  def lower_BinaryOperation(self, node):
    role = self._binary_roles[type(node.operator)]
    left, right = self.lower(node.left), self.lower(node.right)
    # Left-associative operator chains share one formatting precedence group.
    result = self.combine(role, node, [left, right])
    if isinstance(left, Node) and left.type.name == role:
      result.children = left.children + result.children[1:]
      for child in result.children:
        child.parent = result
    return result

  lower_BooleanOperation = lower_BinaryOperation

  def lower_UnaryOperation(self, node):
    return self.combine(
        'not_test' if isinstance(node.operator, cst.Not) else 'factor', node,
        [self.lower(node.expression)])

  def lower_Comparison(self, node):
    parts = [self.lower(node.left)]
    for comparison in node.comparisons:
      op = comparison.operator
      if isinstance(op, (cst.NotIn, cst.IsNot)):
        parts.append(self.combine('comp_op', op))
      parts.append(self.lower(comparison.comparator))
    return self.combine('comparison', node, parts)

  def power(self, node, base, trailer):
    return self.combine('power', node, [base, trailer], flatten=('power',))

  def argument(self, node):
    s, e = self.span(node)
    if isinstance(node.comma, cst.Comma):
      e = self.span(node.comma)[0]
    value = self.lower(node.value)
    # An unparenthesized generator argument has an argument context, not an
    # extra atom/testlist context.
    if isinstance(node.value, cst.GeneratorExp) and not node.value.lpar:
      value = self.group('argument', value._start, value._end,
                         value.children if isinstance(value, Node) else [value])
    return self.group('argument', s, e, [self.lower(node.keyword), value])

  def lower_Call(self, node):
    base = self.lower(node.func)
    s, e = self.span(node)
    args = [self.argument(a) for a in node.args]
    part = self.group('arglist', base._end + 1, e - 1, args)
    trailer = self.group('trailer', base._end, e, [part], True)
    return self.power(node, base, trailer)

  def lower_Attribute(self, node):
    base = self.lower(node.value)
    trailer = self.group('trailer', base._end,
                         self.span(node)[1], [self.lower(node.attr)], True)
    return self.power(node, base, trailer)

  def lower_Subscript(self, node):
    base = self.lower(node.value)
    slices = [self.lower(s.slice) for s in node.slice]
    args = self.group('subscriptlist',
                      self.span(node.lbracket)[1],
                      self.span(node.rbracket)[0], slices)
    trailer = self.group('trailer', base._end, self.span(node)[1], [args], True)
    return self.power(node, base, trailer)

  def lower_Index(self, node):
    value = self.lower(node.value)
    return self.combine('star_expr', node, [value]) if node.star else value

  def lower_Slice(self, node):
    parts = [self.lower(node.lower), self.lower(node.upper)]
    if isinstance(node.second_colon, cst.Colon):
      parts.append(
          self.group('sliceop',
                     self.span(node.second_colon)[0],
                     self.span(node)[1], [self.lower(node.step)]))
    return self.combine('subscript', node, parts)

  def sequence(self, node, elements, role):
    parts = []
    for element in elements:
      if isinstance(element, cst.StarredElement):
        s, e = self.span(element)
        if isinstance(element.comma, cst.Comma):
          e = self.span(element.comma)[0]
        part = self.group('star_expr', s, e, [self.lower(element.value)])
      else:
        part = self.lower(element.value)
      parts.append(part)
    return self.combine(role, node, parts)

  def container(self, node, role, parts):
    s, e = self.span(node)
    inner = self.group(role, s + 1, e - 1, parts)
    return self.group('atom', s, e, [inner], True)

  def lower_List(self, node):
    parts = [self.element(e) for e in node.elements]
    return self.container(node, 'listmaker', parts)

  def element(self, node):
    s, e = self.span(node)
    if isinstance(node.comma, cst.Comma):
      e = self.span(node.comma)[0]
    if isinstance(node, cst.StarredElement):
      return self.group('star_expr', s, e, [self.lower(node.value)])
    return self.lower(node.value)

  def lower_Set(self, node):
    return self.container(node, 'dictsetmaker',
                          [self.element(e) for e in node.elements])

  def lower_Dict(self, node):
    parts = []
    for element in node.elements:
      if isinstance(element, cst.DictElement):
        parts.extend([self.lower(element.key), self.lower(element.value)])
      else:
        parts.append(self.lower(element.value))
    return self.container(node, 'dictsetmaker', parts)

  def comp_for(self, node):
    suffix = self.comp_for(node.inner_for_in) if node.inner_for_in else None
    for cond in reversed(node.ifs):
      end = suffix._end if suffix else self.span(cond)[1]
      suffix = self.group('comp_if',
                          self.span(cond)[0], end,
                          [self.lower(cond.test), suffix])
    return self.combine(
        'comp_for', node,
        [self.lower(node.target, 'exprlist'),
         self.lower(node.iter), suffix])

  def lower_ListComp(self, node):
    return self.container(
        node, 'listmaker',
        [self.lower(node.elt), self.comp_for(node.for_in)])

  def lower_SetComp(self, node):
    return self.container(
        node, 'dictsetmaker',
        [self.lower(node.elt), self.comp_for(node.for_in)])

  def lower_DictComp(self, node):
    return self.container(node, 'dictsetmaker', [
        self.lower(node.key),
        self.lower(node.value),
        self.comp_for(node.for_in)
    ])

  def lower_GeneratorExp(self, node):
    return self.combine(
        'testlist_gexp', node,
        [self.lower(node.elt), self.comp_for(node.for_in)])

  def lower_ConcatenatedString(self, node):
    return self.combine(
        'atom',
        node,
        [self.lower(node.left), self.lower(node.right)],
        flatten=('atom',))

  def lower_Match(self, node):
    return self.combine('match_stmt', node,
                        [self.lower(node.subject, 'subject_expr')] +
                        [self.lower(case) for case in node.cases])

  def lower_MatchCase(self, node):
    parts = [self.lower(node.pattern), self.lower(node.body)]
    if node.guard:
      parts.append(
          self.group('guard',
                     self.span(node.guard)[0] - 1,
                     self.span(node.guard)[1], [self.lower(node.guard)]))
    return self.combine('case_block', node, parts)

  def lower_MatchValue(self, node):
    return self.lower(node.value)

  def lower_MatchSingleton(self, node):
    return self.lower(node.value)

  def lower_MatchAs(self, node):
    return self.combine('asexpr_test', node,
                        [self.lower(node.pattern),
                         self.lower(node.name)])

  def lower_MatchOr(self, node):
    return self.combine('expr', node,
                        [self.lower(e.pattern) for e in node.patterns])

  def lower_MatchStar(self, node):
    start, end = self.span(node)
    if isinstance(node.comma, cst.Comma):
      end = self.span(node.comma)[0]
    return self.group('star_expr', start, end, [self.lower(node.name)])

  def lower_MatchList(self, node):
    parts = [
        self.lower(p if isinstance(p, cst.MatchStar) else p.value)
        for p in node.patterns
    ]
    if node.lbracket is None:
      return self.combine('patterns', node, parts)
    return self.container(node, 'listmaker', parts)

  def lower_MatchTuple(self, node):
    return self.combine('testlist_gexp', node, [
        self.lower(p if isinstance(p, cst.MatchStar) else p.value)
        for p in node.patterns
    ])

  def lower_MatchMapping(self, node):
    parts = []
    for element in node.elements:
      parts.extend([self.lower(element.key), self.lower(element.pattern)])
    if node.rest:
      parts.append(self.lower(node.rest))
    return self.container(node, 'dictsetmaker', parts)

  def lower_MatchClass(self, node):
    base = self.lower(node.cls)
    parts = [
        self.lower(p if isinstance(p, cst.MatchStar) else p.value)
        for p in node.patterns
    ]
    for kw in node.kwds:
      s, e = self.span(kw)
      if isinstance(kw.comma, cst.Comma):
        e = self.span(kw.comma)[0]
      parts.append(
          self.group(
              'argument', s, e,
              [self.lower(kw.key), self.lower(kw.pattern)]))
    s, e = self.span(node)
    args = self.group('arglist', base._end + 1, e - 1, parts)
    return self.power(node, base,
                      self.group('trailer', base._end, e, [args], True))
