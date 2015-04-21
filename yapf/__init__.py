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
"""YAPF.

YAPF uses the algorithm in clang-format to figure out the "best" formatting for
Python code. It looks at the program as a series of "unwrappable lines" ---
i.e., lines which, if there were no column limit, we would place all tokens on
that line. It then uses a priority queue to figure out what the best formatting
is --- i.e., the formatting with the least penalty.

It differs from tools like autopep8 and pep8ify in that it doesn't just look for
violations of the style guide, but looks at the module as a whole, making
formatting decisions based on what's the best format for each line.

If no filenames are specified, YAPF reads the code from stdin.
"""
from __future__ import print_function

import argparse
import logging
import sys

from yapf.yapflib import file_resources
from yapf.yapflib import py3compat
from yapf.yapflib import style
from yapf.yapflib import yapf_api

__version__ = '0.1.6'


class YapfError(Exception):
  pass


def main(argv):
  """Main program.

  Arguments:
    argv: command-line arguments, such as sys.argv (including the program name
      in argv[0]).

  Returns:
    0 if there were no errors, non-zero otherwise.

  Raises:
    YapfError: if none of the supplied files were Python files.
  """
  parser = argparse.ArgumentParser(description='Formatter for Python code.')
  parser.add_argument('--version',
                      action='store_true',
                      help='show version number and exit')
  parser.add_argument('--style-help',
                      action='store_true',
                      help='show style settings and exit')
  parser.add_argument(
      '--style',
      action='store',
      default='pep8',
      help=('specify formatting style: either a style name (for example "pep8" '
            'or "google"), or the name of a file with style settings. pep8 is '
            'the default.'))
  parser.add_argument('--verify',
                      action='store_true',
                      help='try to verify refomatted code for syntax errors')
  diff_inplace_check_group = parser.add_mutually_exclusive_group()
  diff_inplace_check_group.add_argument('-c', '--check',
                                        action='store_true',
                                        help=('check the files adhere to the '
                                              'style, exits with status 3 if '
                                              'not'))
  diff_inplace_check_group.add_argument('-d', '--diff',
                                        action='store_true',
                                        help=('print the diff for the fixed '
                                              'source'))
  diff_inplace_check_group.add_argument('-i', '--in-place',
                                        action='store_true',
                                        help='make changes to files in place')

  lines_recursive_group = parser.add_mutually_exclusive_group()
  lines_recursive_group.add_argument(
      '-l', '--lines',
      metavar='START-END',
      action='append',
      default=None,
      help='range of lines to reformat, one-based')
  lines_recursive_group.add_argument('-r', '--recursive',
                                     action='store_true',
                                     help='run recursively over directories')

  parser.add_argument('files', nargs='*')
  args = parser.parse_args(argv[1:])

  if args.version:
    print('yapf {}'.format(__version__))
    return 0

  if args.style_help:
    style.SetGlobalStyle(style.CreateStyleFromConfig(args.style))
    for option, docstring in sorted(style.Help().items()):
      print(option, '=', style.Get(option), sep='')
      for line in docstring.splitlines():
        print('  ', line)
      print()
    return 0

  if args.lines and len(args.files) > 1:
    parser.error('cannot use -l/--lines with more than one file')

  lines = _GetLines(args.lines) if args.lines is not None else None
  if not args.files:
    # No arguments specified. Read code from stdin.
    if args.in_place or args.diff or args.check:
      parser.error('cannot use --in_place, -diff or --check flags when '
                   'reading from stdin')

    original_source = []
    while True:
      try:
        # Use 'raw_input' instead of 'sys.stdin.read', because otherwise the
        # user will need to hit 'Ctrl-D' more than once if they're inputting
        # the program by hand. 'raw_input' throws an EOFError exception if
        # 'Ctrl-D' is pressed, which makes it easy to bail out of this loop.
        original_source.append(py3compat.raw_input())
      except EOFError:
        break
    sys.stdout.write(yapf_api.FormatCode(
        py3compat.unicode('\n'.join(original_source) + '\n'),
        filename='<stdin>',
        style_config=args.style,
        lines=lines,
        verify=args.verify))
    return 0

  files = file_resources.GetCommandLineFiles(args.files, args.recursive)
  if not files:
    raise YapfError('Input filenames did not match any python files')
  reformatted = FormatFiles(files, lines,
                            style_config=args.style,
                            in_place=args.in_place,
                            print_diff=args.diff or args.check,
                            verify=args.verify)

  if args.check and reformatted:
      return 3

  return 0


def FormatFiles(filenames, lines,
                style_config=None,
                in_place=False,
                print_diff=False,
                verify=True):
  """Format a list of files.

  Arguments:
    filenames: (list of unicode) A list of files to reformat.
    lines: (list of tuples of integers) A list of tuples of lines, [start, end],
      that we want to format. The lines are 1-based indexed. This argument
      overrides the 'args.lines'. It can be used by third-party code (e.g.,
      IDEs) when reformatting a snippet of code.
    style_config: (string) Style name or file path.
    in_place: (bool) Modify the files in place.
    print_diff: (bool) Instead of returning the reformatted source, return a
      diff that turns the formatted source into reformatter source.
    verify: (bool) True if reformatted code should be verified for syntax.

  Returns:
    True if at least one file had been reformatted, False if no file could be
  """
  file_reformatted = False
  for filename in filenames:
    logging.info('Reformatting %s', filename)
    try:
      reformatted_code, encoding = yapf_api.FormatFile(
          filename, style_config=style_config, lines=lines,
          print_diff=print_diff, verify=verify)
    except SyntaxError as e:
      e.filename = filename
      raise
    if reformatted_code is not None:
      file_resources.WriteReformattedCode(filename, reformatted_code, in_place,
                                          encoding)
      file_reformatted = True
  return file_reformatted


def _GetLines(line_strings):
  """Parses the start and end lines from a line string like 'start-end'.

  Arguments:
    line_strings: (array of string) A list of strings representing a line
      range like 'start-end'.

  Returns:
    A list of tuples of the start and end line numbers.

  Raises:
    ValueError: If the line string failed to parse or was an invalid line range.
  """
  lines = []
  for line_string in line_strings:
    # The 'list' here is needed by Python 3.
    line = list(map(int, line_string.split('-', 1)))
    if line[0] < 1:
      raise ValueError('invalid start of line range: %r' % line)
    if line[0] > line[1]:
      raise ValueError('end comes before start in line range: %r', line)
    lines.append(tuple(line))
  return lines


def run_main():  # pylint: disable=invalid-name
  sys.exit(main(sys.argv))


if __name__ == '__main__':
  run_main()
