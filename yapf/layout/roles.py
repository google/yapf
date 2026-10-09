# Copyright 2021 Google Inc. All Rights Reserved.
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
"""Semantic layout categories; no parser or grammar is defined here."""

from enum import IntEnum
from enum import auto


class Kind(IntEnum):
  and_expr = 256
  and_test = auto()
  annassign = auto()
  arglist = auto()
  argument = auto()
  arith_expr = auto()
  asexpr_test = auto()
  assert_stmt = auto()
  async_funcdef = auto()
  async_stmt = auto()
  atom = auto()
  case_block = auto()
  classdef = auto()
  comp_for = auto()
  comp_if = auto()
  comp_op = auto()
  comparison = auto()
  decorated = auto()
  decorator = auto()
  decorators = auto()
  del_stmt = auto()
  dictsetmaker = auto()
  dotted_as_name = auto()
  dotted_as_names = auto()
  dotted_name = auto()
  except_clause = auto()
  expr = auto()
  expr_stmt = auto()
  exprlist = auto()
  factor = auto()
  file_input = auto()
  for_stmt = auto()
  funcdef = auto()
  global_stmt = auto()
  guard = auto()
  if_stmt = auto()
  import_as_name = auto()
  import_as_names = auto()
  import_from = auto()
  import_name = auto()
  lambdef = auto()
  listmaker = auto()
  match_stmt = auto()
  namedexpr_test = auto()
  not_test = auto()
  or_test = auto()
  parameters = auto()
  patterns = auto()
  power = auto()
  raise_stmt = auto()
  return_stmt = auto()
  shift_expr = auto()
  simple_stmt = auto()
  sliceop = auto()
  star_expr = auto()
  subject_expr = auto()
  subscript = auto()
  subscriptlist = auto()
  suite = auto()
  term = auto()
  test = auto()
  testlist_gexp = auto()
  testlist_star_expr = auto()
  tname = auto()
  trailer = auto()
  try_stmt = auto()
  typedargslist = auto()
  varargslist = auto()
  while_stmt = auto()
  with_stmt = auto()
  xor_expr = auto()
  yield_arg = auto()
  yield_expr = auto()
