# Key Grace Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Unify key creation/renewal around a single 3x-ui `Client` per `Key`, with inbound `7` always attached and `AVAILABLE_CONNECTIONS [11,12]` as a payment-gated overlay that detaches into a 7-day Telegram-only grace window on subscription expiry.

**Architecture:** Derived status (`active`/`grace`/`expired`) from a new `keys.grace_expiry` column; a `GraceManager` service encapsulates panel `attach`/`detach` transitions via a new `XUISession.set_inbounds`; panel `expiryTime` is pre-set to `grace_expiry` at creation so the `active→grace` transition is just a detach. A hourly scheduler job + a `panel_sync` reconcile step converge panel state to the DB-derived status. Landing 24h keys become the future paid `Client` via `upgrade_from_landing` on claim/first payment.

**Tech Stack:** Python 3.10, FastAPI, asyncpg, tenacity, httpx (3x-ui standalone API), APScheduler, pytest + AsyncMock.

**Spec:** `docs/superpowers/specs/2026-06-25-key-grace-refactor-design.md`

## Global Constraints

- Backend is the only layer that touches the DB and 3x-ui panel. Bot/web call backend via `X-Bot-Secret`.
- Cache identifiers are immutable: `Key` → `key_{email}` (`CacheKeyManager.key`). Inbound sets are NOT stored in DB (`inbound_ids` not in `_DB_FIELDS`); the panel is source of truth, reconciled by `panel_sync`.
- 3x-ui standalone API: `attach`/`detach`/`update` per email; `expiryTime` is per-client (not per-inbound).
- `XUI_INBOUND_ID_LANDING` (=7) is the always-on baseline inbound; `AVAILABLE_CONNECTIONS` (env, `[11,12]`) is the paid overlay.
- `DEFAULT_PRICING_PLAN` (env, `10`) is the trial tariff id; trial is a subscription (gets grace).
- Tests use `AsyncMock`/`MagicMock`; pure-unit tests must NOT require a live DB. Integration tests gate on `TEST_DATABASE_URL`.
- Conventional commit messages, end with `Co-Authored-By: Claude <noreply@anthropic.com>`.

## File Structure

**New files:**
- `backend/services/core/keys/utils/inbounds.py` — inbound-set constants/helpers + `is_subscription`.
- `backend/services/core/keys/utils/status.py` — `KeyStatus` derived-status helper.
- `backend/services/core/keys/utils/grace.py` — `GraceManager` service.
- `backend/tests/unit/test_inbounds.py`, `test_key_status.py`, `test_grace_manager.py`, `test_xui_set_inbounds.py`, `test_formation_grace.py`, `test_renewal_grace.py`, `test_creation_landing_upgrade.py`, `test_landing_claim_upgrade.py`, `test_scheduler_grace_transitions.py`, `test_panel_sync_reconcile.py`
- `scripts/migrate_grace.py` — one-shot backfill.

**Modified files:**
- `backend/config.py` — `GRACE_PERIOD_DAYS`.
- `backend/models/keys/key.py` — `grace_expiry` field + `_DB_FIELDS`.
- `backend/client.py` — `XUISession.set_inbounds`.
- `backend/services/core/keys/utils/formtion.py` — `paid_inbound_ids()` + `grace_expiry` + `is_subscription`.
- `backend/services/core/keys/utils/create_key.py` — panel `expiryTime = grace_expiry` for subscriptions.
- `backend/services/core/keys/utils/renewal.py` — grace branch + `grace_expiry` + reconcile.
- `backend/app/factories.py` — wire `GraceManager` into `KeyRenewal` and `KeyCreationService`.
- `backend/services/core/payment/creation_service.py` — landing-upgrade branch.
- `backend/api/v1/landing.py` — `claim_key` via `upgrade_from_landing`.
- `backend/background/scheduler.py` — `grace_transitions` job.
- `backend/services/synchron/database_synchronizer.py` — reconcile step in `sync_data`.
- `backend/tests/integration/test_keys_update_real_db.py` — add `grace_expiry` to DDL.
- `backend/init_dev_db.py` — add `grace_expiry` to keys DDL (if it owns the schema).
- `.env` / `.env.example` / `.env.dev.example` — `GRACE_PERIOD_DAYS=7`.

---

### Task 1: Config `GRACE_PERIOD_DAYS` + inbound-set helpers

**Files:**
- Modify: `backend/config.py`
- Create: `backend/services/core/keys/utils/inbounds.py`
- Test: `backend/tests/unit/test_inbounds.py`

**Interfaces:**
- Produces: `BASELINE_INBOUNDS: list[int]`, `PAID_OVERLAY_INBOUNDS: list[int]`, `paid_inbound_ids() -> list[int]`, `grace_inbound_ids() -> list[int]`, `expired_inbound_ids() -> list[int]`, `expected_inbound_ids(status: str) -> list[int]`, `GRACE_PERIOD_DAYS: int`, `GRACE_PERIOD_MS: int`, `is_subscription(tariff) -> bool`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/unit/test_inbounds.py
from unittest.mock import MagicMock
from services.core.keys.utils import inbounds as ib


def test_baseline_and_overlay():
    assert ib.BASELINE_INBOUNDS == [7]
    assert ib.PAID_OVERLAY_INBOUNDS == [11, 12]


def test_paid_grace_expired_sets():
    assert ib.paid_inbound_ids() == [7, 11, 12]
    assert ib.grace_inbound_ids() == [7]
    assert ib.expired_inbound_ids() == []


def test_expected_inbound_ids_by_status():
    assert ib.expected_inbound_ids("active") == [7, 11, 12]
    assert ib.expected_inbound_ids("grace") == [7]
    assert ib.expected_inbound_ids("expired") == []
    assert ib.expected_inbound_ids("none") == []


def test_is_subscription_paid_and_trial():
    paid = MagicMock(id=5, amount=100.0)
    trial = MagicMock(id=10, amount=0.0)
    free = MagicMock(id=2, amount=0.0)
    assert ib.is_subscription(paid) is True
    assert ib.is_subscription(trial) is True
    assert ib.is_subscription(free) is False


def test_grace_period_ms():
    assert ib.GRACE_PERIOD_DAYS == 7
    assert ib.GRACE_PERIOD_MS == 7 * 86_400_000
```

> NOTE: this test asserts the env values `[7]`/`[11,12]`. Set them in the test via monkeypatching `inbounds.BASELINE_INBOUNDS` if your `.env` differs. If `.env` already has `XUI_INBOUND_ID_LANDING=7` and `AVAILABLE_CONNECTIONS=[11,12]`, the assertions hold as-is.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/unit/test_inbounds.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'services.core.keys.utils.inbounds'`

- [ ] **Step 3: Add config var**

In `backend/config.py`, inside `class Settings` (next to `xui_inbound_id_landing`):
```python
    # Grace period (days) of telegram-only access after a paid subscription expires.
    grace_period_days: int = Field(default=7, alias="GRACE_PERIOD_DAYS")
```
And in the module-level compat vars block (next to `LIMIT_IP`):
```python
GRACE_PERIOD_DAYS: int = settings.grace_period_days
```

- [ ] **Step 4: Create the inbounds helper module**

```python
# backend/services/core/keys/utils/inbounds.py
"""Inbound-set helpers for the grace model.

XUI_INBOUND_ID_LANDING (7) is the always-on baseline inbound.
AVAILABLE_CONNECTIONS ([11,12]) is the paid overlay, toggled by subscription state.
"""
from config import (
    LIST_AVAILABLE_CONNECTIONS,
    settings,
    GRACE_PERIOD_DAYS,
)
from models import Tariff  # noqa: F401  (type hint only)

# Always-on baseline (telegram). Empty if landing inbound not configured.
BASELINE_INBOUNDS: list[int] = (
    [settings.xui_inbound_id_landing] if settings.xui_inbound_id_landing else []
)
# Paid overlay (full VPN), filtered to env list.
PAID_OVERLAY_INBOUNDS: list[int] = list(LIST_AVAILABLE_CONNECTIONS)

GRACE_PERIOD_MS: int = GRACE_PERIOD_DAYS * 86_400_000

_TRIAL_TARIFF_ID = 10  # DEFAULT_PRICING_PLAN


def paid_inbound_ids() -> list[int]:
    """active/trial: baseline + paid overlay (dedup, preserve order)."""
    seen = set()
    out = []
    for i in BASELINE_INBOUNDS + PAID_OVERLAY_INBOUNDS:
        if i not in seen:
            seen.add(i)
            out.append(int(i))
    return out


def grace_inbound_ids() -> list[int]:
    """grace: baseline only (telegram)."""
    return list(BASELINE_INBOUNDS)


def expired_inbound_ids() -> list[int]:
    """expired: no inbounds (client disabled/deleted)."""
    return []


def expected_inbound_ids(status: str) -> list[int]:
    if status == "active":
        return paid_inbound_ids()
    if status == "grace":
        return grace_inbound_ids()
    return expired_inbound_ids()


def is_subscription(tariff) -> bool:
    """A subscription is a paid tariff OR the trial tariff (both get grace)."""
    if tariff is None:
        return False
    return (getattr(tariff, "amount", 0) or 0) > 0 or int(getattr(tariff, "id", 0)) == _TRIAL_TARIFF_ID
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && pytest tests/unit/test_inbounds.py -v`
Expected: PASS (5 tests). If `.env` lacks `XUI_INBOUND_ID_LANDING=7`/`AVAILABLE_CONNECTIONS=[11,12]`, set them in `backend/.env` first — they are required by the spec.

- [ ] **Step 6: Commit**

```bash
git add backend/config.py backend/services/core/keys/utils/inbounds.py backend/tests/unit/test_inbounds.py
git commit -m "feat(backend): GRACE_PERIOD_DAYS + inbound-set helpers

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 2: `KeyStatus` derived-status helper

**Files:**
- Create: `backend/services/core/keys/utils/status.py`
- Test: `backend/tests/unit/test_key_status.py`

**Interfaces:**
- Consumes: `Key` with `expiry_time: int`, `grace_expiry: Optional[int]`.
- Produces: `KeyStatus.of(key, now_ms: int | None = None) -> str`; constants `KeyStatus.ACTIVE = "active"`, `.GRACE = "grace"`, `.EXPIRED = "expired"`, `.NONE = "none"`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/unit/test_key_status.py
from unittest.mock import MagicMock
from services.core.keys.utils.status import KeyStatus


def _key(expiry, grace):
    k = MagicMock()
    k.expiry_time = expiry
    k.grace_expiry = grace
    return k


def test_none_when_grace_expiry_is_none():
    assert KeyStatus.of(_key(1000, None), now_ms=0) == "none"


def test_active_before_expiry():
    assert KeyStatus.of(_key(2000, 9000), now_ms=1999) == "active"


def test_grace_between_expiry_and_grace_expiry():
    assert KeyStatus.of(_key(2000, 9000), now_ms=2000) == "grace"
    assert KeyStatus.of(_key(2000, 9000), now_ms=8999) == "grace"


def test_expired_at_grace_expiry():
    assert KeyStatus.of(_key(2000, 9000), now_ms=9000) == "expired"
    assert KeyStatus.of(_key(2000, 9000), now_ms=9999) == "expired"


def test_defaults_to_now(monkeypatch):
    # now_ms defaults to current time; just ensure it runs without error.
    assert KeyStatus.of(_key(2000, 9000)) in ("active", "grace", "expired")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/unit/test_key_status.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Create the helper**

```python
# backend/services/core/keys/utils/status.py
"""Derived subscription status from Key.expiry_time / Key.grace_expiry."""
import time

class KeyStatus:
    ACTIVE = "active"
    GRACE = "grace"
    EXPIRED = "expired"
    NONE = "none"

    @staticmethod
    def of(key, now_ms: int | None = None) -> str:
        grace_expiry = getattr(key, "grace_expiry", None)
        if grace_expiry is None:
            return KeyStatus.NONE
        now = now_ms if now_ms is not None else int(time.time() * 1000)
        expiry = int(getattr(key, "expiry_time", 0) or 0)
        if now < expiry:
            return KeyStatus.ACTIVE
        if now < int(grace_expiry):
            return KeyStatus.GRACE
        return KeyStatus.EXPIRED
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/unit/test_key_status.py -v`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/services/core/keys/utils/status.py backend/tests/unit/test_key_status.py
git commit -m "feat(backend): KeyStatus derived-status helper

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 3: `Key.grace_expiry` field + DDL

**Files:**
- Modify: `backend/models/keys/key.py`
- Modify: `backend/tests/integration/test_keys_update_real_db.py`
- Modify: `backend/init_dev_db.py` (only if it owns the `keys` DDL — verify first)
- Test: `backend/tests/unit/test_key_grace_expiry_field.py`

**Interfaces:**
- Produces: `Key.grace_expiry: Optional[int] = None`; `"grace_expiry"` present in `Key._DB_FIELDS` so `save_data`/`update` persist it.

- [ ] **Step 1: Check whether `init_dev_db.py` owns the keys DDL**

Run: `grep -n "CREATE TABLE.*keys\|keys (" backend/init_dev_db.py`
- If it contains the `keys` DDL, you must add `grace_expiry bigint` there in Step 3.
- If it does NOT (schema managed externally), skip the `init_dev_db.py` edit and instead document the manual `ALTER TABLE` in the commit message.

- [ ] **Step 2: Write the failing test**

```python
# backend/tests/unit/test_key_grace_expiry_field.py
from models.keys.key import Key


def test_grace_expiry_defaults_none():
    k = Key(tg_id=1, client_id="c", email="a@b.c", expiry_time=0, key="k", inbound_id=7)
    assert k.grace_expiry is None


def test_grace_expiry_is_persisted_field():
    assert "grace_expiry" in Key._DB_FIELDS


def test_to_dict_includes_grace_expiry():
    k = Key(tg_id=1, client_id="c", email="a@b.c", expiry_time=0, key="k", inbound_id=7,
            grace_expiry=1234567890000)
    d = k.to_dict()
    assert d["grace_expiry"] == 1234567890000
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd backend && pytest tests/unit/test_key_grace_expiry_field.py -v`
Expected: FAIL (`grace_expiry not in _DB_FIELDS` / `AttributeError`).

- [ ] **Step 4: Add the field**

In `backend/models/keys/key.py`:
- Add the field after `converted_tg_id`:
```python
    converted_tg_id: Optional[int] = None
    landing_uid: Optional[str] = None
    # Planned end of the telegram-only grace window (ms). None = no grace
    # (landing-24h, free non-subscription keys, legacy already-expired).
    grace_expiry: Optional[int] = None
```
- Add `"grace_expiry"` to the `_DB_FIELDS` frozenset.

- [ ] **Step 5: Update DDLs**

In `backend/tests/integration/test_keys_update_real_db.py`, add to the `DDL` `keys` table (after `converted_tg_id bigint`):
```sql
    grace_expiry           bigint
```
If Step 1 found `init_dev_db.py` owns the schema, add the same column to its `keys` DDL.

Production migration SQL (run manually against prod `DATABASE_URL` once, idempotent):
```sql
ALTER TABLE keys ADD COLUMN IF NOT EXISTS grace_expiry bigint;
```

- [ ] **Step 6: Run test to verify it passes**

Run: `cd backend && pytest tests/unit/test_key_grace_expiry_field.py -v`
Expected: PASS (3 tests).

- [ ] **Step 7: Run the integration DDL test compiles (no live DB needed for collection)**

Run: `cd backend && pytest tests/integration/test_keys_update_real_db.py --collect-only -q`
Expected: collects without syntax errors (test is skipped without `TEST_DATABASE_URL`).

- [ ] **Step 8: Commit**

```bash
git add backend/models/keys/key.py backend/tests/integration/test_keys_update_real_db.py backend/tests/unit/test_key_grace_expiry_field.py backend/init_dev_db.py
git commit -m "feat(backend): keys.grace_expiry column + field

Production migration: ALTER TABLE keys ADD COLUMN IF NOT EXISTS grace_expiry bigint;

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 4: `XUISession.set_inbounds`

**Files:**
- Modify: `backend/client.py` (add method on `XUISession`)
- Test: `backend/tests/unit/test_xui_set_inbounds.py`

**Interfaces:**
- Consumes: existing `_StandaloneClientAPI.attach`/`detach`/`get` and `_panel_client_from_raw`.
- Produces: `async def XUISession.set_inbounds(self, email: str, target_inbound_ids: list[int]) -> bool` — idempotently attaches missing and detaches extra inbounds; returns `True` on success, `False` if the client is missing or any op fails (logs, does not raise).

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/unit/test_xui_set_inbounds.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from client import XUISession


def _xui_with_panel(inbound_ids, attach_ok=True, detach_ok=True):
    xui = XUISession.__new__(XUISession)
    xui._standalone = MagicMock()
    raw = {"obj": {"client": {"inboundIds": inbound_ids}}}
    xui._standalone.get = AsyncMock(return_value=raw)
    xui._standalone.attach = AsyncMock(return_value={"success": attach_ok})
    xui._standalone.detach = AsyncMock(return_value={"success": detach_ok})
    xui.ensure_auth = AsyncMock()
    xui._ensure_standalone = AsyncMock()
    return xui


@pytest.mark.asyncio
async def test_noop_when_already_correct():
    xui = _xui_with_panel([7, 11, 12])
    ok = await xui.set_inbounds("a@b.c", [7, 11, 12])
    assert ok is True
    xui._standalone.attach.assert_not_called()
    xui._standalone.detach.assert_not_called()


@pytest.mark.asyncio
async def test_attaches_missing_and_detaches_extra():
    xui = _xui_with_panel([7, 99])  # has 99 (extra), missing 11,12
    ok = await xui.set_inbounds("a@b.c", [7, 11, 12])
    assert ok is True
    # implementation calls _standalone.attach(email, [i]) positionally:
    # call_args.args == (email, [i]) → the inbound id is args[1][0]
    attached = {c.args[1][0] for c in xui._standalone.attach.call_args_list}
    detached = {c.args[1][0] for c in xui._standalone.detach.call_args_list}
    assert attached == {11, 12}
    assert detached == {99}


@pytest.mark.asyncio
async def test_returns_false_when_client_missing():
    xui = _xui_with_panel([7])
    xui._standalone.get = AsyncMock(side_effect=Exception("not found"))
    ok = await xui.set_inbounds("a@b.c", [7, 11, 12])
    assert ok is False
```

> NOTE: the implementation calls `self._standalone.attach(email, [i])` / `detach(email, [i])` **positionally** (Step 3), so `call_args.args == (email, [i])` and the inbound id is `args[1][0]` — the assertions above match that shape. If you instead implement the call with `inbound_ids=[i]` keyword, switch the assertions to `c.kwargs["inbound_ids"][0]`.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/unit/test_xui_set_inbounds.py -v`
Expected: FAIL with `AttributeError: 'XUISession' object has no attribute 'set_inbounds'`.

- [ ] **Step 3: Implement `set_inbounds`**

Add this method to `XUISession` in `backend/client.py` (next to `extend_client_key`):
```python
    async def set_inbounds(self, email: str, target_inbound_ids: list) -> bool:
        """Idempotently converge a client's inbound set to target_inbound_ids.

        Attaches missing inbounds, detaches extra ones. Returns False if the
        client is missing or any panel op fails (logs, does not raise).
        """
        try:
            await self.ensure_auth()
            await self._ensure_standalone()
            raw = await self._standalone.get(email)
            obj = raw.get("obj", {}) if isinstance(raw, dict) else {}
            client = obj.get("client", obj) if isinstance(obj, dict) else {}
            current = list(client.get("inboundIds", []) or [])
        except Exception as e:
            logger.warning(
                "set_inbounds: клиент не найден",
                extra={"email": email, "error": str(e)},
            )
            return False

        target = [int(i) for i in (target_inbound_ids or [])]
        current_i = [int(i) for i in current]
        to_attach = [i for i in target if i not in current_i]
        to_detach = [i for i in current_i if i not in target]

        if not to_attach and not to_detach:
            return True

        ok = True
        for i in to_attach:
            try:
                await self._standalone.attach(email, [i])
            except Exception as e:
                logger.error("set_inbounds: attach провален",
                             extra={"email": email, "inbound_id": i, "error": str(e)})
                ok = False
        for i in to_detach:
            try:
                await self._standalone.detach(email, [i])
            except Exception as e:
                logger.error("set_inbounds: detach провален",
                             extra={"email": email, "inbound_id": i, "error": str(e)})
                ok = False
        return ok
```

> NOTE: `_StandaloneClientAPI.attach(self, email, inbound_ids)` and `detach(self, email, inbound_ids)` already exist with exactly these signatures (see `backend/client.py`). Verify by `grep -n "async def attach\|async def detach" backend/client.py` before running tests; if signatures differ, adjust the call.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/unit/test_xui_set_inbounds.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/client.py backend/tests/unit/test_xui_set_inbounds.py
git commit -m "feat(backend): XUISession.set_inbounds idempotent attach/detach

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 5: `GraceManager` service

**Files:**
- Create: `backend/services/core/keys/utils/grace.py`
- Test: `backend/tests/unit/test_grace_manager.py`

**Interfaces:**
- Consumes: `XUISession.set_inbounds`, `XUISession.extend_client_key`, `XUISession.delete_client`, `ServiceDataModel.keys.update(conn, data, search_data)`, `CacheService.keys.set/delete`, `ExpiryCalculator.key_duration`, `inbounds.*`, `KeyStatus`.
- Produces: `GraceManager(xui_session, model_data, cache, expiry, pool)` with:
  - `async enter_grace(key) -> bool`
  - `async expire_after_grace(key) -> bool`
  - `async renew_from_grace(key, tariff, number_of_months) -> Key | None`
  - `async upgrade_from_landing(key, tariff, number_of_months) -> Key | None`
  - `async reconcile(key) -> bool`

> NOTE: `BaseRepository.update(self, conn: asyncpg.Pool, data, search_data)` forwards `conn` straight to the DB service — it does NOT acquire-from-pool when `conn is None`. So `GraceManager` holds a `pool` and passes `self.pool` to every `keys.update` call. The renewal-from-payment path also uses the pool (panel op and DB write are not one transaction, same as `landing.claim_key` today).

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/unit/test_grace_manager.py
import pytest
from unittest.mock import AsyncMock, MagicMock

from services.core.keys.utils.grace import GraceManager
from services.core.keys.utils.status import KeyStatus


def _key(expiry=2000, grace=9000, tg_id=1, email="a@b.c",
         inbound_ids=None, tariff_id=5, client_id="c1", converted_tg_id=None,
         landing_uid=None, grace_expiry=9000, **kw):
    k = MagicMock()
    k.expiry_time = expiry
    k.grace_expiry = grace_expiry
    k.tg_id = tg_id
    k.email = email
    k.inbound_ids = inbound_ids
    k.tariff_id = tariff_id
    k.client_id = client_id
    k.converted_tg_id = converted_tg_id
    k.landing_uid = landing_uid
    k.limit_ip = 3
    k.name_tariff = "t"
    k.period = 30
    k.amount = 100.0
    k.notified_24h = False
    k.notified_10h = False
    k.notified_expired_grace = False
    return k


def _mgr():
    xui = MagicMock()
    xui.set_inbounds = AsyncMock(return_value=True)
    xui.extend_client_key = AsyncMock(return_value=True)
    xui.delete_client = AsyncMock(return_value=True)
    model_data = MagicMock()
    model_data.keys.update = AsyncMock()
    cache = MagicMock()
    cache.keys.set = AsyncMock()
    cache.keys.delete = AsyncMock()
    expiry = MagicMock()
    expiry.key_duration = MagicMock(return_value=5000)
    expiry.key_duration_new_key = MagicMock(return_value=5000)
    pool = MagicMock()
    return (GraceManager(xui, model_data, cache, expiry, pool),
            xui, model_data, cache, expiry)


@pytest.mark.asyncio
async def test_enter_grace_detaches_to_baseline():
    mgr, xui, md, cache, _ = _mgr()
    ok = await mgr.enter_grace(_key())
    assert ok is True
    args, _ = xui.set_inbounds.call_args
    assert args == ("a@b.c", [7]) or args[0] == "a@b.c" and args[1] == [7]
    cache.keys.set.assert_awaited_once()


@pytest.mark.asyncio
async def test_expire_after_grace_detaches_all_and_deletes():
    mgr, xui, md, cache, _ = _mgr()
    ok = await mgr.expire_after_grace(_key())
    assert ok is True
    # last set_inbounds call must be empty set
    assert xui.set_inbounds.call_args.args[1] == []
    xui.delete_client.assert_awaited_once()
    cache.keys.delete.assert_awaited_once()


@pytest.mark.asyncio
async def test_expire_after_grace_tolerates_missing_client():
    mgr, xui, md, cache, _ = _mgr()
    xui.delete_client = AsyncMock(side_effect=Exception("not found"))
    ok = await mgr.expire_after_grace(_key())
    assert ok is True  # 404 treated as already-deleted
    cache.keys.delete.assert_awaited_once()


@pytest.mark.asyncio
async def test_renew_from_grace_reattaches_and_sets_expiry_grace():
    mgr, xui, md, cache, expiry = _mgr()
    k = _key(expiry=2000, grace_expiry=9000, tariff_id=5)
    out = await mgr.renew_from_grace(k, MagicMock(id=5, period=30, amount=100.0,
                                                  name_tariff="m", limit_ip=3), 1)
    assert out is not None
    assert out.expiry_time == 5000          # new expiry (from mocked calc)
    assert out.grace_expiry == 5000 + 7 * 86_400_000
    # panel inbounds converged to paid set, panel expiryTime set via extend_client_key
    sets = [c.args[1] for c in xui.set_inbounds.call_args_list]
    assert [7, 11, 12] in sets or [7, 11, 12] in sets
    xui.extend_client_key.assert_awaited_once()
    md.keys.update.assert_awaited_once()


@pytest.mark.asyncio
async def test_upgrade_from_landing_transfers_tg_and_reattaches():
    mgr, xui, md, cache, expiry = _mgr()
    k = _key(inbound_ids=[7], converted_tg_id=42, landing_uid="abc",
             grace_expiry=None, tg_id=-1)
    out = await mgr.upgrade_from_landing(k, MagicMock(id=10, period=7, amount=0.0,
                                                       name_tariff="trial", limit_ip=1), 1)
    assert out is not None
    assert out.tg_id == 42
    assert out.converted_tg_id == 42
    sets = [c.args[1] for c in xui.set_inbounds.call_args_list]
    assert [7, 11, 12] in sets or sets[-1] == [7, 11, 12]
    xui.extend_client_key.assert_awaited_once()
    md.keys.update.assert_awaited_once()


@pytest.mark.asyncio
async def test_reconcile_converges_to_active():
    mgr, xui, md, cache, _ = _mgr()
    k = _key(expiry=10**13, grace_expiry=10**13 + 1)  # far future => active
    await mgr.reconcile(k)
    target = xui.set_inbounds.call_args.args[1]
    assert target == [7, 11, 12]
```

> NOTE: `_key()` passes `grace=9000` and `grace_expiry=9000` both so the MagicMock has the attribute regardless of which name the implementation reads — the implementation reads `key.grace_expiry` only.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/unit/test_grace_manager.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement `GraceManager`**

```python
# backend/services/core/keys/utils/grace.py
"""GraceManager — transitions a Key/Client between active/grace/expired
by attaching/detaching 3x-ui inbounds. Panel expiryTime is pre-set to
grace_expiry at creation, so active->grace is just a detach."""
import time
from typing import Optional

from client import XUISession
from logger import logger
from models import Key, Tariff
from services.cache.key_manager import CacheKeyManager
from services.cache.service import CacheService
from services.core.data.service import ServiceDataModel
from services.core.keys.utils.calculator import ExpiryCalculator
from services.core.keys.utils.inbounds import (
    paid_inbound_ids, grace_inbound_ids, expired_inbound_ids,
    expected_inbound_ids, GRACE_PERIOD_MS,
)
from services.core.keys.utils.status import KeyStatus


class GraceManager:
    def __init__(
        self,
        xui_session: XUISession,
        model_data: ServiceDataModel,
        cache: CacheService,
        expiry: ExpiryCalculator,
        pool,
    ):
        self.xui = xui_session
        self.key_data = model_data.keys
        self.cache = cache
        self.expiry = expiry
        self.pool = pool

    async def enter_grace(self, key: Key) -> bool:
        ok = await self.xui.set_inbounds(key.email, grace_inbound_ids())
        await self.cache.keys.set(CacheKeyManager.key(key.email), key)
        logger.info("enter_grace", extra={"email": key.email, "ok": ok})
        return ok

    async def expire_after_grace(self, key: Key) -> bool:
        await self.xui.set_inbounds(key.email, expired_inbound_ids())
        try:
            await self.xui.delete_client(key.email, 0, key.client_id)
        except Exception as e:
            if "not found" not in str(e).lower():
                logger.warning("expire_after_grace: delete провален, считаем уже удалённым",
                               extra={"email": key.email, "error": str(e)})
        await self.cache.keys.delete(CacheKeyManager.key(key.email))
        logger.info("expire_after_grace", extra={"email": key.email})
        return True

    async def renew_from_grace(self, key: Key, tariff: Tariff,
                               number_of_months: int = 1) -> Optional[Key]:
        new_expiry = self.expiry.key_duration(key, tariff.period, number_of_months)
        return await self._apply_paid(key, tariff, new_expiry, number_of_months,
                                       transfer_tg=False)

    async def upgrade_from_landing(self, key: Key, tariff: Tariff,
                                    number_of_months: int = 1) -> Optional[Key]:
        new_expiry = self.expiry.key_duration_new_key(tariff.period, number_of_months)
        return await self._apply_paid(key, tariff, new_expiry, number_of_months,
                                       transfer_tg=True)

    async def _apply_paid(self, key: Key, tariff: Tariff, new_expiry: int,
                          number_of_months: int, transfer_tg: bool) -> Optional[Key]:
        grace_exp = new_expiry + GRACE_PERIOD_MS
        # 1. Converge panel inbounds to paid set.
        if not await self.xui.set_inbounds(key.email, paid_inbound_ids()):
            logger.error("_apply_paid: set_inbounds провален", extra={"email": key.email})
            return None
        # 2. Set panel expiryTime = grace_expiry (pre-emptive), enable=True.
        key.expiry_time = grace_exp
        if not await self.xui.extend_client_key(key):
            logger.error("_apply_paid: extend_client_key провален", extra={"email": key.email})
            return None
        # 3. DB: store paid expiry + planned grace + tariff fields.
        key.expiry_time = new_expiry
        key.grace_expiry = grace_exp
        key.tariff_id = tariff.id
        key.name_tariff = tariff.name_tariff
        key.period = tariff.period
        key.amount = tariff.amount
        key.limit_ip = tariff.limit_ip or key.limit_ip
        key.notified_24h = False
        key.notified_10h = False
        key.notified_expired_grace = False
        if transfer_tg and key.converted_tg_id:
            key.tg_id = key.converted_tg_id
        await self.key_data.update(self.pool, key, search_data={"email": key.email})
        await self.cache.keys.set(CacheKeyManager.key(key.email), key)
        logger.info("_apply_paid", extra={"email": key.email, "new_expiry": new_expiry,
                                           "grace_expiry": grace_exp, "transfer_tg": transfer_tg})
        return key

    async def reconcile(self, key: Key) -> bool:
        st = KeyStatus.of(key)
        target = expected_inbound_ids(st)
        ok = await self.xui.set_inbounds(key.email, target)
        if st == KeyStatus.EXPIRED:
            # client should be gone; ensure cache reflects it
            await self.cache.keys.delete(CacheKeyManager.key(key.email))
        else:
            await self.cache.keys.set(CacheKeyManager.key(key.email), key)
        return ok
```

> NOTE: every `keys.update` call uses `self.pool` (verified: `BaseRepository.update(self, conn, data, search_data)` forwards `conn` to the DB service and requires a real pool — `None` would raise). `reconcile` writes only to the cache (no DB write), so it needs no pool.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/unit/test_grace_manager.py -v`
Expected: PASS (6 tests). Adjust assertion shapes only if the actual call args differ from what the test reads (the test is intentionally lenient on list membership).

- [ ] **Step 5: Commit**

```bash
git add backend/services/core/keys/utils/grace.py backend/tests/unit/test_grace_manager.py
git commit -m "feat(backend): GraceManager (enter/expire/renew/upgrade/reconcile)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 6: `FormationKey` writes `grace_expiry` + paid inbound set

**Files:**
- Modify: `backend/services/core/keys/utils/formtion.py`
- Test: `backend/tests/unit/test_formation_grace.py`

**Interfaces:**
- Consumes: `inbounds.paid_inbound_ids`, `inbounds.is_subscription`, `inbounds.GRACE_PERIOD_MS`, `XUI_INBOUND_ID_LANDING`.
- Produces: `Key.grace_expiry` set for subscription keys (paid/trial), `None` otherwise; `Key.inbound_ids = paid_inbound_ids()` for subscriptions (no override), `[override]` for landing override.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/unit/test_formation_grace.py
import pytest
from unittest.mock import AsyncMock, MagicMock

from services.core.keys.utils.formtion import FormationKey


def _formation(cache_all_keys=()):
    cache = MagicMock()
    cache.keys.all = AsyncMock(return_value=list(cache_all_keys))
    connected_data = MagicMock()
    connected_data.data = AsyncMock(return_value={
        "subscription_url": "https://sub.example",
        "inbound_ids": [11, 12],
    })
    expiry = MagicMock()
    expiry.key_duration_new_key = MagicMock(return_value=2000)
    return FormationKey(cache=cache, connected_data=connected_data, expiry=expiry), connected_data


@pytest.mark.asyncio
async def test_subscription_key_gets_paid_inbounds_and_grace():
    f, _ = _formation()
    paid_tariff = MagicMock(id=5, amount=100.0, period=30, limit_ip=3)
    key = await f.form_new_key(tg_id=1, tariff=paid_tariff, server_id=1, number_of_months=1)
    assert key.inbound_ids == [7, 11, 12]
    assert key.grace_expiry == 2000 + 7 * 86_400_000


@pytest.mark.asyncio
async def test_landing_override_key_has_no_grace():
    f, _ = _formation()
    # landing uses inbound_id_override and a free-ish tariff; is_subscription False
    landing_tariff = MagicMock(id=999, amount=0.0, period=1, limit_ip=1)
    key = await f.form_new_key(tg_id=-1, tariff=landing_tariff, server_id=1,
                               number_of_months=1, inbound_id_override=7)
    assert key.inbound_ids == [7]
    assert key.grace_expiry is None


@pytest.mark.asyncio
async def test_free_non_trial_key_has_no_grace():
    f, _ = _formation()
    free_tariff = MagicMock(id=2, amount=0.0, period=1, limit_ip=1)
    key = await f.form_new_key(tg_id=1, tariff=free_tariff, server_id=1, number_of_months=1)
    assert key.grace_expiry is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/unit/test_formation_grace.py -v`
Expected: FAIL (`key.grace_expiry` not set / inbound_ids not `[7,11,12]`).

- [ ] **Step 3: Update `FormationKey.form_new_key`**

In `backend/services/core/keys/utils/formtion.py`:
- Add imports at top:
```python
from services.core.keys.utils.inbounds import paid_inbound_ids, is_subscription, GRACE_PERIOD_MS
```
- Replace the inbound-selection block and add `grace_expiry` to the `Key(...)` construction:
```python
        subscription_url = f"{server_data.get('subscription_url')}/{email}"

        if inbound_id_override is not None:
            # Landing-page flow: форсируем конкретный inbound.
            inbound_ids = [inbound_id_override]
            primary_inbound_id = inbound_id_override
            grace_expiry = None  # landing 24h — не подписка
        else:
            inbound_ids = paid_inbound_ids() if is_subscription(tariff) else (
                server_data.get("inbound_ids", []))
            primary_inbound_id = inbound_ids[0] if inbound_ids else 0
            grace_expiry = (int(new_expiry_time) + GRACE_PERIOD_MS) if is_subscription(tariff) else None

        key = Key(
            tg_id=tg_id,
            email=email,
            client_id=client_id,
            limit_ip=tariff.limit_ip,
            expiry_time=int(new_expiry_time),
            inbound_id=int(primary_inbound_id),
            inbound_ids=inbound_ids,
            key=subscription_url,
            tariff_id=tariff.id,
            grace_expiry=grace_expiry,
        )
        return key
```

> NOTE: for non-subscription free keys we fall back to `server_data["inbound_ids"]` (the old `[11,12]` behaviour) — free keys keep whatever the panel offers, no grace. Verify `paid_inbound_ids()` returns `[7,11,12]` under your `.env` (Task 1).

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/unit/test_formation_grace.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/services/core/keys/utils/formtion.py backend/tests/unit/test_formation_grace.py
git commit -m "feat(backend): FormationKey writes grace_expiry + paid inbound set

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 7: `CreateKey.proces` sets panel `expiryTime = grace_expiry` for subscriptions

**Files:**
- Modify: `backend/services/core/keys/utils/create_key.py`
- Test: `backend/tests/unit/test_create_key_grace.py`

**Interfaces:**
- Consumes: `Key.grace_expiry` (set by `FormationKey`).
- Produces: `add_client` called with `expiry_time = key.grace_expiry` when the key is a subscription, else `key.expiry_time`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/unit/test_create_key_grace.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from services.core.keys.utils.create_key import CreateKey


def _make_key(grace_expiry):
    k = MagicMock()
    k.client_id = "uuid-1"
    k.email = "a@b.c"
    k.tg_id = 1
    k.limit_ip = 1
    k.inbound_ids = [7, 11, 12]
    k.inbound_id = 7
    k.expiry_time = 2000
    k.grace_expiry = grace_expiry
    k.key = "https://sub.example/a@b.c"
    return k


def _create_key(key):
    model_data = MagicMock()
    model_data.keys.save_data = AsyncMock()
    xui = MagicMock()
    xui.add_client = AsyncMock(return_value=True)
    expiry = MagicMock()
    formation = MagicMock()
    formation.form_new_key = AsyncMock(return_value=key)
    ck = CreateKey(model_data=model_data, xui_session=xui, expiry=expiry, formation=formation)
    return ck, xui


@pytest.mark.asyncio
async def test_subscription_uses_grace_expiry_as_panel_expiry():
    ck, xui = _create_key(_make_key(grace_expiry=9000))
    tariff = MagicMock(id=5, amount=100.0, limit_ip=1, period=1)
    await ck.proces(tg_id=1, tariff=tariff, server_id=2, conn=MagicMock())
    _, kwargs = xui.add_client.call_args
    assert kwargs["expiry_time"] == 9000


@pytest.mark.asyncio
async def test_non_subscription_uses_expiry_time():
    ck, xui = _create_key(_make_key(grace_expiry=None))
    tariff = MagicMock(id=2, amount=0.0, limit_ip=1, period=1)
    await ck.proces(tg_id=1, tariff=tariff, server_id=2, conn=MagicMock())
    _, kwargs = xui.add_client.call_args
    assert kwargs["expiry_time"] == 2000
```

> NOTE: the test asserts `add_client` was called with `expiry_time` as a keyword. The current `create_key.py` calls `add_client(..., expiry_time=key.expiry_time)` as a kwarg — keep that kwarg style and only change the value.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/unit/test_create_key_grace.py -v`
Expected: FAIL (`expiry_time == 2000` for the subscription case, not `9000`).

- [ ] **Step 3: Update `CreateKey.proces`**

In `backend/services/core/keys/utils/create_key.py`, replace the `add_client` call:
```python
            # Панельный expiryTime = grace_expiry для подписок (pre-emptive grace),
            # иначе = оплаченный/бесплатный срок.
            panel_expiry = key.grace_expiry if key.grace_expiry is not None else key.expiry_time
            add_result = await self.xui_session.add_client(
                client_id=key.client_id,
                email=key.email,
                tg_id=key.tg_id,
                limit_ip=key.limit_ip,
                inbound_ids=key.inbound_ids or [key.inbound_id],
                expiry_time=panel_expiry,
            )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/unit/test_create_key_grace.py -v`
Expected: PASS (2 tests). Then run the existing test to confirm no regression:
Run: `cd backend && pytest tests/unit/test_create_key_proces.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/services/core/keys/utils/create_key.py backend/tests/unit/test_create_key_grace.py
git commit -m "feat(backend): CreateKey sets panel expiryTime=grace_expiry for subscriptions

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 8: `KeyRenewal` grace branch + `grace_expiry` + reconcile; wire `GraceManager` into factories

**Files:**
- Modify: `backend/services/core/keys/utils/renewal.py`
- Modify: `backend/app/factories.py`
- Test: `backend/tests/unit/test_renewal_grace.py`

**Interfaces:**
- Consumes: `GraceManager`, `KeyStatus`, `inbounds.paid_inbound_ids`, `inbounds.GRACE_PERIOD_MS`, `inbounds.is_subscription`.
- Produces: `KeyRenewal(..., grace_manager: GraceManager)`; `extension_key` branches on status: `active`→normal extension + `grace_expiry` + reconcile to paid set + panel `expiryTime=grace_expiry`; `grace`→`grace_manager.renew_from_grace`; `expired`→raises `ValueError`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/unit/test_renewal_grace.py
import pytest
from unittest.mock import AsyncMock, MagicMock

from services.core.keys.utils.renewal import KeyRenewal


def _key(status, expiry=2000, grace_expiry=9000, tariff_id=5, email="a@b.c"):
    k = MagicMock()
    k.expiry_time = expiry
    k.grace_expiry = grace_expiry
    k.tariff_id = tariff_id
    k.email = email
    k.client_id = "c1"
    k.tg_id = 1
    k.limit_ip = 3
    k.server_info = None
    k.created_at = 0
    return k


def _renewal(key_status_key, renew_from_grace_return=None):
    xui = MagicMock()
    xui.extend_client_key = AsyncMock(return_value=True)
    xui.set_inbounds = AsyncMock(return_value=True)
    md = MagicMock()
    md.keys.update = AsyncMock()
    refresh = MagicMock()
    refresh.refresh_key = MagicMock(side_effect=lambda k, *a, **kw: k)
    resetter = MagicMock()
    resetter.reset_key_after_renewal = AsyncMock()
    grace = MagicMock()
    grace.renew_from_grace = AsyncMock(return_value=renew_from_grace_return or _key("active"))
    kr = KeyRenewal(model_data=md, xui_session=xui, refresh_key=refresh, resetter=resetter,
                   grace_manager=grace)
    return kr, xui, md, refresh, resetter, grace


@pytest.mark.asyncio
async def test_active_renewal_sets_grace_expiry_and_reconciles():
    kr, xui, md, refresh, resetter, grace = _renewal(_key("active"))
    k = _key("active", expiry=10**13, grace_expiry=10**13 + 1)
    tariff = MagicMock(id=5, period=30, amount=100.0, name_tariff="m", limit_ip=3)
    # refresh_key mutates expiry_time; simulate it
    refresh.refresh_key = MagicMock(side_effect=lambda key, *a, **kw: setattr(key, "expiry_time", 5000) or key)
    out = await kr.extension_key(k, conn=MagicMock(), server=MagicMock(), tariff=tariff, number_of_months=1)
    assert out.expiry_time == 5000
    assert out.grace_expiry == 5000 + 7 * 86_400_000
    xui.set_inbounds.assert_awaited()  # reconcile to paid set
    xui.extend_client_key.assert_awaited_once()
    md.keys.update.assert_awaited_once()
    resetter.reset_key_after_renewal.assert_awaited_once()


@pytest.mark.asyncio
async def test_grace_renewal_delegates_to_grace_manager():
    kr, xui, md, refresh, resetter, grace = _renewal(_key("grace"))
    k = _key("grace", expiry=2000, grace_expiry=9000)
    tariff = MagicMock(id=5, period=30, amount=100.0, name_tariff="m", limit_ip=3)
    out = await kr.extension_key(k, conn=MagicMock(), server=MagicMock(), tariff=tariff, number_of_months=1)
    grace.renew_from_grace.assert_awaited_once()
    xui.extend_client_key.assert_not_awaited()  # grace path does not use the normal extend
    resetter.reset_key_after_renewal.assert_not_awaited()


@pytest.mark.asyncio
async def test_expired_renewal_raises():
    kr, *_ = _renewal(_key("expired"))
    k = _key("expired", expiry=2000, grace_expiry=2000)
    tariff = MagicMock(id=5, period=30, amount=100.0, name_tariff="m", limit_ip=3)
    with pytest.raises(ValueError):
        await kr.extension_key(k, conn=MagicMock(), server=MagicMock(), tariff=tariff, number_of_months=1)
```

> NOTE: `KeyStatus.of` reads real `expiry_time`/`grace_expiry`. The `_key` helper sets explicit values; for the "active" case use a far-future expiry so `KeyStatus.of` returns `active`. Adjust the values if your `GRACE_PERIOD_MS` makes the math differ.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/unit/test_renewal_grace.py -v`
Expected: FAIL (`KeyRenewal.__init__() got an unexpected keyword 'grace_manager'`).

- [ ] **Step 3: Update `KeyRenewal`**

In `backend/services/core/keys/utils/renewal.py`:
```python
from typing import Optional
import asyncpg

from client import XUISession
from models import Tariff, Server, Key
from services.core.data.service import ServiceDataModel
from services.core.keys.utils.updating import KeyUpdater
from services.core.keys.utils.reset import KeyResetter
from services.core.keys.utils.status import KeyStatus
from services.core.keys.utils.inbounds import paid_inbound_ids, GRACE_PERIOD_MS
from logger import logger


class KeyRenewal:
    """Продление ключа."""

    def __init__(
        self,
        model_data: ServiceDataModel,
        xui_session: XUISession,
        refresh_key: KeyUpdater,
        resetter: Optional[KeyResetter] = None,
        grace_manager=None,
    ):
        self.key_data = model_data.keys
        self.xui_session = xui_session
        self.refresh = refresh_key
        self.resetter = resetter
        self.grace_manager = grace_manager

    async def extension_key(
        self,
        key: Key,
        conn: asyncpg.Pool,
        server: Server,
        tariff: Tariff,
        number_of_months: Optional[int] = 1,
    ):
        status = KeyStatus.of(key)
        if status == KeyStatus.GRACE:
            if self.grace_manager is None:
                raise RuntimeError("grace_manager не настроен для продления из grace")
            renewed = await self.grace_manager.renew_from_grace(key, tariff, number_of_months)
            if renewed is None:
                raise ValueError("Не удалось продлить ключ из grace (панель провалена)")
            return renewed
        if status == KeyStatus.EXPIRED:
            raise ValueError(
                "Ключ истёк (grace закончился) — продление невозможно, нужен новый ключ"
            )

        # active path
        refresh_key = self.refresh.refresh_key(key, tariff, server, number_of_months)
        # reconcile inbounds to paid set (heal drift) and set panel expiryTime=grace_expiry
        if key.grace_expiry is not None:
            await self.xui_session.set_inbounds(key.email, paid_inbound_ids())
            panel_expiry = key.expiry_time + GRACE_PERIOD_MS
            key.grace_expiry = panel_expiry
            saved_expiry = key.expiry_time
            key.expiry_time = panel_expiry
            await self.xui_session.extend_client_key(key)
            key.expiry_time = saved_expiry
        else:
            await self.xui_session.extend_client_key(refresh_key)
        await self.key_data.update(conn, key, search_data={"email": key.email})

        if self.resetter:
            await self.resetter.reset_key_after_renewal(conn, key)
        return refresh_key
```

> NOTE: `refresh_key` IS `key` (KeyUpdater mutates in place), so updating `key` then returning `refresh_key` returns the same mutated object. The active path keeps `key.expiry_time = new_expiry` in DB (restored after the panel call) and stores `key.grace_expiry`.

- [ ] **Step 4: Wire `GraceManager` into factories (keep the 3-tuple!)**

`build_key_services` is called from ~12 sites (`admin.py`, `keys.py`, `landing.py`, tests) that all unpack a **3-tuple** `(create_key, key_renewal, xui)`. **Do NOT change its return arity** — that would break every caller. Instead, construct `GraceManager` *inside* `build_key_services` and inject it into `KeyRenewal` only, and expose a separate `build_grace_manager` helper for the few places (`build_payment_router`, `landing.claim_key`) that need a `GraceManager` themselves.

In `backend/app/factories.py`:
- Add imports:
```python
from services.core.keys.utils.grace import GraceManager
```
- Add a new helper next to `build_key_services`:
```python
def build_grace_manager(pool, service_data, cache, data_service, xui=None):
    """Constructs a GraceManager. Reuses the given xui if provided (avoids a
    second auth session); otherwise builds one. Used by build_payment_router
    and landing.claim_key."""
    from services.cache.loader import LoadingService
    from services.core.keys.utils.calculator import ExpiryCalculator
    if xui is None:
        loading = LoadingService(cache=cache, data_service=data_service, pool=pool)
        xui = XUISession(model_service=service_data, loading=loading)
    return GraceManager(xui_session=xui, model_data=service_data, cache=cache,
                        expiry=ExpiryCalculator(), pool=pool)
```
- In `build_key_services`, build `grace_manager` and pass it to `KeyRenewal` (return arity stays 3):
```python
    grace_manager = build_grace_manager(pool, service_data, cache, data_service, xui=xui)
    ...
    key_renewal = KeyRenewal(model_data=service_data, xui_session=xui, refresh_key=updater,
                             resetter=resetter, grace_manager=grace_manager)
    return (create_key, key_renewal, xui)
```
- `build_payment_router` calls `build_key_services` (3-tuple, unchanged) then builds its own `grace_manager` via the helper for `KeyCreationService`:
```python
    create_key, key_renewal, xui = build_key_services(pool, service_data, cache, data_service)
    grace_manager = build_grace_manager(pool, service_data, cache, data_service, xui=xui)
    processor = PaymentProcessor(conn=pool, model_service=service_data, cache=cache)
    creation_svc = KeyCreationService(processor=processor, create_key=create_key,
                                      notifier=notifier, grace_manager=grace_manager)
    renewal_svc = KeyRenewalService(processor=processor, key_manager=key_renewal, notifier=notifier)
    return PaymentRouter(processor=processor, creation_service=creation_svc, renewal_service=renewal_svc)
```

> NOTE: no other `build_key_services` caller needs editing — the 3-tuple is preserved. Verify with `grep -rn "build_key_services" backend/ --include="*.py"` that all unpacks are still 3-tuple (they were before this task and remain so).

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && pytest tests/unit/test_renewal_grace.py -v`
Expected: PASS (3 tests).

- [ ] **Step 6: Verify no caller broke**

Run: `cd backend && python -c "from app.factories import build_payment_router, build_key_services, build_grace_manager; print('ok')"`
Expected: `ok` (no import errors; 3-tuple intact). Also run any existing test that patches `build_key_services` returning a 3-tuple, e.g. `cd backend && pytest tests/api/test_keys_new.py -q -x 2>&1 | tail -5` — they should still pass because the arity is unchanged.

- [ ] **Step 7: Commit**

```bash
git add backend/services/core/keys/utils/renewal.py backend/app/factories.py backend/tests/unit/test_renewal_grace.py
git commit -m "feat(backend): KeyRenewal grace branch + grace_expiry + reconcile

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 9: `KeyCreationService` landing-upgrade branch

**Files:**
- Modify: `backend/services/core/payment/creation_service.py`
- Test: `backend/tests/unit/test_creation_landing_upgrade.py`

**Interfaces:**
- Consumes: `GraceManager.upgrade_from_landing`, `ServiceDataModel.keys` (lookup), `inbounds.grace_inbound_ids` (to recognise a landing-only key).
- Produces: `KeyCreationService(..., grace_manager)`; `process()` before `create_key.proces` looks up the user's landing-origin key (`landing_uid` set, `converted_tg_id == tg_id`, `grace_expiry is None`, inbound set == `[7]`) and upgrades it instead of creating a new key when found.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/unit/test_creation_landing_upgrade.py
import pytest
from unittest.mock import AsyncMock, MagicMock

from services.core.payment.creation_service import KeyCreationService


def _processor(tg_id=42, months=1, amount=100.0, conn=None):
    p = MagicMock()
    p.tg_id = tg_id
    p.number_of_months = months
    p.amount = amount
    p._conn = conn or MagicMock()
    p._model_service = MagicMock()
    p._cache = MagicMock()
    p._cache.tariffs.temporary_get = AsyncMock(return_value=None)
    p._cache.tariffs.delete = AsyncMock()
    p.extract_operation = MagicMock(return_value=["create_key", "5"])
    p._model_service.tariffs.get_data = AsyncMock(return_value=MagicMock(id=5, period=30, amount=100.0, name_tariff="m", limit_ip=3))
    p._model_service.users.get_data = AsyncMock(return_value=MagicMock(tg_id=tg_id, server_id=1))
    return p


@pytest.mark.asyncio
async def test_upgrades_existing_landing_key_instead_of_creating_new():
    p = _processor()
    landing_key = MagicMock()
    landing_key.landing_uid = "abc"
    landing_key.converted_tg_id = 42
    landing_key.grace_expiry = None
    landing_key.inbound_ids = [7]
    landing_key.email = "a@b.c"
    p._model_service.keys.get_all = AsyncMock(return_value=[landing_key])

    create_key = MagicMock()
    create_key.proces = AsyncMock(return_value={"email": "new@x.c"})
    grace = MagicMock()
    grace.upgrade_from_landing = AsyncMock(return_value=MagicMock(email="a@b.c", key="k"))

    svc = KeyCreationService(processor=p, create_key=create_key, notifier=None, grace_manager=grace)
    result = await svc.process(tariff_id="5")

    grace.upgrade_from_landing.assert_awaited_once()
    create_key.proces.assert_not_awaited()
    assert result["email"] == "a@b.c"


@pytest.mark.asyncio
async def test_creates_new_key_when_no_landing_key():
    p = _processor()
    p._model_service.keys.get_all = AsyncMock(return_value=[])
    create_key = MagicMock()
    create_key.proces = AsyncMock(return_value={"email": "new@x.c"})
    grace = MagicMock()
    grace.upgrade_from_landing = AsyncMock()

    svc = KeyCreationService(processor=p, create_key=create_key, notifier=None, grace_manager=grace)
    result = await svc.process(tariff_id="5")

    create_key.proces.assert_awaited_once()
    grace.upgrade_from_landing.assert_not_awaited()
    assert result["email"] == "new@x.c"
```

> NOTE: the lookup uses `keys.get_all()` filtered in-process. If the real `ServiceDataModel.keys` exposes a cheaper `get_all()`, use it; otherwise this is fine. Verify with `grep -n "async def get_all" backend/services/core/data/base.py`.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/unit/test_creation_landing_upgrade.py -v`
Expected: FAIL (`KeyCreationService.__init__() got an unexpected keyword 'grace_manager'`).

- [ ] **Step 3: Update `KeyCreationService`**

In `backend/services/core/payment/creation_service.py`:
```python
from typing import Optional, Dict, Any

from logger import logger

from services.core.keys.utils.create_key import CreateKey
from services.core.payment.processor import PaymentProcessor
from services.core.notifications.protocols import INotifier
from services.core.keys.utils.inbounds import grace_inbound_ids


class KeyCreationService:
    def __init__(
        self,
        processor: PaymentProcessor,
        create_key: CreateKey,
        notifier: Optional[INotifier] = None,
        grace_manager=None,
    ):
        self.processor = processor
        self.create_key = create_key
        self.notifier = notifier
        self.grace_manager = grace_manager

    async def _find_landing_origin_key(self, tg_id: int):
        """Найти landing-ключ юзера, готовый к апгрейду:
        landing_uid set, converted_tg_id == tg_id, grace_expiry is None,
        inbound set == baseline (telegram-only)."""
        try:
            keys = await self.processor._model_service.keys.get_all()
        except Exception:
            return None
        baseline = set(grace_inbound_ids())
        for k in keys or []:
            if (getattr(k, "landing_uid", None)
                    and getattr(k, "converted_tg_id", None) == tg_id
                    and getattr(k, "grace_expiry", None) is None
                    and set(getattr(k, "inbound_ids", None) or []) == baseline):
                return k
        return None

    async def process(self, tariff_id: str = None) -> Optional[Dict[str, Any]]:
        try:
            if tariff_id is None:
                operation, tariff_id = self.processor.extract_operation()
                if operation != "create_key":
                    raise ValueError(f"Ожидалась операция 'create_key', получено: {operation}")

            tariff = await self.processor._model_service.tariffs.get_data(
                int(tariff_id), self.processor._conn
            )
            user = await self.processor._model_service.users.get_data(
                self.processor.tg_id, self.processor._conn
            )

            # Landing-upgrade: если у юзера есть landing-ключ [7] без grace —
            # апгрейдим тот же клиент (Happ-URL сохраняется), не создаём новый.
            if self.grace_manager is not None:
                landing_key = await self._find_landing_origin_key(self.processor.tg_id)
                if landing_key is not None:
                    upgraded = await self.grace_manager.upgrade_from_landing(
                        landing_key, tariff, self.processor.number_of_months
                    )
                    if upgraded is not None:
                        logger.info("[Цена:CreateKey] Landing-ключ апгрейдирован",
                                    tg_id=self.processor.tg_id, email=upgraded.email)
                        return {
                            "public_link": upgraded.key,
                            "days": 0,
                            "link_to_connect": upgraded.key,
                            "email": upgraded.email,
                        }
                    logger.warning("[Цена:CreateKey] upgrade_from_landing провален, создаём новый ключ",
                                   tg_id=self.processor.tg_id)

            key_data = await self.create_key.proces(
                tg_id=self.processor.tg_id,
                tariff=tariff,
                server_id=user.server_id,
                conn=self.processor._conn,
                number_of_months=self.processor.number_of_months,
            )
            if not key_data:
                raise ValueError("Не удалось создать ключ")
            return key_data
        except Exception as e:
            logger.error("Ошибка при создании ключа", error_type=type(e).__name__,
                         error_message=str(e), tg_id=self.processor.tg_id, exc_info=True)
            raise
```

> NOTE: keep `send_notification` unchanged. The `KeyCreationService.send_notification` expects `key_data` with `email`/`public_link`/etc. — the upgrade branch returns a compatible dict.

- [ ] **Step 4: Wire `grace_manager` into `KeyCreationService` via `build_payment_router`**

`build_payment_router` already (after Task 8) builds `grace_manager` via `build_grace_manager` and passes it to `KeyCreationService`. Confirm the wiring in `backend/app/factories.py` `build_payment_router` matches:
```python
    create_key, key_renewal, xui = build_key_services(pool, service_data, cache, data_service)
    grace_manager = build_grace_manager(pool, service_data, cache, data_service, xui=xui)
    processor = PaymentProcessor(conn=pool, model_service=service_data, cache=cache)
    creation_svc = KeyCreationService(processor=processor, create_key=create_key,
                                      notifier=notifier, grace_manager=grace_manager)
    renewal_svc = KeyRenewalService(processor=processor, key_manager=key_renewal, notifier=notifier)
    return PaymentRouter(processor=processor, creation_service=creation_svc, renewal_service=renewal_svc)
```
(This was set up in Task 8 Step 4; this step is a confirmation that `KeyCreationService(..., grace_manager=grace_manager)` is present.)

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && pytest tests/unit/test_creation_landing_upgrade.py -v`
Expected: PASS (2 tests).

- [ ] **Step 6: Commit**

```bash
git add backend/services/core/payment/creation_service.py backend/app/factories.py backend/tests/unit/test_creation_landing_upgrade.py
git commit -m "feat(backend): KeyCreationService landing-upgrade branch

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 10: `landing.claim_key` via `upgrade_from_landing`

**Files:**
- Modify: `backend/api/v1/landing.py`
- Test: `backend/tests/unit/test_landing_claim_upgrade.py`

**Interfaces:**
- Consumes: `GraceManager.upgrade_from_landing`, `build_grace_manager(pool, service_data, cache, data_service, xui=None)`, trial tariff lookup.
- Produces: `claim_key` transfers the landing client to the real `tg_id` + attaches `[11,12]` + sets trial `expiry` + `grace_expiry` using `upgrade_from_landing`, preserving the same email/Happ-URL.

> NOTE: add `build_grace_manager` to the existing `from app.factories import build_key_services` import in `landing.py` (Task 8 created the helper). `claim_key` builds its own `GraceManager` via the helper — it does **not** use the 4-tuple.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/unit/test_landing_claim_upgrade.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_claim_uses_upgrade_from_landing():
    from api.v1 import landing as L

    key_obj = MagicMock()
    key_obj.email = "a@b.c"
    key_obj.key = "https://sub.example/a@b.c"
    key_obj.expiry_time = 1000
    key_obj.converted_tg_id = None
    key_obj.tg_id = -1
    key_obj.inbound_ids = [7]
    key_obj.grace_expiry = None
    key_obj.client_id = "c1"
    key_obj.limit_ip = 1

    upgraded = MagicMock()
    upgraded.email = "a@b.c"
    upgraded.key = "https://sub.example/a@b.c"
    upgraded.expiry_time = 8000
    upgraded.grace_expiry = 8000 + 7 * 86_400_000

    pool = MagicMock()
    sd = MagicMock()
    sd.users.get_data = AsyncMock(return_value=MagicMock(tg_id=42, server_id=1))
    sd.cache_service.keys.all = AsyncMock(return_value=[key_obj])
    sd.keys.update = AsyncMock()
    sd.tariffs.get_data = AsyncMock(return_value=MagicMock(id=10, period=7, amount=0.0, name_tariff="trial", limit_ip=1))
    cache = MagicMock()
    cache.keys.set = AsyncMock()

    grace = MagicMock()
    grace.upgrade_from_landing = AsyncMock(return_value=upgraded)

    with patch.object(L, "_get_key_by_landing_uid", AsyncMock(return_value=key_obj)), \
         patch.object(L, "build_grace_manager", return_value=grace), \
         patch.object(L, "TrialService") as TS, \
         patch.object(L, "DataService", return_value=MagicMock()):
        TS.return_value.installation_trial = AsyncMock()
        # already_claimed guard: converted_tg_id None → proceeds
        resp = await L.claim_key(
            landing_uid="abc",
            body=L.ClaimRequest(tg_id=42),
            pool=pool,
            service_data=sd,
            cache=cache,
        )

    grace.upgrade_from_landing.assert_awaited_once()
    assert resp["status"] == "claimed"
    assert resp["email"] == "a@b.c"
```

> NOTE: `claim_key` currently checks `converted_tg_id == body.tg_id` for idempotency (returns `already_claimed`). The test uses `converted_tg_id = None` so it proceeds to upgrade. After upgrade, the implementation should set `key_obj.converted_tg_id = body.tg_id` (idempotency for repeat clicks) — `upgrade_from_landing` already sets `converted_tg_id` via `transfer_tg`.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/unit/test_landing_claim_upgrade.py -v`
Expected: FAIL (current `claim_key` calls `xui.extend_client_key`, not `grace.upgrade_from_landing`).

- [ ] **Step 3: Update `claim_key`**

In `backend/api/v1/landing.py`, replace the body of `claim_key` from the trial-tariff lookup onward:
```python
    # Trial-тариф (DEFAULT_PRICING_PLAN, обычно id=10, period=7 дней)
    trial_tariff = await service_data.tariffs.get_data(
        int(DEFAULT_PRICING_PLAN), conn=pool
    )
    if not trial_tariff:
        raise HTTPException(status_code=404, detail="Trial tariff not found")

    # Юзер должен быть зарегистрирован ботом заранее
    user = await service_data.users.get_data(body.tg_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not registered")

    # Апгрейд того же клиента: attach [11,12], trial expiry, grace_expiry,
    # перенос tg_id на реальный. Happ-URL (key.key) сохраняется.
    key_obj.converted_tg_id = body.tg_id
    grace = build_grace_manager(pool, service_data, cache, DataService())
    upgraded = await grace.upgrade_from_landing(key_obj, trial_tariff, number_of_months=1)
    if not upgraded:
        raise HTTPException(status_code=500, detail="Failed to upgrade landing key")

    # trial=1 (как в /keys/trial)
    await TrialService(service_data).installation_trial(body.tg_id, pool, trial=1)

    # Выровнять server_id с сервером ключа, чтобы продление из бота работало
    if user.server_id != settings.xui_server_id:
        user.server_id = settings.xui_server_id
        await service_data.users.update(pool, user, {"tg_id": body.tg_id})
        await cache.users.set(CacheKeyManager.user(body.tg_id), user)

    logger.info(
        "Landing key привязан к юзеру и апгрейдирован (trial + grace)",
        landing_uid=landing_uid, tg_id=body.tg_id, email=upgraded.email,
        new_expiry_ms=upgraded.expiry_time, grace_expiry_ms=upgraded.grace_expiry,
    )

    return {
        "status": "claimed",
        "email": upgraded.email,
        "key_value": upgraded.key,
        "expires_at_ms": int(upgraded.expiry_time or 0),
    }
```

> NOTE: remove the old `now_ms`/`period_ms`/`base_expiry`/`new_expiry_ms`/`key_obj.expiry_time = ...`/`extend_client_key`/manual field-setting block — `upgrade_from_landing` now does all of that. Keep the idempotency guards at the top (`already_claimed` / `already_claimed_other`) unchanged.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/unit/test_landing_claim_upgrade.py -v`
Expected: PASS (1 test).

- [ ] **Step 5: Commit**

```bash
git add backend/api/v1/landing.py backend/tests/unit/test_landing_claim_upgrade.py
git commit -m "feat(backend): landing claim upgrades same client via GraceManager

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 11: Scheduler `grace_transitions` job

**Files:**
- Modify: `backend/background/scheduler.py`
- Test: `backend/tests/unit/test_scheduler_grace_transitions.py`

**Interfaces:**
- Consumes: `ServiceDataModel.keys.get_all()`, `GraceManager.reconcile`, `KeyStatus`, `inbounds` (reconcile uses expected set).
- Produces: `SyncScheduler.run_grace_transitions()` iterates keys with `grace_expiry is not None` and calls `GraceManager.reconcile(key)`; registered as an hourly APScheduler job (alongside `notifications`).

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/unit/test_scheduler_grace_transitions.py
import pytest
from unittest.mock import AsyncMock, MagicMock

from background.scheduler import SyncScheduler


@pytest.mark.asyncio
async def test_grace_transitions_reconciles_subscription_keys():
    sd = MagicMock()
    k_active = MagicMock(grace_expiry=10**13, expiry_time=10**13 + 1, email="a@x.c")
    k_grace = MagicMock(grace_expiry=10**13, expiry_time=10**13 - 1, email="b@x.c")
    k_none = MagicMock(grace_expiry=None, email="c@x.c")  # landing/free — skip
    sd.keys.get_all = AsyncMock(return_value=[k_active, k_grace, k_none])
    pool = MagicMock()

    sched = SyncScheduler(service_data=sd, pool=pool)
    reconciled = []
    grace = MagicMock()
    grace.reconcile = AsyncMock(side_effect=lambda k: reconciled.append(k.email) or True)

    with __import__("backend.background.scheduler", fromlist=["GraceManager"]).__dict__.get("_build_grace_manager", lambda *a: grace):
        pass
    # Patch the module-level factory used inside run_grace_transitions:
    import background.scheduler as S
    S._build_grace_manager = lambda *a, **kw: grace

    await sched.run_grace_transitions()

    assert reconciled == ["a@x.c", "b@x.c"]  # k_none skipped
    grace.reconcile.assert_awaited()


@pytest.mark.asyncio
async def test_grace_transitions_no_keys_no_error():
    sd = MagicMock()
    sd.keys.get_all = AsyncMock(return_value=[])
    sched = SyncScheduler(service_data=sd, pool=MagicMock())
    import background.scheduler as S
    S._build_grace_manager = lambda *a, **kw: MagicMock(reconcile=AsyncMock())
    await sched.run_grace_transitions()  # must not raise
```

> NOTE: the test patches a module-level `_build_grace_manager` helper inside `background.scheduler`. Implement that helper in Step 3 so the test can monkeypatch it. This keeps the scheduler testable without a real `XUISession`.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/unit/test_scheduler_grace_transitions.py -v`
Expected: FAIL (`AttributeError: 'SyncScheduler' object has no attribute 'run_grace_transitions'`).

- [ ] **Step 3: Implement the job + helper**

In `backend/background/scheduler.py`:
- Add imports near the top:
```python
from services.core.keys.utils.grace import GraceManager
from services.core.keys.utils.status import KeyStatus
```
- Add a module-level factory (testable seam):
```python
def _build_grace_manager(service_data, pool):
    """Builds a GraceManager for the scheduler. Patchable in tests."""
    from client import XUISession
    from database.service import DataService
    from services.cache.loader import LoadingService
    from services.core.keys.utils.calculator import ExpiryCalculator
    loader = LoadingService(cache=service_data.cache_service, data_service=DataService(), pool=pool)
    xui = XUISession(model_service=service_data, loading=loader)
    return GraceManager(xui_session=xui, model_data=service_data,
                        cache=service_data.cache_service, expiry=ExpiryCalculator(), pool=pool)
```
- Add the method to `SyncScheduler`:
```python
    async def run_grace_transitions(self) -> None:
        """Converge each subscription key's panel inbound set to its DB-derived status.

        active→[7,11,12], grace→[7], expired→[] (+ delete). Idempotent; safe to run hourly.
        """
        try:
            keys = await self._service_data.keys.get_all()
        except Exception as e:
            logger.error("grace_transitions: get_keys провален", error=str(e))
            return
        if not keys:
            return
        grace = _build_grace_manager(self._service_data, self._pool)
        for key in keys:
            if getattr(key, "grace_expiry", None) is None:
                continue  # landing/free — не подписка
            try:
                await grace.reconcile(key)
            except Exception as e:
                logger.warning("grace_transitions: reconcile провален",
                               extra={"email": getattr(key, "email", "?"), "error": str(e)})
```
- Register the job in `create_scheduler` (next to the notifications job):
```python
    scheduler.add_job(
        sync_scheduler.run_grace_transitions,
        "interval",
        hours=1,
        id="grace_transitions",
        replace_existing=True,
        coalesce=True,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/unit/test_scheduler_grace_transitions.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/background/scheduler.py backend/tests/unit/test_scheduler_grace_transitions.py
git commit -m "feat(backend): hourly grace_transitions job (reconcile)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 12: `panel_sync` reconcile step

**Files:**
- Modify: `backend/services/synchron/database_synchronizer.py`
- Test: `backend/tests/unit/test_panel_sync_reconcile.py`

**Interfaces:**
- Consumes: `GraceManager.reconcile`, `ServiceDataModel.keys.get_all`.
- Produces: after the existing traffic update in `sync_data`, a reconcile pass over all subscription keys; adds `reconciled` count to the returned stats.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/unit/test_panel_sync_reconcile.py
import pytest
from unittest.mock import AsyncMock, MagicMock

from services.synchron.database_synchronizer import DatabaseSynchronizer


@pytest.mark.asyncio
async def test_sync_data_runs_grace_reconcile_and_reports_count():
    sd = MagicMock()
    sd.keys.get_all = AsyncMock(return_value=[
        MagicMock(grace_expiry=10**13, expiry_time=10**13 + 1, email="a@x.c"),
        MagicMock(grace_expiry=None, email="b@x.c"),
    ])
    sd.cache_service.keys.all = AsyncMock(return_value=[])

    fetcher = MagicMock()
    fetcher.extract_clients = AsyncMock(return_value=[])
    sync = DatabaseSynchronizer(
        xui_fetcher=fetcher,
        cache_comparator=MagicMock(),
        key_creator=MagicMock(),
        traffic_updater=MagicMock(),
        model_data=sd,
        pool=MagicMock(),
    )

    reconciled = []
    grace = MagicMock()
    grace.reconcile = AsyncMock(side_effect=lambda k: reconciled.append(k.email) or True)

    import services.synchron.database_synchronizer as M
    M._build_grace_manager = lambda *a, **kw: grace

    stats = await sync.sync_data(xui_session=MagicMock())

    assert reconciled == ["a@x.c"]  # only the subscription key
    assert stats.get("grace_reconciled") == 1
```

> NOTE: when `extract_clients` returns `[]`, `sync_data` currently returns early `{"total": 0, ...}`. To make reconcile run even with zero panel clients (panel temporarily unreachable but DB has keys), Step 3 must move the reconcile pass before the early-return OR run it independently. The test therefore expects `extract_clients` to return `[]` and still get `grace_reconciled == 1` — implement reconcile as an early step in `sync_data` (before the clients check) OR as a separate method called from `_sync_panel`. Choose: add reconcile as the FIRST step in `sync_data` (before fetching clients), so it always runs.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/unit/test_panel_sync_reconcile.py -v`
Expected: FAIL (no `grace_reconciled` key / no reconcile call).

- [ ] **Step 3: Add reconcile to `sync_data`**

In `backend/services/synchron/database_synchronizer.py`:
- Add import:
```python
from services.core.keys.utils.grace import GraceManager
```
- Add a module-level factory (testable seam):
```python
def _build_grace_manager(model_data, pool, xui_session):
    from services.core.keys.utils.calculator import ExpiryCalculator
    return GraceManager(xui_session=xui_session, model_data=model_data,
                        cache=model_data.cache_service, expiry=ExpiryCalculator(), pool=pool)
```
- At the very start of `sync_data` (before `extract_clients`), add:
```python
        # Grace reconcile: converge each subscription key's inbound set to its
        # DB-derived status. Runs even if panel client fetch later fails.
        reconcile_start = time.time()
        reconciled_count = 0
        try:
            all_keys = await self.model_data.keys.get_all()
            grace = _build_grace_manager(self.model_data, self.pool, xui_session)
            for key in all_keys or []:
                if getattr(key, "grace_expiry", None) is None:
                    continue
                try:
                    await grace.reconcile(key)
                    reconciled_count += 1
                except Exception as e:
                    logger.warning("grace reconcile провален",
                                   extra={"email": getattr(key, "email", "?"), "error": str(e)})
        except Exception as e:
            logger.error("grace reconcile pass провален", error=str(e))
        logger.info("Grace reconcile завершён", reconciled=reconciled_count,
                    reconcile_time=f"{time.time() - reconcile_start:.2f}s")
```
- At the end of `sync_data`, before returning stats, add:
```python
            stats["grace_reconciled"] = reconciled_count
```
(For the early-return `{"total": 0, ...}` branch, also add `"grace_reconciled": reconciled_count`.)

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/unit/test_panel_sync_reconcile.py -v`
Expected: PASS (1 test).

- [ ] **Step 5: Commit**

```bash
git add backend/services/synchron/database_synchronizer.py backend/tests/unit/test_panel_sync_reconcile.py
git commit -m "feat(backend): panel_sync grace reconcile step

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 13: Backfill script `scripts/migrate_grace.py`

**Files:**
- Create: `scripts/migrate_grace.py`

**Interfaces:**
- Consumes: `GraceManager`, `ServiceDataModel`, DB pool, `inbounds`.
- Produces: idempotent `python scripts/migrate_grace.py [--dry-run]` that for each active paid/trial key with `grace_expiry IS NULL`: attaches inbound 7 (`set_inbounds([7,11,12])`), sets `grace_expiry = expiry_time + GRACE_PERIOD_MS` in DB, sets panel `expiryTime = grace_expiry`.

- [ ] **Step 1: Write the script**

```python
# scripts/migrate_grace.py
"""One-shot backfill: bring existing paid/trial keys into the grace model.

For each key with grace_expiry IS NULL and a paid/trial tariff (amount>0 or
tariff_id == DEFAULT_PRICING_PLAN):
  1. set_inbounds([7,11,12]) — ensure baseline inbound 7 is attached.
  2. write grace_expiry = expiry_time + GRACE_PERIOD_MS to DB.
  3. set panel expiryTime = grace_expiry (pre-emptive).

Idempotent: skips keys already having grace_expiry. --dry-run prints only.

Usage:
  cd backend && python ../scripts/migrate_grace.py --dry-run
  cd backend && python ../scripts/migrate_grace.py
"""
import argparse
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from config import DEFAULT_PRICING_PLAN, settings  # noqa: E402
from services.core.keys.utils.inbounds import paid_inbound_ids, GRACE_PERIOD_MS, is_subscription  # noqa: E402


async def main(dry_run: bool) -> None:
    import asyncpg
    from database.service import DataService
    from services.cache.loader import LoadingService
    from services.core.data.service import ServiceDataModel
    from app.core.database import get_pool  # noqa: F401  (adjust import to project's pool factory)
    from client import XUISession
    from services.core.keys.utils.grace import GraceManager
    from services.core.keys.utils.calculator import ExpiryCalculator

    pool = await asyncpg.create_pool(dsn=settings.database_url)
    data_service = DataService()
    service_data = ServiceDataModel(pool=pool)  # adjust ctor to project's real wiring
    loader = LoadingService(cache=service_data.cache_service, data_service=data_service, pool=pool)
    await loader.loading()
    xui = XUISession(model_service=service_data, loading=loader)
    grace = GraceManager(xui_session=xui, model_data=service_data,
                         cache=service_data.cache_service, expiry=ExpiryCalculator(), pool=pool)

    keys = await service_data.keys.get_all()
    migrated = 0
    for key in keys or []:
        if getattr(key, "grace_expiry", None) is not None:
            continue
        tariff = await service_data.tariffs.get_data(int(key.tariff_id or 0), pool)
        if not is_subscription(tariff):
            continue
        grace_exp = int(key.expiry_time or 0) + GRACE_PERIOD_MS
        print(f"{'[dry] ' if dry_run else ''}migrate {key.email}: set_inbounds({paid_inbound_ids()}), "
              f"grace_expiry={grace_exp}, panel expiryTime={grace_exp}")
        if dry_run:
            migrated += 1
            continue
        await xui.set_inbounds(key.email, paid_inbound_ids())
        key.expiry_time = grace_exp
        await xui.extend_client_key(key)  # panel expiryTime = grace_exp
        key.expiry_time = int(key.expiry_time)  # restore (extend may keep it)
        key.grace_expiry = grace_exp
        await service_data.keys.update(pool, key, search_data={"email": key.email})
        await service_data.cache_service.keys.set(f"key_{key.email}", key)
        migrated += 1
    print(f"done: migrated={migrated} dry_run={dry_run}")
    await pool.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    asyncio.run(main(args.dry_run))
```

> NOTE: the imports `get_pool` / `ServiceDataModel(pool=pool)` / `DataService` ctor may not match the project's exact wiring. Before running, verify with `grep -rn "ServiceDataModel(" backend/app/ backend/ | head` and `grep -rn "def get_pool\|async def create_pool\|create_pool" backend/app/core/database.py` and adjust the script's pool/service-data construction to match. The script is a one-shot op tool, not unit-tested.

- [ ] **Step 2: Smoke-check the script imports compile**

Run: `cd backend && python -c "import ast; ast.parse(open('../scripts/migrate_grace.py').read()); print('ok')"`
Expected: `ok` (syntax valid).

- [ ] **Step 3: Dry-run against a dev DB (manual, optional)**

If a dev `DATABASE_URL` is configured:
Run: `cd backend && python ../scripts/migrate_grace.py --dry-run`
Expected: lists keys that would be migrated, `migrated=N dry_run=True`. Skipped if no DB available.

- [ ] **Step 4: Commit**

```bash
git add scripts/migrate_grace.py
git commit -m "feat(scripts): migrate_grace backfill for existing keys

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 14: Env + docs

**Files:**
- Modify: `.env`, `.env.example`, `.env.dev.example`
- Modify: `backend/CLAUDE.md` (env table), `CLAUDE.md` (cross-cutting env)

**Interfaces:** none (config/docs only).

- [ ] **Step 1: Add `GRACE_PERIOD_DAYS=7` to env files**

Add to `.env`, `.env.example`, `.env.dev.example` (near `XUI_INBOUND_ID_LANDING` / `AVAILABLE_CONNECTIONS`):
```
# Telegram-only grace days after a paid subscription expires (0 = disable grace)
GRACE_PERIOD_DAYS=7
```

- [ ] **Step 2: Update `backend/CLAUDE.md` env section**

In the "Environment Variables" list, add:
```
- `GRACE_PERIOD_DAYS` — telegram-only grace window (days) after paid subscription expiry (default 7).
```
And update the `AVAILABLE_CONNECTIONS` / `XUI_INBOUND_ID_LANDING` bullets to note: "paid keys are created on `[XUI_INBOUND_ID_LANDING] + AVAILABLE_CONNECTIONS`; on expiry the overlay detaches, leaving `XUI_INBOUND_ID_LANDING` for `GRACE_PERIOD_DAYS`."

- [ ] **Step 3: Update root `CLAUDE.md` cross-cutting env block**

Add `GRACE_PERIOD_DAYS` to the "Critical cross-cutting variables" list.

- [ ] **Step 4: Commit**

```bash
git add .env .env.example .env.dev.example backend/CLAUDE.md CLAUDE.md
git commit -m "docs(env): GRACE_PERIOD_DAYS + grace-model notes

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Final Verification

- [ ] **Full backend test run**

Run: `cd backend && pytest -q`
Expected: all green (existing + new tests). Investigate any failure with `superpowers:systematic-debugging` — do not mark the plan done with red tests.

- [ ] **Import sanity**

Run: `cd backend && python -c "from app.main import app; from app.factories import build_payment_router; print('ok')"`
Expected: `ok`.

- [ ] **Production migration applied**

`ALTER TABLE keys ADD COLUMN IF NOT EXISTS grace_expiry bigint;` run against prod `DATABASE_URL`, then `python scripts/migrate_grace.py --dry-run` (review) → `python scripts/migrate_grace.py` (apply).

## Self-Review Notes

- Spec coverage: data model (T1/T3), status (T2), GraceManager (T5), panel set_inbounds (T4), creation (T6/T7), renewal incl grace (T8), landing upgrade (T9/T10), scheduler transitions (T11), panel_sync reconcile (T12), migration (T13), env (T14). All spec sections covered.
- The `_build_grace_manager` testable seams in scheduler (T11) and synchronizer (T12) are intentional — they let unit tests inject a mock GraceManager without a live `XUISession`. Implement them as module-level functions.
- `build_key_services` return arity stays a **3-tuple** — it has ~12 call sites + tests that unpack 3 values. `GraceManager` is constructed *inside* `build_key_services` and injected into `KeyRenewal`; a separate `build_grace_manager(pool, service_data, cache, data_service, xui=None)` helper supplies `GraceManager` to `build_payment_router` (T8/T9) and `landing.claim_key` (T10). No existing caller changes.
- `GraceManager` holds a `pool` and passes `self.pool` to every `keys.update` (verified: `BaseRepository.update(conn, ...)` requires a real pool — `None` would raise). `reconcile` writes only to cache, so it needs no pool. The scheduler/synchronizer/migration helpers all pass `pool`.