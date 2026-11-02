# Copyright (c) 2001, 2002, 2003, 2004, 2005, 2006 Python Software Foundation.
# All rights reserved.
"""Tokenization help for Python programs.

generate_tokens(readline) is a generator that breaks a stream of
text into Python tokens.  It accepts a readline-like method which is called
repeatedly to get the next line of input (or "" for EOF).  It generates
5-tuples with these members:

    the token type (see token.py)
    the token (a string)
    the starting (row, column) indices of the token (a 2-tuple of ints)
    the ending (row, column) indices of the token (a 2-tuple of ints)
    the original line (string)

It is designed to match the working of the Python tokenizer exactly, except
that it produces COMMENT tokens for comments and gives type OP for all
operators

Older entry points
    tokenize_loop(readline, tokeneater)
    tokenize(readline, tokeneater=printtoken)
are the same, except instead of generating tokens, tokeneater is a callback
function to which the 5 fields described above are passed as 5 arguments,
each time a new token is found."""

__author__ = 'Ka-Ping Yee <ping@lfw.org>'
__credits__ = \
    'GvR, ESR, Tim Peters, Thomas Wouters, Fred Drake, Skip Montanaro'

import keyword
import re
import string
from codecs import BOM_UTF8
from codecs import lookup

from . import token
from .token import ASYNC
from .token import AWAIT
from .token import COMMENT
from .token import DEDENT
from .token import ENDMARKER
from .token import ERRORTOKEN
from .token import INDENT
from .token import NAME
from .token import NEWLINE
from .token import NL
from .token import NUMBER
from .token import OP
from .token import STRING
from .token import tok_name

__all__ = [x for x in dir(token) if x[0] != '_'
          ] + ['tokenize', 'generate_tokens', 'untokenize']
del token

try:
  bytes
except NameError:
  # Support bytes type in Python <= 2.5, so 2to3 turns itself into
  # valid Python 3 code.
  bytes = str


def group(*choices):
  return '(' + '|'.join(choices) + ')'


def any(*choices):
  return group(*choices) + '*'


def maybe(*choices):
  return group(*choices) + '?'


def _combinations(*l):  # noqa: E741
  return set(
      x + y for x in l for y in l + ('',) if x.casefold() != y.casefold())


Whitespace = r'[ \f\t]*'
Comment = r'#[^\r\n]*'
Ignore = Whitespace + any(r'\\\r?\n' + Whitespace) + maybe(Comment)
Name = r'\w+'

Binnumber = r'0[bB]_?[01]+(?:_[01]+)*'
Hexnumber = r'0[xX]_?[\da-fA-F]+(?:_[\da-fA-F]+)*[lL]?'
Octnumber = r'0[oO]?_?[0-7]+(?:_[0-7]+)*[lL]?'
Decnumber = group(r'[1-9]\d*(?:_\d+)*[lL]?', '0[lL]?')
Intnumber = group(Binnumber, Hexnumber, Octnumber, Decnumber)
Exponent = r'[eE][-+]?\d+(?:_\d+)*'
Pointfloat = group(r'\d+(?:_\d+)*\.(?:\d+(?:_\d+)*)?',
                   r'\.\d+(?:_\d+)*') + maybe(Exponent)
Expfloat = r'\d+(?:_\d+)*' + Exponent
Floatnumber = group(Pointfloat, Expfloat)
Imagnumber = group(r'\d+(?:_\d+)*[jJ]', Floatnumber + r'[jJ]')
Number = group(Imagnumber, Floatnumber, Intnumber)

# Tail end of ' string.
Single = r"[^'\\]*(?:\\.[^'\\]*)*'"
# Tail end of " string.
Double = r'[^"\\]*(?:\\.[^"\\]*)*"'
# Tail end of ''' string.
Single3 = r"[^'\\]*(?:(?:\\.|'(?!''))[^'\\]*)*'''"
# Tail end of """ string.
Double3 = r'[^"\\]*(?:(?:\\.|"(?!""))[^"\\]*)*"""'
_litprefix = r'(?:[uUrRbBfF]|[rR][fFbB]|[fFbBuU][rR])?'
Triple = group(_litprefix + "'''", _litprefix + '"""')
# Single-line ' or " string.
String = group(_litprefix + r"'[^\n'\\]*(?:\\.[^\n'\\]*)*'",
               _litprefix + r'"[^\n"\\]*(?:\\.[^\n"\\]*)*"')

# Because of leftmost-then-longest match semantics, be sure to put the
# longest operators first (e.g., if = came before ==, == would get
# recognized as two instances of =).
Operator = group(r'\*\*=?', r'>>=?', r'<<=?', r'<>', r'!=', r'//=?', r'->',
                 r'[+\-*/%&@|^=<>]=?', r'~')

Bracket = '[][(){}]'
Special = group(r'\r?\n', r':=', r'[:;.,`@]')
Funny = group(Operator, Bracket, Special)

PlainToken = group(Number, Funny, String, Name)
Token = Ignore + PlainToken

# First (or only) line of ' or " string.
ContStr = group(
    _litprefix + r"'[^\n'\\]*(?:\\.[^\n'\\]*)*" + group("'", r'\\\r?\n'),
    _litprefix + r'"[^\n"\\]*(?:\\.[^\n"\\]*)*' + group('"', r'\\\r?\n'))
PseudoExtras = group(r'\\\r?\n', Comment, Triple)
PseudoToken = Whitespace + group(PseudoExtras, Number, Funny, ContStr, Name)

tokenprog, pseudoprog, single3prog, double3prog = map(
    re.compile, (Token, PseudoToken, Single3, Double3))

_strprefixes = (
    _combinations('r', 'R', 'f', 'F') | _combinations('r', 'R', 'b', 'B')
    | {'u', 'U', 'ur', 'uR', 'Ur', 'UR'})

endprogs = {
    "'": re.compile(Single),
    '"': re.compile(Double),
    "'''": single3prog,
    '"""': double3prog,
    **{
        f"{prefix}'''": single3prog for prefix in _strprefixes
    },
    **{
        f'{prefix}"""': double3prog for prefix in _strprefixes
    },
    **{
        prefix: None for prefix in _strprefixes
    }
}

triple_quoted = ({"'''", '"""'} | {f"{prefix}'''" for prefix in _strprefixes}
                 | {f'{prefix}"""' for prefix in _strprefixes})
single_quoted = ({"'", '"'} | {f"{prefix}'" for prefix in _strprefixes}
                 | {f'{prefix}"' for prefix in _strprefixes})

ftstringprog = re.compile(r'[ \f\t]*((?:[fFtT][rR]?|[rR][fFtT])[\'"])')
_identifier_char = re.compile(r'\w', re.UNICODE)
_whitespace = re.compile(r'[ \f\t]*')
_await_operand = re.compile(r'[ \f\t]*(?:[0-9\'"{(\[]|\.\.\.|\.[0-9]|(\w+))',
                            re.UNICODE)
_async_continuation = re.compile(r'[ \f\t]*(def|for|with)\b')
_line_end = re.compile(r'[ \f\t]*(?:#[^\r\n]*)?\r?$')
_await_operand_keywords = frozenset({'None', 'True', 'False', 'await'})


def _identifier_end(line, start):
  end = start + 1
  while end < len(line) and line[start:end + 1].isidentifier():
    end += 1
  return end


def _starts_await_operand(line, pos):
  match = _await_operand.match(line, pos)
  if not match:
    return False
  word = match.group(1)
  return (word is None or not keyword.iskeyword(word) or
          word in _await_operand_keywords)


tabsize = 8


def _indented_after_continuation(peek_line):
  index = 0
  while True:
    line = peek_line(index)
    if not line:
      return False
    column = 0
    for char in line:
      if char == ' ':
        column += 1
      elif char == '\t':
        column = (column // tabsize + 1) * tabsize
      elif char == '\f':
        column = 0
      else:
        break
    rest = line.lstrip(' \t\f')
    if rest and rest[0] not in '#\\\r\n':
      return column > 0
    if rest[:1] == '\\' and column > 0:
      return True
    index += 1


class TokenError(Exception):
  pass


class StopTokenizing(Exception):
  pass


class _FTStringMode:

  def __init__(self, quote, quote_size, raw):
    self.quote = quote
    self.quote_size = quote_size
    self.raw = raw
    self.in_expr = False
    self.in_format_spec = False
    self.depth = 0
    self.expr_depth = -1


class _FTStringScanner:

  def __init__(self, line, start, lnum, readline):
    self.text = line
    self.lines = [line]
    self.pos = start
    self.start = start
    self.strstart = (lnum, start)
    self.readline = readline
    self.eof = False

  def _char(self, index):
    while index >= len(self.text):
      if self.eof or not self.text.endswith('\n'):
        return ''
      try:
        line = self.readline()
      except StopIteration:
        line = ''
      if not line:
        self.eof = True
        return ''
      self.text += line
      self.lines.append(line)
    return self.text[index]

  def _next(self):
    char = self._char(self.pos)
    if char:
      self.pos += 1
    return char

  def _error(self):
    raise TokenError('EOF in multi-line string', self.strstart)

  def _push(self, modes, prefix):
    quote = self._next()
    quote_size = 1
    if self._char(self.pos) == quote and self._char(self.pos + 1) == quote:
      self.pos += 2
      quote_size = 3
    modes.append(_FTStringMode(quote, quote_size, 'r' in prefix.lower()))

  def _skip_string(self):
    quote = self._next()
    quote_size = 1
    if self._char(self.pos) == quote:
      if self._char(self.pos + 1) == quote:
        self.pos += 2
        quote_size = 3
      else:
        self.pos += 1
        return
    end_quote_size = 0
    while end_quote_size != quote_size:
      char = self._next()
      if not char or (quote_size == 1 and char == '\n'):
        self._error()
      if char == quote:
        end_quote_size += 1
        continue
      end_quote_size = 0
      if char == '\\' and self._next() == '\r':
        self._next()

  def _literal_step(self, modes):
    mode = modes[-1]
    if self._char(self.pos) == '{' and self._char(self.pos + 1) != '{':
      mode.expr_depth += 1
      mode.in_expr = True
      return
    if all(
        self._char(self.pos + i) == mode.quote for i in range(mode.quote_size)):
      self.pos += mode.quote_size
      modes.pop()
      return
    end_quote_size = 0
    unicode_escape = False
    while end_quote_size != mode.quote_size:
      char = self._next()
      in_format_spec = mode.in_format_spec and mode.expr_depth >= 0
      if not char or (mode.quote_size == 1 and char == '\n'):
        self._error()
      if char == mode.quote:
        end_quote_size += 1
        continue
      end_quote_size = 0
      if char == '{':
        if self._char(self.pos) != '{' or in_format_spec:
          self.pos -= 1
          mode.expr_depth += 1
          mode.in_expr = True
          mode.in_format_spec = False
        else:
          self.pos += 1
        return
      if char == '}':
        if unicode_escape:
          return
        if (self._char(self.pos) == '}' and not in_format_spec and
            mode.depth == 0):
          self.pos += 1
        else:
          self.pos -= 1
          mode.in_expr = True
          mode.in_format_spec = False
        return
      if char == '\\':
        peek = self._next()
        if peek == '\r':
          peek = self._next()
        if peek in ('{', '}'):
          self.pos -= 1
        elif peek == 'N' and not mode.raw:
          if self._char(self.pos) == '{':
            self.pos += 1
            unicode_escape = True
    modes.pop()

  def _expr_step(self, modes):
    mode = modes[-1]
    while self._char(self.pos) in (' ', '\t', '\f'):
      self.pos += 1
    char = self._next()
    if not char:
      self._error()
    if char == '#':
      while self._char(self.pos) not in ('', '\n', '\r'):
        self.pos += 1
      return
    if char == '\\':
      if self._next() == '\r':
        self._next()
      return
    if _identifier_char.match(char):
      word_start = self.pos - 1
      while _identifier_char.match(self._char(self.pos) or ' '):
        self.pos += 1
      word = self.text[word_start:self.pos].lower()
      if (self._char(self.pos) in ('"', "'") and len(set(word)) == len(word) and
          set(word) <= set('bruft')):
        if 'f' in word or 't' in word:
          self._push(modes, word)
        else:
          self._skip_string()
      return
    if char in ('"', "'"):
      self.pos -= 1
      self._skip_string()
      return
    if char == ':' and mode.depth - 1 == mode.expr_depth:
      mode.in_expr = False
      mode.in_format_spec = True
      return
    if char in '([{':
      mode.depth += 1
    elif char in ')]}':
      mode.depth -= 1
      if char == '}' and mode.depth == mode.expr_depth:
        mode.expr_depth -= 1
        mode.in_expr = False
        mode.in_format_spec = False

  def scan(self):
    modes = []
    while self._char(self.pos) not in ('"', "'"):
      self.pos += 1
    self._push(modes, self.text[self.start:self.pos])
    while modes:
      if modes[-1].in_expr:
        self._expr_step(modes)
      else:
        self._literal_step(modes)
    assert self.text.count('\n', 0, self.pos) == len(self.lines) - 1
    column = self.pos - (self.text.rfind('\n', 0, self.pos) + 1)
    return self.text[self.start:self.pos], self.lines, column


def printtoken(type, token, xxx_todo_changeme, xxx_todo_changeme1,
               line):  # for testing
  (srow, scol) = xxx_todo_changeme
  (erow, ecol) = xxx_todo_changeme1
  print('%d,%d-%d,%d:\t%s\t%s' %
        (srow, scol, erow, ecol, tok_name[type], repr(token)))


def tokenize(readline, tokeneater=printtoken):
  """
    The tokenize() function accepts two parameters: one representing the
    input stream, and one providing an output mechanism for tokenize().

    The first parameter, readline, must be a callable object which provides
    the same interface as the readline() method of built-in file objects.
    Each call to the function should return one line of input as a string.

    The second parameter, tokeneater, must also be a callable object. It is
    called once for each token, with five arguments, corresponding to the
    tuples generated by generate_tokens().
    """
  try:
    tokenize_loop(readline, tokeneater)
  except StopTokenizing:
    pass


# backwards compatible interface
def tokenize_loop(readline, tokeneater):
  for token_info in generate_tokens(readline):
    tokeneater(*token_info)


class Untokenizer:

  def __init__(self):
    self.tokens = []
    self.prev_row = 1
    self.prev_col = 0

  def add_whitespace(self, start):
    row, col = start
    assert row <= self.prev_row
    col_offset = col - self.prev_col
    if col_offset:
      self.tokens.append(' ' * col_offset)

  def untokenize(self, iterable):
    for t in iterable:
      if len(t) == 2:
        self.compat(t, iterable)
        break
      tok_type, token, start, end, line = t
      self.add_whitespace(start)
      self.tokens.append(token)
      self.prev_row, self.prev_col = end
      if tok_type in (NEWLINE, NL):
        self.prev_row += 1
        self.prev_col = 0
    return ''.join(self.tokens)

  def compat(self, token, iterable):
    startline = False
    indents = []
    toks_append = self.tokens.append
    toknum, tokval = token
    if toknum in (NAME, NUMBER):
      tokval += ' '
    if toknum in (NEWLINE, NL):
      startline = True
    for tok in iterable:
      toknum, tokval = tok[:2]

      if toknum in (NAME, NUMBER, ASYNC, AWAIT):
        tokval += ' '

      if toknum == INDENT:
        indents.append(tokval)
        continue
      elif toknum == DEDENT:
        indents.pop()
        continue
      elif toknum in (NEWLINE, NL):
        startline = True
      elif startline and indents:
        toks_append(indents[-1])
        startline = False
      toks_append(tokval)


cookie_re = re.compile(r'^[ \t\f]*#.*?coding[:=][ \t]*([-\w.]+)', re.ASCII)
blank_re = re.compile(br'^[ \t\f]*(?:[#\r\n]|$)', re.ASCII)


def _get_normal_name(orig_enc):
  """Imitates get_normal_name in tokenizer.c."""
  # Only care about the first 12 characters.
  enc = orig_enc[:12].lower().replace('_', '-')
  if enc == 'utf-8' or enc.startswith('utf-8-'):
    return 'utf-8'
  if enc in ('latin-1', 'iso-8859-1', 'iso-latin-1') or \
     enc.startswith(('latin-1-', 'iso-8859-1-', 'iso-latin-1-')):
    return 'iso-8859-1'
  return orig_enc


def detect_encoding(readline):
  """
    The detect_encoding() function is used to detect the encoding that should
    be used to decode a Python source file. It requires one argument, readline,
    in the same way as the tokenize() generator.

    It will call readline a maximum of twice, and return the encoding used
    (as a string) and a list of any lines (left as bytes) it has read
    in.

    It detects the encoding from the presence of a utf-8 bom or an encoding
    cookie as specified in pep-0263. If both a bom and a cookie are present, but
    disagree, a SyntaxError will be raised. If the encoding cookie is an invalid
    charset, raise a SyntaxError.  Note that if a utf-8 bom is found,
    'utf-8-sig' is returned.

    If no encoding is specified, then the default of 'utf-8' will be returned.
    """
  bom_found = False
  encoding = None
  default = 'utf-8'

  def read_or_stop():
    try:
      return readline()
    except StopIteration:
      return bytes()

  def find_cookie(line):
    try:
      line_string = line.decode('ascii')
    except UnicodeDecodeError:
      return None
    match = cookie_re.match(line_string)
    if not match:
      return None
    encoding = _get_normal_name(match.group(1))
    try:
      codec = lookup(encoding)
    except LookupError:
      # This behaviour mimics the Python interpreter
      raise SyntaxError('unknown encoding: ' + encoding)

    if bom_found:
      if codec.name != 'utf-8':
        # This behaviour mimics the Python interpreter
        raise SyntaxError('encoding problem: utf-8')
      encoding += '-sig'
    return encoding

  first = read_or_stop()
  if first.startswith(BOM_UTF8):
    bom_found = True
    first = first[3:]
    default = 'utf-8-sig'
  if not first:
    return default, []

  encoding = find_cookie(first)
  if encoding:
    return encoding, [first]
  if not blank_re.match(first):
    return default, [first]

  second = read_or_stop()
  if not second:
    return default, [first]

  encoding = find_cookie(second)
  if encoding:
    return encoding, [first, second]

  return default, [first, second]


def untokenize(iterable):
  """Transform tokens back into Python source code.

    Each element returned by the iterable must be a token sequence
    with at least two elements, a token number and token value.  If
    only two tokens are passed, the resulting output is poor.

    Round-trip invariant for full input:
        Untokenized source will match input source exactly

    Round-trip invariant for limited input:
        # Output text will tokenize the back to the input
        t1 = [tok[:2] for tok in generate_tokens(f.readline)]
        newcode = untokenize(t1)
        readline = iter(newcode.splitlines(1)).next
        t2 = [tok[:2] for tokin generate_tokens(readline)]
        assert t1 == t2
    """
  ut = Untokenizer()
  return ut.untokenize(iterable)


def generate_tokens(readline):
  """
    The generate_tokens() generator requires one argument, readline, which
    must be a callable object which provides the same interface as the
    readline() method of built-in file objects. Each call to the function
    should return one line of input as a string.  Alternately, readline
    can be a callable function terminating with StopIteration:
        readline = open(myfile).next    # Example of alternate readline

    The generator produces 5-tuples with these members: the token type; the
    token string; a 2-tuple (srow, scol) of ints specifying the row and
    column where the token begins in the source; a 2-tuple (erow, ecol) of
    ints specifying the row and column where the token ends in the source;
    and the line on which the token was found. The line passed is the
    physical line.
    """
  strstart = ''
  endprog = ''
  lnum = parenlev = continued = 0
  cont_column = None
  cont_indent = ''
  after_comment = False
  contstr, needcont = '', 0
  contline = None
  indents = [0]

  # 'stashed' and 'async_*' are used for async/await parsing
  stashed = None
  async_def = False
  async_def_indent = 0
  async_def_nl = False
  lookahead = []

  def next_line():
    if lookahead:
      return lookahead.pop(0)
    try:
      return readline()
    except StopIteration:
      return ''

  def peek_line(index):
    while len(lookahead) <= index:
      if lookahead and not lookahead[-1]:
        return ''
      try:
        lookahead.append(readline())
      except StopIteration:
        lookahead.append('')
    return lookahead[index]

  while 1:  # loop over lines in stream
    line = next_line()
    lnum = lnum + 1
    pos, max = 0, len(line)

    if contstr:  # continued string
      if not line:
        raise TokenError('EOF in multi-line string', strstart)
      endmatch = endprog.match(line)
      if endmatch:
        pos = end = endmatch.end(0)
        yield (STRING, contstr + line[:end], strstart, (lnum, end),
               contline + line)
        contstr, needcont = '', 0
        contline = None
      elif needcont and line[-2:] != '\\\n' and line[-3:] != '\\\r\n':
        yield (ERRORTOKEN, contstr + line, strstart, (lnum, len(line)),
               contline)
        contstr = ''
        contline = None
        continue
      else:
        contstr = contstr + line
        contline = contline + line
        continue

    elif parenlev == 0 and not continued:  # new statement
      if not line:
        if cont_column is not None:
          raise TokenError('EOF in multi-line statement', (lnum, 0))
        break
      column = 0
      while pos < max:  # measure leading whitespace
        if line[pos] == ' ':
          column = column + 1
        elif line[pos] == '\t':
          column = (column // tabsize + 1) * tabsize
        elif line[pos] == '\f':
          column = 0
        else:
          break
        pos = pos + 1
      if pos == max:
        break
      form_feed_end = line.rfind('\f', 0, pos) + 1
      if form_feed_end:
        line = line[form_feed_end:]
        pos, max = pos - form_feed_end, max - form_feed_end

      if stashed:
        yield stashed
        stashed = None

      if (line[pos:] in ('\\\n', '\\\r\n') and
          (column or cont_column is not None or after_comment or
           indents[-1] > 0 or _indented_after_continuation(peek_line))):
        if not cont_column:
          cont_indent = line[:pos]
        cont_column = cont_column or column
        continue

      if line[pos] in '#\r\n':  # skip comments or blank lines
        cont_column = None
        if line[pos] == '#':
          after_comment = True
          comment_token = line[pos:].rstrip('\r\n')
          nl_pos = pos + len(comment_token)
          yield (COMMENT, comment_token, (lnum, pos),
                 (lnum, pos + len(comment_token)), line)
          yield (NL, line[nl_pos:], (lnum, nl_pos), (lnum, len(line)), line)
        else:
          yield ((NL, COMMENT)[line[pos] == '#'], line[pos:], (lnum, pos),
                 (lnum, len(line)), line)
        continue

      indent = cont_indent if cont_column else line[:pos]
      column = cont_column or column
      cont_column = None
      after_comment = False
      if column > indents[-1]:  # count indents or dedents
        indents.append(column)
        yield (INDENT, indent, (lnum, 0), (lnum, pos), line)
      while column < indents[-1]:
        if column not in indents:
          raise IndentationError(
              'unindent does not match any outer indentation level',
              ('<tokenize>', lnum, pos, line))
        indents = indents[:-1]

        if async_def and async_def_indent >= indents[-1]:
          async_def = False
          async_def_nl = False
          async_def_indent = 0

        yield (DEDENT, '', (lnum, pos), (lnum, pos), line)

      if async_def and async_def_nl and async_def_indent >= indents[-1]:
        async_def = False
        async_def_nl = False
        async_def_indent = 0

    else:  # continued statement
      if not line:
        raise TokenError('EOF in multi-line statement', (lnum, 0))
      continued = 0

    while pos < max:
      ftstringmatch = ftstringprog.match(line, pos)
      if ftstringmatch:
        start = ftstringmatch.start(1)
        spos = (lnum, start)
        scanner = _FTStringScanner(line, start, lnum, next_line)
        token, lines, pos = scanner.scan()
        lnum += len(lines) - 1
        line = lines[-1]
        max = len(line)
        if stashed:
          yield stashed
          stashed = None
        yield (STRING, token, spos, (lnum, pos), ''.join(lines))
        continue

      pseudomatch = pseudoprog.match(line, pos)
      if pseudomatch:  # scan for tokens
        start, end = pseudomatch.span(1)
        spos, epos, pos = (lnum, start), (lnum, end), end
        token, initial = line[start:end], line[start]

        if initial in string.digits or \
           (initial == '.' and token != '.'):      # ordinary number
          yield (NUMBER, token, spos, epos, line)
        elif initial in '\r\n':
          newline = NEWLINE
          if parenlev > 0:
            newline = NL
          elif async_def:
            async_def_nl = True
          if stashed:
            yield stashed
            stashed = None
          yield (newline, token, spos, epos, line)

        elif initial == '#':
          assert not token.endswith('\n')
          if stashed:
            yield stashed
            stashed = None
          yield (COMMENT, token, spos, epos, line)
        elif token in triple_quoted:
          endprog = endprogs[token]
          endmatch = endprog.match(line, pos)
          if endmatch:  # all on one line
            pos = endmatch.end(0)
            token = line[start:pos]
            if stashed:
              yield stashed
              stashed = None
            yield (STRING, token, spos, (lnum, pos), line)
          else:
            strstart = (lnum, start)  # multiple lines
            contstr = line[start:]
            contline = line
            break
        elif initial in single_quoted or \
            token[:2] in single_quoted or \
            token[:3] in single_quoted:
          if token[-1] == '\n':  # continued string
            strstart = (lnum, start)  # noqa: F841
            endprog = (
                endprogs[initial] or endprogs[token[1]] or endprogs[token[2]])
            contstr, needcont = line[start:], 1
            contline = line
            break
          else:  # ordinary string
            if stashed:
              yield stashed
              stashed = None
            yield (STRING, token, spos, epos, line)
        elif initial.isidentifier():  # ordinary name
          if pos < max and line[pos] > '\x7f':
            pos = _identifier_end(line, start)
            token, epos = line[start:pos], (lnum, pos)
          if token in ('async', 'await'):
            if async_def:
              yield (ASYNC if token == 'async' else AWAIT, token, spos, epos,
                     line)
              continue
            if token == 'await' and _starts_await_operand(line, pos):
              if stashed:
                yield stashed
                stashed = None
              yield (AWAIT, token, spos, epos, line)
              continue

          tok = (NAME, token, spos, epos, line)
          if token == 'async' and parenlev > 0 and _line_end.match(line, pos):
            if stashed:
              yield stashed
              stashed = None
            yield (ASYNC, token, spos, epos, line)
            continue
          if token == 'async' and not stashed:
            stashed = tok
            continue

          if token in ('def', 'for', 'with'):
            if (stashed and stashed[0] == NAME and stashed[1] == 'async'):

              if token == 'def':
                async_def = True
                async_def_indent = indents[-1]

              yield (ASYNC, stashed[1], stashed[2], stashed[3], stashed[4])
              stashed = None

          if stashed:
            yield stashed
            stashed = None

          yield tok
        elif initial == '\\':  # continued stmt
          if stashed:
            match = _async_continuation.match(peek_line(0))
            if match:
              if match.group(1) == 'def':
                async_def = True
                async_def_indent = indents[-1]
              stashed = (ASYNC,) + stashed[1:]
          # This yield is new; needed for better idempotency:
          if stashed:
            yield stashed
            stashed = None
          yield (NL, token, spos, (lnum, pos), line)
          continued = 1
        else:
          if initial in '([{':
            parenlev = parenlev + 1
          elif initial in ')]}':
            parenlev = parenlev - 1
          if stashed:
            yield stashed
            stashed = None
          yield (OP, token, spos, epos, line)
      else:
        start = _whitespace.match(line, pos).end()
        if line[start:start + 1].isidentifier():
          pos = _identifier_end(line, start)
          if stashed:
            yield stashed
            stashed = None
          yield (NAME, line[start:pos], (lnum, start), (lnum, pos), line)
          continue
        yield (ERRORTOKEN, line[pos], (lnum, pos), (lnum, pos + 1), line)
        pos = pos + 1

  if stashed:
    yield stashed
    stashed = None

  for indent in indents[1:]:  # pop remaining indent levels
    yield (DEDENT, '', (lnum, 0), (lnum, 0), '')
  yield (ENDMARKER, '', (lnum, 0), (lnum, 0), '')


if __name__ == '__main__':  # testing
  import sys
  if len(sys.argv) > 1:
    tokenize(open(sys.argv[1]).readline)
  else:
    tokenize(sys.stdin.readline)
