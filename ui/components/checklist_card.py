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
        self.has_numeric: bool = bool(task_data["has_numeric_input"])
        self.unit_name: str = task_data["unit_name"] or ""
        self.target_value: float | None = task_data["target_value"]
        self.on_progress_changed = on_progress_changed

        is_done = bool(task_data["is_completed"])
        num_val = float(task_data["numeric_value"] or 0.0)

        # Чек-бокс
        self.checkbox = ft.Checkbox(
            value=is_done,
            active_color=AppColors.SUCCESS,
            check_color="#FFFFFF",
            on_change=self._handle_checkbox_change,
        )

        # Название задачи (при выполнении немного приглушается)
        self.title_text = ft.Text(
            task_data["title"],
            size=16,
            weight=ft.FontWeight.W_600,
            color=AppColors.TEXT_SECONDARY if is_done else AppColors.TEXT_PRIMARY,
        )

        # Подзаголовок с целью (если она задана)
        subtitle_controls: list[ft.Control] = [self.title_text]
        if self.has_numeric and self.target_value:
            target_fmt = int(self.target_value) if self.target_value.is_integer() else self.target_value
            self.target_label = ft.Text(
                f"Цель: {target_fmt} {self.unit_name}".strip(),
                size=12,
                color=AppColors.TEXT_SECONDARY,
            )
            subtitle_controls.append(self.target_label)

        row_controls: list[ft.Control] = [
            self.checkbox,
            ft.Column(
                controls=subtitle_controls,
                spacing=2,
                expand=True,
            ),
        ]

        # Если включен числовой ввод — добавляем компактное поле справа
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
        # Автоматически ставим галочку, если введено значение > 0
        is_done = num_val > 0
        if self.checkbox.value != is_done:
            self.checkbox.value = is_done
            try:
                self.checkbox.update()
            except RuntimeError:
                pass
        self._update_visual_state(is_done)
        self.on_progress_changed(self.task_id, is_done, num_val)
