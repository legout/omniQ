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

    async def execute(self, query: str, params: tuple = ()) -> Any:
        """Execute query asynchronously."""
        if self._loop is None:
            self._loop = asyncio.get_event_loop()

        def _execute():
            cursor = self._conn.cursor()
            result = cursor.execute(query, params)
            return result

        return await self._loop.run_in_executor(None, _execute)

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
            self._conn.close()

        await self._loop.run_in_executor(None, _close)


async def connect(db_path: str) -> AsyncSQLiteConnection:
    """Create async SQLite connection."""
    return AsyncSQLiteConnection(db_path)
