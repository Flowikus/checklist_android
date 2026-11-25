from typing import Callable
import flet as ft
from core.constants.colors import AppColors
from core.constants.strings import AppStrings


class WeekDaySelector(ft.Row):
    def __init__(
        self,
        selected_days: list[int] | None = None,
        allow_multiple: bool = True,
        on_change: Callable[[list[int]], None] | None = None,
    ):
        super().__init__(
            spacing=4,
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )
        self.selected_days: set[int] = set(selected_days) if selected_days else set(range(1, 2))
        self.allow_multiple = allow_multiple
        self.on_change = on_change
        self.day_buttons: dict[int, ft.Container] = {}

        self._build_buttons()

    def _build_buttons(self) -> None:
        self.controls.clear()
        self.day_buttons.clear()

        for idx, day_label in enumerate(AppStrings.DAYS_SHORT, start=1):
            is_selected = idx in self.selected_days
            btn = ft.Container(
                expand=True,
                height=38,
                border_radius=8,
                bgcolor=AppColors.PRIMARY if is_selected else AppColors.SURFACE_VARIANT,
                alignment=ft.Alignment.CENTER,
                ink=True,
                on_click=lambda e, d=idx: self._toggle_day(d),
                content=ft.Text(
                    day_label,
                    size=12,
                    weight=ft.FontWeight.W_600,
                    color="#FFFFFF" if is_selected else AppColors.TEXT_PRIMARY,
                ),
            )
            self.day_buttons[idx] = btn
            self.controls.append(btn)

    def _toggle_day(self, day_num: int) -> None:
        if self.allow_multiple:
            if day_num in self.selected_days:
                if len(self.selected_days) > 1:
                    self.selected_days.remove(day_num)
            else:
                self.selected_days.add(day_num)
        else:
            self.selected_days = {day_num}

        for d_idx, btn in self.day_buttons.items():
            active = d_idx in self.selected_days
            btn.bgcolor = AppColors.PRIMARY if active else AppColors.SURFACE_VARIANT
            btn.content.color = "#FFFFFF" if active else AppColors.TEXT_PRIMARY

        try:
            self.update()
        except RuntimeError:
            pass

        if self.on_change:
            self.on_change(sorted(self.selected_days))

    def get_selected_days_str(self) -> str:
        return ",".join(str(d) for d in sorted(self.selected_days))
