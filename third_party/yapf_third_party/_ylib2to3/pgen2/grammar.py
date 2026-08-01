# Copyright 2004-2005 Elemental Security, Inc. All Rights Reserved.
# Licensed to PSF under a Contributor Agreement.
"""This module defines the data structures used to represent a grammar.

These are a bit arcane because they are derived from the data
structures used by Python's 'pgen' parser generator.

There's also a table here mapping operators to their names in the
token module; the Python tokenize module reports all operators as the
fallback token code OP, but the parser needs the actual token code.

"""

# Python imports
import os
import pickle
import uuid

# Local imports
from . import token

# Flags for opening the temporary cache file written by ``Grammar.dump``.
# We avoid ``tempfile``/``mkstemp`` here: on Windows, Python's tempfile
# module treats a ``PermissionError`` from ``os.open`` as a possible name
# collision and retries up to ``tempfile.TMP_MAX`` (over two billion) times
# whenever the destination directory exists and ``os.access`` reports it
# writable. That can make this optional cache write hang for a very long
# time instead of failing, e.g. in a restricted-token sandbox where the
# directory exists but file creation is denied. Doing a single, explicit
# ``os.open`` attempt lets a denied write fail immediately.
_TEMPFILE_OPEN_FLAGS = os.O_WRONLY | os.O_CREAT | os.O_EXCL
if hasattr(os, 'O_BINARY'):
  _TEMPFILE_OPEN_FLAGS |= os.O_BINARY
if hasattr(os, 'O_NOINHERIT'):
  _TEMPFILE_OPEN_FLAGS |= os.O_NOINHERIT


class Grammar(object):
  """Pgen parsing tables conversion class.

    Once initialized, this class supplies the grammar tables for the
    parsing engine implemented by parse.py.  The parsing engine
    accesses the instance variables directly.  The class here does not
    provide initialization of the tables; several subclasses exist to
    do this (see the conv and pgen modules).

    The load() method reads the tables from a pickle file, which is
    much faster than the other ways offered by subclasses.  The pickle
    file is written by calling dump() (after loading the grammar
    tables using a subclass).  The report() method prints a readable
    representation of the tables to stdout, for debugging.

    The instance variables are as follows:

    symbol2number -- a dict mapping symbol names to numbers.  Symbol
                     numbers are always 256 or higher, to distinguish
                     them from token numbers, which are between 0 and
                     255 (inclusive).

    number2symbol -- a dict mapping numbers to symbol names;
                     these two are each other's inverse.

    states        -- a list of DFAs, where each DFA is a list of
                     states, each state is a list of arcs, and each
                     arc is a (i, j) pair where i is a label and j is
                     a state number.  The DFA number is the index into
                     this list.  (This name is slightly confusing.)
                     Final states are represented by a special arc of
                     the form (0, j) where j is its own state number.

    dfas          -- a dict mapping symbol numbers to (DFA, first)
                     pairs, where DFA is an item from the states list
                     above, and first is a set of tokens that can
                     begin this grammar rule (represented by a dict
                     whose values are always 1).

    labels        -- a list of (x, y) pairs where x is either a token
                     number or a symbol number, and y is either None
                     or a string; the strings are keywords.  The label
                     number is the index in this list; label numbers
                     are used to mark state transitions (arcs) in the
                     DFAs.

    start         -- the number of the grammar's start symbol.

    keywords      -- a dict mapping keyword strings to arc labels.

    tokens        -- a dict mapping token numbers to arc labels.

    """

  def __init__(self):
    self.symbol2number = {}
    self.number2symbol = {}
    self.states = []
    self.dfas = {}
    self.labels = [(0, 'EMPTY')]
    self.keywords = {}
    self.soft_keywords = {}
    self.tokens = {}
    self.symbol2label = {}
    self.start = 256

  def dump(self, filename):
    """Dump the grammar tables to a pickle file."""
    # NOTE:
    # - We're writing a tempfile first so that there is no chance
    #   for someone to read a half-written file from this very spot
    #   while we're were not done writing.
    # - We're using ``os.rename`` to sure not copy data around (which
    #   would get us back to square one with a reading-half-written file
    #   race condition).
    # - We're making the tempfile go to the same directory as the eventual
    #   target ``filename`` so that there is no chance of failing from
    #   cross-file-system renames in ``os.rename``.
    # - We're using the same prefix and suffix for the tempfile so if we
    #   ever have to leave a tempfile around for failure of deletion,
    #   it will have a reasonable filename extension and its name will help
    #   explain is nature.
    # - We close the tempfile before calling ``os.rename``, since a rename
    #   of a still-open file can fail on Windows.
    tempfile_dir = os.path.dirname(filename) or '.'
    tempfile_prefix, tempfile_suffix = os.path.splitext(
        os.path.basename(filename))
    temp_filename = os.path.join(
        tempfile_dir,
        '{}.{}{}'.format(tempfile_prefix, uuid.uuid4().hex, tempfile_suffix))
    try:
      fd = os.open(temp_filename, _TEMPFILE_OPEN_FLAGS, 0o600)
      with os.fdopen(fd, 'wb') as f:
        pickle.dump(self.__dict__, f, pickle.HIGHEST_PROTOCOL)
      os.rename(temp_filename, filename)
    except OSError:
      # This makes sure that we do not leave the tempfile around
      # unless we have to...
      try:
        os.remove(temp_filename)
      except OSError:
        pass
      raise

  def load(self, filename):
    """Load the grammar tables from a pickle file."""
    with open(filename, 'rb') as f:
      d = pickle.load(f)
    self.__dict__.update(d)

  def loads(self, pkl):
    """Load the grammar tables from a pickle bytes object."""
    self.__dict__.update(pickle.loads(pkl))

  def copy(self):
    """
        Copy the grammar.
        """
    new = self.__class__()
    for dict_attr in ('symbol2number', 'number2symbol', 'dfas', 'keywords',
                      'soft_keywords', 'tokens', 'symbol2label'):
      setattr(new, dict_attr, getattr(self, dict_attr).copy())
    new.labels = self.labels[:]
    new.states = self.states[:]
    new.start = self.start
    return new

  def report(self):
    """Dump the grammar tables to standard output, for debugging."""
    from pprint import pprint
    print('s2n')
    pprint(self.symbol2number)
    print('n2s')
    pprint(self.number2symbol)
    print('states')
    pprint(self.states)
    print('dfas')
    pprint(self.dfas)
    print('labels')
    pprint(self.labels)
    print('start', self.start)


# Map from operator to number (since tokenize doesn't do this)

opmap_raw = """
( LPAR
) RPAR
[ LSQB
] RSQB
: COLON
, COMMA
; SEMI
+ PLUS
- MINUS
* STAR
/ SLASH
| VBAR
& AMPER
< LESS
> GREATER
= EQUAL
. DOT
% PERCENT
` BACKQUOTE
{ LBRACE
} RBRACE
@ AT
@= ATEQUAL
== EQEQUAL
!= NOTEQUAL
<> NOTEQUAL
<= LESSEQUAL
>= GREATEREQUAL
~ TILDE
^ CIRCUMFLEX
<< LEFTSHIFT
>> RIGHTSHIFT
** DOUBLESTAR
+= PLUSEQUAL
-= MINEQUAL
*= STAREQUAL
/= SLASHEQUAL
%= PERCENTEQUAL
&= AMPEREQUAL
|= VBAREQUAL
^= CIRCUMFLEXEQUAL
<<= LEFTSHIFTEQUAL
>>= RIGHTSHIFTEQUAL
**= DOUBLESTAREQUAL
// DOUBLESLASH
//= DOUBLESLASHEQUAL
-> RARROW
:= COLONEQUAL
"""

opmap = {}
for line in opmap_raw.splitlines():
  if line:
    op, name = line.split()
    opmap[op] = getattr(token, name)
