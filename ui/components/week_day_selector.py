from typing import Callable
import flet as ft
from core.constants.colors import AppColors
from core.constants.strings import AppStrings


class WeekDaySelector(ft.Row):
    def __init__(
        self,
        selected_days: list[int] | None = None,
        allow_multiple: bool = False,
        on_change: Callable[[list[int]], None] | None = None,
    ):
        super().__init__(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            spacing=4,
        )
        self.allow_multiple = allow_multiple
        self.on_change = on_change
        self.selected_days: set[int] = set(selected_days if selected_days else (1,))
        self.buttons: dict[int, ft.Container] = {}

        self._build_buttons()

    def _build_buttons(self) -> None:
        self.controls.clear()
        self.buttons.clear()

        for idx, day_label in enumerate(AppStrings.DAYS_SHORT, start=1):
            is_selected = idx in self.selected_days
            btn = ft.Container(
                content=ft.Text(
                    day_label,
                    size=13,
                    weight=ft.FontWeight.W_600,
                    color="#FFFFFF" if is_selected else AppColors.TEXT_PRIMARY,
                ),
                width=40,
                height=38,
                border_radius=10,
                bgcolor=AppColors.PRIMARY if is_selected else AppColors.CARD_BG,
                border=ft.Border.all(
                    1,
                    AppColors.PRIMARY if is_selected else AppColors.DIVIDER,
                ),
                alignment=ft.Alignment.CENTER,
                ink=True,
                on_click=lambda e, day_num=idx: self._on_day_click(day_num),
            )
            self.buttons[idx] = btn
            self.controls.append(btn)

    def _on_day_click(self, day_num: int) -> None:
        if self.allow_multiple:
            if day_num in self.selected_days:
                # Не даем снять последний оставшийся день
                if len(self.selected_days) > 1:
                    self.selected_days.remove(day_num)
            else:
                self.selected_days.add(day_num)
        else:
            self.selected_days = {day_num}

        self._refresh_styles()
        if self.on_change:
            self.on_change(sorted(self.selected_days))

    def _refresh_styles(self) -> None:
        for idx, btn in self.buttons.items():
            is_selected = idx in self.selected_days
            btn.bgcolor = AppColors.PRIMARY if is_selected else AppColors.CARD_BG
            btn.border = ft.Border.all(
                1,
                AppColors.PRIMARY if is_selected else AppColors.DIVIDER,
            )
            btn.content.color = "#FFFFFF" if is_selected else AppColors.TEXT_PRIMARY
        try:
            self.update()
        except RuntimeError:
            pass

    def get_selected_days_str(self) -> str:
        return ",".join(str(d) for d in sorted(self.selected_days))
