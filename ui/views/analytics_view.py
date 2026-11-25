import flet as ft
from core.constants.colors import AppColors
from core.constants.strings import AppStrings
from core.database.repository import ChecklistRepository
from core.utils.period_helper import PeriodHelper
from ui.components.analytics_panel import AnalyticsPanel


class AnalyticsView(ft.Container):
    def __init__(self, repo: ChecklistRepository):
        super().__init__(expand=True, padding=ft.Padding.only(left=16, right=16, top=12))
        self.repo = repo

        self.day_panel = AnalyticsPanel(
            repo=self.repo,
            period_type=AppStrings.PERIOD_DAY,
            period_identifier=PeriodHelper.get_current_period_id(AppStrings.PERIOD_DAY),
        )
        # Сразу раскрываем дневную аналитику по умолчанию
        self.day_panel.is_expanded = True
        self.day_panel.details_container.visible = True
        self.day_panel.expand_icon.icon = ft.Icons.EXPAND_LESS

        self.month_panel = AnalyticsPanel(
            repo=self.repo,
            period_type=AppStrings.PERIOD_MONTH,
            period_identifier=PeriodHelper.get_current_period_id(AppStrings.PERIOD_MONTH),
        )

        self.year_panel = AnalyticsPanel(
            repo=self.repo,
            period_type=AppStrings.PERIOD_YEAR,
            period_identifier=PeriodHelper.get_current_period_id(AppStrings.PERIOD_YEAR),
        )

        self.content = ft.Column(
            spacing=12,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
            controls=[
                ft.Text(
                    "Аналитика и прогресс",
                    size=22,
                    weight=ft.FontWeight.BOLD,
                    color=AppColors.TEXT_PRIMARY,
                ),
                ft.Text("Ежедневные задачи", size=14, weight=ft.FontWeight.W_600, color=AppColors.TEXT_SECONDARY),
                self.day_panel,
                ft.Text("Цели на месяц", size=14, weight=ft.FontWeight.W_600, color=AppColors.TEXT_SECONDARY),
                self.month_panel,
                ft.Text("Цели на год", size=14, weight=ft.FontWeight.W_600, color=AppColors.TEXT_SECONDARY),
                self.year_panel,
                ft.Container(height=12),
            ],
        )

        self.refresh_all(should_update=False)

    def refresh_all(self, should_update: bool = True) -> None:
        self.day_panel.refresh_charts(
            PeriodHelper.get_current_period_id(AppStrings.PERIOD_DAY),
            should_update=should_update,
        )
        self.month_panel.refresh_charts(
            PeriodHelper.get_current_period_id(AppStrings.PERIOD_MONTH),
            should_update=should_update,
        )
        self.year_panel.refresh_charts(
            PeriodHelper.get_current_period_id(AppStrings.PERIOD_YEAR),
            should_update=should_update,
        )
