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
"""Python format style guidelines."""


def Get(setting_name):
  """Get a style setting."""
  return _style[setting_name]


def SetGlobalStyle(style):
  """Set a style dict."""
  global _style
  _style = style


def CreatePEP8Style():
  return dict(
      # The column limit.
      COLUMN_LIMIT=80,

      # The regex for an i18n comment. The presence of this comment stops
      # reformatting of that line, because the comments are required to be
      # next to the string they translate.
      I18N_COMMENT='',

      # The i18n function call names. The presence of this function stops
      # reformattting on that line, because the string it has cannot be moved
      # away from the i18n comment.
      I18N_FUNCTION_CALL='',

      # The number of columns to use for indentation.
      INDENT_WIDTH=4,

      # Indent width for line continuations.
      CONTINUATION_INDENT_WIDTH=4,

      # Insert a blank line after the start of a class and before a method.
      NO_BLANK_LINE_AFTER_CLASS_OR_DEF=True,

      # The number of spaces required before a trailing comment.
      SPACES_BEFORE_COMMENT=1,

      # Set to True to prefer splitting before 'and' or 'or' rather than
      # after.
      SPLIT_BEFORE_LOGICAL_OPERATOR=False,

      # Split named assignments onto individual lines.
      SPLIT_BEFORE_NAMED_ASSIGNS=True,

      # The penalty for splitting the line after a unary operator.
      SPLIT_PENALTY_AFTER_UNARY_OPERATOR=100,

      # The penalty for characters over the column limit.
      SPLIT_PENALTY_EXCESS_CHARACTER=200,

      # The penalty of splitting the line around the 'and' and 'or' operators.
      SPLIT_PENALTY_LOGICAL_OPERATOR=30,

      # The penalty for not matching the splitting decision for the matching
      # bracket tokens. For instance, if there is a newline after the opening
      # bracket, we would tend to expect one before the closing bracket, and
      # vice versa.
      SPLIT_PENALTY_MATCHING_BRACKET=50,

      # The penalty for splitting right after the opening bracket.
      SPLIT_PENALTY_AFTER_OPENING_BRACKET=30,

      # The penalty incurred by adding a line split to the unwrapped line. The
      # more line splits added the higher the penalty.
      SPLIT_PENALTY_FOR_ADDED_LINE_SPLIT=30,

      # Use tabs in the resulting file.
      USE_TAB=False,

      # The number of columns used for tab stops.
      TAB_WIDTH=8,
  )


def CreateGoogleStyle():
  style = CreatePEP8Style()
  style['INDENT_WIDTH'] = 2
  style['SPACES_BEFORE_COMMENT'] = 2
  style['NO_BLANK_LINE_AFTER_CLASS_OR_DEF'] = False
  style['I18N_COMMENT'] = r'#\..*'
  style['I18N_FUNCTION_CALL'] = ('N_', '_')
  return style


# TODO(eliben): For now we're preserving the global presence of a style dict.
# Refactor this so that the style is passed around through yapf rather than
# being global.
_style = {}
SetGlobalStyle(CreatePEP8Style())
