#!/usr/bin/env python3
"""semver - semantic versions, precedence and constraints.

This is a stub. The public API is declared here so the test suites import
cleanly; the behaviour is specified in TASK.md and not implemented yet.

Standard library only.
"""

from __future__ import annotations


class InvalidVersion(ValueError):
    """Raised when a version string or component is not valid SemVer."""


class InvalidConstraint(ValueError):
    """Raised when a constraint expression cannot be parsed."""


class Version:
    """An immutable semantic version. See TASK.md section 3."""

    def __init__(self, major, minor, patch, prerelease=(), build=()):
        raise NotImplementedError("Version is not implemented yet")


def parse(text):
    """Parse a version string into a :class:`Version`."""
    raise NotImplementedError("parse is not implemented yet")


def compare(a, b):
    """Return -1, 0 or 1 for the precedence of *a* against *b*."""
    raise NotImplementedError("compare is not implemented yet")


def satisfies(version, constraint):
    """Return True when *version* satisfies the constraint expression."""
    raise NotImplementedError("satisfies is not implemented yet")


def max_satisfying(versions, constraint):
    """Return the highest version string that satisfies *constraint*."""
    raise NotImplementedError("max_satisfying is not implemented yet")
