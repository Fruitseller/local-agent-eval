"""Public smoke tests for parsing, canonical form and precedence.

Read-only: the benchmark restores this directory before scoring. These tests
cover a subset of TASK.md; the hidden suite covers the rest.
"""

import unittest

import semver


class ParseTest(unittest.TestCase):
    def test_plain_version(self):
        version = semver.parse("1.2.3")
        self.assertEqual((version.major, version.minor, version.patch), (1, 2, 3))
        self.assertEqual(version.prerelease, ())
        self.assertEqual(version.build, ())

    def test_prerelease_and_build(self):
        version = semver.parse("1.0.0-alpha.1+exp.sha.5114f85")
        self.assertEqual(version.prerelease, ("alpha", "1"))
        self.assertEqual(version.build, ("exp", "sha", "5114f85"))

    def test_zero_components_are_allowed(self):
        self.assertEqual(str(semver.parse("0.0.0")), "0.0.0")

    def test_canonical_string_round_trip(self):
        for text in ("1.2.3", "1.0.0-rc.1", "0.1.0+build.7", "2.0.0-alpha.beta+1.2"):
            with self.subTest(text=text):
                self.assertEqual(str(semver.parse(text)), text)

    def test_invalid_versions(self):
        for text in ("1.2", "v1.2.3", "1.2.3.4", "01.2.3", "1.2.3-", "1.2.3-a..b", " 1.2.3", "1.2.3-01"):
            with self.subTest(text=text):
                with self.assertRaises(semver.InvalidVersion):
                    semver.parse(text)

    def test_constructor_validates_identifiers(self):
        with self.assertRaises(semver.InvalidVersion):
            semver.Version(1, 0, 0, prerelease=("al pha",))


class PrecedenceTest(unittest.TestCase):
    def test_numeric_components(self):
        self.assertEqual(semver.compare("1.0.0", "2.0.0"), -1)
        self.assertEqual(semver.compare("2.1.0", "2.0.9"), 1)
        self.assertEqual(semver.compare("1.2.3", "1.2.3"), 0)

    def test_prerelease_is_lower_than_release(self):
        self.assertEqual(semver.compare("1.0.0-rc.1", "1.0.0"), -1)

    def test_prerelease_ordering(self):
        ordered = [
            "1.0.0-alpha",
            "1.0.0-alpha.1",
            "1.0.0-alpha.beta",
            "1.0.0-beta",
            "1.0.0-beta.2",
            "1.0.0-beta.11",
            "1.0.0-rc.1",
            "1.0.0",
        ]
        for lower, higher in zip(ordered, ordered[1:]):
            with self.subTest(pair=(lower, higher)):
                self.assertEqual(semver.compare(lower, higher), -1)
                self.assertEqual(semver.compare(higher, lower), 1)

    def test_build_metadata_is_ignored(self):
        self.assertEqual(semver.compare("1.0.0+a", "1.0.0+b"), 0)
        self.assertTrue(semver.parse("1.0.0+a") == semver.parse("1.0.0+b"))
        self.assertEqual(len({semver.parse("1.0.0+a"), semver.parse("1.0.0+b")}), 1)

    def test_rich_comparison(self):
        self.assertTrue(semver.parse("1.0.0") < semver.parse("1.0.1"))
        self.assertTrue(semver.parse("1.0.1") >= semver.parse("1.0.1"))
        self.assertTrue(semver.parse("1.0.0") != semver.parse("1.0.1"))

    def test_comparison_with_other_types(self):
        self.assertFalse(semver.parse("1.0.0") == "1.0.0")
        with self.assertRaises(TypeError):
            semver.parse("1.0.0") < "1.0.0"

    def test_sorting(self):
        versions = ["1.10.0", "1.2.0", "1.2.0-rc.1"]
        self.assertEqual([str(v) for v in sorted(semver.parse(v) for v in versions)],
                         ["1.2.0-rc.1", "1.2.0", "1.10.0"])


if __name__ == "__main__":
    unittest.main()
