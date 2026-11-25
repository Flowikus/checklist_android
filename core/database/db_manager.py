import os
import sqlite3
from datetime import datetime
from pathlib import Path


def get_db_path() -> str:
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
        """Создает таблицы при первом запуске или безопасно мигрирует БД до v5."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='checklists';"
            )
            table_exists = cursor.fetchone() is not None

            if not table_exists:
                self._create_v5_tables(cursor)
            else:
                cursor.execute("PRAGMA table_info(checklists);")
                columns = [row["name"] for row in cursor.fetchall()]

                if "days_of_week" not in columns:
                    self._migrate_v1_to_v5(cursor)
                else:
                    if "goal_type" not in columns:
                        cursor.execute(
                            "ALTER TABLE checklists ADD COLUMN goal_type TEXT NOT NULL DEFAULT 'numeric';"
                        )
                    if "linked_goal_ids" not in columns:
                        cursor.execute(
                            "ALTER TABLE checklists ADD COLUMN linked_goal_ids TEXT;"
                        )

                # Миграция v5: добавляем reward_claimed в checklist_logs и таблицу plant_state
                cursor.execute("PRAGMA table_info(checklist_logs);")
                log_cols = [row["name"] for row in cursor.fetchall()]
                if "reward_claimed" not in log_cols:
                    cursor.execute(
                        "ALTER TABLE checklist_logs ADD COLUMN reward_claimed INTEGER NOT NULL DEFAULT 0;"
                    )

                self._create_plant_table(cursor)

            conn.commit()

    def _create_plant_table(self, cursor: sqlite3.Cursor) -> None:
        today_str = datetime.now().strftime("%Y-%m-%d")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS plant_state (
                id INTEGER PRIMARY KEY CHECK(id = 1),
                plant_name TEXT NOT NULL DEFAULT 'Росток',
                coins INTEGER NOT NULL DEFAULT 30,
                xp INTEGER NOT NULL DEFAULT 0,
                hydration INTEGER NOT NULL DEFAULT 80,
                last_decay_date TEXT NOT NULL,
                care_date TEXT NOT NULL,
                sun_count_today INTEGER NOT NULL DEFAULT 0,
                water_count_today INTEGER NOT NULL DEFAULT 0,
                fertilize_count_today INTEGER NOT NULL DEFAULT 0,
                last_perfect_day_date TEXT
            );
        """)
        cursor.execute(
            """
            INSERT OR IGNORE INTO plant_state (
                id, plant_name, coins, xp, hydration, last_decay_date, care_date
            )
            VALUES (1, 'Росток', 30, 0, 80, ?, ?);
            """,
            (today_str, today_str),
        )

    def _create_v5_tables(self, cursor: sqlite3.Cursor) -> None:
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
                reward_claimed INTEGER NOT NULL DEFAULT 0,
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

        self._create_plant_table(cursor)

    def _migrate_v1_to_v5(self, cursor: sqlite3.Cursor) -> None:
        cursor.execute("PRAGMA foreign_keys = OFF;")

        cursor.execute("ALTER TABLE checklists RENAME TO checklists_old;")
        cursor.execute("ALTER TABLE checklist_logs RENAME TO checklist_logs_old;")
        cursor.execute("ALTER TABLE period_states RENAME TO period_states_old;")

        self._create_v5_tables(cursor)

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
                log_date, is_completed, numeric_value, reward_claimed
            )
            SELECT
                id, checklist_id, period_identifier, 0,
                log_date, is_completed, numeric_value, is_completed
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
