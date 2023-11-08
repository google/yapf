# Change Log
# All notable changes to this project will be documented in this file.
# This project adheres to [Semantic Versioning](http://semver.org/).

## (0.41.0) UNRELEASED
### Added
- New `DISABLE_SPLIT_LIST_WITH_COMMENT` flag.
 `DISABLE_SPLIT_LIST_WITH_COMMENT` is a new knob that changes the
  behavior of splitting a list when a comment is present inside the list.

  Before, we split a list containing a comment just like we split a list
  containing a trailing comma: Each element goes on its own line (unless
  `DISABLE_ENDING_COMMA_HEURISTIC` is true).

  This new flag allows you to control the behavior of a list with a comment
  *separately* from the behavior when the list contains a trailing comma.

  This mirrors the behavior of clang-format, and is useful for e.g. forming
  "logical groups" of elements in a list.

  Without this flag:

  ```
  [
    a,
    b,  #
    c
  ]
  ```

  With this flag:

  ```
  [
    a, b,  #
    c
  ]
  ```

  Before we had one flag that controlled two behaviors.

    - `DISABLE_ENDING_COMMA_HEURISTIC=false` (default):
      - Split a list that has a trailing comma.
      - Split a list that contains a comment.
    - `DISABLE_ENDING_COMMA_HEURISTIC=true`:
      - Don't split on trailing comma.
      - Don't split on comment.

  Now we have two flags.

    - `DISABLE_ENDING_COMMA_HEURISTIC=false` and `DISABLE_SPLIT_LIST_WITH_COMMENT=false` (default):
      - Split a list that has a trailing comma.
      - Split a list that contains a comment.
      Behavior is unchanged from the default before.
    - `DISABLE_ENDING_COMMA_HEURISTIC=true` and `DISABLE_SPLIT_LIST_WITH_COMMENT=false` :
      - Don't split on trailing comma.
      - Do split on comment.  **This is a change in behavior from before.**
    - `DISABLE_ENDING_COMMA_HEURISTIC=false` and `DISABLE_SPLIT_LIST_WITH_COMMENT=true` :
      - Split on trailing comma.
      - Don't split on comment.
    - `DISABLE_ENDING_COMMA_HEURISTIC=true` and `DISABLE_SPLIT_LIST_WITH_COMMENT=true` :
      - Don't split on trailing comma.
      - Don't split on comment.
      **You used to get this behavior just by setting one flag, but now you have to set both.**

  Note the behavioral change above; if you set
  `DISABLE_ENDING_COMMA_HEURISTIC=true` and want to keep the old behavior, you
  now also need to set `DISABLE_SPLIT_LIST_WITH_COMMENT=true`.
### Changes
- Remove dependency on importlib-metadata
- Remove dependency on tomli when using >= py311
- Format '.pyi' type sub files.
### Fixed
- Fix SPLIT_ARGUMENTS_WHEN_COMMA_TERMINATED for one-item named argument lists
  by taking precedence over SPLIT_BEFORE_NAMED_ASSIGNS.
- Fix SPLIT_ALL_COMMA_SEPARATED_VALUES and SPLIT_ALL_TOP_LEVEL_COMMA_SEPARATED_VALUES
  being too agressive for lambdas and unpacking.

## [0.40.2] 2023-09-22
### Changes
- The verification module has been removed. NOTE: this changes the public APIs
  by removing the "verify" parameter.
- Changed FORCE_MULTILINE_DICT to override SPLIT_ALL_TOP_LEVEL_COMMA_SEPARATED_VALUES.
- Adopt pyproject.toml (PEP 517) for build system
### Fixed
- Do not treat variables named `match` as the match keyword.
- Fix SPLIT_ARGUMENTS_WHEN_COMMA_TERMINATED for one-item argument lists.
- Fix trailing backslash-newline on Windows when using stdin.

## [0.40.1] 2023-06-20
### Fixed
- Corrected bad distribution v0.40.0 package.

## [0.40.0] 2023-06-13 [YANKED - [#1107](https://github.com/google/yapf/issues/1107)]
### Added
- Support for Python 3.11
- Add the `--print-modified` flag to print out file names of modified files when
  running in in-place mode.
### Changes
- Replace the outdated and no-longer-supported lib2to3 with a fork of blib2to3,
  Black's version of lib2to3.
### Removed
- Support for Python versions < 3.7 are no longer supported.

## [0.33.0] 2023-04-18 [YANKED - [#1154](https://github.com/google/yapf/issues/1154)]
### Added
- Add a new Python parser to generate logical lines.
- Added support for `# fmt: on` and `# fmt: off` pragmas.
### Changes
- Moved 'pytree' parsing tools into its own subdirectory.
- Add support for Python 3.10.
- Format generated dicts with respect to same rules as regular dicts
- Generalized the ending comma heuristic to subscripts.
- Supports "pyproject.toml" by default.
### Fixed
- Split line before all comparison operators.

## [0.32.0] 2021-12-26
### Added
- Look at the 'pyproject.toml' file to see if it contains ignore file information
  for YAPF.
- New entry point `yapf_api.FormatTree` for formatting lib2to3 concrete
  syntax trees.
- Add CI via GitHub Actions.
### Changes
- Change tests to support "pytest".
- Reformat so that "flake8" is happy.
- Use GitHub Actions instead of Travis for CI.
- Clean up the FormatToken interface to limit how much it relies upon the
  pytree node object.
- Rename "unwrapped_line" module to "logical_line."
- Rename "UnwrappedLine" class to "LogicalLine."
### Fixed
- Added pyproject extra to install toml package as an optional dependency.
- Enable `BLANK_LINE_BEFORE_NESTED_CLASS_OR_DEF` knob for "pep8" style, so
  method definitions inside a class are surrounded by a single blank line as
  prescribed by PEP8.
- Fixed the '...' token to be spaced after a colon.

## [0.31.0] 2021-03-14
### Added
- Renamed 'master' branch to 'main'.
- Add 'BLANK_LINES_BETWEEN_TOP_LEVEL_IMPORTS_AND_VARIABLES' to support setting
  a custom number of blank lines between top-level imports and variable
  definitions.
- Ignore end of line `# copybara:` directives when checking line length.
- Look at the 'pyproject.toml' file to see if it contains style information for
  YAPF.
### Changed
- Do not scan excluded directories. Prior versions would scan an excluded
  folder then exclude its contents on a file by file basis. Preventing the
  folder being scanned is faster.
### Fixed
- Exclude directories on Windows.

## [0.30.0] 2020-04-23
### Added
- Added `SPACES_AROUND_LIST_DELIMITERS`, `SPACES_AROUND_DICT_DELIMITERS`,
  and `SPACES_AROUND_TUPLE_DELIMITERS` to add spaces after the opening-
  and before the closing-delimiters for lists, dicts, and tuples.
- Adds `FORCE_MULTILINE_DICT` knob to ensure dictionaries always split,
  even when shorter than the max line length.
- New knob `SPACE_INSIDE_BRACKETS` to add spaces inside brackets, braces, and
  parentheses.
- New knob `SPACES_AROUND_SUBSCRIPT_COLON` to add spaces around the subscript /
  slice operator.
### Changed
- Renamed "chromium" style to "yapf". Chromium will now use PEP-8 directly.
- `CONTINUATION_ALIGN_STYLE` with `FIXED` or `VALIGN-RIGHT` now works with
  space indentation.
### Fixed
- Honor a disable directive at the end of a multiline comment.
- Don't require splitting before comments in a list when
  `SPLIT_ALL_TOP_LEVEL_COMMA_SEPARATED_VALUES` is set. The knob is meant for
  values, not comments, which may be associated with the current line.
- Don't over-indent a parameter list when not needed. But make sure it is
  properly indented so that it doesn't collide with the lines afterwards.
- Don't split between two-word comparison operators: "is not", "not in", etc.

## [0.29.0] 2019-11-28
### Added
- Add the `--quiet` flag to suppress output. The return code is 1 if there are
  changes, similarly to the `--diff` flag.
- Add the `indent_closing_brackets` option. This is the same as the
  `dedent_closing_brackets` option except the brackets are indented the same
  as the previous line.
### Changed
- Collect a parameter list into a single object. This allows us to track how a
  parameter list is formatted, keeping state along the way. This helps when
  supporting Python 3 type annotations.
- Catch and report `UnicodeDecodeError` exceptions.
- Improved description of .yapfignore syntax.
### Fixed
- Format subscript lists so that splits are essentially free after a comma.
- Don't add a space between a string and its subscript.
- Extend discovery of '.style.yapf' & 'setup.cfg' files to search the root
  directory as well.
- Make sure we have parameters before we start calculating penalties for
  splitting them.
- Indicate if a class/function is nested to ensure blank lines when needed.
- Fix extra indentation in async-for else statement.
- A parameter list with no elements shouldn't count as exceeding the column
  limit.
- When splitting all comma separated values, don't treat the ending bracket as
  special.
- The "no blank lines between nested classes or functions" knob should only
  apply to the first nested class or function, not all of them.

## [0.28.0] 2019-07-11
### Added
- New knob `SPLIT_ALL_TOP_LEVEL_COMMA_SEPARATED_VALUES` is a variation on
  `SPLIT_ALL_COMMA_SEPARATED_VALUES` in which, if a subexpression with a comma
  fits in its starting line, then the subexpression is not split (thus avoiding
  unnecessary splits).
### Changed
- Set `INDENT_DICTIONARY_VALUE` for Google style.
- Set `JOIN_MULTIPLE_LINES = False` for Google style.
### Fixed
- `BLANK_LINE_BEFORE_NESTED_CLASS_OR_DEF=False` wasn't honored because the
  number of newlines was erroneously calculated beforehand.
- Lambda expressions shouldn't have an increased split penalty applied to the
  'lambda' keyword. This prevents them from being properly formatted when they're
  arguments to functions.
- A comment with continuation markers (??) shouldn't mess with the lineno count.
- Only emit unformatted if the "disable long line" is at the end of the line.
  Otherwise we could mess up formatting for containers which have them
  interspersed with code.
- Fix a potential race condition by using the correct style for opening a file
  which may not exist.

## [0.27.0] 2019-04-07
### Added
- `SPLIT_BEFORE_ARITHMETIC_OPERATOR` splits before an arithmetic operator when
  set. `SPLIT_PENALTY_ARITHMETIC_OPERATOR` allows you to set the split penalty
  around arithmetic operators.
### Changed
- Catch lib2to3's "TokenError" exception and output a nicer message.
### Fixed
- Parse integer lists correctly, removing quotes if the list is within a
  string.
- Adjust the penalties of bitwise operands for '&' and '^', similar to '|'.
- Avoid splitting after opening parens if SPLIT_BEFORE_FIRST_ARGUMENT is set
  to False.
- Adjust default SPLIT_PENALTY_AFTER_OPENING_BRACKET.
- Re-enable removal of extra lines on the boundaries of formatted regions.
- Adjust list splitting to avoid splitting before a dictionary element, because
  those are likely to be split anyway. If we do split, it leads to horrible
  looking code.
- Dictionary arguments were broken in a recent version. It resulted in
  unreadable formatting, where the remaining arguments were indented far more
  than the dictionary. Fixed so that if the dictionary is the first argument in
  a function call and doesn't fit on a single line, then it forces a split.
- Improve the connectiveness between items in a list. This prevents random
  splitting when it's not 100% necessary.
- Don't remove a comment attached to a previous object just because it's part
  of the "prefix" of a function/class node.

## [0.26.0] 2019-02-08
### Added
- `ALLOW_SPLIT_BEFORE_DEFAULT_OR_NAMED_ASSIGNS` allows us to split before
  default / named assignments.
- `ARITHMETIC_PRECEDENCE_INDICATION` removes spacing around binary operators
  if they have higher precedence than other operators in the same expression.
### Changed
- `SPACES_BEFORE_COMMENT` can now be assigned to a specific value (standard
  behavior) or a list of column values. When assigned to a list, trailing
  comments will be horizontally aligned to the first column value within
  the list that is greater than the maximum line length in the block.
- Don't modify the vertical spacing of a line that has a comment "pylint:
  disable=line-too-long". The line is expected to be too long.
- improved `CONTINUATION_ALIGN_STYLE` to accept quoted or underline-separated
  option value for passing option with command line arguments.
### Fixed
- When retrieving the opening bracket make sure that it's actually an opening
  bracket.
- Don't completely deny a lambda formatting if it goes over the column limit.
  Split only if absolutely necessary.
- Bump up penalty for splitting before a dot ('.').
- Ignore pseudo tokens when calculating split penalties.
- Increase the penalty for splitting before the first bit of a subscript.
- Improve splitting before dictionary values. Look more closely to see if the
  dictionary entry is a container. If so, then it's probably split over
  multiple lines with the opening bracket on the same line as the key.
  Therefore, we shouldn't enforce a split because of that.
- Increase split penalty around exponent operator.
- Correct spacing when using binary operators on strings with the
  `NO_SPACES_AROUND_SELECTED_BINARY_OPERATORS` option enabled.

## [0.25.0] 2018-11-25
### Added
- Added `INDENT_BLANK_LINES` knob to select whether the blank lines are empty
  or indented consistently with the current block.
- Support additional file exclude patterns in .yapfignore file.
### Fixed
- Correctly determine if a scope is the last in line. It avoids a wrong
  computation of the line end when determining if it must split after the
  opening bracket with `DEDENT_CLOSING_BRACKETS` enabled.

## [0.24.0] 2018-09-07
### Added
- Added 'SPLIT_BEFORE_DOT' knob to support "builder style" calls. The "builder
  style" option didn't work as advertised. Lines would split after the dots,
  not before them regardless of the penalties.
### Changed
- Support Python 3.7 in the tests. The old "comp_for" and "comp_if" nodes are
  now "old_comp_for" and "old_comp_if" in lib2to3.
### Fixed
- Don't count inner function calls when marking arguments as named assignments.
- Make sure that tuples and the like are formatted nicely if they all can't fit
  on a single line. This is similar to how we format function calls within an
  argument list.
- Allow splitting in a subscript if it goes over the line limit.
- Increase the split penalty for an if-expression.
- Increase penalty for splitting in a subscript so that it's more likely to
  split in a function call or other data literal.
- Cloning a pytree node doesn't transfer its a annotations. Make sure we do
  that so that we don't lose information.
- Revert change that broke the "no_spaces_around_binary_operators" option.
- The "--style-help" option would output string lists and sets in Python types.
  If the output was used as a style, then it wouldn't parse those values
  correctly.

## [0.23.0] 2018-08-27
### Added
- `DISABLE_ENDING_COMMA_HEURISTIC` is a new knob to disable the heuristic which
  splits a list onto separate lines if the list is comma-terminated.
### Fixed
- There's no need to increase N_TOKENS. In fact, it causes other things which
  use lib2to3 to fail if called from YAPF.
- Change the exception message instead of creating a new one that's just a
  clone.
- Make sure not to reformat when a line is disabled even if the --lines option
  is specified.
- The "no spaces around operators" flag wasn't correctly converting strings to
  sets. Changed the regexp to handle it better.

## [0.22.0] 2018-05-15
### Added
- The `BLANK_LINE_BEFORE_MODULE_DOCSTRING` knob adds a blank line before a
  module's docstring.
- The `SPLIT_ALL_COMMA_SEPARATED_VALUES` knob causes all lists, tuples, dicts
  function defs, etc... to split on all values, instead of maximizing the
  number of elements on each line, when not able to fit on a single line.
### Changed
- Improve the heuristic we use to determine when to split at the start of a
  function call. First check whether or not all elements can fit in the space
  without wrapping. If not, then we split.
- Check all of the elements of a tuple. Similarly to how arguments are
  analyzed. This allows tuples to be split more rationally.
- Adjust splitting penalties around arithmetic operators so that the code can
  flow more freely. The code must flow!
- Try to meld an argument list's closing parenthesis to the last argument.
### Fixed
- Attempt to determine if long lambdas are allowed. This can be done on a
  case-by-case basis with a "pylint" disable comment.
- A comment before a decorator isn't part of the decorator's line.
- Only force a new wrapped line after a comment in a decorator when it's the
  first token in the decorator.

## [0.21.0] 2018-03-18
### Added
- Introduce a new option of formatting multiline literals. Add
  `SPLIT_BEFORE_CLOSING_BRACKET` knob to control whether closing bracket should
  get their own line.
- Added `CONTINUATION_ALIGN_STYLE` knob to choose continuation alignment style
  when `USE_TABS` is enabled.
- Add 'BLANK_LINES_AROUND_TOP_LEVEL_DEFINITION' knob to control the number
  of blank lines between top-level function and class definitions.
### Fixed
- Don't split ellipses.

## [0.20.2] 2018-02-12
### Changed
- Improve the speed at which files are excluded by ignoring them earlier.
- Allow dictionaries to stay on a single line if they only have one entry
### Fixed
- Use tabs when constructing a continuation line when `USE_TABS` is enabled.
- A dictionary entry may not end in a colon, but may be an "unpacking"
  operation: `**foo`. Take that into account and don't split after the
  unpacking operator.

## [0.20.1] 2018-01-13
### Fixed
- Don't treat 'None' as a keyword if calling a function on it, like '__ne__()'.
- use_tabs=True always uses a single tab per indentation level; spaces are
  used for aligning vertically after that.
- Relax the split of a paren at the end of an if statement. With
  `dedent_closing_brackets` option requires that it be able to split there.

## [0.20.0] 2017-11-14
### Added
- Improve splitting of comprehensions and generators. Add
  `SPLIT_PENALTY_COMPREHENSION` knob to control preference for keeping
  comprehensions on a single line and `SPLIT_COMPLEX_COMPREHENSION` to enable
  splitting each clause of complex comprehensions onto its own line.
### Changed
- Take into account a named function argument when determining if we should
  split before the first argument in a function call.
- Split before the first argument in a function call if the arguments contain a
  dictionary that doesn't fit on a single line.
- Improve splitting of elements in a tuple. We want to split if there's a
  function call in the tuple that doesn't fit on the line.
### Fixed
- Enforce spaces between ellipses and keywords.
- When calculating the split penalty for a "trailer", process the child nodes
  afterwards because their penalties may change. For example if a list
  comprehension is an argument.
- Don't enforce a split before a comment after the opening of a container if it
  doesn't it on the current line. We try hard not to move such comments around.
- Use a TextIOWrapper when reading from stdin in Python3. This is necessary for
  some encodings, like cp936, used on Windows.
- Remove the penalty for a split before the first argument in a function call
  where the only argument is a generator expression.

## [0.19.0] 2017-10-14
### Added
- Added `SPLIT_BEFORE_EXPRESSION_AFTER_OPENING_PAREN` that enforces a split
  after the opening paren of an expression that's surrounded by parens.
### Changed
- Split before the ending bracket of a comma-terminated tuple / argument list
  if it's not a single element tuple / arg list.
### Fixed
- Prefer to split after a comma in an argument list rather than in the middle
  of an argument.
- A non-multiline string may have newlines if it contains continuation markers
  itself. Don't add a newline after the string when retaining the vertical
  space.
- Take into account the "async" keyword when determining if we must split
  before the first argument.
- Increase affinity for "atom" arguments in function calls. This helps prevent
  lists from being separated when they don't need to be.
- Don't place a dictionary argument on its own line if it's the last argument
  in the function call where that function is part of a builder-style call.
- Append the "var arg" type to a star in a star_expr.

## [0.18.0] 2017-09-18
### Added
- Option `ALLOW_SPLIT_BEFORE_DICT_VALUE` allows a split before a value. If
  False, then it won't be split even if it goes over the column limit.
### Changed
- Use spaces around the '=' in a typed name argument to align with 3.6 syntax.
### Fixed
- Allow semicolons if the line is disabled.
- Fix issue where subsequent comments at decreasing levels of indentation
  were improperly aligned and/or caused output with invalid syntax.
- Fix issue where specifying a line range removed a needed line before a
  comment.
- Fix spacing between unary operators if one is 'not'.
- Indent the dictionary value correctly if there's a multi-line key.
- Don't remove needed spacing before a comment in a dict when in "chromium"
  style.
- Increase indent for continuation line with same indent as next logical line
  with 'async with' statement.

## [0.17.0] 2017-08-20
### Added
- Option `NO_SPACES_AROUND_SELECTED_BINARY_OPERATORS` prevents adding spaces
  around selected binary operators, in accordance with the current style guide.
### Changed
- Adjust blank lines on formatting boundaries when using the `--lines` option.
- Return 1 if a diff changed the code. This is in line with how GNU diff acts.
- Add `-vv` flag to print out file names as they are processed
### Fixed
- Corrected how `DEDENT_CLOSING_BRACKETS` and `COALESCE_BRACKETS` interacted.
- Fix return value to return a boolean.
- Correct vim plugin not to clobber edited code if yapf returns an error.
- Ensured comma-terminated tuples with multiple elements are split onto separate lines.

## [0.16.3] 2017-07-13
### Changed
- Add filename information to a ParseError exception.
### Fixed
- A token that ends in a continuation marker may have more than one newline in
  it, thus changing its "lineno" value. This can happen if multiple
  continuation markers are used with no intervening tokens. Adjust the line
  number to account for the lines covered by those markers.
- Make sure to split after a comment even for "pseudo" parentheses.

## [0.16.2] 2017-05-19
### Fixed
- Treat expansion operators ('*', '**') in a similar way to function calls to
  avoid splitting directly after the opening parenthesis.
- Increase the penalty for splitting after the start of a tuple.
- Increase penalty for excess characters.
- Check that we have enough children before trying to access them all.
- Remove trailing whitespaces from comments.
- Split before a function call in a list if the full list isn't able to fit on
  a single line.
- Trying not to split around the '=' of a named assign.
- Changed split before the first argument behavior to ignore compound
  statements like if and while, but not function declarations.
- Changed coalesce brackets not to line split before closing bracket.

## [0.16.1] 2017-03-22
### Changed
- Improved performance of cloning the format decision state object. This
  improved the time in one *large* case from 273.485s to 234.652s.
- Relax the requirement that a named argument needs to be on one line. Going
  over the column limit is more of an issue to pylint than putting named args
  on multiple lines.
- Don't make splitting penalty decisions based on the original formatting. This
  can and does lead to non-stable formatting, where yapf will reformat the same
  code in different ways.
### Fixed
- Ensure splitting of arguments if there's a named assign present.
- Prefer to coalesce opening brackets if it's not at the beginning of a
  function call.
- Prefer not to squish all of the elements in a function call over to the
  right-hand side. Split the arguments instead.
- We need to split a dictionary value if the first element is a comment anyway,
  so don't force the split here. It's forced elsewhere.
- Ensure tabs are used for continued indentation when USE_TABS is True.

## [0.16.0] 2017-02-05
### Added
- The `EACH_DICT_ENTRY_ON_SEPARATE_LINE` knob indicates that each dictionary
  entry should be in separate lines if the full dictionary isn't able to fit on
  a single line.
- The `SPLIT_BEFORE_DICT_SET_GENERATOR` knob splits before the `for` part of a
  dictionary/set generator.
- The `BLANK_LINE_BEFORE_CLASS_DOCSTRING` knob adds a blank line before a
  class's docstring.
- The `ALLOW_MULTILINE_DICTIONARY_KEYS` knob allows dictionary keys to span
  more than one line.
### Fixed
- Split before all entries in a dict/set or list maker when comma-terminated,
  even if there's only one entry.
- Will now try to set O_BINARY mode on stdout under Windows and Python 2.
- Avoid unneeded newline transformation when writing formatted code to
  output on (affects only Python 2)

## [0.15.2] 2017-01-29
### Fixed
- Don't perform a global split when a named assign is part of a function call
  which itself is an argument to a function call. I.e., don't cause 'a' to
  split here:

      func(a, b, c, d(x, y, z=42))
- Allow splitting inside a subscript if it's a logical or bitwise operating.
  This should keep the subscript mostly contiguous otherwise.

## [0.15.1] 2017-01-21
### Fixed
- Don't insert a space between a type hint and the '=' sign.
- The '@' operator can be used in Python 3 for matrix multiplication. Give the
  '@' in the decorator a DECORATOR subtype to distinguish it.
- Encourage the formatter to split at the beginning of an argument list instead
  of in the middle. Especially if the middle is an empty parameter list. This
  adjusts the affinity of binary and comparison operators. In particular, the
  "not in" and other such operators don't want to have a split after it (or
  before it) if at all possible.

## [0.15.0] 2017-01-12
### Added
- Keep type annotations intact as much as possible. Don't try to split the over
  multiple lines.
### Fixed
- When determining if each element in a dictionary can fit on a single line, we
  are skipping dictionary entries. However, we need to ignore comments in our
  calculations and implicitly concatenated strings, which are already placed on
  separate lines.
- Allow text before a "pylint" comment.
- Also allow text before a "yapf: (disable|enable)" comment.

## [0.14.0] 2016-11-21
### Added
- formatting can be run in parallel using the "-p" / "--parallel" flags.
### Fixed
- "not in" and "is not" should be subtyped as binary operators.
- A non-Node dictionary value may have a comment before it. In those cases, we
  want to avoid encompassing only the comment in pseudo parens. So we include
  the actual value as well.
- Adjust calculation so that pseudo-parentheses don't count towards the total
  line length.
- Don't count a dictionary entry as not fitting on a single line in a
  dictionary.
- Don't count pseudo-parentheses in the length of the line.

## [0.13.2] 2016-10-22
### Fixed
- REGRESSION: A comment may have a prefix with newlines in it. When calculating
  the prefix indent, we cannot take the newlines into account. Otherwise, the
  comment will be misplaced causing the code to fail.

## [0.13.1] 2016-10-17
### Fixed
- Correct emitting a diff that was accidentally removed.

## [0.13.0] 2016-10-16
### Added
- Added support to retain the original line endings of the source code.

### Fixed
- Functions or classes with comments before them were reformatting the comments
  even if the code was supposed to be ignored by the formatter. We now don't
  adjust the whitespace before a function's comment if the comment is a
  "disabled" line. We also don't count "# yapf: {disable|enable}" as a disabled
  line, which seems logical.
- It's not really more readable to split before a dictionary value if it's part
  of a dictionary comprehension.
- Enforce two blank lines after a function or class definition, even before a
  comment. (But not between a decorator and a comment.) This is related to PEP8
  error E305.
- Remove O(n^2) algorithm from the line disabling logic.

## [0.12.2] 2016-10-09
### Fixed
- If `style.SetGlobalStyle(<create pre-defined style>)` was called and then
  `yapf_api.FormatCode` was called, the style set by the first call would be
  lost, because it would return the style created by `DEFAULT_STYLE_FACTORY`,
  which is set to PEP8 by default. Fix this by making the first call set which
  factory we call as the "default" style.
- Don't force a split before non-function call arguments.
- A dictionary being used as an argument to a function call and which can exist
  on a single line shouldn't be split.
- Don't rely upon the original line break to determine if we should split
  before the elements in a container. Especially split if there's a comment in
  the container.
- Don't add spaces between star and args in a lambda expression.
- If a nested data structure terminates in a comma, then split before the first
  element, but only if there's more than one element in the list.

## [0.12.1] 2016-10-02
### Changed
- Dictionary values will be placed on the same line as the key if *all* of the
  elements in the dictionary can be placed on one line. Otherwise, the
  dictionary values will be placed on the next line.

### Fixed
- Prefer to split before a terminating r-paren in an argument list if the line
  would otherwise go over the column limit.
- Split before the first key in a dictionary if the dictionary cannot fit on a
  single line.
- Don't count "pylint" comments when determining if the line goes over the
  column limit.
- Don't count the argument list of a lambda as a named assign in a function
  call.

## [0.12.0] 2016-09-25
### Added
- Support formatting of typed names. Typed names are formatted a similar way to
  how named arguments are formatted, except that there's a space after the
  colon.
- Add a knob, 'SPACES_AROUND_DEFAULT_OR_NAMED_ASSIGN', to allow adding spaces
  around the assign operator on default or named assigns.

## Changed
- Turn "verification" off by default for external APIs.
- If a function call in an argument list won't fit on the current line but will
  fit on a line by itself, then split before the call so that it won't be split
  up unnecessarily.

## Fixed
- Don't add space after power operator if the next operator's a unary operator.

## [0.11.1] 2016-08-17
### Changed
- Issue #228: Return exit code 0 on success, regardless of whether files were
  changed.  (Previously, 0 meant success with no files
  modified, and 2 meant success with at least one file modified.)

### Fixed
- Enforce splitting each element in a dictionary if comma terminated.
- It's okay to split in the middle of a dotted name if the whole expression is
  going to go over the column limit.
- Asynchronous functions were going missing if they were preceded by a comment
  (a what? exactly). The asynchronous function processing wasn't taking the
  comment into account and thus skipping the whole function.
- The splitting of arguments when comma terminated had a conflict. The split
  penalty of the closing bracket was set to the maximum, but it shouldn't be if
  the closing bracket is preceded by a comma.

## [0.11.0] 2016-07-17
### Added
- The COALESCE_BRACKETS knob prevents splitting consecutive brackets when
  DEDENT_CLOSING_BRACKETS is set.
- Don't count "pylint" directives as exceeding the column limit.

### Changed
- We split all of the arguments to a function call if there's a named argument.
  In this case, we want to split after the opening bracket too. This makes
  things look a bit better.

### Fixed
- When retaining format of a multiline string with Chromium style, make sure
  that the multiline string doesn't mess up where the following comma ends up.
- Correct for when 'lib2to3' smooshes comments together into the same DEDENT
  node.

## [0.10.0] 2016-06-14
### Added
- Add a knob, 'USE_TABS', to allow using tabs for indentation.

### Changed
- Performance enhancements.

### Fixed
- Don't split an import list if it's not surrounded by parentheses.

## [0.9.0] 2016-05-29
### Added
- Added a knob (SPLIT_PENALTY_BEFORE_IF_EXPR) to adjust the split penalty
  before an if expression. This allows the user to place a list comprehension
  all on one line.
- Added a knob (SPLIT_BEFORE_FIRST_ARGUMENT) that encourages splitting before
  the first element of a list of arguments or parameters if they are going to
  be split anyway.
- Added a knob (SPLIT_ARGUMENTS_WHEN_COMMA_TERMINATED) splits arguments to a
  function if the list is terminated by a comma.

### Fixed
- Don't split before a first element list argument as we would before a first
  element function call.
- Don't penalize when we must split a line.
- Allow splitting before the single argument in a function call.

## [0.8.2] 2016-05-21
### Fixed
- Prefer not to split after the opening of a subscript.
- Don't add space before the 'await' keyword if it's preceded by an opening
  paren.
- When we're setting the split penalty for a continuous list, we don't want to
  mistake a comment at the end of that list as part of the list.
- When calculating blank lines, don't assume the last seen object was a class
  or function when we're in a class or function.
- Don't count the closing scope when determining if the current scope is the
  last scope on the line.

## [0.8.1] 2016-05-18
### Fixed
- 'SPLIT_BEFORE_LOGICAL_OPERATOR' wasn't working correctly. The penalty was
  being set incorrectly when it was part of a larger construct.
- Don't separate a keyword, like "await", from a left paren.
- Don't rely upon the original tokens' line number to determine if we should
  perform splitting in Facebook mode. The line number isn't the line number of
  the reformatted token, but the line number where it was in the original code.
  Instead, we need to carefully determine if the line is liabel to be split and
  act accordingly.

## [0.8.0] 2016-05-10
### Added
- Add a knob, 'SPACES_AROUND_POWER_OPERATOR', to allow adding spaces around the
  power operator.

### Fixed
- There shouldn't be a space between a decorator and an intervening comment.
- If we split before a bitwise operator, then we assume that the programmer
  knows what they're doing, more or less, and so we enforce a split before said
  operator if one exists in the original program.
- Strengthen the bond between a keyword and value argument.
- Don't add a blank line after a multiline string.
- If the "for" part of a list comprehension can exist on the starting line
  without going over the column limit, then let it remain there.

## [0.7.1] 2016-04-21
### Fixed
- Don't rewrite the file if there are no changes.
- Ensure the proper number of blank lines before an async function.
- Split after a bitwise operator when in PEP 8 mode.
- Retain the splitting within a dictionary data literal between the key and
  value.
- Try to keep short function calls all on one line even if they're part of a
  larger series of tokens. This stops us from splitting too much.

## [0.7.0] 2016-04-09
### Added
- Support for Python 3.5.
- Add 'ALLOW_MULTILINE_LAMBDAS' which allows lambdas to be formatted onto
  multiple lines.

### Fixed
- Lessen penalty for splitting before a dictionary keyword.
- Formatting of trailing comments on disabled formatting lines.
- Disable / enable formatting at end of multi-line comment.

## [0.6.3] 2016-03-06
### Changed
- Documentation updated.

### Fixed
- Fix spacing of multiline comments when formatting is disabled.

## [0.6.2] 2015-11-01
### Changed
- Look at the 'setup.cfg' file to see if it contains style information for
  YAPF.
- Look at the '~/.config/yapf/style' file to see if it contains global style
  information for YAPF.

### Fixed
- Make lists that can fit on one line more likely to stay together.
- Correct formatting of '*args' and '**kwargs' when there are default values in
  the argument list.

## [0.6.1] 2015-10-24
### Fixed
- Make sure to align comments in data literals correctly. Also make sure we
  don't count a "#." in a string as an i18n comment.
- Retain proper vertical spacing before comments in a data literal.
- Make sure that continuations from a compound statement are distinguished from
  the succeeding line.
- Ignore preceding comments when calculating what is a "dictionary maker".
- Add a small penalty for splitting before a closing bracket.
- Ensure that a space is enforced after we remove a pseudo-paren that's between
  two names, keywords, numbers, etc.
- Increase the penalty for splitting after a pseudo-paren. This could lead to
  less readable code in some circumstances.

## [0.6.0] 2015-10-18
### Added
- Add knob to indent the dictionary value if there is a split before it.

### Changed
- No longer check that a file is a "Python" file unless the '--recursive' flag
  is specified.
- No longer allow the user to specify a directory unless the '--recursive' flag
  is specified.

### Fixed
- When determining if we should split a dictionary's value to a new line, use
  the longest entry instead of the total dictionary's length. This allows the
  formatter to reformat the dictionary in a more consistent manner.
- Improve how list comprehensions are formatted. Make splitting dependent upon
  whether the "comp_for" or "comp_if" goes over the column limit.
- Don't over indent if expression hanging indents if we expect to dedent the
  closing bracket.
- Improve splitting heuristic when the first argument to a function call is
  itself a function call with arguments. In cases like this, the remaining
  arguments to the function call would look badly aligned, even though they are
  technically correct (the best kind of correct!).
- Improve splitting heuristic more so that if the first argument to a function
  call is a data literal that will go over the column limit, then we want to
  split before it.
- Remove spaces around '**' operator.
- Retain formatting of comments in the middle of an expression.
- Don't add a newline to an empty file.
- Over indent a function's parameter list if it's not distinguished from the
  body of the function.

## [0.5.0] 2015-10-11
### Added
- Add option to exclude files/directories from formatting.
- Add a knob to control whether import names are split after the first '('.

### Fixed
- Indent the continuation of an if-then statement when it's not distinguished
  from the body of the if-then.
- Allow for sensible splitting of array indices where appropriate.
- Prefer to not split before the ending bracket of an atom. This produces
  better code in most cases.
- Corrected how horizontal spaces were presevered in a disabled region.

## [0.4.0] 2015-10-07
### Added
- Support for dedenting closing brackets, "facebook" style.

### Fixed
- Formatting of tokens after a multiline string didn't retain their horizontal
  spacing.

## [0.3.1] 2015-09-30
### Fixed
- Format closing scope bracket correctly when indentation size changes.

## [0.3.0] 2015-09-20
### Added
- Return a 2 if the source changed, 1 on error, and 0 for no change.

### Fixed
- Make sure we format if the "lines" specified are in the middle of a
  statement.

## [0.2.9] - 2015-09-13
### Fixed
- Formatting of multiple files. It was halting after formatting the first file.

## [0.2.8] - 2015-09-12
### Added
- Return a non-zero exit code if the source was changed.
- Add bitwise operator splitting penalty and prefer to split before bitwise
  operators.

### Fixed
- Retain vertical spacing between disabled and enabled lines.
- Split only at start of named assign.
- Retain comment position when formatting is disabled.
- Honor splitting before or after logical ops.
