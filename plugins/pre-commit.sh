#!/usr/bin/env bash

# Git pre-commit hook to check staged Python files for formatting issues with
# yapf.
#
# INSTALLING: Copy this script into `.git/hooks/pre-commit`, and mark it as
# executable.
#
# This requires that yapf is installed and runnable in the environment running
# the pre-commit hook.
#
# When running, this first checks for unstaged changes to staged files, and if
# there are any, it will exit with an error. Files with unstaged changes will be
# printed.
#
# If all staged files have no unstaged changes, it will run yapf against them,
# leaving the formatting changes unstaged. Changed files will be printed.
#
# BUGS: This does not leave staged changes alone when used with the -a flag to
# git commit, due to the fact that git stages ALL unstaged files when that flag
# is used.

# Find all staged Python files, and exit early if there aren't any.
PYTHON_FILES=()
while IFS=$'\n' read -r line; do PYTHON_FILES+=("$line"); done \
  < <(git diff --name-only --cached --diff-filter=AM | grep --color=never '.py$')
if [ ${#PYTHON_FILES[@]} -eq 0 ]; then
  exit 0
fi

########## PIP VERSION #############
# Verify that yapf is installed; if not, warn and exit.
if ! command -v yapf >/dev/null; then
  echo 'yapf not on path; can not format. Please install yapf:'
  echo '    pip install yapf'
  exit 2
fi
######### END PIP VERSION ##########

########## PIPENV VERSION ##########
# if ! pipenv run yapf --version 2>/dev/null 2>&1; then
#   echo 'yapf not on path; can not format. Please install yapf:'
#   echo '    pipenv install yapf'
#   exit 2
# fi
###### END PIPENV VERSION ##########


# Check for unstaged changes to files in the index.
CHANGED_FILES=()
while IFS=$'\n' read -r line; do CHANGED_FILES+=("$line"); done \
  < <(git diff --name-only "${PYTHON_FILES[@]}")
if [ ${#CHANGED_FILES[@]} -gt 0 ]; then
  echo 'You have unstaged changes to some files in your commit; skipping '
  echo 'auto-format. Please stage, stash, or revert these changes. You may '
  echo 'find `git stash -k` helpful here.'
  echo 'Files with unstaged changes:' "${CHANGED_FILES[@]}"
  exit 1
fi

# Format all staged files, then exit with an error code if any have uncommitted
# changes.
echo 'Formatting staged Python files . . .'

########## PIP VERSION #############
yapf -i -r "${PYTHON_FILES[@]}"
######### END PIP VERSION ##########

########## PIPENV VERSION ##########
# pipenv run yapf -i -r "${PYTHON_FILES[@]}"
###### END PIPENV VERSION ##########


CHANGED_FILES=()
while IFS=$'\n' read -r line; do CHANGED_FILES+=("$line"); done \
  < <(git diff --name-only "${PYTHON_FILES[@]}")
if [ ${#CHANGED_FILES[@]} -gt 0 ]; then
  echo 'Reformatted staged files. Please review and stage the changes.'
  echo 'Files updated: ' "${CHANGED_FILES[@]}"
  exit 1
else
  exit 0
fi
