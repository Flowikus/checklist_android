from typing import Any
import flet as ft
from core.constants.colors import AppColors
from core.constants.strings import AppStrings
from core.database.repository import ChecklistRepository


class SettingsView(ft.Container):
    def __init__(self, page: ft.Page, repo: ChecklistRepository, initial_period: str = AppStrings.PERIOD_WEEK):
        super().__init__(expand=True, padding=ft.Padding.only(left=16, right=16, top=12))
        self.app_page = page
        self.repo = repo
        self.selected_period = initial_period

        # Переключатель периодов (Неделя / Месяц / Год)
        self.period_selector = ft.SegmentedButton(
            selected=[self.selected_period],
            allow_multiple_selection=False,
            on_change=self._on_period_change,
            segments=[
                ft.Segment(value=AppStrings.PERIOD_WEEK, label=ft.Text(AppStrings.TAB_WEEK)),
                ft.Segment(value=AppStrings.PERIOD_MONTH, label=ft.Text(AppStrings.TAB_MONTH)),
                ft.Segment(value=AppStrings.PERIOD_YEAR, label=ft.Text(AppStrings.TAB_YEAR)),
            ],
        )

        # Контейнер со списком задач
        self.tasks_column = ft.Column(
            spacing=10,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )

        # Кнопка добавления новой задачи
        add_button = ft.FilledButton(
            content=ft.Row(
                [ft.Icon(ft.Icons.ADD, size=20), ft.Text("Добавить пункт", weight=ft.FontWeight.W_600)],
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

        self.load_tasks(should_update=False)


    def set_period(self, period_type: str) -> None:
        """Позволяет программно переключить вкладку (например, из диалога ротации)."""
        self.selected_period = period_type
        self.period_selector.selected = [period_type]
        self.load_tasks()

    def _on_period_change(self, e: ft.ControlEvent) -> None:
        if e.control.selected:
            self.selected_period = next(iter(e.control.selected))
            self.load_tasks()

    def load_tasks(self, should_update: bool = True) -> None:
        """Загружает список шаблонов задач для выбранного периода из SQLite."""
        self.tasks_column.controls.clear()
        items = self.repo.get_all_items(period_type=self.selected_period, only_active=True)

        if not items:
            self.tasks_column.controls.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Icon(ft.Icons.CHECKLIST_RTL, size=48, color=AppColors.DIVIDER),
                            ft.Text(
                                "Список для этого периода пока пуст",
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


    def _build_task_card(self, item: dict[str, Any]) -> ft.Card:
        """Формирует карточку настройки задачи с кнопками редактирования и удаления."""
        subtitle_parts = []
        if item["has_numeric_input"]:
            unit = item["unit_name"] or "ед."
            if item["target_value"]:
                target_fmt = int(item["target_value"]) if item["target_value"].is_integer() else item["target_value"]
                subtitle_parts.append(f"Числовой ввод • Цель: {target_fmt} {unit}")
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
        """Открывает диалог создания новой или редактирования существующей задачи."""
        is_edit = item is not None

        title_field = ft.TextField(
            label=AppStrings.FIELD_TITLE_LABEL,
            value=item["title"] if is_edit else "",
            border_radius=10,
            autofocus=True,
        )

        unit_field = ft.TextField(
            label=AppStrings.FIELD_UNIT_LABEL,
            value=item["unit_name"] or "" if is_edit else "",
            border_radius=10,
        )

        target_str = ""
        if is_edit and item["target_value"] is not None:
            target_str = str(int(item["target_value"]) if item["target_value"].is_integer() else item["target_value"])

        target_field = ft.TextField(
            label=AppStrings.FIELD_TARGET_LABEL,
            value=target_str,
            keyboard_type=ft.KeyboardType.NUMBER,
            border_radius=10,
        )

        numeric_fields_container = ft.Column(
            controls=[unit_field, target_field],
            spacing=12,
            visible=bool(item["has_numeric_input"]) if is_edit else False,
        )

        def on_numeric_toggle(e: ft.ControlEvent) -> None:
            numeric_fields_container.visible = e.control.value
            dialog.update()

        numeric_checkbox = ft.Checkbox(
            label=AppStrings.CHECKBOX_NUMERIC,
            value=bool(item["has_numeric_input"]) if is_edit else False,
            active_color=AppColors.PRIMARY,
            on_change=on_numeric_toggle,
        )

        def handle_save(e: ft.ControlEvent) -> None:
            title_val = (title_field.value or "").strip()
            if not title_val:
                title_field.error_text = "Введите название задачи"
                dialog.update()
                return

            has_num = bool(numeric_checkbox.value)
            unit_val = (unit_field.value or "").strip() if has_num else None
            target_val: float | None = None

            if has_num and target_field.value:
                try:
                    target_val = float(target_field.value.replace(",", "."))
                except ValueError:
                    target_field.error_text = "Введите корректное число"
                    dialog.update()
                    return

            if is_edit:
                self.repo.update_checklist_item(
                    item_id=item["id"],
                    title=title_val,
                    period_type=self.selected_period,
                    has_numeric_input=has_num,
                    unit_name=unit_val,
                    target_value=target_val,
                )
            else:
                self.repo.create_checklist_item(
                    title=title_val,
                    period_type=self.selected_period,
                    has_numeric_input=has_num,
                    unit_name=unit_val,
                    target_value=target_val,
                )

            self.app_page.pop_dialog()
            self.load_tasks()

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(
                "Редактировать пункт" if is_edit else AppStrings.ADD_TASK_TITLE,
                size=18,
                weight=ft.FontWeight.BOLD,
                color=AppColors.TEXT_PRIMARY,
            ),
            content=ft.Container(
                width=320,
                content=ft.Column(
                    tight=True,
                    spacing=12,
                    controls=[
                        title_field,
                        numeric_checkbox,
                        numeric_fields_container,
                    ],
                ),
            ),
            actions=[
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
