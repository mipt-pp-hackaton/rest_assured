"""Unit tests for the Alembic revision that adds is_active / is_superuser /
updated_at to ``users`` and drops the legacy ``is_admin`` column.

These tests intentionally do NOT touch a real database — they statically
inspect the migration file (import as a module + read its source) so the
RED phase can fail fast even in environments without Docker.
"""

from __future__ import annotations

import importlib.util
import inspect
import os
import re
from pathlib import Path
from types import ModuleType
from typing import List

import pytest

VERSIONS_DIR = Path(__file__).resolve().parents[3] / "rest_assured" / "src" / "alembic" / "versions"


def _load_module(path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(f"_mig_{path.stem}", str(path))
    assert spec is not None and spec.loader is not None, f"cannot load {path}"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _all_version_files() -> List[Path]:
    return sorted(p for p in VERSIONS_DIR.glob("*.py") if p.name != "__init__.py")


def _candidate_revisions() -> List[ModuleType]:
    """Return migration modules whose upgrade() source references all three
    new columns (is_active, is_superuser, updated_at) on the users table."""
    candidates: List[ModuleType] = []
    for path in _all_version_files():
        try:
            mod = _load_module(path)
        except Exception:  # pragma: no cover - import-time errors surface elsewhere
            continue
        upgrade = getattr(mod, "upgrade", None)
        if upgrade is None:
            continue
        try:
            src = inspect.getsource(upgrade)
        except OSError:
            continue
        # All three column names must be present in the upgrade body.
        if "is_active" in src and "is_superuser" in src and "updated_at" in src:
            candidates.append(mod)
    return candidates


def test_versions_directory_exists() -> None:
    assert VERSIONS_DIR.is_dir(), f"alembic versions dir missing: {VERSIONS_DIR}"


def test_exactly_one_revision_adds_user_auth_fields() -> None:
    """Acceptance criterion #1: exactly one revision file references all
    three new columns in its upgrade()."""
    matches = _candidate_revisions()
    names = [os.path.basename(inspect.getsourcefile(m) or "") for m in matches]
    assert len(matches) == 1, (
        "expected exactly one Alembic revision adding is_active / is_superuser"
        f" / updated_at to users, found {len(matches)}: {names}"
    )


def test_revision_upgrade_drops_is_admin() -> None:
    """Acceptance criterion #1 (cont.): the same migration must drop the
    legacy is_admin column."""
    matches = _candidate_revisions()
    assert (
        len(matches) == 1
    ), "cannot verify is_admin drop until exactly one matching revision exists"
    src = inspect.getsource(matches[0].upgrade)
    # Drop-column call referencing is_admin (allow either positional or kwarg form).
    pattern = re.compile(r"drop_column\([^)]*is_admin", re.DOTALL)
    assert pattern.search(src), (
        "upgrade() must call op.drop_column(..., 'is_admin', ...) to remove the " "legacy column"
    )


def test_updated_at_uses_timezone_aware_datetime() -> None:
    """Acceptance criterion #2: ``updated_at`` is declared with
    ``sa.DateTime(timezone=True)`` (project convention — see CLAUDE.md)."""
    matches = _candidate_revisions()
    assert len(matches) == 1, (
        "cannot verify timezone-aware updated_at until exactly one matching " "revision exists"
    )
    path = Path(inspect.getsourcefile(matches[0]) or "")
    source = path.read_text(encoding="utf-8")
    # The column declaration for updated_at must use DateTime(timezone=True).
    # We accept any whitespace between the parts.
    pattern = re.compile(
        r"updated_at[\s\S]{0,200}?DateTime\(\s*timezone\s*=\s*True\s*\)",
    )
    assert pattern.search(source), (
        "updated_at column must be declared with sa.DateTime(timezone=True) "
        "in the migration source"
    )


def test_revision_down_revision_points_at_prior_head() -> None:
    """Acceptance criterion #5: ``down_revision`` references the most
    recent existing head(s) — i.e., a leaf revision (no other migration
    has it as its own ``down_revision``)."""
    matches = _candidate_revisions()
    assert (
        len(matches) == 1
    ), "cannot verify down_revision until exactly one matching revision exists"
    new_mod = matches[0]
    new_path = Path(inspect.getsourcefile(new_mod) or "")

    # Compute set of leaf revisions among files OTHER than the new one.
    referenced: set[str] = set()
    revisions: set[str] = set()
    for path in _all_version_files():
        if path == new_path:
            continue
        mod = _load_module(path)
        rev = getattr(mod, "revision", None)
        down = getattr(mod, "down_revision", None)
        if isinstance(rev, str):
            revisions.add(rev)
        if isinstance(down, str):
            referenced.add(down)
        elif isinstance(down, (list, tuple)):
            referenced.update(d for d in down if isinstance(d, str))

    leaves = revisions - referenced
    assert leaves, "expected at least one leaf revision in the existing tree"

    new_down = getattr(new_mod, "down_revision", None)
    if isinstance(new_down, str):
        new_down_set = {new_down}
    elif isinstance(new_down, (list, tuple)):
        new_down_set = {d for d in new_down if isinstance(d, str)}
    else:
        new_down_set = set()

    assert new_down_set, f"new revision must set down_revision to a prior head; got {new_down!r}"
    # Every entry in the new down_revision must be a leaf in the pre-existing tree.
    unexpected = new_down_set - leaves
    assert not unexpected, (
        f"down_revision entries {unexpected} are not leaves of the existing "
        f"migration tree (leaves were {leaves})"
    )


def test_revision_has_distinct_revision_id() -> None:
    """Sanity: the new revision id must not collide with any existing one."""
    matches = _candidate_revisions()
    if len(matches) != 1:
        pytest.skip("matching revision count is wrong — covered by other tests")
    new_mod = matches[0]
    new_path = Path(inspect.getsourcefile(new_mod) or "")
    new_rev = getattr(new_mod, "revision", None)
    assert isinstance(new_rev, str) and new_rev, "revision id must be a non-empty string"

    other_revs: set[str] = set()
    for path in _all_version_files():
        if path == new_path:
            continue
        mod = _load_module(path)
        rev = getattr(mod, "revision", None)
        if isinstance(rev, str):
            other_revs.add(rev)
    assert (
        new_rev not in other_revs
    ), f"new revision id {new_rev!r} collides with an existing migration"
