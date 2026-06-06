"""Regression test for the bot restart-storm bug.

Phase B root cause: when `dp.start_polling(bot)` raises inside
`main()`'s retry loop, the next iteration calls `dp.include_router(router)`
again on the same module-level Dispatcher instance, which already owns
that router — aiogram 3 raises `RuntimeError: Router is already attached`.

The test reproduces that failure mode in isolation: register the same
router twice on a fresh Dispatcher and assert that the second
include_router raises. The fix removes the in-process retry loop
(variant A) so the bug path is no longer reachable.
"""

from __future__ import annotations

import pytest
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram import Router


@pytest.fixture
def bot() -> Bot:
    return Bot(
        token="123456:test-token",
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


def test_double_include_router_raises(bot: Bot) -> None:
    """The bug-trigger: include_router twice on the same Dispatcher raises.

    Reproduces the production failure mode where `main()`'s retry loop
    re-enters with the same module-level `dp` that already owns the
    router, and aiogram refuses the second `include_router` call.
    """
    router = Router(name="regression-router-double-attach")
    dp = Dispatcher(bot=bot, storage=MemoryStorage())
    dp.include_router(router)

    with pytest.raises(RuntimeError, match="already attached"):
        dp.include_router(router)


def test_router_remains_attached_after_parent_swap(bot: Bot) -> None:
    """A fresh Router instance attaches cleanly to a fresh Dispatcher.

    Captures the contract any fix must honour: once a Router is bound
    to a Dispatcher (via `parent_router`), you cannot re-bind it; you
    must create new Router instances. This is why variant B
    (re-create dp but keep routers) is not viable — the routers carry
    sticky `parent_router` references.
    """
    router1 = Router(name="r1")
    dp1 = Dispatcher(bot=bot, storage=MemoryStorage())
    dp1.include_router(router1)
    assert router1.parent_router is dp1

    # Same router cannot be re-attached, even to a new Dispatcher:
    dp2 = Dispatcher(bot=bot, storage=MemoryStorage())
    with pytest.raises(RuntimeError, match="already attached"):
        dp2.include_router(router1)

    # A brand-new Router attaches fine — this is the only safe path.
    router2 = Router(name="r2")
    dp2.include_router(router2)
    assert router2.parent_router is dp2
