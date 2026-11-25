from typing import Any
import flet as ft
from core.constants.colors import AppColors
from core.constants.strings import AppStrings
from core.database.repository import ChecklistRepository
from ui.components.week_day_selector import WeekDaySelector


class SettingsView(ft.Container):
    def __init__(self, page: ft.Page, repo: ChecklistRepository, initial_period: str = AppStrings.PERIOD_DAY):
        super().__init__(expand=True, padding=ft.Padding.only(left=16, right=16, top=12))
        self.app_page = page
        self.repo = repo
        self.selected_period = initial_period

        self.period_selector = ft.SegmentedButton(
            selected=[self.selected_period],
            allow_multiple_selection=False,
            on_change=self._on_period_change,
            segments=[
                ft.Segment(value=AppStrings.PERIOD_DAY, label=ft.Text(AppStrings.TAB_DAY)),
                ft.Segment(value=AppStrings.PERIOD_WEEK, label=ft.Text(AppStrings.TAB_WEEK)),
                ft.Segment(value=AppStrings.PERIOD_MONTH, label=ft.Text(AppStrings.TAB_MONTH)),
                ft.Segment(value=AppStrings.PERIOD_YEAR, label=ft.Text(AppStrings.TAB_YEAR)),
            ],
        )

        self.tasks_column = ft.Column(
            spacing=10,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )

        self.add_button_label = ft.Text("Добавить пункт", weight=ft.FontWeight.W_600)

        add_button = ft.FilledButton(
            content=ft.Row(
                [ft.Icon(ft.Icons.ADD, size=20), self.add_button_label],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=6,
            ),
            style=ft.ButtonStyle(
                bgcolor=AppColors.PRIMARY,
                color="#FFFFFF",
                shape=ft.RoundedRectangleBorder(radius=12),
                padding=ft.Padding.symmetric(vertical=14),
            ),
            on_click=lambda e: self._open_task_dialog(item=None),
        )

        self.content = ft.Column(
            controls=[
                ft.Text(
                    AppStrings.SETTINGS_HEADER,
                    size=22,
                    weight=ft.FontWeight.BOLD,
                    color=AppColors.TEXT_PRIMARY,
                ),
                ft.Container(content=self.period_selector, alignment=ft.Alignment.CENTER),
                self.tasks_column,
                ft.Container(content=add_button, padding=ft.Padding.only(bottom=12, top=4)),
            ],
            spacing=14,
            expand=True,
        )

        self._update_add_button_label()
        self.load_tasks(should_update=False)

    def _update_add_button_label(self) -> None:
        is_goal = self.selected_period in (AppStrings.PERIOD_MONTH, AppStrings.PERIOD_YEAR)
        self.add_button_label.value = "Добавить цель" if is_goal else "Добавить пункт"

    def set_period(self, period_type: str) -> None:
        self.selected_period = period_type
        self.period_selector.selected = [period_type]
        self._update_add_button_label()
        self.load_tasks()

    def _on_period_change(self, e: ft.ControlEvent) -> None:
        if e.control.selected:
            self.selected_period = next(iter(e.control.selected))
            self._update_add_button_label()
            self.load_tasks()
    def load_tasks(self, should_update: bool = True) -> None:
        self.tasks_column.controls.clear()
        items = self.repo.get_all_items(period_type=self.selected_period, only_active=True)
        is_goal = self.selected_period in (AppStrings.PERIOD_MONTH, AppStrings.PERIOD_YEAR)

        if not items:
            self.tasks_column.controls.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Icon(
                                ft.Icons.FLAG_OUTLINED if is_goal else ft.Icons.CHECKLIST_RTL,
                                size=48,
                                color=AppColors.DIVIDER,
                            ),
                            ft.Text(
                                "Целей для этого периода пока нет" if is_goal else "Список для этого периода пока пуст",
                                size=15,
                                color=AppColors.TEXT_SECONDARY,
                            ),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=8,
                    ),
                    alignment=ft.Alignment.CENTER,
                    padding=ft.Padding.only(top=60),
                )
            )
        else:
            for item in items:
                self.tasks_column.controls.append(self._build_task_card(item))

        if should_update:
            try:
                self.update()
            except RuntimeError:
                pass

    @staticmethod
    def _format_days_badge(days_raw: str | None) -> str:
        if not days_raw:
            return "Все дни"
        nums = [int(d) for d in days_raw.split(",") if d.isdigit()]
        if len(nums) == 7:
            return "Все дни"
        return ", ".join(AppStrings.DAYS_SHORT[n - 1] for n in sorted(nums) if 1 <= n <= 7)

    def _build_task_card(self, item: dict[str, Any]) -> ft.Card:
        is_goal = item["period_type"] in (AppStrings.PERIOD_MONTH, AppStrings.PERIOD_YEAR)
        subtitle_parts = []

        if item["period_type"] == AppStrings.PERIOD_WEEK:
            days_text = self._format_days_badge(item.get("days_of_week"))
            subtitle_parts.append(f"[{days_text}]")

        if is_goal:
            unit = item["unit_name"] or "ед."
            target = item["target_value"] or 0
            target_fmt = int(target) if float(target).is_integer() else target
            subtitle_parts.append(f"Цель: {target_fmt} {unit} (автоподсчёт)")
        elif item["has_numeric_input"]:
            unit = item["unit_name"] or "ед."
            if item["target_value"]:
                target_fmt = int(item["target_value"]) if item["target_value"].is_integer() else item["target_value"]
                subtitle_parts.append(f"Числовой ввод • Ориентир: {target_fmt} {unit}")
            else:
                subtitle_parts.append(f"Числовой ввод ({unit})")
        else:
            subtitle_parts.append("Обычная отметка (чек-бокс)")

        return ft.Card(
            content=ft.Container(
                padding=ft.Padding.symmetric(horizontal=14, vertical=10),
                content=ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Column(
                            spacing=3,
                            expand=True,
                            controls=[
                                ft.Text(
                                    item["title"],
                                    size=16,
                                    weight=ft.FontWeight.W_600,
                                    color=AppColors.TEXT_PRIMARY,
                                ),
                                ft.Text(
                                    " ".join(subtitle_parts),
                                    size=13,
                                    color=AppColors.TEXT_SECONDARY,
                                ),
                            ],
                        ),
                        ft.Row(
                            spacing=0,
                            controls=[
                                ft.IconButton(
                                    icon=ft.Icons.EDIT_OUTLINED,
                                    icon_color=AppColors.PRIMARY,
                                    tooltip="Редактировать",
                                    on_click=lambda e, data=item: self._open_task_dialog(item=data),
                                ),
                                ft.IconButton(
                                    icon=ft.Icons.DELETE_OUTLINE,
                                    icon_color=AppColors.WARNING_DELETE,
                                    tooltip="Удалить",
                                    on_click=lambda e, item_id=item["id"]: self._confirm_delete(item_id),
                                ),
                            ],
                        ),
                    ],
                ),
            )
        )
    def _open_task_dialog(self, item: dict[str, Any] | None = None) -> None:
        is_edit = item is not None
        is_week = self.selected_period == AppStrings.PERIOD_WEEK
        is_goal = self.selected_period in (AppStrings.PERIOD_MONTH, AppStrings.PERIOD_YEAR)
        selected_goal_key: str | None = item.get("goal_key") if is_edit else None

        title_field = ft.TextField(
            label="Название цели (например, Чтение)" if is_goal else AppStrings.FIELD_TITLE_LABEL,
            value=item["title"] if is_edit else "",
            border_radius=10,
        )

        # --- ПОДСКАЗКИ ИЗ ЦЕЛЕЙ МЕСЯЦА/ГОДА (для вкладок "День" и "Неделя") ---
        suggestions_section = ft.Column(visible=False, spacing=6)
        if not is_goal:
            suggestions = self.repo.get_active_goal_suggestions()
            if suggestions:
                chips: list[ft.Control] = []

                def apply_suggestion(s_data: dict[str, Any]) -> None:
                    nonlocal selected_goal_key
                    title_field.value = s_data["title"]
                    selected_goal_key = s_data["goal_key"]
                    numeric_checkbox.value = True
                    numeric_fields_container.visible = True
                    unit_field.value = s_data.get("unit_name") or ""
                    dialog.update()

                for s in suggestions:
                    unit_hint = f" ({s['unit_name']})" if s.get("unit_name") else ""
                    chips.append(
                        ft.Container(
                            content=ft.Text(
                                f"{s['title']}{unit_hint}",
                                size=12,
                                weight=ft.FontWeight.W_600,
                                color=AppColors.PRIMARY,
                            ),
                            bgcolor=AppColors.PRIMARY_LIGHT,
                            padding=ft.Padding.symmetric(horizontal=10, vertical=6),
                            border_radius=16,
                            ink=True,
                            on_click=lambda e, data=s: apply_suggestion(data),
                        )
                    )

                suggestions_section.visible = True
                suggestions_section.controls = [
                    ft.Text(
                        "Подсказки из ваших целей (нажмите, чтобы связать):",
                        size=12,
                        weight=ft.FontWeight.W_500,
                        color=AppColors.TEXT_SECONDARY,
                    ),
                    ft.Row(controls=chips, wrap=True, spacing=6, run_spacing=6),
                ]

        # --- ВЫБОР ДНЕЙ НЕДЕЛИ (только для вкладки "Неделя") ---
        initial_days = list(range(1, 8))
        if is_edit and item.get("days_of_week"):
            initial_days = [int(x) for x in item["days_of_week"].split(",") if x.isdigit()]

        days_selector = WeekDaySelector(selected_days=initial_days, allow_multiple=True)
        days_section = ft.Column(
            visible=is_week,
            spacing=6,
            controls=[
                ft.Text(
                    "Дни недели для этой задачи:",
                    size=13,
                    weight=ft.FontWeight.W_500,
                    color=AppColors.TEXT_SECONDARY,
                ),
                days_selector,
            ],
        )

        # --- ПОЛЯ ЕДИНИЦЫ ИЗМЕРЕНИЯ И ЦЕЛИ ---
        unit_field = ft.TextField(
            label=AppStrings.FIELD_UNIT_LABEL,
            value=item["unit_name"] or "" if is_edit else "",
            border_radius=10,
        )

        target_str = ""
        if is_edit and item["target_value"] is not None:
            target_str = str(int(item["target_value"]) if item["target_value"].is_integer() else item["target_value"])

        target_field = ft.TextField(
            label="Целевое значение на период *" if is_goal else AppStrings.FIELD_TARGET_LABEL,
            value=target_str,
            keyboard_type=ft.KeyboardType.NUMBER,
            border_radius=10,
        )

        numeric_fields_container = ft.Column(
            controls=[unit_field, target_field],
            spacing=12,
            visible=True if is_goal else (bool(item["has_numeric_input"]) if is_edit else False),
        )

        def on_numeric_toggle(e: ft.ControlEvent) -> None:
            numeric_fields_container.visible = bool(e.control.value)
            dialog.update()

        numeric_checkbox = ft.Checkbox(
            value=True if is_goal else (bool(item["has_numeric_input"]) if is_edit else False),
            active_color=AppColors.PRIMARY,
            on_change=on_numeric_toggle,
        )

        # Текст чек-бокса в отдельной колонке с expand=True, чтобы не уезжал за край экрана
        checkbox_row = ft.Row(
            visible=not is_goal,
            spacing=6,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                numeric_checkbox,
                ft.GestureDetector(
                    expand=True,
                    on_tap=lambda e: _toggle_checkbox_by_text(),
                    content=ft.Text(
                        AppStrings.CHECKBOX_NUMERIC,
                        size=13,
                        color=AppColors.TEXT_PRIMARY,
                        max_lines=2,
                    ),
                ),
            ],
        )

        def _toggle_checkbox_by_text() -> None:
            numeric_checkbox.value = not bool(numeric_checkbox.value)
            numeric_fields_container.visible = bool(numeric_checkbox.value)
            dialog.update()
        def handle_save(e: ft.ControlEvent) -> None:
            title_val = (title_field.value or "").strip()
            if not title_val:
                title_field.error_text = "Введите название"
                dialog.update()
                return

            has_num = True if is_goal else bool(numeric_checkbox.value)
            unit_val = (unit_field.value or "").strip() if has_num else None
            target_val: float | None = None

            if has_num and target_field.value:
                try:
                    target_val = float(target_field.value.replace(",", ".").strip())
                except ValueError:
                    target_field.error_text = "Введите корректное число"
                    dialog.update()
                    return

            if is_goal and (target_val is None or target_val <= 0):
                target_field.error_text = "Укажите целевое значение больше 0"
                dialog.update()
                return

            days_str = days_selector.get_selected_days_str() if is_week else None
            final_goal_key = selected_goal_key or title_val.lower()

            if is_edit:
                self.repo.update_checklist_item(
                    item_id=item["id"],
                    title=title_val,
                    period_type=self.selected_period,
                    has_numeric_input=has_num,
                    unit_name=unit_val,
                    target_value=target_val,
                    days_of_week=days_str,
                    goal_key=final_goal_key,
                )
            else:
                self.repo.create_checklist_item(
                    title=title_val,
                    period_type=self.selected_period,
                    has_numeric_input=has_num,
                    unit_name=unit_val,
                    target_value=target_val,
                    days_of_week=days_str,
                    goal_key=final_goal_key,
                )

            self.app_page.pop_dialog()
            self.load_tasks()

        # Кнопки перенесены внутрь прокручиваемой области, чтобы не перекрывать поля при открытии клавиатуры
        buttons_row = ft.Row(
            alignment=ft.MainAxisAlignment.END,
            spacing=8,
            controls=[
                ft.TextButton(
                    content=ft.Text(AppStrings.BTN_CANCEL, color=AppColors.TEXT_SECONDARY),
                    on_click=lambda e: self.app_page.pop_dialog(),
                ),
                ft.FilledButton(
                    content=ft.Text(AppStrings.BTN_SAVE),
                    style=ft.ButtonStyle(bgcolor=AppColors.PRIMARY, color="#FFFFFF"),
                    on_click=handle_save,
                ),
            ],
        )

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(
                ("Редактировать цель" if is_goal else "Редактировать пункт")
                if is_edit
                else ("Новая цель" if is_goal else AppStrings.ADD_TASK_TITLE),
                size=18,
                weight=ft.FontWeight.BOLD,
                color=AppColors.TEXT_PRIMARY,
            ),
            content=ft.Container(
                width=330,
                content=ft.Column(
                    tight=True,
                    scroll=ft.ScrollMode.AUTO,
                    spacing=12,
                    controls=[
                        suggestions_section,
                        title_field,
                        days_section,
                        checkbox_row,
                        numeric_fields_container,
                        ft.Container(content=buttons_row, padding=ft.Padding.only(top=6)),
                    ],
                ),
            ),
            bgcolor=AppColors.CARD_BG,
            shape=ft.RoundedRectangleBorder(radius=16),
        )

        self.app_page.show_dialog(dialog)

    def _confirm_delete(self, item_id: int) -> None:
        """Запрашивает подтверждение перед удалением задачи (в цветах индиго, без красного)."""
        def do_delete(e: ft.ControlEvent) -> None:
            self.repo.delete_checklist_item(item_id)
            self.app_page.pop_dialog()
            self.load_tasks()

        confirm_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(
                "Удалить пункт?",
                size=18,
                weight=ft.FontWeight.BOLD,
                color=AppColors.TEXT_PRIMARY,
            ),
            content=ft.Text(
                "Пункт и вся история его выполнения будут удалены.",
                size=14,
                color=AppColors.TEXT_SECONDARY,
            ),
            actions=[
                ft.TextButton(
                    content=ft.Text(AppStrings.BTN_CANCEL, color=AppColors.TEXT_SECONDARY),
                    on_click=lambda e: self.app_page.pop_dialog(),
                ),
                ft.FilledButton(
                    content=ft.Text("Удалить"),
                    style=ft.ButtonStyle(bgcolor=AppColors.WARNING_DELETE, color="#FFFFFF"),
                    on_click=do_delete,
                ),
            ],
            bgcolor=AppColors.CARD_BG,
            shape=ft.RoundedRectangleBorder(radius=16),
        )

        self.app_page.show_dialog(confirm_dialog)
