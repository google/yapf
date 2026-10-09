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
"""Small mutable layout IR populated from LibCST, not a syntax parser.

Groups describe formatting contexts and leaves describe printable tokens. The
layout passes may annotate, insert or replace these objects without modifying
LibCST's immutable source tree. No grammar, matching engine or tokenizer lives
here.
"""

from yapf.layout import tokens as token
from yapf.layout.roles import Kind


def type_repr(kind):
  if kind >= 256:
    return Kind(kind).name
  return token.tok_name.get(kind, 'CONTINUATION')


class Base:
  parent = None

  @property
  def prev_sibling(self):
    if self.parent is None:
      return None
    siblings = self.parent.children
    i = next(i for i, sibling in enumerate(siblings) if sibling is self)
    return siblings[i - 1] if i else None

  @property
  def next_sibling(self):
    if self.parent is None:
      return None
    siblings = self.parent.children
    i = next(i for i, sibling in enumerate(siblings) if sibling is self)
    return siblings[i + 1] if i + 1 < len(siblings) else None

  def remove(self):
    if self.parent is not None:
      siblings = self.parent.children
      i = next(i for i, sibling in enumerate(siblings) if sibling is self)
      del siblings[i]
      self.parent = None
      return i
    return None

  def replace(self, replacement):
    parent = self.parent
    if parent is None:
      raise ValueError('Cannot replace the root of a layout tree')
    i = self.remove()
    for child in reversed(
        replacement if isinstance(replacement, list) else [replacement]):
      parent.insert_child(i, child)

  def pre_order(self):
    yield self
    for child in self.children:
      yield from child.pre_order()

  def get_lineno(self):
    return next(self.leaves()).lineno


class Leaf(Base):
  children = ()

  def __init__(self, type, value, context=None, prefix=None):
    self.type = type
    self.value = value
    self.prefix = ''
    self.lineno = 0
    self.column = 0
    if context is not None:
      self.prefix, (self.lineno, self.column) = context
    if prefix is not None:
      self.prefix = prefix
    self.parent = None

  def leaves(self):
    yield self

  def clone(self):
    result = Leaf(self.type, self.value,
                  (self.prefix, (self.lineno, self.column)))
    for key, value in vars(self).items():
      if key.startswith('_yapf_'):
        setattr(result, key, value.copy() if isinstance(value, set) else value)
    return result

  def __str__(self):
    return self.prefix + self.value

  def __repr__(self):
    return 'Leaf(%s, %r)' % (type_repr(self.type), self.value)


class Node(Base):

  def __init__(self, type, children, prefix=None):
    self.type = type
    self.children = []
    self.parent = None
    for child in children:
      self.append_child(child)
    if prefix is not None:
      self.prefix = prefix

  @property
  def prefix(self):
    return self.children[0].prefix if self.children else ''

  @prefix.setter
  def prefix(self, value):
    if self.children:
      self.children[0].prefix = value

  def leaves(self):
    for child in self.children:
      yield from child.leaves()

  def append_child(self, child):
    child.parent = self
    self.children.append(child)

  def insert_child(self, index, child):
    child.parent = self
    self.children.insert(index, child)

  def clone(self):
    result = Node(self.type, [child.clone() for child in self.children])
    for key, value in vars(self).items():
      if key.startswith('_yapf_'):
        setattr(result, key, value.copy() if isinstance(value, set) else value)
    return result

  def __str__(self):
    return ''.join(str(child) for child in self.children)

  def __repr__(self):
    return 'Node(%s, %r)' % (type_repr(self.type), self.children)
