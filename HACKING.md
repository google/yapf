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

- Run tests with Python 3.7 and 3.11:

```bash
$ python setup.py test
```

- Bump version in `setup.py`.

- Build source distribution:

```bash
$ python setup.py sdist
```

- Check that it looks OK.
  - Install it onto a virtualenv,
  - run tests, and
  - run yapf as a tool.

- Build release:

```bash
$ python setup.py sdist bdist_wheel
```

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
