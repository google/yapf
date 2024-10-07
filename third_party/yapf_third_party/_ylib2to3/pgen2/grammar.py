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
import tempfile

# Local imports
from . import token


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
    tempfile_dir = os.path.dirname(filename)
    tempfile_prefix, tempfile_suffix = os.path.splitext(filename)
    with tempfile.NamedTemporaryFile(
        mode='wb',
        suffix=tempfile_suffix,
        prefix=tempfile_prefix,
        dir=tempfile_dir,
        delete=False) as f:
      pickle.dump(self.__dict__, f.file, pickle.HIGHEST_PROTOCOL)
      try:
        os.rename(f.name, filename)
      except OSError:
        # This makes sure that we do not leave the tempfile around
        # unless we have to...
        try:
          os.remove(f.name)
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
