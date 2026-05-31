"""CLI wiring tests for ``python3 -m rest_assured [--seed | seed | migrate]``.

These tests verify routing only: which entry point ``cli.main()`` reaches for a
given ``sys.argv``. No real DB, server, or migration I/O is performed -- the
seed, server, and migration entries are replaced with lightweight spies. The
async spies are trivial no-ops, so the real ``asyncio.run`` may drive them to
completion while staying hermetic (no sockets, no event-loop I/O).
"""

import sys

import pytest

import rest_assured.src.cli as cli
import rest_assured.src.scripts.seed as seed_module


@pytest.fixture
def spies(monkeypatch):
    """Replace all three CLI sink points with I/O-free spies.

    ``cli._run_seed`` lazily imports ``seed`` from ``rest_assured.src.scripts.seed``
    at call time, so patching the module attribute there intercepts the real call
    while still exercising the real ``cli._run_seed`` coroutine. ``_start_server``
    is patched on ``cli`` directly. ``asyncio.run`` is deliberately left intact:
    the spies are async no-ops, so running them is genuinely I/O-free.
    """
    calls = {"seed": 0, "server": 0, "migrate": 0}

    async def _seed_spy():
        calls["seed"] += 1

    async def _server_spy():
        calls["server"] += 1

    def _migrate_spy():
        calls["migrate"] += 1

    monkeypatch.setattr(seed_module, "seed", _seed_spy)
    monkeypatch.setattr(cli, "_start_server", _server_spy)
    monkeypatch.setattr(cli, "_run_migrations", _migrate_spy)
    return calls


@pytest.mark.parametrize(
    "argv",
    [
        pytest.param(["rest-assured", "--seed"], id="seed-flag"),
        pytest.param(["rest-assured", "seed"], id="seed-subcommand"),
    ],
)
def test_seed_path_invoked(monkeypatch, spies, argv):
    """Both ``--seed`` and the ``seed`` subcommand reach the seed routine once.

    Only ``seed`` is patched, so the real ``cli._run_seed`` truly runs and awaits
    the spy -- proving the seed branch is wired end to end, not just touched.
    """
    monkeypatch.setattr(sys, "argv", argv)

    cli.main()

    assert spies["seed"] == 1
    assert spies["server"] == 0
    assert spies["migrate"] == 0


def test_entry_point_identity():
    """``python3 -m rest_assured`` must route to ``cli.main``."""
    import rest_assured.__main__ as m

    assert m.main is cli.main


def test_no_args_starts_server_not_seed(monkeypatch, spies):
    """No args: the server path is taken and the seed path is not.

    ``_start_server`` is an async spy that records only when its body actually
    runs (i.e. when the coroutine is awaited by the real ``asyncio.run``), so a
    recorded call genuinely proves the server branch executed -- not merely that
    the coroutine object was constructed.
    """
    monkeypatch.setattr(sys, "argv", ["rest-assured"])

    cli.main()

    assert spies["server"] == 1
    assert spies["seed"] == 0
    assert spies["migrate"] == 0
