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
"""Python formatting style settings."""

import os
import re
import textwrap

from yapf.yapflib import py3compat
from yapf.yapflib import errors


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
STYLE_DIRECTORY = os.path.join(os.path.dirname(SCRIPT_DIR), 'styles')


class StyleConfigError(errors.YapfError):
  """Raised when there's a problem reading the style configuration."""
  pass


def Get(setting_name):
  """Get a style setting."""
  return _style[setting_name]


def Help():
  """Return dict mapping style names to help strings."""
  return _STYLE_HELP


def SetGlobalStyle(style):
  """Set a style dict."""
  global _style
  _style = style


_STYLE_HELP = dict(
    ALIGN_CLOSING_BRACKET_WITH_VISUAL_INDENT=
    'Align closing bracket with visual indentation.',
    COLUMN_LIMIT='The column limit.',
    I18N_COMMENT=textwrap.dedent("""\
      The regex for an i18n comment. The presence of this comment stops
      reformatting of that line, because the comments are required to be
      next to the string they translate."""),
    I18N_FUNCTION_CALL=textwrap.dedent("""\
      The i18n function call names. The presence of this function stops
      reformattting on that line, because the string it has cannot be moved
      away from the i18n comment."""),
    INDENT_WIDTH='The number of columns to use for indentation.',
    CONTINUATION_INDENT_WIDTH='Indent width used for line continuations.',
    BLANK_LINE_BEFORE_NESTED_CLASS_OR_DEF=textwrap.dedent("""\
      Insert a blank line before a 'def' or 'class' immediately nested
      within another 'def' or 'class'.

      For example:

      class Foo:
                         # <------ this blank line
        def method():
          ..."""),
    SPACE_BETWEEN_ENDING_COMMA_AND_CLOSING_BRACKET=textwrap.dedent("""\
      Insert a space between the ending comma and closing bracket of a list,
      etc."""),
    SPACES_BEFORE_COMMENT=(
        'The number of spaces required before a trailing comment.'),
    SPLIT_BEFORE_LOGICAL_OPERATOR=
    "Set to True to prefer splitting before 'and' or 'or' rather than after.",
    SPLIT_BEFORE_NAMED_ASSIGNS='Split named assignments onto individual lines.',
    SPLIT_PENALTY_AFTER_UNARY_OPERATOR=
    'The penalty for splitting the line after a unary operator.',
    SPLIT_PENALTY_EXCESS_CHARACTER=
    'The penalty for characters over the column limit.',
    SPLIT_PENALTY_LOGICAL_OPERATOR=
    "The penalty of splitting the line around the 'and' and 'or' operators.",
    SPLIT_PENALTY_MATCHING_BRACKET=textwrap.dedent("""\
      The penalty for not matching the splitting decision for the matching
      bracket tokens. For instance, if there is a newline after the opening
      bracket, we would tend to expect one before the closing bracket, and
      vice versa."""),
    SPLIT_PENALTY_AFTER_OPENING_BRACKET=
    'The penalty for splitting right after the opening bracket.',
    SPLIT_PENALTY_FOR_ADDED_LINE_SPLIT=textwrap.dedent("""\
      The penalty incurred by adding a line split to the unwrapped line. The
      more line splits added the higher the penalty."""),
    # BASED_ON_STYLE='Which predefined style this style is based on',
)


def _StringListConverter(s):
  """Option value converter for a comma-separated list of strings."""
  return [part.strip() for part in s.split(',')]


def _BoolConverter(s):
  """Option value converter for a boolean."""
  return py3compat.CONFIGPARSER_BOOLEAN_STATES[s.lower()]


# Different style options need to have their values interpreted differently when
# read from the config file. This dict maps an option name to a "converter"
# function that accepts the string read for the option's value from the file and
# returns it wrapper in actual Python type that's going to be meaningful to
# yapf.
#
# Note: this dict has to map all the supported style options.
_STYLE_OPTION_VALUE_CONVERTER = dict(
    ALIGN_CLOSING_BRACKET_WITH_VISUAL_INDENT=_BoolConverter,
    COLUMN_LIMIT=int,
    I18N_COMMENT=str,
    I18N_FUNCTION_CALL=_StringListConverter,
    INDENT_WIDTH=int,
    CONTINUATION_INDENT_WIDTH=int,
    BLANK_LINE_BEFORE_NESTED_CLASS_OR_DEF=_BoolConverter,
    SPACE_BETWEEN_ENDING_COMMA_AND_CLOSING_BRACKET=_BoolConverter,
    SPACES_BEFORE_COMMENT=int,
    SPLIT_BEFORE_LOGICAL_OPERATOR=_BoolConverter,
    SPLIT_BEFORE_NAMED_ASSIGNS=_BoolConverter,
    SPLIT_PENALTY_AFTER_UNARY_OPERATOR=int,
    SPLIT_PENALTY_EXCESS_CHARACTER=int,
    SPLIT_PENALTY_LOGICAL_OPERATOR=int,
    SPLIT_PENALTY_MATCHING_BRACKET=int,
    SPLIT_PENALTY_AFTER_OPENING_BRACKET=int,
    SPLIT_PENALTY_FOR_ADDED_LINE_SPLIT=int,
)


def CreateStyleFromConfig(style_config):
  """Create a style dict from the given config.

  Arguments:
    style_config: either a style name or a file name. The file is expected to
      contain settings. It can have a special BASED_ON_STYLE setting naming the
      style which it derives from. If no such setting is found, it derives from
      the default style. When style_config is None then DEFAULT_STYLE is used.

  Returns:
    A style dict.

  Raises:
    StyleConfigError: if an unknown style option was encountered.
  """
  if style_config is None:
    style_config = DEFAULT_STYLE
  if style_config.startswith('{'):
    # Most likely a style specification from the command line.
    config = _CreateConfigParserFromConfigString(style_config)
  else:
    if os.path.isfile(style_config):
      style_filename = style_config
    else:
      # Search for style in default locations.
      style_filename = os.path.join(STYLE_DIRECTORY, style_config.lower() + '.ini')
      if not os.path.exists(style_filename):
        # Provide a more meaningful error here.
        raise StyleConfigError('"{0}" is not a valid style or file path'.format(
                               style_config))
    config = _CreateConfigParserFromConfigFile(style_filename)
  return _CreateStyleFromConfigParser(config, style_config)


def _CreateConfigParserFromConfigString(config_string):
  """Given a config string from the command line, return a config parser."""
  if config_string[0] != "{" or config_string[-1] != "}":
    raise StyleConfigError(
        "Invalid style dict syntax: '{}'.".format(config_string))
  config = py3compat.ConfigParser()
  config.add_section('style')
  for key, value in re.findall(r'([a-zA-Z0-9_]+)\s*[:=]\s*([a-zA-Z0-9_]+)',
                               config_string):
    config.set('style', key, value)
  return config


def _CreateConfigParserFromConfigFile(config_filename):
  """Read the file and return a ConfigParser object."""
  with open(config_filename) as style_file:
    config = py3compat.ConfigParser()
    config.read_file(style_file)
    if not config.has_section('style'):
      raise StyleConfigError(
          'Unable to find section [style] in {0}'.format(config_filename))
    return config


def _CreateStyleFromConfigParser(config, style_name):
  """Create a style dict from a configuration file.

  Arguments:
    config: a ConfigParser object.

  Returns:
    A style dict.

  Raises:
    StyleConfigError: if an unknown style option was encountered.
  """
  # Initialize the base style.
  if config.has_option('style', 'based_on_style'):
    based_on = config.get('style', 'based_on_style').lower()
  else:
    based_on = DEFAULT_STYLE
  if style_name == DEFAULT_STYLE:
    base_style = dict()
  else:
    base_style = CreateStyleFromConfig(based_on)
  # Read all options specified in the file and update the style.
  for option, value in config.items('style'):
    if option.lower() == 'based_on_style':
      # Now skip this one - we've already handled it and it's not one of the
      # recognized style options.
      continue
    option = option.upper()
    if option not in _STYLE_OPTION_VALUE_CONVERTER:
      raise StyleConfigError('Unknown style option "{0}"'.format(option))
    try:
      base_style[option] = _STYLE_OPTION_VALUE_CONVERTER[option](value)
    except ValueError:
      raise StyleConfigError(
          "'{}' is not a valid setting for {}.".format(value, option))
  return base_style


# The default style - used if yapf is not invoked without specifically
# requesting a formatting style.
DEFAULT_STYLE = 'pep8'

# The name of the file to use for directory-local style defintion.
LOCAL_STYLE = '.style.yapf'

# TODO(eliben): For now we're preserving the global presence of a style dict.
# Refactor this so that the style is passed around through yapf rather than
# being global.
_style = {}
SetGlobalStyle(CreateStyleFromConfig(DEFAULT_STYLE))
