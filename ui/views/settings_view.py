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

        self.period_selector = ft.Dropdown(
            value=self.selected_period,
            label="Раздел задач / целей",
            border_radius=12,
            bgcolor=AppColors.CARD_BG,
            border_color=AppColors.DIVIDER,
            focused_border_color=AppColors.PRIMARY,
            content_padding=ft.Padding.symmetric(horizontal=14, vertical=10),
            expand=True,
            on_select=self._on_period_change,
            options=[
                ft.DropdownOption(key=AppStrings.PERIOD_DAY, text="Ежедневные задачи (Каждый день)"),
                ft.DropdownOption(key=AppStrings.PERIOD_WEEK, text="Задачи по дням недели (Пн–Вс)"),
                ft.DropdownOption(key=AppStrings.PERIOD_MONTH, text="Цели на месяц"),
                ft.DropdownOption(key=AppStrings.PERIOD_YEAR, text="Цели на год"),
            ],
        )


        self.tasks_column = ft.Column(
            spacing=10,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )

        self.add_button_label = ft.Text("Добавить задачу", weight=ft.FontWeight.W_600)

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
                ft.Row(controls=[self.period_selector]),
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
        self.add_button_label.value = "Добавить цель" if is_goal else "Добавить задачу"

    def set_period(self, period_type: str) -> None:
        self.selected_period = period_type
        self.period_selector.value = period_type
        self._update_add_button_label()
        self.load_tasks()

    def _on_period_change(self, e: ft.ControlEvent) -> None:
        if e.control.value:
            self.selected_period = e.control.value
            self._update_add_button_label()
            self.load_tasks()

    def load_tasks(self, should_update: bool = True) -> None:
        self.tasks_column.controls.clear()
        items = self.repo.get_all_items(period_type=self.selected_period, only_active=True)
        is_goal = self.selected_period in (AppStrings.PERIOD_MONTH, AppStrings.PERIOD_YEAR)

        all_goals_map = {g["id"]: g["title"] for g in self.repo.get_numeric_goals()}

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
                                "Целей для этого периода пока нет" if is_goal else "Задач для этого периода пока нет",
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
                self.tasks_column.controls.append(self._build_task_card(item, all_goals_map))

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

    def _build_task_card(self, item: dict[str, Any], goals_map: dict[int, str]) -> ft.Card:
        is_goal = item["period_type"] in (AppStrings.PERIOD_MONTH, AppStrings.PERIOD_YEAR)
        g_type = item.get("goal_type") or "numeric"
        subtitle_parts = []

        if item["period_type"] == AppStrings.PERIOD_WEEK:
            days_text = self._format_days_badge(item.get("days_of_week"))
            subtitle_parts.append(f"[{days_text}]")

        if is_goal:
            if g_type == "boolean":
                subtitle_parts.append("Разовая цель (чек-бокс)")
            else:
                unit = item["unit_name"] or "ед."
                target = item["target_value"] or 0
                target_fmt = int(target) if float(target).is_integer() else target
                subtitle_parts.append(f"Накопительная цель: {target_fmt} {unit}")
        else:
            if item["has_numeric_input"]:
                unit = item["unit_name"] or "ед."
                subtitle_parts.append(f"Числовой ввод ({unit})")
            else:
                subtitle_parts.append("Чек-бокс")

            linked_raw = item.get("linked_goal_ids")
            if linked_raw:
                linked_names = [
                    goals_map[int(gid)]
                    for gid in linked_raw.split(",")
                    if gid.strip().isdigit() and int(gid.strip()) in goals_map
                ]
                if linked_names:
                    subtitle_parts.append(f"→ {', '.join(linked_names)}")

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

        title_field = ft.TextField(
            label="Название цели (например, Прочитать книгу)" if is_goal else AppStrings.FIELD_TITLE_LABEL,
            value=item["title"] if is_edit else "",
            border_radius=10,
        )

        # --- 1. ПЕРЕКЛЮЧАТЕЛЬ ТИПА ЦЕЛИ (только для "Месяц" и "Год") ---
        current_goal_type = (item.get("goal_type") or "numeric") if is_edit else "numeric"

        goal_type_selector = ft.SegmentedButton(
            selected=[current_goal_type],
            allow_multiple_selection=False,
            segments=[
                ft.Segment(value="numeric", label=ft.Text("С цифрами")),
                ft.Segment(value="boolean", label=ft.Text("Чек-бокс")),
            ],
        )

        goal_type_section = ft.Column(
            visible=is_goal,
            spacing=6,
            controls=[
                ft.Text(
                    "Тип цели:",
                    size=13,
                    weight=ft.FontWeight.W_500,
                    color=AppColors.TEXT_SECONDARY,
                ),
                goal_type_selector,
            ],
        )

        # --- 2. ПРИВЯЗКА К НАКОПИТЕЛЬНЫМ ЦЕЛЯМ (только для "Каждый день" и "По дням") ---
        selected_goal_ids: set[int] = set()
        if is_edit and item.get("linked_goal_ids"):
            for x in item["linked_goal_ids"].split(","):
                if x.strip().isdigit():
                    selected_goal_ids.add(int(x.strip()))

        goal_link_section = ft.Column(visible=False, spacing=6)
        goal_chips_map: dict[int, ft.Container] = {}

        if not is_goal:
            available_goals = self.repo.get_numeric_goals()
            if available_goals:
                chips_list: list[ft.Control] = []

                def toggle_goal_link(goal_obj: dict[str, Any]) -> None:
                    gid = goal_obj["id"]
                    if gid in selected_goal_ids:
                        selected_goal_ids.remove(gid)
                    else:
                        selected_goal_ids.add(gid)
                        # Автоматически включаем числовой ввод и подставляем единицу измерения
                        numeric_checkbox.value = True
                        numeric_fields_container.visible = True
                        if not (unit_field.value or "").strip() and goal_obj.get("unit_name"):
                            unit_field.value = goal_obj["unit_name"]

                    # Обновляем внешний вид чипов
                    for chip_id, chip_ctrl in goal_chips_map.items():
                        active = chip_id in selected_goal_ids
                        chip_ctrl.bgcolor = AppColors.PRIMARY if active else AppColors.PRIMARY_LIGHT
                        chip_ctrl.content.color = "#FFFFFF" if active else AppColors.PRIMARY
                    dialog.update()

                for g in available_goals:
                    gid = g["id"]
                    active = gid in selected_goal_ids
                    period_tag = "Месяц" if g["period_type"] == "month" else "Год"
                    unit_tag = f", {g['unit_name']}" if g.get("unit_name") else ""
                    chip = ft.Container(
                        content=ft.Text(
                            f"{g['title']} ({period_tag}{unit_tag})",
                            size=12,
                            weight=ft.FontWeight.W_600,
                            color="#FFFFFF" if active else AppColors.PRIMARY,
                        ),
                        bgcolor=AppColors.PRIMARY if active else AppColors.PRIMARY_LIGHT,
                        padding=ft.Padding.symmetric(horizontal=10, vertical=6),
                        border_radius=16,
                        ink=True,
                        on_click=lambda e, obj=g: toggle_goal_link(obj),
                    )
                    goal_chips_map[gid] = chip
                    chips_list.append(chip)

                goal_link_section.visible = True
                goal_link_section.controls = [
                    ft.Text(
                        "Суммировать результат в цели (можно выбрать несколько):",
                        size=12,
                        weight=ft.FontWeight.W_500,
                        color=AppColors.TEXT_SECONDARY,
                    ),
                    ft.Row(controls=chips_list, wrap=True, spacing=6, run_spacing=6),
                ]

        # --- 3. ВЫБОР ДНЕЙ НЕДЕЛИ (только для "По дням") ---
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
        # --- 4. ПОЛЯ ЕДИНИЦЫ ИЗМЕРЕНИЯ И ЦЕЛИ ---
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

        initial_numeric_visible = (
            (current_goal_type == "numeric")
            if is_goal
            else (bool(item["has_numeric_input"]) if is_edit else False)
        )

        numeric_fields_container = ft.Column(
            controls=[unit_field, target_field],
            spacing=12,
            visible=initial_numeric_visible,
        )

        def on_goal_type_change(e: ft.ControlEvent) -> None:
            if e.control.selected:
                chosen = next(iter(e.control.selected))
                numeric_fields_container.visible = (chosen == "numeric")
                dialog.update()

        goal_type_selector.on_change = on_goal_type_change

        def on_numeric_toggle(e: ft.ControlEvent) -> None:
            numeric_fields_container.visible = bool(e.control.value)
            dialog.update()

        numeric_checkbox = ft.Checkbox(
            value=initial_numeric_visible,
            active_color=AppColors.PRIMARY,
            on_change=on_numeric_toggle,
        )

        def _toggle_checkbox_by_text() -> None:
            numeric_checkbox.value = not bool(numeric_checkbox.value)
            numeric_fields_container.visible = bool(numeric_checkbox.value)
            dialog.update()

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

        def handle_save(e: ft.ControlEvent) -> None:
            title_val = (title_field.value or "").strip()
            if not title_val:
                title_field.error_text = "Введите название"
                dialog.update()
                return

            chosen_goal_type = (
                next(iter(goal_type_selector.selected))
                if (is_goal and goal_type_selector.selected)
                else "numeric"
            )

            has_num = (chosen_goal_type == "numeric") if is_goal else bool(numeric_checkbox.value)
            unit_val = (unit_field.value or "").strip() if has_num else None
            target_val: float | None = None

            if has_num and target_field.value:
                try:
                    target_val = float(target_field.value.replace(",", ".").strip())
                except ValueError:
                    target_field.error_text = "Введите корректное число"
                    dialog.update()
                    return

            if is_goal and chosen_goal_type == "numeric" and (target_val is None or target_val <= 0):
                target_field.error_text = "Укажите целевое значение больше 0"
                dialog.update()
                return

            days_str = days_selector.get_selected_days_str() if is_week else None
            linked_str = (
                ",".join(str(gid) for gid in sorted(selected_goal_ids))
                if (not is_goal and selected_goal_ids)
                else None
            )

            if is_edit:
                self.repo.update_checklist_item(
                    item_id=item["id"],
                    title=title_val,
                    period_type=self.selected_period,
                    has_numeric_input=has_num,
                    unit_name=unit_val,
                    target_value=target_val,
                    days_of_week=days_str,
                    goal_type=chosen_goal_type,
                    linked_goal_ids=linked_str,
                )
            else:
                self.repo.create_checklist_item(
                    title=title_val,
                    period_type=self.selected_period,
                    has_numeric_input=has_num,
                    unit_name=unit_val,
                    target_value=target_val,
                    days_of_week=days_str,
                    goal_type=chosen_goal_type,
                    linked_goal_ids=linked_str,
                )

            self.app_page.pop_dialog()
            self.load_tasks()

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
                ("Редактировать цель" if is_goal else "Редактировать задачу")
                if is_edit
                else ("Новая цель" if is_goal else "Новая задача"),
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
                        title_field,
                        goal_type_section,
                        days_section,
                        goal_link_section,
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
