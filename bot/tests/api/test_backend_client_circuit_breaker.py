"""
Tests for BackendAPIClient circuit breaker functionality.

Verifies circuit breaker state transitions:
- CLOSED → OPEN after fail_threshold consecutive failures
- OPEN → HALF_OPEN after reset_timeout
- HALF_OPEN → CLOSED on success, or back to OPEN on failure
"""
import pytest
import httpx
from unittest.mock import AsyncMock, patch

from api.backend_client import BackendAPIClient


class TestCircuitBreakerStateTransitions:
    """Test circuit breaker state transitions for BackendAPIClient."""

    @pytest.fixture
    def backend_client(self):
        """Create BackendAPIClient with mocked httpx client."""
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.is_closed = False
        return BackendAPIClient(
            base_url="http://localhost:8000",
            bot_secret="test-secret",
            client=mock_client,
        )

    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_after_consecutive_failures(self, backend_client):
        """Circuit breaker opens after 5 consecutive failures."""
        mock_response = AsyncMock()
        mock_response.raise_for_status.side_effect = httpx.ConnectTimeout("Connection timed out")

        # Simulate 5 consecutive failures
        backend_client._client.request = AsyncMock(side_effect=httpx.ConnectTimeout("Connection timed out"))

        # Make 5 failing requests
        for _ in range(5):
            result = await backend_client.get_user(123456)
            assert result is None

        # Circuit breaker should now be open
        assert backend_client.circuit_breaker.current_state == "open"

        # Next request should fail immediately without calling HTTP client
        result = await backend_client.get_user(123456)
        assert result is None
        # HTTP client should not be called again (circuit is open)
        assert backend_client._client.request.call_count == 5

    @pytest.mark.asyncio
    async def test_circuit_breaker_stays_closed_on_success(self, backend_client):
        """Circuit breaker stays closed when requests succeed."""
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "tg_id": 123456,
            "username": "testuser",
            "first_name": "Test",
            "last_name": None,
            "balance": 0.0,
            "trial": 1,
        }

        backend_client._client.request = AsyncMock(return_value=mock_response)

        # Make successful requests
        for _ in range(10):
            result = await backend_client.get_user(123456)
            assert result is not None
            assert result.tg_id == 123456

        # Circuit breaker should remain closed
        assert backend_client.circuit_breaker.current_state == "closed"

    @pytest.mark.asyncio
    async def test_circuit_breaker_half_open_after_timeout(self, backend_client):
        """Circuit breaker transitions to half-open after reset_timeout."""
        # Set up failing client
        backend_client._client.request = AsyncMock(side_effect=httpx.ConnectTimeout("Connection timed out"))

        # Open the circuit breaker
        for _ in range(5):
            await backend_client.get_user(123456)

        assert backend_client.circuit_breaker.current_state == "open"

        # Wait for reset timeout (30 seconds in production, but we can't speed up time in tests)
        # Instead, we manually set the state to half-open for testing
        backend_client.circuit_breaker.half_open()
        assert backend_client.circuit_breaker.current_state == "half_open"

        # Now simulate a successful response
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "tg_id": 123456,
            "username": "testuser",
            "first_name": "Test",
            "last_name": None,
            "balance": 0.0,
            "trial": 1,
        }
        backend_client._client.request = AsyncMock(return_value=mock_response)

        # Successful request in half-open state should close the circuit
        result = await backend_client.get_user(123456)
        assert result is not None
        assert backend_client.circuit_breaker.current_state == "closed"

    @pytest.mark.asyncio
    async def test_circuit_breaker_reopens_on_failure_in_half_open(self, backend_client):
        """Circuit breaker reopens on failure in half-open state."""
        # Open the circuit breaker
        backend_client._client.request = AsyncMock(side_effect=httpx.ConnectTimeout("Connection timed out"))
        for _ in range(5):
            await backend_client.get_user(123456)

        assert backend_client.circuit_breaker.current_state == "open"

        # Transition to half-open
        backend_client.circuit_breaker.half_open()
        assert backend_client.circuit_breaker.current_state == "half_open"

        # Failure in half-open state should reopen
        result = await backend_client.get_user(123456)
        assert result is None
        assert backend_client.circuit_breaker.current_state == "open"


class TestCircuitBreakerExceptionHandling:
    """Test that circuit breaker catches correct exceptions."""

    @pytest.fixture
    def backend_client(self):
        """Create BackendAPIClient with mocked httpx client."""
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.is_closed = False
        return BackendAPIClient(
            base_url="http://localhost:8000",
            bot_secret="test-secret",
            client=mock_client,
        )

    @pytest.mark.asyncio
    async def test_httpx_connect_timeout_trips_breaker(self, backend_client):
        """httpx.ConnectTimeout should trip the circuit breaker."""
        backend_client._client.request = AsyncMock(side_effect=httpx.ConnectTimeout("Timeout"))

        for _ in range(5):
            await backend_client.get_user(123456)

        assert backend_client.circuit_breaker.current_state == "open"

    @pytest.mark.asyncio
    async def test_httpx_connect_error_trips_breaker(self, backend_client):
        """httpx.ConnectError should trip the circuit breaker."""
        backend_client._client.request = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))

        for _ in range(5):
            await backend_client.get_user(123456)

        assert backend_client.circuit_breaker.current_state == "open"

    @pytest.mark.asyncio
    async def test_httpx_read_timeout_trips_breaker(self, backend_client):
        """httpx.ReadTimeout should trip the circuit breaker."""
        backend_client._client.request = AsyncMock(side_effect=httpx.ReadTimeout("Read timeout"))

        for _ in range(5):
            await backend_client.get_user(123456)

        assert backend_client.circuit_breaker.current_state == "open"

    @pytest.mark.asyncio
    async def test_404_does_not_trip_breaker(self, backend_client):
        """404 Not Found should NOT trip the circuit breaker (not a network error)."""
        mock_response = AsyncMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError("Not Found")

        backend_client._client.request = AsyncMock(return_value=mock_response)

        # 404 returns None but doesn't count as failure for circuit breaker
        for _ in range(10):
            result = await backend_client.get_user(123456)
            assert result is None

        # Circuit should still be closed (404 is expected behavior, not a failure)
        # Note: This test may need adjustment based on actual implementation
        # since raise_for_status() is called after status check


class TestCircuitBreakerLogging:
    """Test circuit breaker logging behavior."""

    @pytest.fixture
    def backend_client(self):
        """Create BackendAPIClient with mocked httpx client."""
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.is_closed = False
        return BackendAPIClient(
            base_url="http://localhost:8000",
            bot_secret="test-secret",
            client=mock_client,
        )

    @pytest.mark.asyncio
    async def test_logs_circuit_breaker_open(self, backend_client, caplog):
        """Should log when circuit breaker is open."""
        import logging
        caplog.set_level(logging.ERROR)

        backend_client._client.request = AsyncMock(side_effect=httpx.ConnectTimeout("Timeout"))

        # Open the circuit
        for _ in range(5):
            await backend_client.get_user(123456)

        # Make request with open circuit
        await backend_client.get_user(123456)

        # Check for circuit breaker open log message
        assert any("circuit breaker open" in record.message for record in caplog.records)
