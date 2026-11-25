import flet as ft
from core.constants.colors import AppColors
from core.constants.strings import AppStrings
from core.database.repository import ChecklistRepository
from core.utils.period_helper import PeriodHelper
from ui.components.checklist_card import ChecklistCard
from ui.components.week_day_selector import WeekDaySelector


class TodayView(ft.Container):
    def __init__(self, page: ft.Page, repo: ChecklistRepository):
        super().__init__(expand=True, padding=ft.Padding.only(left=16, right=16, top=12))
        self.app_page = page
        self.repo = repo
        self.selected_weekday: int = PeriodHelper.get_current_day_of_week()
        self.selected_date = PeriodHelper.get_date_for_weekday_in_current_week(self.selected_weekday)

        self.month_expanded = False
        self.year_expanded = False

        # Заголовок даты ("Сегодня, 25 ноября (Ср)")
        self.header_title = ft.Text(
            PeriodHelper.get_period_display_name(AppStrings.PERIOD_DAY, self.selected_date),
            size=19,
            weight=ft.FontWeight.BOLD,
            color=AppColors.TEXT_PRIMARY,
            expand=True,
        )

        # Бейдж баланса монет
        self.coins_text = ft.Text(
            "0",
            size=13,
            weight=ft.FontWeight.BOLD,
            color=AppColors.PRIMARY,
        )
        self.coins_badge = ft.Container(
            bgcolor=AppColors.PRIMARY_LIGHT,
            padding=ft.Padding.symmetric(horizontal=10, vertical=5),
            border_radius=16,
            content=ft.Row(
                spacing=4,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Icon(ft.Icons.MONETIZATION_ON_OUTLINED, size=16, color=AppColors.PRIMARY),
                    self.coins_text,
                ],
            ),
        )

        # Бейдж прогресса дня ("2 из 5")
        self.progress_badge = ft.Container(
            bgcolor=AppColors.SURFACE_VARIANT,
            padding=ft.Padding.symmetric(horizontal=10, vertical=5),
            border_radius=16,
            content=ft.Text(
                "0 из 0",
                size=13,
                weight=ft.FontWeight.W_600,
                color=AppColors.TEXT_PRIMARY,
            ),
        )

        self.progress_bar = ft.ProgressBar(
            value=0.0,
            color=AppColors.SUCCESS,
            bgcolor=AppColors.DIVIDER,
            height=6,
            border_radius=3,
        )

        self.week_day_selector = WeekDaySelector(
            selected_days=[self.selected_weekday],
            allow_multiple=False,
            on_change=self._on_weekday_changed,
        )

        self.daily_tasks_column = ft.Column(spacing=8)

        # --- СВОРАЧИВАЕМЫЙ БЛОК: ЦЕЛИ МЕСЯЦА ---
        self.month_expand_icon = ft.Icon(ft.Icons.EXPAND_MORE, color=AppColors.TEXT_SECONDARY)
        self.month_summary_text = ft.Text(
            "Цели месяца • 0 из 0",
            size=15,
            weight=ft.FontWeight.W_600,
            color=AppColors.TEXT_PRIMARY,
        )
        self.month_goals_list = ft.Column(spacing=8, visible=self.month_expanded)
        self.month_accordion = self._build_accordion_card(
            title_control=self.month_summary_text,
            icon_control=self.month_expand_icon,
            body_control=self.month_goals_list,
            on_toggle=self._toggle_month_goals,
        )

        # --- СВОРАЧИВАЕМЫЙ БЛОК: ЦЕЛИ ГОДА ---
        self.year_expand_icon = ft.Icon(ft.Icons.EXPAND_MORE, color=AppColors.TEXT_SECONDARY)
        self.year_summary_text = ft.Text(
            "Цели года • 0 из 0",
            size=15,
            weight=ft.FontWeight.W_600,
            color=AppColors.TEXT_PRIMARY,
        )
        self.year_goals_list = ft.Column(spacing=8, visible=self.year_expanded)
        self.year_accordion = self._build_accordion_card(
            title_control=self.year_summary_text,
            icon_control=self.year_expand_icon,
            body_control=self.year_goals_list,
            on_toggle=self._toggle_year_goals,
        )

        scroll_body = ft.Column(
            spacing=12,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
            controls=[
                ft.Text(
                    "Задачи на день",
                    size=14,
                    weight=ft.FontWeight.W_600,
                    color=AppColors.TEXT_SECONDARY,
                ),
                self.daily_tasks_column,
                ft.Divider(height=8, color=AppColors.DIVIDER),
                self.month_accordion,
                self.year_accordion,
                ft.Container(height=12),
            ],
        )

        self.content = ft.Column(
            spacing=10,
            expand=True,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=6,
                    controls=[self.header_title, self.coins_badge, self.progress_badge],
                ),
                self.progress_bar,
                self.week_day_selector,
                scroll_body,
            ],
        )

        self.refresh_data(should_update=False)
    @staticmethod
    def _build_accordion_card(
        title_control: ft.Text,
        icon_control: ft.Icon,
        body_control: ft.Control,
        on_toggle,
    ) -> ft.Card:
        header = ft.GestureDetector(
            on_tap=on_toggle,
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Row(
                        spacing=8,
                        controls=[
                            ft.Icon(ft.Icons.FLAG, size=18, color=AppColors.PRIMARY),
                            title_control,
                        ],
                    ),
                    icon_control,
                ],
            ),
        )
        return ft.Card(
            content=ft.Container(
                padding=ft.Padding.symmetric(horizontal=14, vertical=10),
                content=ft.Column(
                    spacing=8,
                    controls=[header, body_control],
                ),
            )
        )

    def _toggle_month_goals(self, e: ft.ControlEvent) -> None:
        self.month_expanded = not self.month_expanded
        self.month_goals_list.visible = self.month_expanded
        self.month_expand_icon.icon = ft.Icons.EXPAND_LESS if self.month_expanded else ft.Icons.EXPAND_MORE
        try:
            self.month_accordion.update()
        except RuntimeError:
            pass

    def _toggle_year_goals(self, e: ft.ControlEvent) -> None:
        self.year_expanded = not self.year_expanded
        self.year_goals_list.visible = self.year_expanded
        self.year_expand_icon.icon = ft.Icons.EXPAND_LESS if self.year_expanded else ft.Icons.EXPAND_MORE
        try:
            self.year_accordion.update()
        except RuntimeError:
            pass

    def _on_weekday_changed(self, selected: list[int]) -> None:
        if selected:
            self.selected_weekday = selected[0]
            self.selected_date = PeriodHelper.get_date_for_weekday_in_current_week(self.selected_weekday)
            self.refresh_data(should_update=True)

    def _update_coins_display(self, should_update: bool = True) -> None:
        state = self.repo.get_plant_state()
        self.coins_text.value = str(state["coins"])
        if should_update:
            try:
                self.coins_badge.update()
            except RuntimeError:
                pass

    def _show_reward_toast(self, coins_delta: int, bonus_awarded: int = 0) -> None:
        if coins_delta <= 0:
            return
        if bonus_awarded > 0:
            msg = f"День закрыт на 100%! +{coins_delta} монет (включая бонус +{bonus_awarded})!"
        else:
            msg = f"+{coins_delta} монет за выполнение!"
        self.app_page.show_dialog(
            ft.SnackBar(
                content=ft.Text(msg, color="#FFFFFF"),
                bgcolor=AppColors.SUCCESS,
                duration=1600,
            )
        )

    def refresh_data(self, should_update: bool = True) -> None:
        self.selected_date = PeriodHelper.get_date_for_weekday_in_current_week(self.selected_weekday)
        date_str = PeriodHelper.get_current_period_id(AppStrings.PERIOD_DAY, self.selected_date)
        self.header_title.value = PeriodHelper.get_period_display_name(AppStrings.PERIOD_DAY, self.selected_date)
        self._update_coins_display(should_update=False)

        tasks = self.repo.get_tasks_for_date(date_str=date_str, day_of_week=self.selected_weekday)
        self.daily_tasks_column.controls.clear()

        if not tasks:
            self.daily_tasks_column.controls.append(
                ft.Container(
                    alignment=ft.Alignment.CENTER,
                    padding=ft.Padding.symmetric(vertical=24),
                    content=ft.Text(
                        "На этот день задач пока нет. Добавьте их в «Настройках».",
                        size=14,
                        color=AppColors.TEXT_SECONDARY,
                        text_align=ft.TextAlign.CENTER,
                    ),
                )
            )
        else:
            for t in tasks:
                self.daily_tasks_column.controls.append(
                    ChecklistCard(
                        task_data=t,
                        on_progress_changed=self._on_daily_task_changed,
                    )
                )

        total_tasks = len(tasks)
        done_tasks = sum(1 for t in tasks if t["is_completed"] == 1)
        self.progress_badge.content.value = f"{done_tasks} из {total_tasks}"
        self.progress_bar.value = (done_tasks / total_tasks) if total_tasks > 0 else 0.0

        self._refresh_goals_blocks(should_update=False)

        if should_update:
            try:
                self.update()
            except RuntimeError:
                pass

    def _refresh_goals_blocks(self, should_update: bool = True) -> None:
        month_id = PeriodHelper.get_current_period_id(AppStrings.PERIOD_MONTH, self.selected_date)
        year_id = PeriodHelper.get_current_period_id(AppStrings.PERIOD_YEAR, self.selected_date)

        month_goals = self.repo.get_goals_with_progress(AppStrings.PERIOD_MONTH, month_id)
        year_goals = self.repo.get_goals_with_progress(AppStrings.PERIOD_YEAR, year_id)

        m_done = sum(1 for g in month_goals if g["is_completed"] == 1)
        self.month_summary_text.value = f"Цели месяца • {m_done} из {len(month_goals)}"
        self.month_goals_list.controls.clear()
        if not month_goals:
            self.month_goals_list.controls.append(
                ft.Text("Цели на месяц не заданы", size=13, color=AppColors.TEXT_SECONDARY)
            )
        else:
            for g in month_goals:
                self.month_goals_list.controls.append(
                    ChecklistCard(
                        task_data=g,
                        on_progress_changed=lambda gid, done, val, pid=month_id: self._on_boolean_goal_changed(
                            gid, pid, done
                        ),
                    )
                )

        y_done = sum(1 for g in year_goals if g["is_completed"] == 1)
        self.year_summary_text.value = f"Цели года • {y_done} из {len(year_goals)}"
        self.year_goals_list.controls.clear()
        if not year_goals:
            self.year_goals_list.controls.append(
                ft.Text("Цели на год не заданы", size=13, color=AppColors.TEXT_SECONDARY)
            )
        else:
            for g in year_goals:
                self.year_goals_list.controls.append(
                    ChecklistCard(
                        task_data=g,
                        on_progress_changed=lambda gid, done, val, pid=year_id: self._on_boolean_goal_changed(
                            gid, pid, done
                        ),
                    )
                )

        if should_update:
            try:
                self.month_accordion.update()
                self.year_accordion.update()
            except RuntimeError:
                pass

    def _on_daily_task_changed(self, task_id: int, is_completed: bool, numeric_value: float) -> None:
        date_str = PeriodHelper.get_current_period_id(AppStrings.PERIOD_DAY, self.selected_date)
        reward_info = self.repo.save_daily_task_progress(
            checklist_id=task_id,
            date_str=date_str,
            is_completed=is_completed,
            numeric_value=numeric_value,
        )

        tasks = self.repo.get_tasks_for_date(date_str=date_str, day_of_week=self.selected_weekday)
        total = len(tasks)
        done = sum(1 for t in tasks if t["is_completed"] == 1)
        self.progress_badge.content.value = f"{done} из {total}"
        self.progress_bar.value = (done / total) if total > 0 else 0.0

        self._update_coins_display(should_update=True)
        self._refresh_goals_blocks(should_update=True)
        self._show_reward_toast(reward_info["coins_delta"], reward_info["bonus_awarded"])

        try:
            self.progress_badge.update()
            self.progress_bar.update()
        except RuntimeError:
            pass

    def _on_boolean_goal_changed(self, goal_id: int, period_identifier: str, is_completed: bool) -> None:
        coins_delta = self.repo.save_boolean_goal_progress(
            goal_id=goal_id,
            period_identifier=period_identifier,
            is_completed=is_completed,
        )
        self._update_coins_display(should_update=True)
        self._refresh_goals_blocks(should_update=True)
        self._show_reward_toast(coins_delta)
