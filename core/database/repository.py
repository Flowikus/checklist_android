from datetime import datetime
from typing import Any
from core.database.db_manager import DatabaseManager


class ChecklistRepository:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    # --- УПРАВЛЕНИЕ ШАБЛОНАМИ ЗАДАЧ (ЭКРАН НАСТРОЕК) ---

    def create_checklist_item(
        self,
        title: str,
        period_type: str,
        has_numeric_input: bool = False,
        unit_name: str | None = None,
        target_value: float | None = None,
        days_of_week: str | None = None,
    ) -> int:
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # Для недели по умолчанию ставим все дни, если не переданы конкретные
        if period_type == "week" and not days_of_week:
            days_of_week = "1,2,3,4,5,6,7"
        elif period_type != "week":
            days_of_week = None

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO checklists (
                    title, period_type, days_of_week, has_numeric_input, unit_name, target_value, is_active, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, 1, ?)
                """,
                (
                    title.strip(),
                    period_type,
                    days_of_week,
                    1 if has_numeric_input else 0,
                    unit_name.strip() if unit_name else None,
                    target_value,
                    created_at,
                ),
            )
            conn.commit()
            return cursor.lastrowid

    def get_all_items(self, period_type: str | None = None, only_active: bool = True) -> list[dict[str, Any]]:
        query = "SELECT * FROM checklists WHERE 1=1"
        params: list[Any] = []

        if period_type:
            query += " AND period_type = ?"
            params.append(period_type)
        if only_active:
            query += " AND is_active = 1"

        query += " ORDER BY id ASC"

        with self.db.get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]

    def update_checklist_item(
        self,
        item_id: int,
        title: str,
        period_type: str,
        has_numeric_input: bool,
        unit_name: str | None,
        target_value: float | None,
        days_of_week: str | None = None,
    ) -> None:
        if period_type == "week" and not days_of_week:
            days_of_week = "1,2,3,4,5,6,7"
        elif period_type != "week":
            days_of_week = None

        with self.db.get_connection() as conn:
            conn.execute(
                """
                UPDATE checklists
                SET title = ?, period_type = ?, days_of_week = ?, has_numeric_input = ?, unit_name = ?, target_value = ?
                WHERE id = ?
                """,
                (
                    title.strip(),
                    period_type,
                    days_of_week,
                    1 if has_numeric_input else 0,
                    unit_name.strip() if unit_name else None,
                    target_value,
                    item_id,
                ),
            )
            conn.commit()

    def delete_checklist_item(self, item_id: int) -> None:
        """Удаляет пункт и всю связанную историю (через ON DELETE CASCADE)."""
        with self.db.get_connection() as conn:
            conn.execute("DELETE FROM checklists WHERE id = ?", (item_id,))
            conn.commit()

    # --- РАБОТА С ПРОГРЕССОМ В ТЕКУЩЕМ ПЕРИОДЕ ---

    def get_period_tasks_with_progress(
        self,
        period_type: str,
        period_identifier: str,
        day_of_week: int | None = None,
    ) -> list[dict[str, Any]]:
        """Возвращает активные задачи периода (с учетом дня недели для 'week') и их прогресс."""
        log_day = day_of_week if (period_type == "week" and day_of_week is not None) else 0

        query = """
            SELECT 
                c.id,
                c.title,
                c.period_type,
                c.days_of_week,
                c.has_numeric_input,
                c.unit_name,
                c.target_value,
                COALESCE(l.is_completed, 0) AS is_completed,
                COALESCE(l.numeric_value, 0.0) AS numeric_value,
                l.log_date
            FROM checklists c
            LEFT JOIN checklist_logs l 
                ON c.id = l.checklist_id 
                AND l.period_identifier = ?
                AND l.day_of_week = ?
            WHERE c.period_type = ? AND c.is_active = 1
            ORDER BY c.id ASC
        """
        with self.db.get_connection() as conn:
            rows = conn.execute(query, (period_identifier, log_day, period_type)).fetchall()
            result = [dict(row) for row in rows]

        # Для недельного чек-листа оставляем только задачи, назначенные на выбранный день (1..7)
        if period_type == "week" and day_of_week is not None:
            day_str = str(day_of_week)
            filtered = []
            for task in result:
                days_raw = task.get("days_of_week")
                if not days_raw or day_str in days_raw.split(","):
                    filtered.append(task)
            return filtered

        return result

    def save_task_progress(
        self,
        checklist_id: int,
        period_identifier: str,
        is_completed: bool,
        numeric_value: float = 0.0,
        day_of_week: int = 0,
    ) -> None:
        """Создает или обновляет отметку выполнения / числовое значение."""
        today_str = datetime.now().strftime("%Y-%m-%d")
        with self.db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO checklist_logs (
                    checklist_id, period_identifier, day_of_week, log_date, is_completed, numeric_value
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(checklist_id, period_identifier, day_of_week) DO UPDATE SET
                    log_date = excluded.log_date,
                    is_completed = excluded.is_completed,
                    numeric_value = excluded.numeric_value
                """,
                (
                    checklist_id,
                    period_identifier,
                    day_of_week,
                    today_str,
                    1 if is_completed else 0,
                    float(numeric_value),
                ),
            )
            conn.commit()

    # --- РОТАЦИЯ ПЕРИОДОВ ---

    def get_last_prompted_period(self, period_type: str) -> str | None:
        with self.db.get_connection() as conn:
            row = conn.execute(
                "SELECT last_prompted_period FROM period_states WHERE period_type = ?",
                (period_type,),
            ).fetchone()
            return row["last_prompted_period"] if row else None

    def set_last_prompted_period(self, period_type: str, period_identifier: str) -> None:
        with self.db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO period_states (period_type, last_prompted_period)
                VALUES (?, ?)
                ON CONFLICT(period_type) DO UPDATE SET
                    last_prompted_period = excluded.last_prompted_period
                """,
                (period_type, period_identifier),
            )
            conn.commit()

    # --- АНАЛИТИКА И ГРАФИКИ ---

    def get_period_summary_stats(
        self,
        period_type: str,
        period_identifier: str,
        day_of_week: int | None = None,
    ) -> dict[str, Any]:
        """Считает общую статистику для кольцевой диаграммы (PieChart)."""
        if period_type == "week" and day_of_week is None:
            # Сводный прогресс по всем 7 дням недели
            total = 0
            completed = 0
            for d in range(1, 8):
                day_tasks = self.get_period_tasks_with_progress("week", period_identifier, day_of_week=d)
                total += len(day_tasks)
                completed += sum(1 for t in day_tasks if t["is_completed"] == 1)
        else:
            tasks = self.get_period_tasks_with_progress(period_type, period_identifier, day_of_week=day_of_week)
            total = len(tasks)
            completed = sum(1 for t in tasks if t["is_completed"] == 1)

        percent = round((completed / total) * 100, 1) if total > 0 else 0.0
        return {
            "total": total,
            "completed": completed,
            "remaining": total - completed,
            "percent": percent,
        }

    def get_historical_completion(self, period_type: str, limit: int = 7) -> list[dict[str, Any]]:
        """Возвращает статистику выполнения за последние периоды для BarChart и LineChart."""
        query = """
            SELECT 
                l.period_identifier,
                SUM(l.is_completed) AS completed_count,
                SUM(l.numeric_value) AS total_numeric
            FROM checklist_logs l
            JOIN checklists c ON c.id = l.checklist_id
            WHERE c.period_type = ?
            GROUP BY l.period_identifier
            ORDER BY l.period_identifier DESC
            LIMIT ?
        """
        with self.db.get_connection() as conn:
            rows = conn.execute(query, (period_type, limit)).fetchall()
            return [dict(row) for row in reversed(rows)]
