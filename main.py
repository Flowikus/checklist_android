import flet as ft
from core.constants.strings import AppStrings
from core.database.db_manager import DatabaseManager
from core.database.repository import ChecklistRepository
from core.utils.period_helper import PeriodHelper
from ui.components.renewal_dialog import show_renewal_dialog
from ui.theme.app_theme import get_app_theme
from ui.views.period_view import PeriodView
from ui.views.settings_view import SettingsView


def main(page: ft.Page):
    db_manager = DatabaseManager()
    db_manager.init_db()
    repo = ChecklistRepository(db_manager)

    page.title = AppStrings.APP_TITLE
    page.theme = get_app_theme()
    page.theme_mode = ft.ThemeMode.LIGHT
    #page.window.width = 400
    #page.window.height = 800

    # Инициализация всех 4 экранов
    week_view = PeriodView(repo=repo, period_type=AppStrings.PERIOD_WEEK)
    month_view = PeriodView(repo=repo, period_type=AppStrings.PERIOD_MONTH)
    year_view = PeriodView(repo=repo, period_type=AppStrings.PERIOD_YEAR)
    settings_view = SettingsView(page=page, repo=repo)

    views = [week_view, month_view, year_view, settings_view]
    body_container = ft.Container(content=week_view, expand=True)

    def on_nav_change(e: ft.ControlEvent):
        idx = int(e.control.selected_index)
        selected_view = views[idx]
        body_container.content = selected_view

        # Обновляем данные при переключении вкладки
        if isinstance(selected_view, PeriodView):
            selected_view.refresh_data(should_update=False)
        elif isinstance(selected_view, SettingsView):
            selected_view.load_tasks(should_update=False)

        body_container.update()

    def switch_to_settings(filter_period: str):
        page.navigation_bar.selected_index = 3
        settings_view.set_period(filter_period)
        body_container.content = settings_view
        page.update()

    def refresh_active_period_view():
        current = body_container.content
        if isinstance(current, PeriodView):
            current.refresh_data(should_update=True)

    def check_renewals():
        pending_periods = PeriodHelper.check_periods_needing_renewal(repo)
        if pending_periods:
            show_renewal_dialog(
                page=page,
                repo=repo,
                period_type=pending_periods,
                on_edit_requested=switch_to_settings,
                on_keep_requested=refresh_active_period_view,
            )

    def on_lifecycle_change(e: ft.AppLifecycleStateChangeEvent):
        if e.state == ft.AppLifecycleState.RESUME:
            check_renewals()

    page.on_lifecycle_state_change = on_lifecycle_change

    page.navigation_bar = ft.NavigationBar(
        selected_index=0,
        on_change=on_nav_change,
        destinations=[
            ft.NavigationBarDestination(
                icon=ft.Icons.VIEW_WEEK_OUTLINED,
                selected_icon=ft.Icons.VIEW_WEEK,
                label=AppStrings.TAB_WEEK,
            ),
            ft.NavigationBarDestination(
                icon=ft.Icons.CALENDAR_MONTH_OUTLINED,
                selected_icon=ft.Icons.CALENDAR_MONTH,
                label=AppStrings.TAB_MONTH,
            ),
            ft.NavigationBarDestination(
                icon=ft.Icons.EVENT_NOTE_OUTLINED,
                selected_icon=ft.Icons.EVENT_NOTE,
                label=AppStrings.TAB_YEAR,
            ),
            ft.NavigationBarDestination(
                icon=ft.Icons.SETTINGS_OUTLINED,
                selected_icon=ft.Icons.SETTINGS,
                label=AppStrings.TAB_SETTINGS,
            ),
        ],
    )

    page.add(body_container)
    check_renewals()


if __name__ == "__main__":
    ft.run(main)
