## Running YAPF on itself

- To run YAPF on all of YAPF:

```bash
$ PYTHONPATH=$PWD/yapf python -m yapf -i -r .
```

- To run YAPF on just the files changed in the current git branch:

```bash
$ PYTHONPATH=$PWD/yapf python -m yapf -i $(git diff --name-only @{upstream})
```

## Releasing a new version

- Run tests against Python 3.7 - 3.11 with `tox`

- Bump version in `pyproject.toml`.

- Build distributions with `build`

- Check that it looks OK.
  - Install it onto a virtualenv,
  - run tests, and
  - run yapf as a tool.

- Push to PyPI:

```bash
$ twine upload dist/*
```

- Test in a clean virtualenv that 'pip install yapf' works with the new
  version.

- Commit the version bump and add tag with:

```bash
$ git tag v$(VERSION_NUM)
$ git push --tags
```
