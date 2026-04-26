"""
Тесты для BaseRepository.

Причина переписывания: оригинальные тесты использовали mock_conn как AsyncMock(spec=asyncpg.Pool),
но BaseRepository._acquire() вызывает pool.acquire() для Pool-экземпляров,
что даёт цепочку AsyncMock.acquire().__aenter__() вместо прямого соединения.
Решение: передавать мок как asyncpg.Connection (не Pool) — тогда _acquire()
использует _ConnectionWrapper напрямую.
"""

import pytest
from unittest.mock import AsyncMock

from database.base import BaseRepository


class TestModel:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


def create_repository():
    return BaseRepository("test_table", TestModel)


def make_conn_mock():
    """
    Создаёт мок соединения (Connection, не Pool).
    BaseRepository._acquire проверяет isinstance(x, asyncpg.Pool).
    Если передать объект, который НЕ является Pool, используется _ConnectionWrapper,
    и conn передаётся напрямую — без дополнительной цепочки acquire().
    """
    conn = AsyncMock()
    # Явно НЕ ставим spec=asyncpg.Pool — тогда isinstance(conn, asyncpg.Pool) == False
    return conn


# ---------------------------------------------------------------------------
# Инициализация
# ---------------------------------------------------------------------------


def test_init_repository():
    table_name = "users"
    model = TestModel
    repository = BaseRepository(table_name, model)
    assert repository.table_name == table_name
    assert repository.model == model


# ---------------------------------------------------------------------------
# get()
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_success():
    repository = create_repository()
    conn = make_conn_mock()
    expected_record = {"id": 1, "name": "test"}
    conn.fetchrow.return_value = expected_record

    result = await repository.get(conn, id=1)

    assert result is not None
    assert result.id == 1
    assert result.name == "test"
    conn.fetchrow.assert_called_once_with("SELECT * FROM test_table WHERE id = $1", 1)


@pytest.mark.asyncio
async def test_get_no_result():
    repository = create_repository()
    conn = make_conn_mock()
    conn.fetchrow.return_value = None

    result = await repository.get(conn, id=999)

    assert result is None


@pytest.mark.asyncio
async def test_get_multiple_filters_raises_error():
    repository = create_repository()
    conn = make_conn_mock()

    with pytest.raises(ValueError, match="Only one filter parameter is allowed"):
        await repository.get(conn, id=1, name="test")


# ---------------------------------------------------------------------------
# get_all()
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_all():
    repository = create_repository()
    conn = make_conn_mock()
    records = [{"id": 1, "name": "test1"}, {"id": 2, "name": "test2"}]
    conn.fetch.return_value = records

    result = await repository.get_all(conn)

    assert len(result) == 2
    assert result[0].id == 1
    assert result[1].name == "test2"
    conn.fetch.assert_called_once_with("SELECT * FROM test_table")


# ---------------------------------------------------------------------------
# delete()
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_success():
    repository = create_repository()
    conn = make_conn_mock()
    conn.execute.return_value = "DELETE 1"

    result = await repository.delete(conn, id=1)

    assert result is True
    conn.execute.assert_called_once_with("DELETE FROM test_table WHERE id = $1", 1)


@pytest.mark.asyncio
async def test_delete_no_filters():
    repository = create_repository()
    conn = make_conn_mock()

    result = await repository.delete(conn)

    assert result is False


@pytest.mark.asyncio
async def test_delete_failure():
    repository = create_repository()
    conn = make_conn_mock()
    conn.execute.return_value = "DELETE 0"

    result = await repository.delete(conn, id=999)

    assert result is False


# ---------------------------------------------------------------------------
# create()
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_success():
    repository = create_repository()
    conn = make_conn_mock()
    conn.execute.return_value = "INSERT 1"
    data = {"name": "test", "value": "data"}

    result = await repository.create(conn, **data)

    assert result is True
    conn.execute.assert_called_once()
    call_args = conn.execute.call_args
    query = call_args[0][0]
    assert "INSERT INTO test_table" in query
    assert "name" in query
    assert "value" in query
    assert call_args[0][1] == "test"
    assert call_args[0][2] == "data"


@pytest.mark.asyncio
async def test_create_failure():
    repository = create_repository()
    conn = make_conn_mock()
    conn.execute.return_value = "INSERT 0"

    result = await repository.create(conn, name="test")

    assert result is False


@pytest.mark.asyncio
async def test_create_rejects_id_in_payload():
    """
    Регрессионный тест: если вызывающий код передаёт id в create(),
    он попадёт в INSERT — это нарушает SERIAL семантику.
    Правильный путь: использовать model.to_dict() перед вызовом create().
    Тест документирует это поведение (id проходит напрямую).
    """
    repository = create_repository()
    conn = make_conn_mock()
    conn.execute.return_value = "INSERT 1"

    result = await repository.create(conn, id=99, name="test")

    assert result is True
    call_args = conn.execute.call_args
    query = call_args[0][0]
    # id присутствует в запросе — это нежелательно для SERIAL-полей,
    # поэтому модели должны использовать _DB_FIELDS в to_dict()
    assert "id" in query


# ---------------------------------------------------------------------------
# update()
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_success():
    repository = create_repository()
    conn = make_conn_mock()
    conn.execute.return_value = "UPDATE 1"
    search_data = {"id": 1}
    update_data = {"name": "updated", "value": "new"}

    result = await repository.update(conn, search_data, **update_data)

    assert result is True
    conn.execute.assert_called_once()
    call_args = conn.execute.call_args
    query = call_args[0][0]
    assert "UPDATE test_table" in query
    assert "WHERE id = $1" in query
    assert call_args[0][1] == 1


@pytest.mark.asyncio
async def test_update_no_data_or_search():
    repository = create_repository()
    conn = make_conn_mock()

    result1 = await repository.update(conn, {}, name="test")
    result2 = await repository.update(conn, {"id": 1})

    assert result1 is False
    assert result2 is False


@pytest.mark.asyncio
async def test_update_failure():
    repository = create_repository()
    conn = make_conn_mock()
    conn.execute.return_value = "UPDATE 0"

    result = await repository.update(conn, {"id": 1}, name="test")

    assert result is False
