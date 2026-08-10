# semver

A Semantic Versioning 2.0.0 implementation: parsing, precedence and
constraint matching.

**The full specification is in [`TASK.md`](TASK.md).** This file only
describes the layout of the repository.

```
semver.py            the module you implement (stub)
tests/               public smoke tests - read-only
```

## Running the tests

```sh
python3 -m unittest -v tests.test_version
python3 -m unittest -v tests.test_constraints
```

Run from the repository root. Standard library only (Python 3.9+).

## Trying it by hand

```sh
python3 -c 'import semver; print(semver.max_satisfying(["1.2.3","1.3.0","2.0.0"], "^1.2"))'
```
