"""Doc-contract guard for the README "Seed" documentation block (task T3).

These tests pin the README's seed documentation to the NEW contract:

    make seed  ==  python3 -m rest_assured --seed

which creates an admin ``admin@admin.com`` / password ``admin`` plus demo
services, is idempotent, and runs through the service layer.

The OLD (dead) contract documented ``SEED_ADMIN_PASSWORD=<...> make seed``
creating ``admin@example.com``. This module asserts the new wording is present
and the dead wording is gone.

NOTE on the negative ``admin@example.com`` check: a grep over the current
README shows ``admin@example.com`` occurs on exactly one line (the stale seed
line) and nowhere else, so the robust "absent from the whole README" check is
used rather than scoping to the seed section.
"""

from __future__ import annotations

import re
from pathlib import Path

# This test file lives at <repo>/rest_assured/tests/test_readme_seed_docs.py,
# so the repo root (where README.md lives) is parents[2].
REPO_ROOT = Path(__file__).resolve().parents[2]
README_PATH = REPO_ROOT / "README.md"


def _read_readme() -> str:
    assert README_PATH.is_file(), (
        f"README.md not found at expected repo root: {README_PATH}. "
        "Adjust the parents[...] depth if the layout changed."
    )
    return README_PATH.read_text(encoding="utf-8")


def test_readme_documents_new_seed_command_form() -> None:
    """Assertion 1: README mentions ``python3 -m rest_assured --seed``."""
    text = _read_readme()
    assert "python3 -m rest_assured --seed" in text, (
        "README must document the new seed command form "
        "'python3 -m rest_assured --seed', but it was not found in README.md."
    )


def test_readme_documents_new_admin_email() -> None:
    """Assertion 2a: README mentions admin email ``admin@admin.com``."""
    text = _read_readme()
    assert "admin@admin.com" in text, (
        "README must document the seed admin email 'admin@admin.com', "
        "but it was not found in README.md."
    )


def test_readme_documents_admin_password() -> None:
    """Assertion 2b: README mentions the seed password ``admin``.

    Matched as a standalone token (word boundaries) so it is not satisfied by
    incidental substrings such as 'admin@admin.com' or 'administrator'.
    """
    text = _read_readme()
    assert re.search(r"(?<![\w@.])admin(?![\w@.])", text), (
        "README must document the seed admin password 'admin' as a standalone "
        "token, but no such standalone 'admin' password mention was found."
    )


def test_readme_states_seed_is_idempotent() -> None:
    """Assertion 3: README states the seed is idempotent (RU or EN)."""
    text = _read_readme().lower()
    assert ("идемпотент" in text) or ("idempotent" in text), (
        "README must state that the seed is idempotent "
        "(expected a case-insensitive 'идемпотент' or 'idempotent' mention), "
        "but neither was found in README.md."
    )


def test_readme_has_no_seed_admin_password_env_var() -> None:
    """Assertion 4 (negative): the dead 'SEED_ADMIN_PASSWORD' env var is gone."""
    text = _read_readme()
    assert "SEED_ADMIN_PASSWORD" not in text, (
        "README still references the dead env var 'SEED_ADMIN_PASSWORD'; "
        "the new seed contract does not use it and it must be removed."
    )


def test_readme_has_no_old_seed_admin_email() -> None:
    """Assertion 5 (negative): the dead 'admin@example.com' email is gone.

    'admin@example.com' currently occurs only on the stale seed line, so an
    absent-from-whole-README check is both robust and simple here.
    """
    text = _read_readme()
    assert "admin@example.com" not in text, (
        "README still references the dead seed admin email 'admin@example.com'; "
        "the new seed contract uses 'admin@admin.com' and the old one must go."
    )
