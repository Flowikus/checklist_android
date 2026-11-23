import os
import sqlite3
from pathlib import Path


def get_db_path() -> str:
    """Возвращает безопасный путь к файлу БД для Android и ПК."""
    storage_dir = os.getenv("FLET_APP_STORAGE_DATA")
    if storage_dir:
        base_path = Path(storage_dir)
    else:
        # Локальная папка при разработке и тестировании на ПК
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
        """Создает таблицы при первом запуске или безопасно мигрирует старую БД."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Проверяем, существует ли уже таблица checklists от старой версии
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='checklists';"
            )
            table_exists = cursor.fetchone() is not None

            if not table_exists:
                self._create_v2_tables(cursor)
            else:
                # Проверяем, нужна ли миграция (есть ли колонка days_of_week)
                cursor.execute("PRAGMA table_info(checklists);")
                columns = [row["name"] for row in cursor.fetchall()]
                if "days_of_week" not in columns:
                    self._migrate_v1_to_v2(cursor)

            conn.commit()

    def _create_v2_tables(self, cursor: sqlite3.Cursor) -> None:
        """Создает актуальную структуру таблиц v2 с поддержкой 'day' и дней недели."""
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS checklists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                period_type TEXT NOT NULL CHECK(period_type IN ('day', 'week', 'month', 'year')),
                days_of_week TEXT,
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

    def _migrate_v1_to_v2(self, cursor: sqlite3.Cursor) -> None:
        """Переносит существующие данные из v1 в v2 с обновлением CHECK и UNIQUE."""
        cursor.execute("PRAGMA foreign_keys = OFF;")

        # 1. Переименовываем старые таблицы
        cursor.execute("ALTER TABLE checklists RENAME TO checklists_old;")
        cursor.execute("ALTER TABLE checklist_logs RENAME TO checklist_logs_old;")
        cursor.execute("ALTER TABLE period_states RENAME TO period_states_old;")

        # 2. Создаем новые таблицы v2
        self._create_v2_tables(cursor)

        # 3. Копируем данные из старых таблиц (старые недельные задачи будут видны во все дни недели: '1,2,3,4,5,6,7')
        cursor.execute("""
            INSERT INTO checklists (
                id, title, period_type, days_of_week, has_numeric_input,
                unit_name, target_value, is_active, created_at
            )
            SELECT
                id,
                title,
                period_type,
                CASE WHEN period_type = 'week' THEN '1,2,3,4,5,6,7' ELSE NULL END,
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

        # 4. Удаляем временные старые таблицы
        cursor.execute("DROP TABLE checklist_logs_old;")
        cursor.execute("DROP TABLE checklists_old;")
        cursor.execute("DROP TABLE period_states_old;")

        cursor.execute("PRAGMA foreign_keys = ON;")
