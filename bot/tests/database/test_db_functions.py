import pytest
from unittest.mock import AsyncMock, patch

from database import create_db_pool


@pytest.mark.asyncio
async def test_create_db_pool_success():
    # Given
    with patch(
        "database.base.asyncpg.create_pool", new_callable=AsyncMock
    ) as mock_create_pool:
        mock_pool = AsyncMock()
        mock_create_pool.return_value = mock_pool

        # When
        result = await create_db_pool()

        # Then
        assert result == mock_pool
        mock_create_pool.assert_called_once()


@pytest.mark.asyncio
async def test_create_db_pool_failure():
    # Given
    with patch("database.base.asyncpg.create_pool") as mock_create_pool:
        mock_create_pool.side_effect = Exception("Connection failed")

        # When/Then
        with pytest.raises(Exception, match="Connection failed"):
            await create_db_pool()
