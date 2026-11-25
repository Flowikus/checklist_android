import os
import sqlite3
from pathlib import Path


def get_db_path() -> str:
    """Возвращает безопасный путь к файлу БД для Android и ПК."""
    storage_dir = os.getenv("FLET_APP_STORAGE_DATA")
    if storage_dir:
        base_path = Path(storage_dir)
    else:
        base_path = Path("storage/data")

    base_path.mkdir(parents=True, exist_ok=True)
    return str(base_path / "checklists.db")


class DatabaseManager:
    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or get_db_path()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def init_db(self) -> None:
        """Создает таблицы при первом запуске или безопасно мигрирует старую БД до v4."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='checklists';"
            )
            table_exists = cursor.fetchone() is not None

            if not table_exists:
                self._create_v4_tables(cursor)
            else:
                cursor.execute("PRAGMA table_info(checklists);")
                columns = [row["name"] for row in cursor.fetchall()]

                # Если база совсем старая (v1)
                if "days_of_week" not in columns:
                    self._migrate_v1_to_v4(cursor)
                else:
                    # Миграция с v2/v3 до v4
                    if "goal_type" not in columns:
                        cursor.execute(
                            "ALTER TABLE checklists ADD COLUMN goal_type TEXT NOT NULL DEFAULT 'numeric';"
                        )
                    if "linked_goal_ids" not in columns:
                        cursor.execute(
                            "ALTER TABLE checklists ADD COLUMN linked_goal_ids TEXT;"
                        )
                        # Переносим старые связи по goal_key в прямые ID целей
                        if "goal_key" in columns:
                            self._migrate_goal_keys_to_ids(cursor)

            conn.commit()

    def _migrate_goal_keys_to_ids(self, cursor: sqlite3.Cursor) -> None:
        """Связывает существующие дневные/недельные задачи с целями месяца/года по старому goal_key."""
        cursor.execute(
            "SELECT id, goal_key FROM checklists WHERE period_type IN ('month', 'year') AND is_active = 1;"
        )
        goals = cursor.fetchall()
        key_to_ids: dict[str, list[str]] = {}
        for g in goals:
            g_key = (g["goal_key"] or "").strip().lower()
            if g_key:
                key_to_ids.setdefault(g_key, []).append(str(g["id"]))

        cursor.execute(
            "SELECT id, goal_key FROM checklists WHERE period_type IN ('day', 'week');"
        )
        tasks = cursor.fetchall()
        for t in tasks:
            t_key = (t["goal_key"] or "").strip().lower()
            if t_key and t_key in key_to_ids:
                linked_str = ",".join(key_to_ids[t_key])
                cursor.execute(
                    "UPDATE checklists SET linked_goal_ids = ? WHERE id = ?;",
                    (linked_str, t["id"]),
                )

    def _create_v4_tables(self, cursor: sqlite3.Cursor) -> None:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS checklists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                period_type TEXT NOT NULL CHECK(period_type IN ('day', 'week', 'month', 'year')),
                days_of_week TEXT,
                goal_type TEXT NOT NULL DEFAULT 'numeric',
                linked_goal_ids TEXT,
                has_numeric_input INTEGER NOT NULL DEFAULT 0,
                unit_name TEXT,
                target_value REAL,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS checklist_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                checklist_id INTEGER NOT NULL,
                period_identifier TEXT NOT NULL,
                day_of_week INTEGER NOT NULL DEFAULT 0,
                log_date TEXT NOT NULL,
                is_completed INTEGER NOT NULL DEFAULT 0,
                numeric_value REAL NOT NULL DEFAULT 0.0,
                FOREIGN KEY (checklist_id) REFERENCES checklists (id) ON DELETE CASCADE,
                UNIQUE(checklist_id, period_identifier, day_of_week)
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS period_states (
                period_type TEXT PRIMARY KEY CHECK(period_type IN ('day', 'week', 'month', 'year')),
                last_prompted_period TEXT NOT NULL
            );
        """)

    def _migrate_v1_to_v4(self, cursor: sqlite3.Cursor) -> None:
        cursor.execute("PRAGMA foreign_keys = OFF;")

        cursor.execute("ALTER TABLE checklists RENAME TO checklists_old;")
        cursor.execute("ALTER TABLE checklist_logs RENAME TO checklist_logs_old;")
        cursor.execute("ALTER TABLE period_states RENAME TO period_states_old;")

        self._create_v4_tables(cursor)

        cursor.execute("""
            INSERT INTO checklists (
                id, title, period_type, days_of_week, goal_type, linked_goal_ids,
                has_numeric_input, unit_name, target_value, is_active, created_at
            )
            SELECT
                id,
                title,
                period_type,
                CASE WHEN period_type = 'week' THEN '1,2,3,4,5,6,7' ELSE NULL END,
                'numeric',
                NULL,
                has_numeric_input,
                unit_name,
                target_value,
                is_active,
                created_at
            FROM checklists_old;
        """)

        cursor.execute("""
            INSERT INTO checklist_logs (
                id, checklist_id, period_identifier, day_of_week,
                log_date, is_completed, numeric_value
            )
            SELECT
                id, checklist_id, period_identifier, 0,
                log_date, is_completed, numeric_value
            FROM checklist_logs_old;
        """)

        cursor.execute("""
            INSERT INTO period_states (period_type, last_prompted_period)
            SELECT period_type, last_prompted_period
            FROM period_states_old;
        """)

        cursor.execute("DROP TABLE checklist_logs_old;")
        cursor.execute("DROP TABLE checklists_old;")
        cursor.execute("DROP TABLE period_states_old;")

        cursor.execute("PRAGMA foreign_keys = ON;")
