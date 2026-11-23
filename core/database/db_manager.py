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
        conn.row_factory = sqlite3.Row  # Позволяет обращаться к колонкам по имени: row["title"]
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def init_db(self) -> None:
        """Создает таблицы при первом запуске приложения."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # 1. Шаблоны чек-листов
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS checklists (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    period_type TEXT NOT NULL CHECK(period_type IN ('week', 'month', 'year')),
                    has_numeric_input INTEGER NOT NULL DEFAULT 0,
                    unit_name TEXT,
                    target_value REAL,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL
                );
            """)

            # 2. История выполнения и числовой прогресс
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS checklist_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    checklist_id INTEGER NOT NULL,
                    period_identifier TEXT NOT NULL,
                    log_date TEXT NOT NULL,
                    is_completed INTEGER NOT NULL DEFAULT 0,
                    numeric_value REAL NOT NULL DEFAULT 0.0,
                    FOREIGN KEY (checklist_id) REFERENCES checklists (id) ON DELETE CASCADE,
                    UNIQUE(checklist_id, period_identifier)
                );
            """)

            # 3. Контроль ротации периодов
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS period_states (
                    period_type TEXT PRIMARY KEY CHECK(period_type IN ('week', 'month', 'year')),
                    last_prompted_period TEXT NOT NULL
                );
            """)

            conn.commit()
