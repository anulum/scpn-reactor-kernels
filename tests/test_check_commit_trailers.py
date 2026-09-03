# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SCPN Reactor Kernels — commit trailer verifier tests

"""Contract tests for the commit-message trailer guard."""

from __future__ import annotations

from pathlib import Path

import pytest

from check_commit_trailers import REQUIRED_AUTHORSHIP_LINE, main, message_violations

VALID_MESSAGE = (
    "feat: add configuration policy surface\n\nbody text\n\n"
    f"Seat: rs01\n{REQUIRED_AUTHORSHIP_LINE}\n"
)


def test_valid_message_has_no_violations() -> None:
    """A compliant message passes with no findings."""
    assert message_violations(VALID_MESSAGE) == []


@pytest.mark.parametrize(
    ("message", "fragment"),
    [
        ("feat: x\n\nSeat: rs01\n", "missing required authorship line"),
        (
            (
                f"feat: x\n\nSeat: rs01\n{REQUIRED_AUTHORSHIP_LINE}\n"
                f"{REQUIRED_AUTHORSHIP_LINE}\n"
            ),
            "exactly one authorship line",
        ),
        (f"feat: x\n\n{REQUIRED_AUTHORSHIP_LINE}\n", "missing `Seat:"),
        (
            f"feat: x\n\nSeat: a1\nSeat: b2\n{REQUIRED_AUTHORSHIP_LINE}\n",
            "exactly one `Seat:",
        ),
        (f"feat: x\n\nSeat: !bad!\n{REQUIRED_AUTHORSHIP_LINE}\n", "invalid `Seat:"),
        (
            f"feat: x\n\nSeat: claude-1\n{REQUIRED_AUTHORSHIP_LINE}\n",
            "vendor-prefixed",
        ),
        (
            f"feat: x\n\nSeat: rs01\nextra\n{REQUIRED_AUTHORSHIP_LINE}\n",
            "immediately precede",
        ),
        (
            f"feat: x\n\n{REQUIRED_AUTHORSHIP_LINE}\nSeat: rs01\n",
            "immediately precede",
        ),
        (
            (
                f"feat: x\n\nCo-Authored-By: Someone\nSeat: rs01\n"
                f"{REQUIRED_AUTHORSHIP_LINE}\n"
            ),
            "Co-Authored-By",
        ),
        (
            (
                f"feat: comprehensive robust module\n\nSeat: rs01\n"
                f"{REQUIRED_AUTHORSHIP_LINE}\n"
            ),
            "banned public subject term(s): comprehensive, robust",
        ),
    ],
)
def test_violation_is_reported(message: str, fragment: str) -> None:
    """Each policy breach yields a finding naming the failing rule."""
    findings = message_violations(message)
    assert any(fragment in finding for finding in findings), findings


def test_main_accepts_valid_file(tmp_path: Path) -> None:
    """The hook exits 0 for a compliant commit-message file."""
    path = tmp_path / "COMMIT_EDITMSG"
    path.write_text(VALID_MESSAGE, encoding="utf-8")
    assert main([str(path)]) == 0


def test_main_rejects_invalid_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The hook exits 1 and names the violations for a bad message."""
    path = tmp_path / "COMMIT_EDITMSG"
    path.write_text("feat: x\n", encoding="utf-8")
    assert main([str(path)]) == 1
    err = capsys.readouterr().err
    assert "Commit message rejected" in err
    assert "Seat: <seat-id>" in err
