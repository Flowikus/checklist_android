from datetime import datetime
from typing import Any
from core.database.db_manager import DatabaseManager


class ChecklistRepository:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    # --- УПРАВЛЕНИЕ ШАБЛОНАМИ ЗАДАЧ И ЦЕЛЕЙ ---

    def create_checklist_item(
        self,
        title: str,
        period_type: str,
        has_numeric_input: bool = False,
        unit_name: str | None = None,
        target_value: float | None = None,
        days_of_week: str | None = None,
        goal_type: str = "numeric",
        linked_goal_ids: str | None = None,
    ) -> int:
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        clean_title = title.strip()

        if period_type == "week" and not days_of_week:
            days_of_week = "1,2,3,4,5,6,7"
        elif period_type != "week":
            days_of_week = None

        if period_type in ("month", "year"):
            linked_goal_ids = None
            has_numeric_input = (goal_type == "numeric")
        else:
            goal_type = "numeric"

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO checklists (
                    title, period_type, days_of_week, goal_type, linked_goal_ids,
                    has_numeric_input, unit_name, target_value, is_active, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
                """,
                (
                    clean_title,
                    period_type,
                    days_of_week,
                    goal_type,
                    linked_goal_ids if linked_goal_ids else None,
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

    def get_numeric_goals(self) -> list[dict[str, Any]]:
        """Возвращает все активные накопительные цели месяца и года для привязки к задачам."""
        query = """
            SELECT id, title, period_type, unit_name, target_value
            FROM checklists
            WHERE period_type IN ('month', 'year')
              AND goal_type = 'numeric'
              AND is_active = 1
            ORDER BY period_type ASC, id ASC
        """
        with self.db.get_connection() as conn:
            rows = conn.execute(query).fetchall()
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
        goal_type: str = "numeric",
        linked_goal_ids: str | None = None,
    ) -> None:
        clean_title = title.strip()

        if period_type == "week" and not days_of_week:
            days_of_week = "1,2,3,4,5,6,7"
        elif period_type != "week":
            days_of_week = None

        if period_type in ("month", "year"):
            linked_goal_ids = None
            has_numeric_input = (goal_type == "numeric")
        else:
            goal_type = "numeric"

        with self.db.get_connection() as conn:
            conn.execute(
                """
                UPDATE checklists
                SET title = ?, period_type = ?, days_of_week = ?, goal_type = ?,
                    linked_goal_ids = ?, has_numeric_input = ?, unit_name = ?, target_value = ?
                WHERE id = ?
                """,
                (
                    clean_title,
                    period_type,
                    days_of_week,
                    goal_type,
                    linked_goal_ids if linked_goal_ids else None,
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
    # --- ЕДИНЫЙ СПИСОК ЗАДАЧ НА ВЫБРАННЫЙ ДЕНЬ (ДНЕВНЫЕ + НЕДЕЛЬНЫЕ) ---

    def get_tasks_for_date(self, date_str: str, day_of_week: int) -> list[dict[str, Any]]:
        """
        Возвращает все задачи на конкретную дату ('YYYY-MM-DD') и день недели (1..7):
        1) Все ежедневные ('day') задачи
        2) Недельные ('week') задачи, назначенные на этот день недели
        """
        with self.db.get_connection() as conn:
            rows = conn.execute(
                """
                SELECT 
                    c.id,
                    c.title,
                    c.period_type,
                    c.days_of_week,
                    c.linked_goal_ids,
                    c.has_numeric_input,
                    c.unit_name,
                    c.target_value,
                    COALESCE(l.is_completed, 0) AS is_completed,
                    COALESCE(l.numeric_value, 0.0) AS numeric_value
                FROM checklists c
                LEFT JOIN checklist_logs l 
                    ON c.id = l.checklist_id 
                    AND l.period_identifier = ?
                    AND l.day_of_week = 0
                WHERE c.period_type IN ('day', 'week') AND c.is_active = 1
                ORDER BY c.period_type ASC, c.id ASC
                """,
                (date_str,),
            ).fetchall()

        day_str = str(day_of_week)
        tasks: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            if item["period_type"] == "week":
                days_raw = item.get("days_of_week")
                if days_raw and day_str not in days_raw.split(","):
                    continue
            item["is_goal_card"] = False
            tasks.append(item)

        return tasks

    def save_daily_task_progress(
        self,
        checklist_id: int,
        date_str: str,
        is_completed: bool,
        numeric_value: float = 0.0,
    ) -> None:
        """Сохраняет отметку или число для задачи на выбранную дату ('YYYY-MM-DD')."""
        with self.db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO checklist_logs (
                    checklist_id, period_identifier, day_of_week, log_date, is_completed, numeric_value
                )
                VALUES (?, ?, 0, ?, ?, ?)
                ON CONFLICT(checklist_id, period_identifier, day_of_week) DO UPDATE SET
                    log_date = excluded.log_date,
                    is_completed = excluded.is_completed,
                    numeric_value = excluded.numeric_value
                """,
                (
                    checklist_id,
                    date_str,
                    date_str,
                    1 if is_completed else 0,
                    float(numeric_value),
                ),
            )
            conn.commit()

    # --- ЦЕЛИ МЕСЯЦА И ГОДА (НАКОПИТЕЛЬНЫЕ И ЧЕК-БОКСЫ) ---

    def _calculate_linked_goal_sum(
        self,
        conn: Any,
        goal_id: int,
        period_identifier: str,
    ) -> float:
        """Суммирует числа из всех задач ('day'/'week'), привязанных к goal_id за месяц или год."""
        date_prefix = f"{period_identifier}%"
        rows = conn.execute(
            """
            SELECT c.linked_goal_ids, l.numeric_value
            FROM checklist_logs l
            JOIN checklists c ON c.id = l.checklist_id
            WHERE c.period_type IN ('day', 'week')
              AND c.linked_goal_ids IS NOT NULL
              AND l.log_date LIKE ?
              AND l.numeric_value > 0
            """,
            (date_prefix,),
        ).fetchall()

        target_id_str = str(goal_id)
        total = 0.0
        for r in rows:
            linked = [x.strip() for x in (r["linked_goal_ids"] or "").split(",") if x.strip()]
            if target_id_str in linked:
                total += float(r["numeric_value"] or 0.0)
        return total

    def get_goals_with_progress(self, period_type: str, period_identifier: str) -> list[dict[str, Any]]:
        """Возвращает цели 'month' или 'year' (накопительные считаются автоматически, разовые — из логов)."""
        with self.db.get_connection() as conn:
            goals = conn.execute(
                """
                SELECT 
                    c.id,
                    c.title,
                    c.period_type,
                    c.goal_type,
                    c.has_numeric_input,
                    c.unit_name,
                    c.target_value,
                    COALESCE(l.is_completed, 0) AS manual_completed
                FROM checklists c
                LEFT JOIN checklist_logs l
                    ON c.id = l.checklist_id
                    AND l.period_identifier = ?
                    AND l.day_of_week = 0
                WHERE c.period_type = ? AND c.is_active = 1
                ORDER BY c.id ASC
                """,
                (period_identifier, period_type),
            ).fetchall()

            result: list[dict[str, Any]] = []
            for g in goals:
                item = dict(g)
                g_type = item.get("goal_type") or "numeric"
                item["is_goal_card"] = True

                if g_type == "boolean":
                    item["is_completed"] = int(item["manual_completed"])
                    item["numeric_value"] = 0.0
                else:
                    accumulated = self._calculate_linked_goal_sum(conn, item["id"], period_identifier)
                    target = float(item["target_value"] or 0.0)
                    item["numeric_value"] = accumulated
                    item["is_completed"] = 1 if (target > 0 and accumulated >= target) else 0

                result.append(item)
            return result

    def save_boolean_goal_progress(
        self,
        goal_id: int,
        period_identifier: str,
        is_completed: bool,
    ) -> None:
        """Сохраняет отметку выполнения для разовой цели-чекбокса ('Прочитать книгу' и т.п.)."""
        today_str = datetime.now().strftime("%Y-%m-%d")
        with self.db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO checklist_logs (
                    checklist_id, period_identifier, day_of_week, log_date, is_completed, numeric_value
                )
                VALUES (?, ?, 0, ?, ?, 0.0)
                ON CONFLICT(checklist_id, period_identifier, day_of_week) DO UPDATE SET
                    log_date = excluded.log_date,
                    is_completed = excluded.is_completed
                """,
                (goal_id, period_identifier, today_str, 1 if is_completed else 0),
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

    def get_period_summary_stats(self, period_type: str, period_identifier: str) -> dict[str, Any]:
        """Считает статистику для кольцевой диаграммы на экране 'Аналитика'."""
        if period_type == "day":
            dt = datetime.strptime(period_identifier, "%Y-%m-%d")
            tasks = self.get_tasks_for_date(period_identifier, dt.isoweekday())
        elif period_type in ("month", "year"):
            tasks = self.get_goals_with_progress(period_type, period_identifier)
        else:
            tasks = []

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
        """Возвращает историю для BarChart и LineChart."""
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
                      AND c.linked_goal_ids IS NOT NULL
                    GROUP BY period_identifier
                    ORDER BY period_identifier DESC
                    LIMIT ?
                """
                rows = conn.execute(query, (limit,)).fetchall()
                return [dict(row) for row in reversed(rows)]

            query = """
                SELECT 
                    l.period_identifier,
                    SUM(l.is_completed) AS completed_count,
                    SUM(l.numeric_value) AS total_numeric
                FROM checklist_logs l
                JOIN checklists c ON c.id = l.checklist_id
                WHERE c.period_type IN ('day', 'week')
                GROUP BY l.period_identifier
                ORDER BY l.period_identifier DESC
                LIMIT ?
            """
            rows = conn.execute(query, (limit,)).fetchall()
            return [dict(row) for row in reversed(rows)]
