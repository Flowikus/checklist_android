from datetime import datetime
from typing import Any
from core.database.db_manager import DatabaseManager


class ChecklistRepository:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    @staticmethod
    def _normalize_key(title: str) -> str:
        return title.strip().lower()

    # --- УПРАВЛЕНИЕ ШАБЛОНАМИ ЗАДАЧ И ЦЕЛЕЙ (ЭКРАН НАСТРОЕК) ---

    def create_checklist_item(
        self,
        title: str,
        period_type: str,
        has_numeric_input: bool = False,
        unit_name: str | None = None,
        target_value: float | None = None,
        days_of_week: str | None = None,
        goal_key: str | None = None,
    ) -> int:
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        clean_title = title.strip()
        resolved_goal_key = (goal_key or self._normalize_key(clean_title)).strip().lower()

        if period_type == "week" and not days_of_week:
            days_of_week = "1,2,3,4,5,6,7"
        elif period_type != "week":
            days_of_week = None

        # Для целей месяца и года числовой формат обязателен
        if period_type in ("month", "year"):
            has_numeric_input = True

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO checklists (
                    title, goal_key, period_type, days_of_week, has_numeric_input,
                    unit_name, target_value, is_active, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)
                """,
                (
                    clean_title,
                    resolved_goal_key,
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

    def get_active_goal_suggestions(self) -> list[dict[str, Any]]:
        """Возвращает уникальные цели из вкладок 'Месяц' и 'Год' для подсказок в 'Дне' и 'Неделе'."""
        query = """
            SELECT title, goal_key, unit_name, period_type, target_value
            FROM checklists
            WHERE period_type IN ('month', 'year') AND is_active = 1
            ORDER BY id ASC
        """
        with self.db.get_connection() as conn:
            rows = conn.execute(query).fetchall()

        seen_keys: set[str] = set()
        suggestions: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            g_key = item.get("goal_key") or self._normalize_key(item["title"])
            if g_key not in seen_keys:
                seen_keys.add(g_key)
                item["goal_key"] = g_key
                suggestions.append(item)
        return suggestions

    def update_checklist_item(
        self,
        item_id: int,
        title: str,
        period_type: str,
        has_numeric_input: bool,
        unit_name: str | None,
        target_value: float | None,
        days_of_week: str | None = None,
        goal_key: str | None = None,
    ) -> None:
        clean_title = title.strip()
        resolved_goal_key = (goal_key or self._normalize_key(clean_title)).strip().lower()

        if period_type == "week" and not days_of_week:
            days_of_week = "1,2,3,4,5,6,7"
        elif period_type != "week":
            days_of_week = None

        if period_type in ("month", "year"):
            has_numeric_input = True

        with self.db.get_connection() as conn:
            conn.execute(
                """
                UPDATE checklists
                SET title = ?, goal_key = ?, period_type = ?, days_of_week = ?,
                    has_numeric_input = ?, unit_name = ?, target_value = ?
                WHERE id = ?
                """,
                (
                    clean_title,
                    resolved_goal_key,
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
        with self.db.get_connection() as conn:
            conn.execute("DELETE FROM checklists WHERE id = ?", (item_id,))
            conn.commit()

    # --- РАБОТА С ПРОГРЕССОМ В ТЕКУЩЕМ ПЕРИОДЕ ---

    def _calculate_goal_accumulated_value(
        self,
        conn: Any,
        goal_key: str,
        period_type: str,
        period_identifier: str,
    ) -> float:
        """
        Суммирует числовые записи из дневных и недельных чек-листов
        за указанный месяц ('YYYY-MM') или год ('YYYY').
        """
        # period_identifier для месяца имеет вид '2026-11', для года — '2026'.
        # log_date в checklist_logs хранится как 'YYYY-MM-DD', поэтому LIKE '2026-11%' и '2026%'
        # точно захватывают все записи за нужный месяц или год!
        date_prefix = f"{period_identifier}%"

        row = conn.execute(
            """
            SELECT COALESCE(SUM(l.numeric_value), 0.0) AS total_val
            FROM checklist_logs l
            JOIN checklists c ON c.id = l.checklist_id
            WHERE c.period_type IN ('day', 'week')
              AND c.goal_key = ?
              AND l.log_date LIKE ?
            """,
            (goal_key, date_prefix),
        ).fetchone()

        return float(row["total_val"] or 0.0)

    def get_period_tasks_with_progress(
        self,
        period_type: str,
        period_identifier: str,
        day_of_week: int | None = None,
    ) -> list[dict[str, Any]]:
        """Возвращает задачи (для 'day'/'week') или цели с накопленным итогом (для 'month'/'year')."""
        with self.db.get_connection() as conn:
            # Для месяца и года считаем цели автоматически из дневных и недельных записей
            if period_type in ("month", "year"):
                goals = conn.execute(
                    """
                    SELECT id, title, goal_key, period_type, has_numeric_input, unit_name, target_value
                    FROM checklists
                    WHERE period_type = ? AND is_active = 1
                    ORDER BY id ASC
                    """,
                    (period_type,),
                ).fetchall()

                result_goals: list[dict[str, Any]] = []
                for g in goals:
                    item = dict(g)
                    g_key = item.get("goal_key") or self._normalize_key(item["title"])
                    accumulated = self._calculate_goal_accumulated_value(
                        conn, g_key, period_type, period_identifier
                    )
                    target = float(item["target_value"] or 0.0)
                    is_done = 1 if (target > 0 and accumulated >= target) else 0

                    item["numeric_value"] = accumulated
                    item["is_completed"] = is_done
                    item["is_goal_card"] = True
                    result_goals.append(item)

                return result_goals

            # Для дня и недели работаем с обычными задачами
            log_day = day_of_week if (period_type == "week" and day_of_week is not None) else 0
            rows = conn.execute(
                """
                SELECT 
                    c.id,
                    c.title,
                    c.goal_key,
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
                """,
                (period_identifier, log_day, period_type),
            ).fetchall()
            result = [dict(row) for row in rows]

        if period_type == "week" and day_of_week is not None:
            day_str = str(day_of_week)
            return [
                task for task in result
                if not task.get("days_of_week") or day_str in task["days_of_week"].split(",")
            ]

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
        """Считает общую статистику для бейджа и кольцевой диаграммы."""
        if period_type == "week" and day_of_week is None:
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

    def get_historical_completion(self, period_type: str, limit: int = 6) -> list[dict[str, Any]]:
        """Возвращает статистику выполнения за последние периоды для BarChart и LineChart."""
        with self.db.get_connection() as conn:
            if period_type in ("month", "year"):
                slice_len = 7 if period_type == "month" else 4
                query = f"""
                    SELECT 
                        SUBSTR(l.log_date, 1, {slice_len}) AS period_identifier,
                        SUM(l.is_completed) AS completed_count,
                        SUM(l.numeric_value) AS total_numeric
                    FROM checklist_logs l
                    JOIN checklists c ON c.id = l.checklist_id
                    WHERE c.period_type IN ('day', 'week')
                      AND c.goal_key IN (
                          SELECT goal_key FROM checklists WHERE period_type = ? AND is_active = 1
                      )
                    GROUP BY period_identifier
                    ORDER BY period_identifier DESC
                    LIMIT ?
                """
                rows = conn.execute(query, (period_type, limit)).fetchall()
                return [dict(row) for row in reversed(rows)]

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
            rows = conn.execute(query, (period_type, limit)).fetchall()
            return [dict(row) for row in reversed(rows)]
