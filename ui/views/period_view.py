import flet as ft
from core.constants.colors import AppColors
from core.database.repository import ChecklistRepository
from core.utils.period_helper import PeriodHelper
from ui.components.checklist_card import ChecklistCard
from ui.components.analytics_panel import AnalyticsPanel


class PeriodView(ft.Container):
    def __init__(self, repo: ChecklistRepository, period_type: str):
        super().__init__(expand=True, padding=ft.Padding.only(left=16, right=16, top=12))
        self.repo = repo
        self.period_type = period_type
        self.current_period_id = PeriodHelper.get_current_period_id(period_type)

        # Заголовок периода (например, "Неделя №48 (2026)")
        self.header_title = ft.Text(
            PeriodHelper.get_period_display_name(period_type),
            size=22,
            weight=ft.FontWeight.BOLD,
            color=AppColors.TEXT_PRIMARY,
        )

        # Бейдж общего прогресса ("Выполнено: 2 из 5")
        self.progress_badge = ft.Container(
            bgcolor=AppColors.PRIMARY_LIGHT,
            padding=ft.Padding.symmetric(horizontal=12, vertical=6),
            border_radius=20,
            content=ft.Text(
                "0 из 0",
                size=13,
                weight=ft.FontWeight.W_600,
                color=AppColors.PRIMARY,
            ),
        )

        # Полоса прогресса
        self.progress_bar = ft.ProgressBar(
            value=0.0,
            color=AppColors.SUCCESS,
            bgcolor=AppColors.DIVIDER,
            height=6,
            border_radius=3,
        )

        # Контейнер для будущего блока графиков (Этап 7)
        self.analytics_panel = AnalyticsPanel(
            repo=self.repo,
            period_type=self.period_type,
            period_identifier=self.current_period_id,
        )


        # Список карточек задач
        self.tasks_column = ft.Column(
            spacing=10,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )

        self.content = ft.Column(
            spacing=12,
            expand=True,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[self.header_title, self.progress_badge],
                ),
                self.progress_bar,
                self.analytics_panel,
                self.tasks_column,
            ],
        )

        self.refresh_data(should_update=False)

    def refresh_data(self, should_update: bool = True) -> None:
        """Перезагружает задачи и пересчитывает прогресс периода."""
        self.current_period_id = PeriodHelper.get_current_period_id(self.period_type)
        self.header_title.value = PeriodHelper.get_period_display_name(self.period_type)
        self.analytics_panel.refresh_charts(self.current_period_id, should_update=should_update)

        tasks = self.repo.get_period_tasks_with_progress(
            period_type=self.period_type,
            period_identifier=self.current_period_id,
        )

        self.tasks_column.controls.clear()

        if not tasks:
            self.tasks_column.controls.append(
                ft.Container(
                    alignment=ft.Alignment.CENTER,
                    padding=ft.Padding.only(top=50),
                    content=ft.Column(
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=8,
                        controls=[
                            ft.Icon(ft.Icons.TASK_ALT, size=48, color=AppColors.DIVIDER),
                            ft.Text(
                                "Задач на этот период пока нет",
                                size=15,
                                color=AppColors.TEXT_SECONDARY,
                            ),
                            ft.Text(
                                "Добавьте их во вкладке «Настройки»",
                                size=13,
                                color=AppColors.TEXT_SECONDARY,
                            ),
                        ],
                    ),
                )
            )
        else:
            for task in tasks:
                card = ChecklistCard(
                    task_data=task,
                    on_progress_changed=self._on_task_progress_changed,
                )
                self.tasks_column.controls.append(card)

        self._update_summary_header(should_update=False)

        if should_update:
            try:
                self.update()
            except RuntimeError:
                pass

    def _on_task_progress_changed(self, task_id: int, is_completed: bool, numeric_value: float) -> None:
        """Сохраняет изменение в БД и обновляет верхний индикатор прогресса."""
        self.repo.save_task_progress(
            checklist_id=task_id,
            period_identifier=self.current_period_id,
            is_completed=is_completed,
            numeric_value=numeric_value,
        )
        self._update_summary_header(should_update=True)

    def _update_summary_header(self, should_update: bool = True) -> None:
        stats = self.repo.get_period_summary_stats(
            period_type=self.period_type,
            period_identifier=self.current_period_id,
        )
        total = stats["total"]
        completed = stats["completed"]

        self.progress_badge.content.value = f"{completed} из {total}"
        self.progress_bar.value = (completed / total) if total > 0 else 0.0
        self.analytics_panel.refresh_charts(self.current_period_id, should_update=should_update)

        if should_update:
            try:
                self.progress_badge.update()
                self.progress_bar.update()
            except RuntimeError:
                pass
