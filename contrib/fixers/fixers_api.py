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
"""Entry point for refactoring via the lib2to3 fixer."""

from lib2to3 import refactor as lib2to3_refactor
from lib2to3.pgen2 import parse as pgen2_parse
from lib2to3.pgen2 import tokenize as pgen2_tokenize

# Our path in the source tree.
MODULE_NAME_PREFIX = 'contrib.fixers.fix_'

# A list of available fixers.
AVAILABLE_FIXERS = ['quotes']


def ValidateCommandLineArguments(args):
  if args.fixers:
    for fixer in args.fixers:
      if fixer not in AVAILABLE_FIXERS:
        return 'invalid fixer specified: ' + fixer

  if ((not args.fixers or 'quotes' not in args.fixers) and
      args.force_quote_type != 'none'):
    return 'cannot use --force-quote-type without --fixers=quotes'

  return None


def Pre2to3FixerRun(original_source, options):
  """2to3 fixers to run before reformatting the file."""
  if options and options['fixers']:
    return _Run2to3Fixers(original_source, options=options)
  return original_source


def Post2to3FixerRun(original_source, options):
  """2to3 fixers to run after reformatting the file."""
  if options and options['fixers']:
    return _Run2to3Fixers(original_source, options)
  return original_source


def _Run2to3Fixers(source, options):
  """Use lib2to3 to reformat the source.

  Args:
    source: (unicode) The source to reformat.
    options: dictionary of options to pass to lib2to3_refactor.RefactoringTool

  Returns:
    Reformatted source code.
  """
  fixer_names = [MODULE_NAME_PREFIX + fixer for fixer in options['fixers']]
  options['print_function'] = True
  try:
    try:
      tool = lib2to3_refactor.RefactoringTool(
          fixer_names=fixer_names, explicit=fixer_names, options=options)
      return '{}'.format(tool.refactor_string(source, name=''))
    except pgen2_parse.ParseError:
      options['print_function'] = False
      tool = lib2to3_refactor.RefactoringTool(
          fixer_names=fixer_names, explicit=fixer_names, options=options)
      return '{}'.format(tool.refactor_string(source, name=''))
  except (pgen2_tokenize.TokenError, pgen2_parse.ParseError, SyntaxError,
          UnicodeDecodeError, UnicodeEncodeError) as err:
    logging.error(err)
    raise
