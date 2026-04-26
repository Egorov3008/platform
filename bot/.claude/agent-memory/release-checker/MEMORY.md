# Release Checker -- Memory

## Project Structure
- Python 3.10.12 (not 3.11 as README says)
- ruff now in requirements.txt and .venv (added 2026-03-07)
- mypy config in pyproject.toml disables many checks (assignment, arg-type, attr-defined, etc.)
- 42 window configs in ALL_WINDOW_CONFIGS (not 38 as old docs say)
- config.py exports `API_TOKEN` (from `BOT_TOKEN` env var)

## Known Test Issues (2026-03-07, post-cleanup)
- 908 collected, 907 passed, 1 failure, 0 errors
- Previous 16 errors all fixed via new conftest.py files and signature updates
- 1 FAILURE: `test_check_event_message_with_update` -- `is True` vs truthy check
- 1 WARNING: TestModel __init__ constructor (PytestCollectionWarning)

## Config Validation (FIXED 2026-03-07)
- `config.py` now has REQUIRED_ENV check + `_safe_literal_eval()`
- Previous crash risk (ast.literal_eval on None) eliminated

## Empty/Dead Legacy Files (partially cleaned 2026-03-07)
- DELETED: dialog_factory.py, setup.py, form.py, view_tariff.py (getter), gift_getter.py, core/texts.py, referral_registration.py, key_management.py, admin_getter.py
- STILL EXIST (dead): `dialogs/loader.py` (imports deleted dialog_factory), `dialogs/gift_dialog.py` (imports deleted gift_getter)

## Middleware Stack
- Actual: DI -> Database -> Cache -> XUI -> Registration -> Logging -> DialogErrorHandler
- CLAUDE.md omits DI middleware (first in chain)
- `logging_middlewaries.py` renamed to `logging_middleware.py` (2026-03-07)

## Test Coverage Gaps
- `handlers/` -- only empty __init__.py, 0 actual tests
- `states/` -- only 1 test file (usage_rules) for 10 state files
- `middlewares/` -- 5 new test files added (2026-03-07)

## Vulture (project code only, post-cleanup)
- Only 2 findings: unused `caplog` in test_gift_scenario.py and test_registration.py
- jsonpickle import removed from client.py

## Startup Bug (main.py)
- while True retry loop re-registers middleware/routers on TelegramNetworkError
- Will cause duplicate middleware if network error occurs during polling
- Previous version had recursive `await main()` (stack overflow risk) -- new is better but not ideal

## Release Checklist Patterns
- Always verify conftest.py fixtures match current class signatures after refactoring
- After deleting files, grep for imports of those files in the entire codebase
- Check `dialogs/__init__.py` -- it's the real entry point, not loader.py or gift_dialog.py
- `ruff check --fix` safely removes ~150 unused imports
- Payment getters must return dict, never None (aiogram-dialog requirement)
- Webhook server is in tasks.py BackgroundTaskManager, NOT in main.py
