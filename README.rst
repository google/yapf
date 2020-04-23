====
YAPF
====

.. image:: https://badge.fury.io/py/yapf.svg
    :target: https://badge.fury.io/py/yapf
    :alt: PyPI version

.. image:: https://travis-ci.org/google/yapf.svg?branch=master
    :target: https://travis-ci.org/google/yapf
    :alt: Build status

.. image:: https://coveralls.io/repos/google/yapf/badge.svg?branch=master
    :target: https://coveralls.io/r/google/yapf?branch=master
    :alt: Coverage status


Introduction
============

Most of the current formatters for Python --- e.g., autopep8, and pep8ify ---
are made to remove lint errors from code. This has some obvious limitations.
For instance, code that conforms to the PEP 8 guidelines may not be
reformatted.  But it doesn't mean that the code looks good.

YAPF takes a different approach. It's based off of `'clang-format' <https://cl
ang.llvm.org/docs/ClangFormat.html>`_, developed by Daniel Jasper. In essence,
the algorithm takes the code and reformats it to the best formatting that
conforms to the style guide, even if the original code didn't violate the
style guide. The idea is also similar to the `'gofmt' <https://golang.org/cmd/
gofmt/>`_ tool for the Go programming language: end all holy wars about
formatting - if the whole codebase of a project is simply piped through YAPF
whenever modifications are made, the style remains consistent throughout the
project and there's no point arguing about style in every code review.

The ultimate goal is that the code YAPF produces is as good as the code that a
programmer would write if they were following the style guide. It takes away
some of the drudgery of maintaining your code.

Try out YAPF with this `online demo <https://yapf.now.sh>`_.

.. footer::

    YAPF is not an official Google product (experimental or otherwise), it is
    just code that happens to be owned by Google.

.. contents::


Installation
============

To install YAPF from PyPI:

.. code-block:: shell

    $ pip install yapf

(optional) If you are using Python 2.7 and want to enable multiprocessing:

.. code-block:: shell

    $ pip install futures

YAPF is still considered in "alpha" stage, and the released version may change
often; therefore, the best way to keep up-to-date with the latest development
is to clone this repository.

Note that if you intend to use YAPF as a command-line tool rather than as a
library, installation is not necessary. YAPF supports being run as a directory
by the Python interpreter. If you cloned/unzipped YAPF into ``DIR``, it's
possible to run:

.. code-block:: shell

    $ PYTHONPATH=DIR python DIR/yapf [options] ...


Python versions
===============

YAPF supports Python 2.7 and 3.6.4+. (Note that some Python 3 features may fail
to parse with Python versions before 3.6.4.)

YAPF requires the code it formats to be valid Python for the version YAPF itself
runs under. Therefore, if you format Python 3 code with YAPF, run YAPF itself
under Python 3 (and similarly for Python 2).


Usage
=====

Options::

    usage: yapf [-h] [-v] [-d | -i] [-r | -l START-END] [-e PATTERN]
                [--style STYLE] [--style-help] [--no-local-style] [-p]
                [-vv]
                [files [files ...]]

    Formatter for Python code.

    positional arguments:
      files

    optional arguments:
      -h, --help            show this help message and exit
      -v, --version         show version number and exit
      -d, --diff            print the diff for the fixed source
      -i, --in-place        make changes to files in place
      -r, --recursive       run recursively over directories
      -l START-END, --lines START-END
                            range of lines to reformat, one-based
      -e PATTERN, --exclude PATTERN
                            patterns for files to exclude from formatting
      --style STYLE         specify formatting style: either a style name (for
                            example "pep8" or "google"), or the name of a file
                            with style settings. The default is pep8 unless a
                            .style.yapf or setup.cfg file located in the same
                            directory as the source or one of its parent
                            directories (for stdin, the current directory is
                            used).
      --style-help          show style settings and exit; this output can be saved
                            to .style.yapf to make your settings permanent
      --no-local-style      don't search for local style definition
      -p, --parallel        Run yapf in parallel when formatting multiple files.
                            Requires concurrent.futures in Python 2.X
      -vv, --verbose        Print out file names while processing


------------
Return Codes
------------

Normally YAPF returns zero on successful program termination and non-zero otherwise.

If ``--diff`` is supplied, YAPF returns zero when no changes were necessary, non-zero
otherwise (including program error). You can use this in a CI workflow to test that code
has been YAPF-formatted.

---------------------------------------------
Excluding files from formatting (.yapfignore)
---------------------------------------------

In addition to exclude patterns provided on commandline, YAPF looks for additional
patterns specified in a file named ``.yapfignore`` located in the working directory from
which YAPF is invoked.

``.yapfignore``'s syntax is similar to UNIX's filename pattern matching::

    *       matches everything
    ?       matches any single character
    [seq]   matches any character in seq
    [!seq]  matches any character not in seq

Note that no entry should begin with `./`.


Formatting style
================

The formatting style used by YAPF is configurable and there are many "knobs"
that can be used to tune how YAPF does formatting. See the ``style.py`` module
for the full list.

To control the style, run YAPF with the ``--style`` argument. It accepts one of
the predefined styles (e.g., ``pep8`` or ``google``), a path to a configuration
file that specifies the desired style, or a dictionary of key/value pairs.

The config file is a simple listing of (case-insensitive) ``key = value`` pairs
with a ``[yapf]`` heading. For example:

.. code-block:: ini

    [yapf]
    based_on_style = pep8
    spaces_before_comment = 4
    split_before_logical_operator = true

The ``based_on_style`` setting determines which of the predefined styles this
custom style is based on (think of it like subclassing). Four
styles are predefined: ``pep8`` (default), ``google``, ``yapf``, and ``facebook``
(see ``_STYLE_NAME_TO_FACTORY`` in style.py_).

.. _style.py: https://github.com/google/yapf/blob/master/yapf/yapflib/style.py#L445

It's also possible to do the same on the command line with a dictionary. For
example:

.. code-block:: shell

    --style='{based_on_style: pep8, indent_width: 2}'

This will take the ``pep8`` base style and modify it to have two space
indentations.

YAPF will search for the formatting style in the following manner:

1. Specified on the command line
2. In the ``[style]`` section of a ``.style.yapf`` file in either the current
   directory or one of its parent directories.
3. In the ``[yapf]`` section of a ``setup.cfg`` file in either the current
   directory or one of its parent directories.
4. In the ``[style]`` section of a ``~/.config/yapf/style`` file in your home
   directory.

If none of those files are found, the default style is used (PEP8).


Example
=======

An example of the type of formatting that YAPF can do, it will take this ugly
code:

.. code-block:: python

    x = {  'a':37,'b':42,

    'c':927}

    y = 'hello ''world'
    z = 'hello '+'world'
    a = 'hello {}'.format('world')
    class foo  (     object  ):
      def f    (self   ):
        return       37*-+2
      def g(self, x,y=42):
          return y
    def f  (   a ) :
      return      37+-+a[42-x :  y**3]

and reformat it into:

.. code-block:: python

    x = {'a': 37, 'b': 42, 'c': 927}

    y = 'hello ' 'world'
    z = 'hello ' + 'world'
    a = 'hello {}'.format('world')


    class foo(object):
        def f(self):
            return 37 * -+2

        def g(self, x, y=42):
            return y


    def f(a):
        return 37 + -+a[42 - x:y**3]


Example as a module
===================

The two main APIs for calling yapf are ``FormatCode`` and ``FormatFile``, these
share several arguments which are described below:

.. code-block:: python

    >>> from yapf.yapflib.yapf_api import FormatCode  # reformat a string of code

    >>> FormatCode("f ( a = 1, b = 2 )")
    'f(a=1, b=2)\n'

A ``style_config`` argument: Either a style name or a path to a file that contains
formatting style settings. If None is specified, use the default style
as set in ``style.DEFAULT_STYLE_FACTORY``.

.. code-block:: python

    >>> FormatCode("def g():\n  return True", style_config='pep8')
    'def g():\n    return True\n'

A ``lines`` argument: A list of tuples of lines (ints), [start, end],
that we want to format. The lines are 1-based indexed. It can be used by
third-party code (e.g., IDEs) when reformatting a snippet of code rather
than a whole file.

.. code-block:: python

    >>> FormatCode("def g( ):\n    a=1\n    b = 2\n    return a==b", lines=[(1, 1), (2, 3)])
    'def g():\n    a = 1\n    b = 2\n    return a==b\n'

A ``print_diff`` (bool): Instead of returning the reformatted source, return a
diff that turns the formatted source into reformatter source.

.. code-block:: python

    >>> print(FormatCode("a==b", filename="foo.py", print_diff=True))
    --- foo.py (original)
    +++ foo.py (reformatted)
    @@ -1 +1 @@
    -a==b
    +a == b

Note: the ``filename`` argument for ``FormatCode`` is what is inserted into
the diff, the default is ``<unknown>``.

``FormatFile`` returns reformatted code from the passed file along with its encoding:

.. code-block:: python

    >>> from yapf.yapflib.yapf_api import FormatFile  # reformat a file

    >>> print(open("foo.py").read())  # contents of file
    a==b

    >>> FormatFile("foo.py")
    ('a == b\n', 'utf-8')

The ``in_place`` argument saves the reformatted code back to the file:

.. code-block:: python

    >>> FormatFile("foo.py", in_place=True)
    (None, 'utf-8')

    >>> print(open("foo.py").read())  # contents of file (now fixed)
    a == b


Knobs
=====

``ALIGN_CLOSING_BRACKET_WITH_VISUAL_INDENT``
    Align closing bracket with visual indentation.

``ALLOW_MULTILINE_LAMBDAS``
    Allow lambdas to be formatted on more than one line.

``ALLOW_MULTILINE_DICTIONARY_KEYS``
    Allow dictionary keys to exist on multiple lines. For example:

    .. code-block:: python

        x = {
            ('this is the first element of a tuple',
             'this is the second element of a tuple'):
                 value,
        }

``ALLOW_SPLIT_BEFORE_DEFAULT_OR_NAMED_ASSIGNS``
    Allow splitting before a default / named assignment in an argument list.

``ALLOW_SPLIT_BEFORE_DICT_VALUE``
    Allow splits before the dictionary value.

``ARITHMETIC_PRECEDENCE_INDICATION``
    Let spacing indicate operator precedence. For example:

    .. code-block:: python

        a = 1 * 2 + 3 / 4
        b = 1 / 2 - 3 * 4
        c = (1 + 2) * (3 - 4)
        d = (1 - 2) / (3 + 4)
        e = 1 * 2 - 3
        f = 1 + 2 + 3 + 4

    will be formatted as follows to indicate precedence:

    .. code-block:: python

        a = 1*2 + 3/4
        b = 1/2 - 3*4
        c = (1+2) * (3-4)
        d = (1-2) / (3+4)
        e = 1*2 - 3
        f = 1 + 2 + 3 + 4

``BLANK_LINE_BEFORE_NESTED_CLASS_OR_DEF``
    Insert a blank line before a ``def`` or ``class`` immediately nested within
    another ``def`` or ``class``. For example:

    .. code-block:: python

        class Foo:
                           # <------ this blank line
            def method():
                pass

``BLANK_LINE_BEFORE_MODULE_DOCSTRING``
    Insert a blank line before a module docstring.

``BLANK_LINE_BEFORE_CLASS_DOCSTRING``
    Insert a blank line before a class-level docstring.

``BLANK_LINES_AROUND_TOP_LEVEL_DEFINITION``
    Sets the number of desired blank lines surrounding top-level function and
    class definitions. For example:

    .. code-block:: python

        class Foo:
            pass
                           # <------ having two blank lines here
                           # <------ is the default setting
        class Bar:
            pass

``COALESCE_BRACKETS``
    Do not split consecutive brackets. Only relevant when
    ``DEDENT_CLOSING_BRACKETS`` or ``INDENT_CLOSING_BRACKETS``
    is set. For example:

    .. code-block:: python

        call_func_that_takes_a_dict(
            {
                'key1': 'value1',
                'key2': 'value2',
            }
        )

    would reformat to:

    .. code-block:: python

        call_func_that_takes_a_dict({
            'key1': 'value1',
            'key2': 'value2',
        })


``COLUMN_LIMIT``
    The column limit (or max line-length)

``CONTINUATION_ALIGN_STYLE``
    The style for continuation alignment. Possible values are:

    - ``SPACE``: Use spaces for continuation alignment. This is default
      behavior.
    - ``FIXED``: Use fixed number (CONTINUATION_INDENT_WIDTH) of columns
      (ie: CONTINUATION_INDENT_WIDTH/INDENT_WIDTH tabs or CONTINUATION_INDENT_WIDTH
      spaces) for continuation alignment.
    - ``VALIGN-RIGHT``: Vertically align continuation lines to multiple of
      INDENT_WIDTH columns. Slightly right (one tab or a few spaces) if cannot
      vertically align continuation lines with indent characters.

``CONTINUATION_INDENT_WIDTH``
    Indent width used for line continuations.

``DEDENT_CLOSING_BRACKETS``
    Put closing brackets on a separate line, dedented, if the bracketed
    expression can't fit in a single line. Applies to all kinds of brackets,
    including function definitions and calls. For example:

    .. code-block:: python

        config = {
            'key1': 'value1',
            'key2': 'value2',
        }  # <--- this bracket is dedented and on a separate line

        time_series = self.remote_client.query_entity_counters(
            entity='dev3246.region1',
            key='dns.query_latency_tcp',
            transform=Transformation.AVERAGE(window=timedelta(seconds=60)),
            start_ts=now()-timedelta(days=3),
            end_ts=now(),
        )  # <--- this bracket is dedented and on a separate line

``DISABLE_ENDING_COMMA_HEURISTIC``
    Disable the heuristic which places each list element on a separate line if
    the list is comma-terminated.

``EACH_DICT_ENTRY_ON_SEPARATE_LINE``
    Place each dictionary entry onto its own line.

``FORCE_MULTILINE_DICT``
    Respect EACH_DICT_ENTRY_ON_SEPARATE_LINE even if the line is shorter than
    COLUMN_LIMIT.

``I18N_COMMENT``
    The regex for an internationalization comment. The presence of this comment
    stops reformatting of that line, because the comments are required to be
    next to the string they translate.

``I18N_FUNCTION_CALL``
    The internationalization function call names. The presence of this function
    stops reformatting on that line, because the string it has cannot be moved
    away from the i18n comment.

``INDENT_DICTIONARY_VALUE``
    Indent the dictionary value if it cannot fit on the same line as the
    dictionary key. For example:

    .. code-block:: python

        config = {
            'key1':
                'value1',
            'key2': value1 +
                    value2,
        }

``INDENT_WIDTH``
    The number of columns to use for indentation.

``INDENT_BLANK_LINES``
    Set to ``True`` to prefer indented blank lines rather than empty

``INDENT_CLOSING_BRACKETS``
    Put closing brackets on a separate line, indented, if the bracketed
    expression can't fit in a single line. Applies to all kinds of brackets,
    including function definitions and calls. For example:

    .. code-block:: python

        config = {
            'key1': 'value1',
            'key2': 'value2',
            }  # <--- this bracket is indented and on a separate line

        time_series = self.remote_client.query_entity_counters(
            entity='dev3246.region1',
            key='dns.query_latency_tcp',
            transform=Transformation.AVERAGE(window=timedelta(seconds=60)),
            start_ts=now()-timedelta(days=3),
            end_ts=now(),
            )  # <--- this bracket is indented and on a separate line

``JOIN_MULTIPLE_LINES``
    Join short lines into one line. E.g., single line ``if`` statements.

``NO_SPACES_AROUND_SELECTED_BINARY_OPERATORS``
    Do not include spaces around selected binary operators. For example:

    .. code-block:: python

        1 + 2 * 3 - 4 / 5

    will be formatted as follows when configured with ``*``, ``/``:

    .. code-block:: python

        1 + 2*3 - 4/5

``SPACES_AROUND_POWER_OPERATOR``
    Set to ``True`` to prefer using spaces around ``**``.

``SPACES_AROUND_DEFAULT_OR_NAMED_ASSIGN``
    Set to ``True`` to prefer spaces around the assignment operator for default
    or keyword arguments.

``SPACES_AROUND_DICT_DELIMITERS``
    Adds a space after the opening '{' and before the ending '}' dict delimiters.

    .. code-block:: python

        {1: 2}

    will be formatted as:

    .. code-block:: python

        { 1: 2 }

``SPACES_AROUND_LIST_DELIMITERS``
    Adds a space after the opening '[' and before the ending ']' list delimiters.

    .. code-block:: python

        [1, 2]

    will be formatted as:
    
    .. code-block:: python

        [ 1, 2 ]

``SPACES_AROUND_SUBSCRIPT_COLON``
    Use spaces around the subscript / slice operator.  For example:

    .. code-block:: python

        my_list[1 : 10 : 2]

``SPACES_AROUND_TUPLE_DELIMITERS``
    Adds a space after the opening '(' and before the ending ')' tuple delimiters.

    .. code-block:: python

        (1, 2, 3)

    will be formatted as:

    .. code-block:: python

        ( 1, 2, 3 )

``SPACES_BEFORE_COMMENT``
    The number of spaces required before a trailing comment.
    This can be a single value (representing the number of spaces
    before each trailing comment) or list of of values (representing
    alignment column values; trailing comments within a block will
    be aligned to the first column value that is greater than the maximum
    line length within the block). For example:

    With ``spaces_before_comment=5``:

    .. code-block:: python

        1 + 1 # Adding values

    will be formatted as:

    .. code-block:: python

        1 + 1     # Adding values <-- 5 spaces between the end of the statement and comment

    With ``spaces_before_comment=15, 20``:

    .. code-block:: python

        1 + 1 # Adding values
        two + two # More adding

        longer_statement # This is a longer statement
        short # This is a shorter statement

        a_very_long_statement_that_extends_beyond_the_final_column # Comment
        short # This is a shorter statement

    will be formatted as:

    .. code-block:: python

        1 + 1          # Adding values <-- end of line comments in block aligned to col 15
        two + two      # More adding

        longer_statement    # This is a longer statement <-- end of line comments in block aligned to col 20
        short               # This is a shorter statement

        a_very_long_statement_that_extends_beyond_the_final_column  # Comment <-- the end of line comments are aligned based on the line length
        short                                                       # This is a shorter statement

``SPACE_BETWEEN_ENDING_COMMA_AND_CLOSING_BRACKET``
    Insert a space between the ending comma and closing bracket of a list, etc.

``SPACE_INSIDE_BRACKETS``
    Use spaces inside brackets, braces, and parentheses.  For example:

    .. code-block:: python

        method_call( 1 )
        my_dict[ 3 ][ 1 ][ get_index( *args, **kwargs ) ]
        my_set = { 1, 2, 3 }

``SPLIT_ARGUMENTS_WHEN_COMMA_TERMINATED``
    Split before arguments if the argument list is terminated by a comma.

``SPLIT_ALL_COMMA_SEPARATED_VALUES``
    If a comma separated list (``dict``, ``list``, ``tuple``, or function
    ``def``) is on a line that is too long, split such that all elements
    are on a single line.

``SPLIT_ALL_TOP_LEVEL_COMMA_SEPARATED_VALUES``
    Variation on ``SPLIT_ALL_COMMA_SEPARATED_VALUES`` in which, if a
    subexpression with a comma fits in its starting line, then the
    subexpression is not split. This avoids splits like the one for
    ``b`` in this code:

    .. code-block:: python
      
      abcdef(
          aReallyLongThing: int,
          b: [Int,
              Int])
   
    With the new knob this is split as:

    .. code-block:: python
      
      abcdef(
          aReallyLongThing: int,
          b: [Int, Int])

``SPLIT_BEFORE_BITWISE_OPERATOR``
    Set to ``True`` to prefer splitting before ``&``, ``|`` or ``^`` rather
    than after.

``SPLIT_BEFORE_ARITHMETIC_OPERATOR``
    Set to ``True`` to prefer splitting before ``+``, ``-``, ``*``, ``/``, ``//``,
    or ``@`` rather than after.

``SPLIT_BEFORE_CLOSING_BRACKET``
    Split before the closing bracket if a ``list`` or ``dict`` literal doesn't
    fit on a single line.

``SPLIT_BEFORE_DICT_SET_GENERATOR``
    Split before a dictionary or set generator (comp_for). For example, note
    the split before the ``for``:

    .. code-block:: python

        foo = {
            variable: 'Hello world, have a nice day!'
            for variable in bar if variable != 42
        }

``SPLIT_BEFORE_DOT``
    Split before the ``.`` if we need to split a longer expression:

    .. code-block:: python

      foo = ('This is a really long string: {}, {}, {}, {}'.format(a, b, c, d))

    would reformat to something like:

    .. code-block:: python

      foo = ('This is a really long string: {}, {}, {}, {}'
             .format(a, b, c, d))

``SPLIT_BEFORE_EXPRESSION_AFTER_OPENING_PAREN``
    Split after the opening paren which surrounds an expression if it doesn't
    fit on a single line.

``SPLIT_BEFORE_FIRST_ARGUMENT``
    If an argument / parameter list is going to be split, then split before the
    first argument.

``SPLIT_BEFORE_LOGICAL_OPERATOR``
    Set to ``True`` to prefer splitting before ``and`` or ``or`` rather than
    after.

``SPLIT_BEFORE_NAMED_ASSIGNS``
    Split named assignments onto individual lines.

``SPLIT_COMPLEX_COMPREHENSION``
    For list comprehensions and generator expressions with multiple clauses
    (e.g multiple ``for`` calls, ``if`` filter expressions) and which need to
    be reflowed, split each clause onto its own line. For example:

    .. code-block:: python

      result = [
          a_var + b_var for a_var in xrange(1000) for b_var in xrange(1000)
          if a_var % b_var]

    would reformat to something like:

    .. code-block:: python

      result = [
          a_var + b_var
          for a_var in xrange(1000)
          for b_var in xrange(1000)
          if a_var % b_var]

``SPLIT_PENALTY_AFTER_OPENING_BRACKET``
    The penalty for splitting right after the opening bracket.

``SPLIT_PENALTY_AFTER_UNARY_OPERATOR``
    The penalty for splitting the line after a unary operator.

``SPLIT_PENALTY_ARITHMETIC_OPERATOR``
    The penalty of splitting the line around the ``+``, ``-``, ``*``, ``/``,
    ``//``, ``%``, and ``@`` operators.

``SPLIT_PENALTY_BEFORE_IF_EXPR``
    The penalty for splitting right before an ``if`` expression.

``SPLIT_PENALTY_BITWISE_OPERATOR``
    The penalty of splitting the line around the ``&``, ``|``, and ``^``
    operators.

``SPLIT_PENALTY_COMPREHENSION``
    The penalty for splitting a list comprehension or generator expression.

``SPLIT_PENALTY_EXCESS_CHARACTER``
    The penalty for characters over the column limit.

``SPLIT_PENALTY_FOR_ADDED_LINE_SPLIT``
    The penalty incurred by adding a line split to the unwrapped line. The more
    line splits added the higher the penalty.

``SPLIT_PENALTY_IMPORT_NAMES``
    The penalty of splitting a list of ``import as`` names. For example:

    .. code-block:: python

      from a_very_long_or_indented_module_name_yada_yad import (long_argument_1,
                                                                long_argument_2,
                                                                long_argument_3)

    would reformat to something like:

    .. code-block:: python

      from a_very_long_or_indented_module_name_yada_yad import (
          long_argument_1, long_argument_2, long_argument_3)

``SPLIT_PENALTY_LOGICAL_OPERATOR``
    The penalty of splitting the line around the ``and`` and ``or`` operators.

``USE_TABS``
    Use the Tab character for indentation.

(Potentially) Frequently Asked Questions
========================================

--------------------------------------------
Why does YAPF destroy my awesome formatting?
--------------------------------------------

YAPF tries very hard to get the formatting correct. But for some code, it won't
be as good as hand-formatting. In particular, large data literals may become
horribly disfigured under YAPF.

The reasons for this are manyfold. In short, YAPF is simply a tool to help
with development. It will format things to coincide with the style guide, but
that may not equate with readability.

What can be done to alleviate this situation is to indicate regions YAPF should
ignore when reformatting something:

.. code-block:: python

    # yapf: disable
    FOO = {
        # ... some very large, complex data literal.
    }

    BAR = [
        # ... another large data literal.
    ]
    # yapf: enable

You can also disable formatting for a single literal like this:

.. code-block:: python

    BAZ = {
        (1, 2, 3, 4),
        (5, 6, 7, 8),
        (9, 10, 11, 12),
    }  # yapf: disable

To preserve the nice dedented closing brackets, use the
``dedent_closing_brackets`` in your style. Note that in this case all
brackets, including function definitions and calls, are going to use
that style.  This provides consistency across the formatted codebase.

-------------------------------
Why Not Improve Existing Tools?
-------------------------------

We wanted to use clang-format's reformatting algorithm. It's very powerful and
designed to come up with the best formatting possible. Existing tools were
created with different goals in mind, and would require extensive modifications
to convert to using clang-format's algorithm.

-----------------------------
Can I Use YAPF In My Program?
-----------------------------

Please do! YAPF was designed to be used as a library as well as a command line
tool. This means that a tool or IDE plugin is free to use YAPF.

-----------------------------------------
I still get non Pep8 compliant code! Why?
-----------------------------------------

YAPF tries very hard to be fully PEP 8 compliant. However, it is paramount
to not risk altering the semantics of your code. Thus, YAPF tries to be as
safe as possible and does not change the token stream
(e.g., by adding parentheses).
All these cases however, can be easily fixed manually. For instance,

.. code-block:: python

    from my_package import my_function_1, my_function_2, my_function_3, my_function_4, my_function_5

    FOO = my_variable_1 + my_variable_2 + my_variable_3 + my_variable_4 + my_variable_5 + my_variable_6 + my_variable_7 + my_variable_8

won't be split, but you can easily get it right by just adding parentheses:

.. code-block:: python

    from my_package import (my_function_1, my_function_2, my_function_3,
                            my_function_4, my_function_5)

    FOO = (my_variable_1 + my_variable_2 + my_variable_3 + my_variable_4 +
           my_variable_5 + my_variable_6 + my_variable_7 + my_variable_8)

Gory Details
============

----------------
Algorithm Design
----------------

The main data structure in YAPF is the ``UnwrappedLine`` object. It holds a list
of ``FormatToken``\s, that we would want to place on a single line if there were
no column limit. An exception being a comment in the middle of an expression
statement will force the line to be formatted on more than one line. The
formatter works on one ``UnwrappedLine`` object at a time.

An ``UnwrappedLine`` typically won't affect the formatting of lines before or
after it. There is a part of the algorithm that may join two or more
``UnwrappedLine``\s into one line. For instance, an if-then statement with a
short body can be placed on a single line:

.. code-block:: python

    if a == 42: continue

YAPF's formatting algorithm creates a weighted tree that acts as the solution
space for the algorithm. Each node in the tree represents the result of a
formatting decision --- i.e., whether to split or not to split before a token.
Each formatting decision has a cost associated with it. Therefore, the cost is
realized on the edge between two nodes. (In reality, the weighted tree doesn't
have separate edge objects, so the cost resides on the nodes themselves.)

For example, take the following Python code snippet. For the sake of this
example, assume that line (1) violates the column limit restriction and needs to
be reformatted.

.. code-block:: python

    def xxxxxxxxxxx(aaaaaaaaaaaa, bbbbbbbbb, cccccccc, dddddddd, eeeeee):  # 1
        pass                                                               # 2

For line (1), the algorithm will build a tree where each node (a
``FormattingDecisionState`` object) is the state of the line at that token given
the decision to split before the token or not. Note: the ``FormatDecisionState``
objects are copied by value so each node in the graph is unique and a change in
one doesn't affect other nodes.

Heuristics are used to determine the costs of splitting or not splitting.
Because a node holds the state of the tree up to a token's insertion, it can
easily determine if a splitting decision will violate one of the style
requirements. For instance, the heuristic is able to apply an extra penalty to
the edge when not splitting between the previous token and the one being added.

There are some instances where we will never want to split the line, because
doing so will always be detrimental (i.e., it will require a backslash-newline,
which is very rarely desirable). For line (1), we will never want to split the
first three tokens: ``def``, ``xxxxxxxxxxx``, and ``(``. Nor will we want to
split between the ``)`` and the ``:`` at the end. These regions are said to be
"unbreakable." This is reflected in the tree by there not being a "split"
decision (left hand branch) within the unbreakable region.

Now that we have the tree, we determine what the "best" formatting is by finding
the path through the tree with the lowest cost.

And that's it!
