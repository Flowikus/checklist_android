from typing import Any, Callable
import flet as ft
from core.constants.colors import AppColors


class ChecklistCard(ft.Card):
    def __init__(
        self,
        task_data: dict[str, Any],
        on_progress_changed: Callable[[int, bool, float], None],
    ):
        super().__init__()
        self.task_id: int = task_data["id"]
        self.has_numeric: bool = bool(task_data.get("has_numeric_input", False))
        self.unit_name: str = task_data.get("unit_name") or ""
        self.target_value: float | None = task_data.get("target_value")
        self.on_progress_changed = on_progress_changed
        self.number_field: ft.TextField | None = None

        is_done = bool(task_data["is_completed"])
        num_val = float(task_data.get("numeric_value") or 0.0)
        is_goal_card = bool(task_data.get("is_goal_card", False))
        goal_type = task_data.get("goal_type") or "numeric"

        # --- РЕЖИМ 1: РАЗОВАЯ ЦЕЛЬ-ЧЕКБОКС ("Прочитать книгу", "Освоить навык") ---
        if is_goal_card and goal_type == "boolean":
            self.checkbox = ft.Checkbox(
                value=is_done,
                active_color=AppColors.SUCCESS,
                check_color="#FFFFFF",
                on_change=self._handle_checkbox_change,
            )
            self.title_text = ft.Text(
                task_data["title"],
                size=15,
                weight=ft.FontWeight.W_600,
                color=AppColors.TEXT_SECONDARY if is_done else AppColors.TEXT_PRIMARY,
                expand=True,
            )
            self.content = ft.Container(
                padding=ft.Padding.symmetric(horizontal=10, vertical=6),
                content=ft.Row(
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        self.checkbox,
                        ft.Icon(
                            ft.Icons.EMOJI_EVENTS if is_done else ft.Icons.FLAG_OUTLINED,
                            size=18,
                            color=AppColors.SUCCESS if is_done else AppColors.PRIMARY,
                        ),
                        self.title_text,
                    ],
                ),
            )
            return

        # --- РЕЖИМ 2: НАКОПИТЕЛЬНАЯ ЦЕЛЬ С ПРОГРЕСС-БАРОМ ---
        if is_goal_card:
            target = float(self.target_value or 0.0)
            progress = min(num_val / target, 1.0) if target > 0 else 0.0
            percent = round((num_val / target) * 100, 1) if target > 0 else 0.0

            cur_fmt = int(num_val) if num_val.is_integer() else round(num_val, 1)
            target_fmt = int(target) if target.is_integer() else target

            status_color = AppColors.SUCCESS if is_done else AppColors.PRIMARY

            self.content = ft.Container(
                padding=ft.Padding.symmetric(horizontal=14, vertical=10),
                content=ft.Column(
                    spacing=6,
                    controls=[
                        ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            controls=[
                                ft.Row(
                                    spacing=8,
                                    expand=True,
                                    controls=[
                                        ft.Icon(
                                            ft.Icons.EMOJI_EVENTS if is_done else ft.Icons.FLAG_OUTLINED,
                                            size=18,
                                            color=status_color,
                                        ),
                                        ft.Text(
                                            task_data["title"],
                                            size=15,
                                            weight=ft.FontWeight.W_600,
                                            color=AppColors.TEXT_PRIMARY,
                                            expand=True,
                                        ),
                                    ],
                                ),
                                ft.Container(
                                    bgcolor=AppColors.PRIMARY_LIGHT,
                                    padding=ft.Padding.symmetric(horizontal=8, vertical=3),
                                    border_radius=12,
                                    content=ft.Text(
                                        f"{percent}%",
                                        size=12,
                                        weight=ft.FontWeight.W_600,
                                        color=status_color,
                                    ),
                                ),
                            ],
                        ),
                        ft.ProgressBar(
                            value=progress,
                            color=status_color,
                            bgcolor=AppColors.DIVIDER,
                            height=7,
                            border_radius=4,
                        ),
                        ft.Text(
                            f"Накоплено: {cur_fmt} / {target_fmt} {self.unit_name}".strip(),
                            size=12,
                            color=AppColors.TEXT_SECONDARY,
                        ),
                    ],
                ),
            )
            return

        # --- РЕЖИМ 3: ЗАДАЧА НА СЕГОДНЯ ("День" или "Неделя") ---

        if self.has_numeric:
            target = float(self.target_value or 0.0)
            is_done = (num_val >= target) if target > 0 else (num_val > 0)

        self.checkbox = ft.Checkbox(
            value=is_done,
            disabled=self.has_numeric,
            active_color=AppColors.SUCCESS,
            check_color="#FFFFFF",
            on_change=self._handle_checkbox_change,
        )


        self.title_text = ft.Text(
            task_data["title"],
            size=16,
            weight=ft.FontWeight.W_600,
            color=AppColors.TEXT_SECONDARY if is_done else AppColors.TEXT_PRIMARY,
        )

        subtitle_controls: list[ft.Control] = [self.title_text]
        sub_hints: list[str] = []

        if self.has_numeric and self.target_value:
            target_fmt = int(self.target_value) if self.target_value.is_integer() else self.target_value
            sub_hints.append(f"Ориентир: {target_fmt} {self.unit_name}".strip())

        if task_data.get("linked_goal_ids"):
            sub_hints.append("Связано с целью")

        if sub_hints:
            subtitle_controls.append(
                ft.Text(
                    " • ".join(sub_hints),
                    size=12,
                    color=AppColors.TEXT_SECONDARY,
                )
            )

        row_controls: list[ft.Control] = [
            self.checkbox,
            ft.Column(
                controls=subtitle_controls,
                spacing=2,
                expand=True,
            ),
        ]

        self.number_field: ft.TextField | None = None
        if self.has_numeric:
            display_val = ""
            if num_val > 0:
                display_val = str(int(num_val) if num_val.is_integer() else num_val)

            self.number_field = ft.TextField(
                value=display_val,
                hint_text="0",
                width=85,
                height=44,
                text_align=ft.TextAlign.RIGHT,
                keyboard_type=ft.KeyboardType.NUMBER,
                content_padding=ft.Padding.symmetric(horizontal=10, vertical=8),
                border_radius=10,
                border_color=AppColors.DIVIDER,
                focused_border_color=AppColors.PRIMARY,
                text_size=15,
                on_change=self._handle_number_change,
            )

            row_controls.append(
                ft.Row(
                    spacing=6,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        self.number_field,
                        ft.Text(
                            self.unit_name,
                            size=13,
                            color=AppColors.TEXT_SECONDARY,
                            width=36,
                        ),
                    ],
                )
            )

        self.content = ft.Container(
            padding=ft.Padding.symmetric(horizontal=10, vertical=8),
            content=ft.Row(
                controls=row_controls,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=8,
            ),
        )

    def _parse_numeric_value(self) -> float:
        if not self.number_field or not self.number_field.value:
            return 0.0
        try:
            val = float(self.number_field.value.replace(",", ".").strip())
            return max(0.0, val)
        except ValueError:
            return 0.0

    def _update_visual_state(self, is_done: bool) -> None:
        self.title_text.color = AppColors.TEXT_SECONDARY if is_done else AppColors.TEXT_PRIMARY
        try:
            self.title_text.update()
        except RuntimeError:
            pass

    def _handle_checkbox_change(self, e: ft.ControlEvent) -> None:
        is_done = bool(self.checkbox.value)
        num_val = self._parse_numeric_value()
        self._update_visual_state(is_done)
        self.on_progress_changed(self.task_id, is_done, num_val)

    def _handle_number_change(self, e: ft.ControlEvent) -> None:
        num_val = self._parse_numeric_value()
        target = float(self.target_value or 0.0)
        is_done = (num_val >= target) if target > 0 else (num_val > 0)

        if self.checkbox.value != is_done:
            self.checkbox.value = is_done
            try:
                self.checkbox.update()
            except RuntimeError:
                pass
        self._update_visual_state(is_done)
        self.on_progress_changed(self.task_id, is_done, num_val)
