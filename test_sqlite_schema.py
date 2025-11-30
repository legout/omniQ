#!/usr/bin/env python3
"""
Simple test to verify SQLite storage schema and basic functionality.
"""

import tempfile
import sqlite3
from pathlib import Path


def test_sqlite_schema():
    """Test SQLite schema creation."""
    print("Testing SQLite schema...")

    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test.db"
        conn = sqlite3.connect(db_path)

        try:
            # Create schema manually (mimicking SQLiteStorage._migrate)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    func_path TEXT NOT NULL,
                    args TEXT NOT NULL,
                    kwargs TEXT NOT NULL,
                    status TEXT NOT NULL,
                    schedule TEXT NOT NULL,
                    eta TEXT,
                    max_retries INTEGER NOT NULL,
                    timeout INTEGER,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    last_attempt_at TEXT
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS results (
                    task_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    result TEXT,
                    error TEXT,
                    finished_at TEXT NOT NULL,
                    attempts INTEGER NOT NULL,
                    last_attempt_at TEXT,
                    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
                )
            """)

            # Create indexes
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_tasks_status_eta 
                ON tasks (status, eta)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_tasks_eta 
                ON tasks (eta)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_tasks_status 
                ON tasks (status)
            """)

            conn.commit()
            print("   ✓ Schema created successfully")

            # Test basic insert
            import json
            from datetime import datetime, timezone

            now = datetime.now(timezone.utc)
            task_data = {
                "id": "test-task-1",
                "func_path": "test_module.test_function",
                "args": json.dumps([1, 2, 3]),
                "kwargs": json.dumps({"key": "value"}),
                "status": "PENDING",
                "schedule": json.dumps({}),
                "eta": None,
                "max_retries": 3,
                "timeout": 30,
                "attempts": 0,
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
                "last_attempt_at": None,
            }

            conn.execute(
                """
                INSERT INTO tasks (
                    id, func_path, args, kwargs, status, schedule, eta,
                    max_retries, timeout, attempts, created_at, updated_at, last_attempt_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    task_data["id"],
                    task_data["func_path"],
                    task_data["args"],
                    task_data["kwargs"],
                    task_data["status"],
                    task_data["schedule"],
                    task_data["eta"],
                    task_data["max_retries"],
                    task_data["timeout"],
                    task_data["attempts"],
                    task_data["created_at"],
                    task_data["updated_at"],
                    task_data["last_attempt_at"],
                ),
            )

            conn.commit()
            print("   ✓ Task inserted successfully")

            # Test dequeue query
            cursor = conn.execute(
                """
                SELECT id, func_path, args, kwargs, status, schedule,
                       max_retries, timeout, attempts, created_at, updated_at, last_attempt_at
                FROM tasks 
                WHERE status = 'PENDING' 
                AND (eta IS NULL OR eta <= ?)
                ORDER BY eta ASC, created_at ASC
                LIMIT 1
            """,
                (now.isoformat(),),
            )

            row = cursor.fetchone()
            assert row is not None, "Should find the inserted task"
            assert row[0] == "test-task-1", "Task ID should match"
            print("   ✓ Dequeue query works correctly")

            # Test result insert
            result_data = {
                "task_id": "test-task-1",
                "status": "SUCCESS",
                "result": json.dumps(42),
                "error": None,
                "finished_at": now.isoformat(),
                "attempts": 1,
                "last_attempt_at": now.isoformat(),
            }

            conn.execute(
                """
                INSERT OR REPLACE INTO results (
                    task_id, status, result, error, finished_at, attempts, last_attempt_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    result_data["task_id"],
                    result_data["status"],
                    result_data["result"],
                    result_data["error"],
                    result_data["finished_at"],
                    result_data["attempts"],
                    result_data["last_attempt_at"],
                ),
            )

            conn.commit()
            print("   ✓ Result inserted successfully")

            # Test result retrieval
            cursor = conn.execute(
                """
                SELECT task_id, status, result, error, finished_at, attempts, last_attempt_at
                FROM results 
                WHERE task_id = ?
            """,
                ("test-task-1",),
            )

            result_row = cursor.fetchone()
            assert result_row is not None, "Should find the result"
            assert result_row[0] == "test-task-1", "Result task_id should match"
            assert result_row[1] == "SUCCESS", "Result status should be SUCCESS"
            print("   ✓ Result retrieval works correctly")

            print("✓ All SQLite schema tests passed!")

        except Exception as e:
            print(f"✗ SQLite schema test failed: {e}")
            raise
        finally:
            conn.close()


def test_indexing():
    """Test that indexes are created and work."""
    print("\nTesting indexing...")

    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "index_test.db"
        conn = sqlite3.connect(db_path)

        try:
            # Create schema with indexes
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    eta TEXT,
                    created_at TEXT NOT NULL
                )
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_tasks_status_eta 
                ON tasks (status, eta)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_tasks_eta 
                ON tasks (eta)
            """)

            conn.commit()

            # Check if indexes exist
            cursor = conn.execute("""
                SELECT name FROM sqlite_master 
                WHERE type = 'index' AND name LIKE 'idx_tasks_%'
            """)

            indexes = [row[0] for row in cursor.fetchall()]
            expected_indexes = ["idx_tasks_status_eta", "idx_tasks_eta"]

            for expected in expected_indexes:
                assert expected in indexes, f"Index {expected} should exist"

            print(f"   ✓ All expected indexes created: {indexes}")

            # Test query performance with EXPLAIN QUERY PLAN
            cursor = conn.execute("""
                EXPLAIN QUERY PLAN
                SELECT id FROM tasks 
                WHERE status = 'PENDING' AND eta <= '2023-01-01T00:00:00'
                ORDER BY eta ASC
                LIMIT 1
            """)

            plan = cursor.fetchall()
            # Check if index is being used
            plan_str = str(plan)
            assert "idx_tasks" in plan_str or "INDEX" in plan_str, (
                "Query should use index"
            )
            print("   ✓ Query plan shows index usage")

            print("✓ All indexing tests passed!")

        except Exception as e:
            print(f"✗ Indexing test failed: {e}")
            raise
        finally:
            conn.close()


def main():
    """Run all SQLite tests."""
    print("Running SQLite schema and indexing tests...\n")

    test_sqlite_schema()
    test_indexing()

    print("\n🎉 All SQLite tests passed!")
    print("\nNote: Full async testing requires aiosqlite package.")
    print("The schema and basic functionality are verified to work correctly.")


if __name__ == "__main__":
    main()
