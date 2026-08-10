"""Public smoke tests for satisfies() and max_satisfying().

Read-only: the benchmark restores this directory before scoring. These tests
cover a subset of TASK.md; the hidden suite covers the rest.
"""

import unittest

import semver


class SatisfiesTest(unittest.TestCase):
    def assertMatches(self, version, constraint, expected):
        self.assertIs(
            semver.satisfies(version, constraint),
            expected,
            f"{version!r} vs {constraint!r}",
        )

    def test_equality(self):
        self.assertMatches("1.2.3", "1.2.3", True)
        self.assertMatches("1.2.3", "=1.2.3", True)
        self.assertMatches("1.2.3+build", "1.2.3", True)
        self.assertMatches("1.2.4", "1.2.3", False)
        self.assertMatches("1.2.4", "!=1.2.3", True)

    def test_inequalities(self):
        self.assertMatches("1.2.3", ">=1.2.3", True)
        self.assertMatches("1.2.3", ">1.2.3", False)
        self.assertMatches("1.2.3", "<2.0.0", True)
        self.assertMatches("2.0.0", "<=2.0.0", True)

    def test_partial_operands_are_zero_filled(self):
        self.assertMatches("1.2.0", ">=1.2", True)
        self.assertMatches("1.1.9", ">=1.2", False)

    def test_and_within_a_comparator_set(self):
        self.assertMatches("1.5.0", ">=1.2.0 <2.0.0", True)
        self.assertMatches("2.0.0", ">=1.2.0 <2.0.0", False)
        self.assertMatches("1.5.0", ">=1.2.0,<2.0.0", True)

    def test_or_between_comparator_sets(self):
        self.assertMatches("3.1.0", ">=1.2.0 <2.0.0 || >=3.0.0", True)
        self.assertMatches("2.5.0", ">=1.2.0 <2.0.0 || >=3.0.0", False)

    def test_tilde(self):
        self.assertMatches("1.2.9", "~1.2.3", True)
        self.assertMatches("1.3.0", "~1.2.3", False)
        self.assertMatches("1.2.0", "~1.2", True)
        self.assertMatches("1.9.9", "~1", True)
        self.assertMatches("2.0.0", "~1", False)

    def test_caret(self):
        self.assertMatches("1.9.9", "^1.2.3", True)
        self.assertMatches("2.0.0", "^1.2.3", False)
        self.assertMatches("0.2.9", "^0.2.3", True)
        self.assertMatches("0.3.0", "^0.2.3", False)
        self.assertMatches("0.0.3", "^0.0.3", True)
        self.assertMatches("0.0.4", "^0.0.3", False)
        self.assertMatches("0.9.9", "^0", True)
        self.assertMatches("1.0.0", "^0", False)

    def test_star(self):
        self.assertMatches("0.0.1", "*", True)
        self.assertMatches("99.0.0", "*", True)

    def test_prerelease_rule(self):
        self.assertMatches("1.2.3-rc.1", ">=1.0.0", False)
        self.assertMatches("1.2.3-rc.1", "*", False)
        self.assertMatches("1.2.3-rc.1", ">=1.2.3-rc.0", True)
        self.assertMatches("1.2.4-rc.1", ">=1.2.3-rc.0", False)
        self.assertMatches("1.2.3", ">=1.2.3-rc.0", True)
        self.assertMatches("3.1.0-beta", ">=1.2.3-rc.0 <2.0.0 || >=3.0.0", False)

    def test_whitespace_between_operator_and_operand(self):
        self.assertMatches("1.5.0", ">= 1.2.0", True)

    def test_version_object_is_accepted(self):
        self.assertMatches(semver.parse("1.5.0"), "^1.0.0", True)

    def test_invalid_constraints(self):
        for constraint in ("", "   ", ">>1.2.3", ">=", "*1.2.3", ">=abc"):
            with self.subTest(constraint=constraint):
                with self.assertRaises(semver.InvalidConstraint):
                    semver.satisfies("1.2.3", constraint)


class MaxSatisfyingTest(unittest.TestCase):
    VERSIONS = ["1.2.0", "1.2.9", "1.3.0", "2.0.0", "1.4.0-rc.1"]

    def test_picks_the_highest_match(self):
        self.assertEqual(semver.max_satisfying(self.VERSIONS, "^1.0.0"), "1.3.0")
        self.assertEqual(semver.max_satisfying(self.VERSIONS, "~1.2"), "1.2.9")

    def test_no_match_returns_none(self):
        self.assertIsNone(semver.max_satisfying(self.VERSIONS, ">=3.0.0"))

    def test_ties_keep_the_first_input(self):
        self.assertEqual(semver.max_satisfying(["1.0.0+a", "1.0.0+b"], "1.0.0"), "1.0.0+a")

    def test_invalid_version_in_the_list(self):
        with self.assertRaises(semver.InvalidVersion):
            semver.max_satisfying(["1.0.0", "nope"], "*")


if __name__ == "__main__":
    unittest.main()
