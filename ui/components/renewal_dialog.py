from typing import Callable
import flet as ft
from core.constants.colors import AppColors
from core.constants.strings import AppStrings
from core.database.repository import ChecklistRepository
from core.utils.period_helper import PeriodHelper


def show_renewal_dialog(
    page: ft.Page,
    repo: ChecklistRepository,
    period_type: str,
    on_edit_requested: Callable[[str], None],
    on_keep_requested: Callable[[], None],
) -> None:
    """Показывает модальное окно при наступлении нового периода."""
    current_period_id = PeriodHelper.get_current_period_id(period_type)
    period_name = PeriodHelper.get_period_label_nominative(period_type)

    def handle_keep(e):
        # Фиксируем, что пользователь подтвердил новый период (задачи останутся с 0 прогрессом)
        repo.set_last_prompted_period(period_type, current_period_id)
        page.pop_dialog()
        on_keep_requested()

    def handle_edit(e):
        repo.set_last_prompted_period(period_type, current_period_id)
        page.pop_dialog()
        on_edit_requested(period_type)

    dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text(
            f"Наступила {period_name}!" if period_type == AppStrings.PERIOD_WEEK else f"Наступил {period_name}!",
            size=18,
            weight=ft.FontWeight.BOLD,
            color=AppColors.TEXT_PRIMARY,
        ),
        content=ft.Text(
            AppStrings.RENEWAL_TEXT,
            size=15,
            color=AppColors.TEXT_SECONDARY,
        ),
        actions=[
            ft.TextButton(
                content=ft.Text(AppStrings.BTN_KEEP, color=AppColors.TEXT_SECONDARY),
                on_click=handle_keep,
            ),
            ft.FilledButton(
                content=ft.Text(AppStrings.BTN_EDIT),
                style=ft.ButtonStyle(
                    bgcolor=AppColors.PRIMARY,
                    color="#FFFFFF",
                ),
                on_click=handle_edit,
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
        bgcolor=AppColors.CARD_BG,
        shape=ft.RoundedRectangleBorder(radius=16),
    )

    page.show_dialog(dialog)
