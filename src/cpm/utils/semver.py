"""
Semantic versioning utilities
"""

import re
from typing import Optional, Tuple


class SemanticVersion:
    """Semantic version parser and comparator"""

    def __init__(self, version: str):
        """
        Parse semantic version string

        Args:
            version: Version string (e.g., "1.2.3", "1.2.3-alpha.1", "1.2.3+build.123")
        """
        self.original = version
        self.major = 0
        self.minor = 0
        self.patch = 0
        self.prerelease = None
        self.build = None

        # Handle special versions
        if version in ["latest", "linked"]:
            self.major = 999999  # Very high version for comparison
            return

        # Parse semver
        self._parse(version)

    def _parse(self, version: str):
        """Parse semver string"""
        # Semver regex pattern
        pattern = r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"

        match = re.match(pattern, version)

        if not match:
            raise ValueError(f"Invalid semver: {version}")

        self.major = int(match.group(1))
        self.minor = int(match.group(2))
        self.patch = int(match.group(3))
        self.prerelease = match.group(4)
        self.build = match.group(5)

    def __str__(self) -> str:
        """String representation"""
        if self.original in ["latest", "linked"]:
            return self.original

        version = f"{self.major}.{self.minor}.{self.patch}"

        if self.prerelease:
            version += f"-{self.prerelease}"

        if self.build:
            version += f"+{self.build}"

        return version

    def __repr__(self) -> str:
        return f"SemanticVersion('{str(self)}')"

    def __eq__(self, other) -> bool:
        """Equality comparison"""
        if not isinstance(other, SemanticVersion):
            return False

        return (
            self.major == other.major
            and self.minor == other.minor
            and self.patch == other.patch
            and self.prerelease == other.prerelease
        )

    def __lt__(self, other) -> bool:
        """Less than comparison"""
        if not isinstance(other, SemanticVersion):
            return NotImplemented

        # Compare major.minor.patch
        if self.major != other.major:
            return self.major < other.major

        if self.minor != other.minor:
            return self.minor < other.minor

        if self.patch != other.patch:
            return self.patch < other.patch

        # Handle prerelease versions
        # No prerelease > has prerelease
        if self.prerelease is None and other.prerelease is None:
            return False

        if self.prerelease is None:
            return False  # 1.0.0 > 1.0.0-alpha

        if other.prerelease is None:
            return True  # 1.0.0-alpha < 1.0.0

        # Compare prerelease strings
        return self._compare_prerelease(self.prerelease, other.prerelease) < 0

    def __le__(self, other) -> bool:
        return self == other or self < other

    def __gt__(self, other) -> bool:
        return not self <= other

    def __ge__(self, other) -> bool:
        return not self < other

    def _compare_prerelease(self, pr1: str, pr2: str) -> int:
        """
        Compare prerelease strings

        Returns:
            -1 if pr1 < pr2
            0 if pr1 == pr2
            1 if pr1 > pr2
        """
        parts1 = pr1.split(".")
        parts2 = pr2.split(".")

        for i in range(max(len(parts1), len(parts2))):
            # Get parts or None if out of range
            p1 = parts1[i] if i < len(parts1) else None
            p2 = parts2[i] if i < len(parts2) else None

            # Shorter prerelease < longer prerelease
            if p1 is None:
                return -1
            if p2 is None:
                return 1

            # Try numeric comparison
            try:
                n1 = int(p1)
                n2 = int(p2)

                if n1 < n2:
                    return -1
                elif n1 > n2:
                    return 1

            except ValueError:
                # String comparison
                if p1 < p2:
                    return -1
                elif p1 > p2:
                    return 1

        return 0


def parse_version(version: str) -> Optional[SemanticVersion]:
    """
    Parse version string into SemanticVersion

    Args:
        version: Version string

    Returns:
        SemanticVersion or None if invalid
    """
    try:
        return SemanticVersion(version)
    except ValueError:
        return None


def compare_versions(v1: str, v2: str) -> int:
    """
    Compare two version strings

    Args:
        v1: First version
        v2: Second version

    Returns:
        -1 if v1 < v2
        0 if v1 == v2
        1 if v1 > v2
    """
    sv1 = parse_version(v1)
    sv2 = parse_version(v2)

    if sv1 is None or sv2 is None:
        raise ValueError("Invalid version string")

    if sv1 < sv2:
        return -1
    elif sv1 > sv2:
        return 1
    else:
        return 0


def satisfies_range(version: str, range_spec: str) -> bool:
    """
    Check if version satisfies a semver range

    Supports:
    - Exact: "1.2.3"
    - Caret: "^1.2.3" (compatible with 1.x.x)
    - Tilde: "~1.2.3" (compatible with 1.2.x)
    - Greater: ">1.2.3", ">=1.2.3"
    - Less: "<1.2.3", "<=1.2.3"
    - Wildcard: "1.2.x", "1.x"

    Args:
        version: Version to check
        range_spec: Range specification

    Returns:
        True if version satisfies range
    """
    sv = parse_version(version)

    if sv is None:
        return False

    # Handle special cases
    if range_spec == "latest":
        return True

    # Handle caret (^)
    if range_spec.startswith("^"):
        base_version = range_spec[1:]
        base = parse_version(base_version)

        if base is None:
            return False

        # Compatible with same major version
        return sv.major == base.major and sv >= base

    # Handle tilde (~)
    if range_spec.startswith("~"):
        base_version = range_spec[1:]
        base = parse_version(base_version)

        if base is None:
            return False

        # Compatible with same major.minor version
        return (
            sv.major == base.major and sv.minor == base.minor and sv.patch >= base.patch
        )

    # Handle comparison operators
    if range_spec.startswith(">="):
        base = parse_version(range_spec[2:].strip())
        return sv >= base if base else False

    if range_spec.startswith(">"):
        base = parse_version(range_spec[1:].strip())
        return sv > base if base else False

    if range_spec.startswith("<="):
        base = parse_version(range_spec[2:].strip())
        return sv <= base if base else False

    if range_spec.startswith("<"):
        base = parse_version(range_spec[1:].strip())
        return sv < base if base else False

    # Handle wildcards
    if "x" in range_spec or "*" in range_spec:
        parts = range_spec.replace("*", "x").split(".")

        if len(parts) >= 1 and parts[0] != "x":
            if sv.major != int(parts[0]):
                return False

        if len(parts) >= 2 and parts[1] != "x":
            if sv.minor != int(parts[1]):
                return False

        if len(parts) >= 3 and parts[2] != "x":
            if sv.patch != int(parts[2]):
                return False

        return True

    # Exact match
    base = parse_version(range_spec)

    if base is None:
        return False

    return sv == base


def increment_version(version: str, level: str = "patch") -> str:
    """
    Increment version number

    Args:
        version: Current version
        level: Which part to increment (major, minor, patch)

    Returns:
        Incremented version string
    """
    sv = parse_version(version)

    if sv is None:
        raise ValueError(f"Invalid version: {version}")

    if level == "major":
        sv.major += 1
        sv.minor = 0
        sv.patch = 0
    elif level == "minor":
        sv.minor += 1
        sv.patch = 0
    elif level == "patch":
        sv.patch += 1
    else:
        raise ValueError(f"Invalid level: {level}")

    # Clear prerelease and build
    sv.prerelease = None
    sv.build = None

    return str(sv)


def get_latest_version(versions: list[str]) -> Optional[str]:
    """
    Get the latest version from a list of versions

    Args:
        versions: List of version strings

    Returns:
        Latest version or None if list is empty
    """
    if not versions:
        return None

    parsed = [parse_version(v) for v in versions]
    valid = [v for v in parsed if v is not None]

    if not valid:
        return None

    return str(max(valid))
