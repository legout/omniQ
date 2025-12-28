"""
Simple async SQLite wrapper using built-in sqlite3 with thread executor.
This is a fallback implementation when aiosqlite is not available.
"""

import asyncio
import sqlite3
from typing import Any, Optional


class AsyncSQLiteConnection:
    """Async wrapper around sqlite3 connection."""

    def __init__(self, db_path: str):
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._loop = None
        self._cursor = None

    async def execute(self, query: str, params: tuple = ()) -> Any:
        """Execute query asynchronously."""
        if self._loop is None:
            self._loop = asyncio.get_event_loop()

        def _execute():
            self._cursor = self._conn.cursor()
            result = self._cursor.execute(query, params)
            return result

        return await self._loop.run_in_executor(None, _execute)

    async def executemany(self, query: str, params_list: list) -> Any:
        """Execute query with multiple parameter sets asynchronously."""
        if self._loop is None:
            self._loop = asyncio.get_event_loop()

        def _executemany():
            self._cursor = self._conn.cursor()
            result = self._cursor.executemany(query, params_list)
            return result

        return await self._loop.run_in_executor(None, _executemany)

    async def fetchone(self) -> Optional[sqlite3.Row]:
        """Fetch one row from last query result."""
        if self._loop is None:
            self._loop = asyncio.get_event_loop()

        def _fetchone():
            if self._cursor is None:
                return None
            return self._cursor.fetchone()

        return await self._loop.run_in_executor(None, _fetchone)

    async def fetchall(self) -> list:
        """Fetch all rows from last query result."""
        if self._loop is None:
            self._loop = asyncio.get_event_loop()

        def _fetchall():
            if self._cursor is None:
                return []
            return self._cursor.fetchall()

        return await self._loop.run_in_executor(None, _fetchall)

    async def commit(self) -> None:
        """Commit transaction asynchronously."""
        if self._loop is None:
            self._loop = asyncio.get_event_loop()

        def _commit():
            self._conn.commit()

        await self._loop.run_in_executor(None, _commit)

    async def rollback(self) -> None:
        """Rollback transaction asynchronously."""
        if self._loop is None:
            self._loop = asyncio.get_event_loop()

        def _rollback():
            self._conn.rollback()

        await self._loop.run_in_executor(None, _rollback)

    async def close(self) -> None:
        """Close connection asynchronously."""
        if self._loop is None:
            self._loop = asyncio.get_event_loop()

        def _close():
            if self._cursor is not None:
                self._cursor.close()
            self._conn.close()

        await self._loop.run_in_executor(None, _close)


async def connect(db_path: str) -> AsyncSQLiteConnection:
    """Create async SQLite connection."""
    return AsyncSQLiteConnection(db_path)
