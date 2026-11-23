import flet as ft
from core.constants.colors import AppColors


def get_app_theme() -> ft.Theme:
    return ft.Theme(
        use_material3=True,
        color_scheme=ft.ColorScheme(
            primary=AppColors.PRIMARY,
            on_primary="#FFFFFF",
            primary_container=AppColors.PRIMARY_LIGHT,
            on_primary_container=AppColors.TEXT_PRIMARY,
            secondary=AppColors.SUCCESS,
            surface=AppColors.CARD_BG,
            on_surface=AppColors.TEXT_PRIMARY,
            on_surface_variant=AppColors.TEXT_SECONDARY,
            outline=AppColors.DIVIDER,
            error=AppColors.WARNING_DELETE,  # Переопределяем системный красный на индиго
        ),
        scaffold_bgcolor=AppColors.BACKGROUND,
        card_theme=ft.CardTheme(
            color=AppColors.CARD_BG,
            elevation=1,
            shape=ft.RoundedRectangleBorder(radius=12),
        ),
        navigation_bar_theme=ft.NavigationBarTheme(
            bgcolor=AppColors.CARD_BG,
            indicator_color=AppColors.PRIMARY_LIGHT,
            label_behavior=ft.NavigationBarLabelBehavior.ALWAYS_SHOW,
        ),
    )
