# Copyright 2004-2005 Elemental Security, Inc. All Rights Reserved.
# Licensed to PSF under a Contributor Agreement.

# Modifications:
# Copyright 2006 Google, Inc. All Rights Reserved.
# Licensed to PSF under a Contributor Agreement.
"""Parser driver.

This provides a high-level interface to parse a file into a syntax tree.

"""

__author__ = 'Guido van Rossum <guido@python.org>'

__all__ = ['Driver', 'load_grammar']

import hashlib
import io
import logging
import os
import pkgutil
import sys
# Python imports
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from typing import Dict
from typing import Iterator
from typing import List

from platformdirs import user_cache_dir

from yapf._version import __version__ as yapf_version

# Pgen imports
from . import grammar
from . import parse
from . import pgen
from . import token
from . import tokenize


@dataclass
class _Lookahead:
  """An independent cursor for one speculative parser invocation."""

  start: int
  next_position: int


class TokenProxy:
  """Buffer unread tokens once, independently of speculative parser cursors.

  A release scope observes tokens without consuming the main iterator. Nested
  scopes start after the token most recently observed by their parent, and
  returning from a nested scope restores the parent's cursor. All scopes share
  the same indexed buffer, so competing parser routes see identical tokens.
  Committed tokens are discarded immediately rather than retaining and scanning
  one release record for every soft keyword in the input.
  """

  def __init__(self, generator: Any) -> None:
    self._tokens = iter(generator)
    self._position = 0
    self._read_position = 0
    self._buffer: Dict[int, Any] = {}
    self._lookahead: List[_Lookahead] = []

  def _get(self, position: int) -> Any:
    while self._read_position <= position:
      self._buffer[self._read_position] = next(self._tokens)
      self._read_position += 1
    return self._buffer[position]

  @contextmanager
  def release(self) -> Iterator['TokenProxy']:
    start = (
        self._lookahead[-1].next_position
        if self._lookahead else self._position)
    self._lookahead.append(_Lookahead(start, start))
    try:
      yield self
    finally:
      self._lookahead.pop()

  def eat(self, point: int) -> Any:
    if point < 0:
      raise IndexError('lookahead offset must be nonnegative')
    scope = self._lookahead[-1]
    position = scope.start + point
    value = self._get(position)
    scope.next_position = position + 1
    return value

  def __iter__(self) -> 'TokenProxy':
    return self

  def __next__(self) -> Any:
    value = self._get(self._position)
    del self._buffer[self._position]
    self._position += 1
    return value

  def can_advance(self, to: int) -> bool:
    try:
      self.eat(to)
    except StopIteration:
      return False
    return True


class Driver(object):

  def __init__(self, grammar, convert=None, logger=None):
    self.grammar = grammar
    if logger is None:
      logger = logging.getLogger()
    self.logger = logger
    self.convert = convert

  def parse_tokens(self, tokens, debug=False):
    """Parse a series of tokens and return the syntax tree."""
    # XXX Move the prefix computation into a wrapper around tokenize.
    p = parse.Parser(self.grammar, self.convert)
    proxy = TokenProxy(tokens)
    p.setup(proxy=proxy)
    lineno = 1
    column = 0
    type = value = start = end = line_text = None
    prefix = ''
    for quintuple in proxy:
      type, value, start, end, line_text = quintuple
      if start != (lineno, column):
        assert (lineno, column) <= start, ((lineno, column), start)
        s_lineno, s_column = start
        if lineno < s_lineno:
          prefix += '\n' * (s_lineno - lineno)
          lineno = s_lineno
          column = 0
        if column < s_column:
          prefix += line_text[column:s_column]
          column = s_column
      if type in (tokenize.COMMENT, tokenize.NL):
        prefix += value
        lineno, column = end
        if value.endswith('\n'):
          lineno += 1
          column = 0
        continue
      if type == token.OP:
        type = grammar.opmap[value]
      if debug:
        self.logger.debug('%s %r (prefix=%r)', token.tok_name[type], value,
                          prefix)
      if p.addtoken(type, value, (prefix, start)):
        if debug:
          self.logger.debug('Stop.')
        break
      prefix = ''
      lineno, column = end
      if value.endswith('\n'):
        lineno += 1
        column = 0
    else:
      # We never broke out -- EOF is too soon (how can this happen???)
      raise parse.ParseError('incomplete input', type, value, (prefix, start))
    return p.rootnode

  def parse_stream_raw(self, stream, debug=False):
    """Parse a stream and return the syntax tree."""
    tokens = tokenize.generate_tokens(stream.readline)
    return self.parse_tokens(tokens, debug)

  def parse_stream(self, stream, debug=False):
    """Parse a stream and return the syntax tree."""
    return self.parse_stream_raw(stream, debug)

  def parse_file(self, filename, encoding=None, debug=False):
    """Parse a file and return the syntax tree."""
    with io.open(filename, 'r', encoding=encoding) as stream:
      return self.parse_stream(stream, debug)

  def parse_string(self, text, debug=False):
    """Parse a string and return the syntax tree."""
    tokens = tokenize.generate_tokens(io.StringIO(text).readline)
    return self.parse_tokens(tokens, debug)


def _generate_pickle_name(gt, source=None):
  # type:(str, bytes | None) -> str
  """Get the filepath to write a pickle file to
  given the path of a grammar textfile.

  The returned filepath should be in a user-specific cache directory.

  Args:
      gt (str): path to grammar text file
      source (bytes): optional source snapshot used to isolate cache entries

  Returns:
      str: path to pickle file
  """

  grammar_textfile_name = os.path.basename(gt)
  head, tail = os.path.splitext(grammar_textfile_name)
  if tail == '.txt':
    tail = ''
  if source is not None:
    head += '-' + hashlib.sha256(source).hexdigest()
  cache_dir = user_cache_dir(
      appname='YAPF', appauthor='Google', version=yapf_version)
  return cache_dir + os.sep + head + tail + '-py' + '.'.join(
      map(str, sys.version_info)) + '.pickle'


def load_grammar(gt='Grammar.txt',
                 gp=None,
                 save=True,
                 force=False,
                 logger=None):
  # type:(str, str | None, bool, bool, logging.Logger | None) -> grammar.Grammar
  """Load the grammar (maybe from a pickle)."""
  if logger is None:
    logger = logging.getLogger()
  # Different checkouts can have the same package/interpreter version and
  # file timestamps, but different grammars. Key the cache by the source,
  # and parse the same snapshot so no checkout can reuse another's grammar.
  try:
    with open(gt, 'rb') as source_file:
      source = source_file.read()
  except FileNotFoundError:
    gt_basename = os.path.basename(gt)
    source = pkgutil.get_data('yapf_third_party._ylib2to3', gt_basename)
    if source is None:
      raise RuntimeError('Failed to load grammar %s from package' % gt_basename)
  gp = _generate_pickle_name(gt, source) if gp is None else gp
  grammar_text = io.StringIO(source.decode(encoding='utf-8'))
  try:
    newer = _newer(gp, gt)
  except OSError as err:
    logger.debug('OSError, could not check if newer: %s', err.args)
    newer = True
  if force or not newer:
    g = pgen.generate_grammar(grammar_text)
    if save:
      try:
        Path(gp).parent.mkdir(parents=True, exist_ok=True)
        g.dump(gp)
      except OSError:
        # Ignore error, caching is not vital.
        pass
  else:
    g = grammar.Grammar()
    g.load(gp)
  return g


def _newer(a, b):
  """Inquire whether file a was written since file b."""
  if not os.path.exists(a):
    return False
  if not os.path.exists(b):
    return True
  return os.path.getmtime(a) >= os.path.getmtime(b)


def load_packaged_grammar(package, grammar_source):
  """Normally, loads a pickled grammar by doing
        pkgutil.get_data(package, pickled_grammar)
    where *pickled_grammar* is computed from *grammar_source* by adding the
    Python version and using a ``.pickle`` extension.

    However, if *grammar_source* is an extant file, load_grammar(grammar_source)
    is called instead. This facilitates using a packaged grammar file when needed
    but preserves load_grammar's automatic regeneration behavior when possible.

    """  # noqa: E501
  if os.path.isfile(grammar_source):
    return load_grammar(grammar_source)
  pickled_name = _generate_pickle_name(os.path.basename(grammar_source))
  data = pkgutil.get_data(package, pickled_name)
  g = grammar.Grammar()
  g.loads(data)
  return g


def main(*args):
  """Main program, when run as a script: produce grammar pickle files.

    Calls load_grammar for each argument, a path to a grammar text file.
    """
  if not args:
    args = sys.argv[1:]
  logging.basicConfig(
      level=logging.INFO, stream=sys.stdout, format='%(message)s')
  for gt in args:
    load_grammar(gt, save=True, force=True)
  return True


if __name__ == '__main__':
  sys.exit(int(not main()))
