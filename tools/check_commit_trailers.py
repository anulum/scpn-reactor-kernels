# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SCPN Reactor Kernels — commit trailer verifier

"""Validate commit-message trailers as the ``commit-msg`` hook.

The hook receives the pending commit-message file path and rejects messages
without exactly one required authorship line and exactly one vendor-neutral
``Seat:`` trailer immediately preceding it, messages carrying the superseded
``Co-Authored-By:`` trailer, and commit subjects containing outward-facing
self-praise terms.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Final

REQUIRED_AUTHORSHIP_LINE: Final = (
    "Authored by Anulum Fortis & Arcane Sapience (protoscience@anulum.li)"
)
LEGACY_COAUTHOR_RE: Final = re.compile(r"^\s*Co-Authored-By:", re.IGNORECASE)
SEAT_PREFIX_RE: Final = re.compile(r"^\s*Seat:")
SEAT_TRAILER_RE: Final = re.compile(r"^Seat:\s+([A-Za-z0-9][A-Za-z0-9_-]{0,63})\s*$")
FORBIDDEN_SEAT_PREFIXES: Final = (
    "claude-",
    "codex-",
    "gemini-",
    "grok-",
    "kimi-",
    "openai-",
)
BANNED_SUBJECT_RE: Final = re.compile(
    r"\b(world-class|best-in-class|state-of-the-art|cutting-edge|revolutionary"
    r"|groundbreaking|unrivalled|elite|comprehensive|robust|leveraging)\b",
    re.IGNORECASE,
)


def _subject_line(message: str) -> str:
    """Return the first non-empty commit-message line.

    Parameters
    ----------
    message
        Full commit-message text.

    Returns
    -------
    str
        The stripped subject line, or an empty string.
    """
    return next((line.strip() for line in message.splitlines() if line.strip()), "")


def _seat_violations(lines: list[str], authorship_indices: list[int]) -> list[str]:
    """Return validation errors for the ``Seat:`` trailer.

    Parameters
    ----------
    lines
        Commit-message lines.
    authorship_indices
        Indexes of lines equal to the required authorship line.

    Returns
    -------
    list[str]
        Violations; empty when the trailer is valid.
    """
    seat_indices = [i for i, line in enumerate(lines) if SEAT_PREFIX_RE.match(line)]
    if not seat_indices:
        return ["missing `Seat: <seat-id>` trailer"]
    if len(seat_indices) != 1:
        return ["expected exactly one `Seat: <seat-id>` trailer"]
    seat_index = seat_indices[0]
    match = SEAT_TRAILER_RE.match(lines[seat_index].strip())
    if match is None:
        return ["invalid `Seat: <seat-id>` trailer"]
    violations: list[str] = []
    seat_id = match.group(1).lower()
    if seat_id.startswith(FORBIDDEN_SEAT_PREFIXES):
        violations.append("vendor-prefixed `Seat:` trailer is forbidden")
    if len(authorship_indices) == 1:
        authorship_index = authorship_indices[0]
        between = lines[seat_index + 1 : authorship_index]
        if seat_index >= authorship_index or any(line.strip() for line in between):
            violations.append(
                "`Seat:` trailer must immediately precede the authorship line"
            )
    return violations


def message_violations(message: str) -> list[str]:
    """Return commit-message policy violations.

    Parameters
    ----------
    message
        Full commit-message text.

    Returns
    -------
    list[str]
        Empty when the message satisfies the local agent commit policy.
    """
    lines = message.splitlines()
    violations: list[str] = []
    authorship_indices = [
        i for i, line in enumerate(lines) if line.strip() == REQUIRED_AUTHORSHIP_LINE
    ]
    if not authorship_indices:
        violations.append("missing required authorship line")
    elif len(authorship_indices) != 1:
        violations.append("expected exactly one authorship line")
    violations.extend(_seat_violations(lines, authorship_indices))
    if any(LEGACY_COAUTHOR_RE.match(line) for line in lines):
        violations.append("legacy `Co-Authored-By:` trailer is forbidden")
    banned = sorted(
        {m.group(1).lower() for m in BANNED_SUBJECT_RE.finditer(_subject_line(message))}
    )
    if banned:
        violations.append(f"banned public subject term(s): {', '.join(banned)}")
    return violations


def main(argv: list[str] | None = None) -> int:
    """Run the commit-trailer hook.

    Parameters
    ----------
    argv
        Argument vector; ``None`` reads ``sys.argv``.

    Returns
    -------
    int
        ``0`` when validation passes, ``1`` for policy violations.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("message_file", type=Path)
    args = parser.parse_args(argv)
    violations = message_violations(args.message_file.read_text(encoding="utf-8"))
    if not violations:
        return 0
    print("Commit message rejected:", file=sys.stderr)
    for violation in violations:
        print(f"  - {violation}", file=sys.stderr)
    print("Required block:\n  Seat: <seat-id>", file=sys.stderr)
    print(f"  {REQUIRED_AUTHORSHIP_LINE}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
