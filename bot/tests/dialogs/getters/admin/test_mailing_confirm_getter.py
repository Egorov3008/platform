"""
Tests for MailingConfirmGetter.

MailingConfirmGetter.get_data():
- Reads 'text' from dialog_data (default "Не задано")
- Returns statuses list with exactly 2 items (pin / no-pin)
- No external dependencies — pure dialog_data access
"""

from unittest.mock import AsyncMock

import pytest

from dialogs.windows.getters.admin.mailing import MailingConfirmGetter


@pytest.fixture
def mock_dialog_manager():
    manager = AsyncMock()
    manager.dialog_data = {}
    manager.start_data = {}
    manager.middleware_data = {}
    return manager


class TestMailingConfirmGetter:
    """Tests for MailingConfirmGetter.get_data()."""

    async def test_returns_text_key(self, mock_dialog_manager):
        """Result dict must always contain 'text' key."""
        mock_dialog_manager.dialog_data["text"] = "Test broadcast message"

        getter = MailingConfirmGetter()
        result = await getter.get_data(mock_dialog_manager)

        assert "text" in result

    async def test_text_from_dialog_data(self, mock_dialog_manager):
        """text must equal the value stored in dialog_data['text']."""
        mock_dialog_manager.dialog_data["text"] = "Hello subscribers!"

        getter = MailingConfirmGetter()
        result = await getter.get_data(mock_dialog_manager)

        assert result["text"] == "Hello subscribers!"

    async def test_text_default_when_absent(self, mock_dialog_manager):
        """When 'text' is absent from dialog_data, default 'Не задано' is returned."""
        mock_dialog_manager.dialog_data = {}

        getter = MailingConfirmGetter()
        result = await getter.get_data(mock_dialog_manager)

        assert result["text"] == "Не задано"

    async def test_statuses_has_two_items(self, mock_dialog_manager):
        """statuses must contain exactly 2 items: pin and no-pin options."""
        getter = MailingConfirmGetter()
        result = await getter.get_data(mock_dialog_manager)

        assert "statuses" in result
        assert len(result["statuses"]) == 2
