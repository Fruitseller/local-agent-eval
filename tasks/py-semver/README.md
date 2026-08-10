# Task: `semver` — versions, precedence and constraints

Implement `semver.py`, a module that parses [Semantic Versioning
2.0.0](https://semver.org) strings, orders them by precedence, and decides
whether a version satisfies a constraint expression.

Python 3.9+, **standard library only**. No new dependencies, no network.
Everything under `tests/` is read-only and restored before scoring.

---

## 1. Version syntax

```
<major> "." <minor> "." <patch> [ "-" <prerelease> ] [ "+" <build> ]
```

* `major`, `minor`, `patch` — non-negative decimal integers **without leading
  zeros** (`0` itself is fine, `01` is not).
* `prerelease` — one or more dot-separated identifiers. An identifier is
  non-empty and consists of `[0-9A-Za-z-]`. A **numeric** identifier (digits
  only) must not have leading zeros.
* `build` — one or more dot-separated identifiers of `[0-9A-Za-z-]`. Build
  identifiers may be numeric with leading zeros.

Anything else is invalid, including a leading `v`, missing components
(`1.2`), empty identifiers (`1.2.3-`, `1.2.3-a..b`) and surrounding
whitespace.

## 2. Precedence

Compare `major`, then `minor`, then `patch` numerically.

If those are equal:

* a version **with** a prerelease is **lower** than the same version without
  one (`1.0.0-rc.1 < 1.0.0`);
* otherwise compare prerelease identifiers left to right:
  * both numeric → compare numerically;
  * both non-numeric → compare as ASCII strings;
  * numeric is **lower** than non-numeric;
  * if all shared identifiers are equal, the version with **fewer**
    identifiers is lower (`1.0.0-alpha < 1.0.0-alpha.1`).

Build metadata is **ignored** for precedence and for equality:
`1.0.0+a == 1.0.0+b` is true.

## 3. Module API

`semver.py` lives in the repository root and exposes exactly these names.

### `InvalidVersion(ValueError)` and `InvalidConstraint(ValueError)`

Raised for malformed versions and malformed constraints.

### `class Version`

```python
Version(major, minor, patch, prerelease=(), build=())
```

`prerelease` and `build` are iterables of identifier strings; invalid
identifiers raise `InvalidVersion`. Attributes:

| Attribute | Type |
|---|---|
| `major`, `minor`, `patch` | `int` |
| `prerelease` | `tuple` of `str` (empty when absent) |
| `build` | `tuple` of `str` (empty when absent) |

* `str(v)` returns the canonical string, e.g. `1.2.3-alpha.1+build.5`.
* `repr(v)` is unspecified but must not raise.
* `<`, `<=`, `>`, `>=`, `==`, `!=` follow section 2. Comparison against a
  non-`Version` object returns `NotImplemented` (so Python raises `TypeError`
  for ordering and falls back to identity for `==`).
* `hash(v)` ignores build metadata, so two versions that compare equal hash
  equally and can share a `set` slot.

### `parse(text) -> Version`

Parses a version string; raises `InvalidVersion` on anything invalid.
`parse` accepts `str` only.

### `compare(a, b) -> int`

Returns `-1`, `0` or `1`. Both arguments may be `str` or `Version`.

### `satisfies(version, constraint) -> bool`

`version` is a `str` or `Version`, `constraint` a `str` (section 4).

### `max_satisfying(versions, constraint) -> str | None`

`versions` is an iterable of version strings. Returns the **highest**
satisfying version, as the original input string, or `None` if none matches.
When several inputs are equal in precedence (they differ only in build
metadata), return the one that appears **first** in `versions`. An invalid
version string in `versions` raises `InvalidVersion`.

## 4. Constraint syntax

A constraint is one or more **comparator sets** separated by `||` (OR).
A comparator set is one or more comparators separated by whitespace and/or
commas (AND). A version satisfies the constraint when it satisfies at least
one comparator set, i.e. every comparator in it.

A comparator is an operator followed by a version, with optional whitespace
between them:

| Operator | Meaning |
|---|---|
| `=` or none | exactly equal (build metadata ignored) |
| `!=` | not equal |
| `>` `>=` `<` `<=` | precedence comparison |
| `~` | "same minor": see below |
| `^` | "compatible with": see below |
| `*` | any version (no operand) |

For `=`, `!=`, `<`, `<=`, `>`, `>=` a missing `minor` or `patch` is filled
with `0`: `>=1.2` means `>=1.2.0`, and `=1.2` means exactly `1.2.0`.

### Tilde `~`

| Constraint | Range |
|---|---|
| `~1.2.3` | `>=1.2.3 <1.3.0` |
| `~1.2` | `>=1.2.0 <1.3.0` |
| `~1` | `>=1.0.0 <2.0.0` |

### Caret `^`

Allows changes that do not modify the leftmost **specified** non-zero
component:

| Constraint | Range |
|---|---|
| `^1.2.3` | `>=1.2.3 <2.0.0` |
| `^0.2.3` | `>=0.2.3 <0.3.0` |
| `^0.0.3` | `>=0.0.3 <0.0.4` |
| `^1.2` | `>=1.2.0 <2.0.0` |
| `^0.0` | `>=0.0.0 <0.1.0` |
| `^0` | `>=0.0.0 <1.0.0` |

The upper bound is always exclusive.

### Prereleases

A version **with** a prerelease satisfies a comparator set only if that set
contains at least one comparator whose operand has a prerelease **and** the
same `major.minor.patch`. Otherwise the version is rejected even when it
falls inside the range.

```python
satisfies("1.2.3-rc.1", ">=1.0.0")             # False
satisfies("1.2.3-rc.1", ">=1.2.3-rc.0")        # True
satisfies("1.2.4-rc.1", ">=1.2.3-rc.0")        # False  (different triple)
satisfies("1.2.3", ">=1.2.3-rc.0")             # True   (no prerelease in the version)
```

This rule is evaluated per comparator set, so
`">=1.2.3-rc.0 <2.0.0 || >=3.0.0"` still rejects `3.1.0-beta`.

### Errors

An empty constraint, an unknown operator, a missing operand, a `*` with an
operand, or an operand that is not a (possibly partial) version raises
`InvalidConstraint`. Constraints never raise `InvalidVersion`.

## 5. Public tests

```
python3 -m unittest -v tests.test_version
python3 -m unittest -v tests.test_constraints
```

Hidden tests check the same specification on further edge cases — in
particular the precedence table of section 2 and the prerelease rule of
section 4.
