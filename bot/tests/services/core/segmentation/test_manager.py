import pytest
from unittest.mock import AsyncMock

from models import User
from services.core.segmentation.manager import SegmentationManager
from services.core.segmentation.model import UserSegment


class TestSegmentationManager:
    @pytest.fixture
    def mock_segmenter(self):
        segmenter = AsyncMock()
        segmenter.determine_segment.return_value = UserSegment.NEW_USER
        return segmenter

    @pytest.fixture
    def manager(self, mock_segmenter):
        return SegmentationManager(mock_segmenter)

    @pytest.fixture
    def users_data(self):
        user1 = User(tg_id=123, username="user1", trial=0, created_at=None, server_id=1)
        user2 = User(tg_id=456, username="user2", trial=1, created_at=None, server_id=1)
        return [{"user": user1, "keys": []}, {"user": user2, "keys": []}]

    @pytest.mark.asyncio
    async def test_distribution_proces_single_segment(
        self, manager, users_data, mock_segmenter
    ):
        # Все пользователи попадают в один сегмент

        mock_segmenter.determine_segment.return_value = UserSegment.NEW_USER

        result: dict = await manager.distribution_proces(users_data)

        assert len(result) == 1
        assert UserSegment.NEW_USER in result.keys()
        assert len(result[UserSegment.NEW_USER]) == 2
        assert result[UserSegment.NEW_USER][0].tg_id == 123
        assert result[UserSegment.NEW_USER][1].tg_id == 456

    @pytest.mark.asyncio
    async def test_distribution_proces_multiple_segments(
        self, manager, users_data, mock_segmenter
    ):
        # Разные пользователи попадают в разные сегменты
        mock_segmenter.determine_segment.side_effect = [
            UserSegment.NEW_USER,
            UserSegment.INACTIVE_TRIAL,
        ]

        result = await manager.distribution_proces(users_data)

        assert len(result) == 2
        assert UserSegment.NEW_USER in result
        assert UserSegment.INACTIVE_TRIAL in result
        assert len(result[UserSegment.NEW_USER]) == 1
        assert len(result[UserSegment.INACTIVE_TRIAL]) == 1
        assert result[UserSegment.NEW_USER][0].tg_id == 123
        assert result[UserSegment.INACTIVE_TRIAL][0].tg_id == 456

    @pytest.mark.asyncio
    async def test_distribution_proces_empty_users(self, manager):
        """Проверка, что при пустом списке пользователей возвращается пустой словарь"""
        result = await manager.distribution_proces([])

        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_distribution_proces_updates_existing_segments(
        self, manager, users_data, mock_segmenter
    ):
        # Проверяем, что сегменты накапливаются правильно
        mock_segmenter.determine_segment.side_effect = [
            UserSegment.NEW_USER,
            UserSegment.NEW_USER,
        ]

        result = await manager.distribution_proces(users_data)

        assert len(result) == 1
        assert UserSegment.NEW_USER in result
        assert len(result[UserSegment.NEW_USER]) == 2
