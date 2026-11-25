from typing import Any
import flet as ft
from core.constants.colors import AppColors
from core.constants.plant_config import PlantConfig
from core.database.repository import ChecklistRepository


class PlantView(ft.Container):
    def __init__(self, page: ft.Page, repo: ChecklistRepository):
        super().__init__(expand=True, padding=ft.Padding.only(left=16, right=16, top=12))
        self.app_page = page
        self.repo = repo

        # Заголовок с именем растения и кнопкой переименования
        self.plant_name_text = ft.Text(
            "Росток",
            size=22,
            weight=ft.FontWeight.BOLD,
            color=AppColors.TEXT_PRIMARY,
        )

        # Бейдж баланса монет
        self.coins_text = ft.Text(
            "0",
            size=15,
            weight=ft.FontWeight.BOLD,
            color=AppColors.PRIMARY,
        )
        self.coins_badge = ft.Container(
            bgcolor=AppColors.PRIMARY_LIGHT,
            padding=ft.Padding.symmetric(horizontal=12, vertical=6),
            border_radius=20,
            content=ft.Row(
                spacing=6,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Icon(ft.Icons.MONETIZATION_ON_OUTLINED, size=18, color=AppColors.PRIMARY),
                    self.coins_text,
                ],
            ),
        )

        # Визуальный контейнер растения (горшок + дерево по стадиям 1..6)
        self.plant_visual_holder = ft.Container(
            height=175,
            alignment=ft.Alignment.CENTER,
        )

        self.stage_title = ft.Text(
            "Стадия 1 • Семечко в горшке",
            size=17,
            weight=ft.FontWeight.BOLD,
            color=AppColors.TEXT_PRIMARY,
            text_align=ft.TextAlign.CENTER,
        )
        self.stage_desc = ft.Text(
            "",
            size=13,
            color=AppColors.TEXT_SECONDARY,
            text_align=ft.TextAlign.CENTER,
        )

        # Шкала опыта (XP) до следующей стадии
        self.xp_label = ft.Text("0 XP", size=12, weight=ft.FontWeight.W_600, color=AppColors.PRIMARY)
        self.xp_progress = ft.ProgressBar(
            value=0.0,
            color=AppColors.PRIMARY,
            bgcolor=AppColors.DIVIDER,
            height=7,
            border_radius=4,
        )

        # Шкала влажности почвы
        self.hydration_label = ft.Text("Влажность: 80%", size=12, color=AppColors.SUCCESS)
        self.hydration_progress = ft.ProgressBar(
            value=0.8,
            color=AppColors.SUCCESS,
            bgcolor=AppColors.DIVIDER,
            height=7,
            border_radius=4,
        )
        # Карточка растения
        plant_card = ft.Card(
            content=ft.Container(
                padding=ft.Padding.symmetric(horizontal=16, vertical=14),
                content=ft.Column(
                    spacing=8,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        self.plant_visual_holder,
                        self.stage_title,
                        self.stage_desc,
                        ft.Divider(height=6, color=AppColors.DIVIDER),
                        ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            controls=[
                                ft.Text("Рост до следующей стадии", size=12, color=AppColors.TEXT_SECONDARY),
                                self.xp_label,
                            ],
                        ),
                        self.xp_progress,
                        ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            controls=[
                                self.hydration_label,
                                ft.Text(
                                    "+10% XP при влажности ≥70%",
                                    size=11,
                                    color=AppColors.TEXT_SECONDARY,
                                ),
                            ],
                        ),
                        self.hydration_progress,
                    ],
                ),
            )
        )

        # Контейнер для кнопок ухода
        self.actions_column = ft.Column(spacing=8)

        self.content = ft.Column(
            spacing=12,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Row(
                            spacing=4,
                            controls=[
                                self.plant_name_text,
                                ft.IconButton(
                                    icon=ft.Icons.EDIT_OUTLINED,
                                    icon_size=18,
                                    icon_color=AppColors.TEXT_SECONDARY,
                                    tooltip="Переименовать",
                                    on_click=self._open_rename_dialog,
                                ),
                            ],
                        ),
                        self.coins_badge,
                    ],
                ),
                plant_card,
                ft.Text(
                    "Уход за растением",
                    size=14,
                    weight=ft.FontWeight.W_600,
                    color=AppColors.TEXT_SECONDARY,
                ),
                self.actions_column,
                ft.Container(height=12),
            ],
        )

        self.refresh_data(should_update=False)

    def refresh_data(self, should_update: bool = True) -> None:
        state = self.repo.get_plant_state()
        stage_info = PlantConfig.get_stage_info(state["xp"])
        cur = stage_info["current"]
        nxt = stage_info["next"]

        self.plant_name_text.value = state["plant_name"]
        self.coins_text.value = str(state["coins"])
        self.stage_title.value = f"Стадия {cur['stage']} из 6 • {cur['name']}"
        self.stage_desc.value = cur["desc"]

        if nxt is None:
            self.xp_label.value = f"{state['xp']} XP (Максимум!)"
        else:
            self.xp_label.value = f"{state['xp']} / {nxt['min_xp']} XP"
        self.xp_progress.value = stage_info["progress"]

        hyd = int(state["hydration"])
        self.hydration_progress.value = hyd / 100.0
        if hyd >= 70:
            self.hydration_label.value = f"Влажность: {hyd}% (Бодрое)"
            self.hydration_label.color = AppColors.SUCCESS
            self.hydration_progress.color = AppColors.SUCCESS
        elif hyd >= 30:
            self.hydration_label.value = f"Влажность: {hyd}% (Норма)"
            self.hydration_label.color = AppColors.PRIMARY
            self.hydration_progress.color = AppColors.PRIMARY
        else:
            self.hydration_label.value = f"Влажность: {hyd}% (Хочет пить)"
            self.hydration_label.color = AppColors.WARNING_DELETE
            self.hydration_progress.color = AppColors.WARNING_DELETE

        self.plant_visual_holder.content = self._build_plant_illustration(cur["stage"], hyd)
        self._rebuild_action_cards(state)

        if should_update:
            try:
                self.update()
            except RuntimeError:
                pass
    @staticmethod
    def _build_plant_illustration(stage: int, hydration: int) -> ft.Control:
        """Рисует стилизованное растение в горшке в зависимости от стадии (1..6) и влажности."""
        leaf_color = AppColors.SUCCESS if hydration >= 30 else AppColors.NEUTRAL_ACCENT
        stem_color = AppColors.PRIMARY
        pot_color = AppColors.NEUTRAL_ACCENT
        pot_rim_color = "#6E6256"

        # Горшок (общий для всех стадий)
        pot = ft.Column(
            spacing=0,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Container(
                    width=84,
                    height=12,
                    bgcolor=pot_rim_color,
                    border_radius=4,
                ),
                ft.Container(
                    width=70,
                    height=42,
                    bgcolor=pot_color,
                    border_radius=ft.BorderRadius.only(bottom_left=14, bottom_right=14),
                ),
            ],
        )

        # Верхняя часть растения по стадиям 1..6
        if stage == 1:
            # Семечко в холмике земли
            top_part = ft.Container(
                width=46,
                height=16,
                bgcolor="#5C5248",
                border_radius=ft.BorderRadius.only(top_left=20, top_right=20),
                alignment=ft.Alignment.CENTER,
                content=ft.Container(width=10, height=10, bgcolor=leaf_color, border_radius=5),
            )
        elif stage == 2:
            # Первый росток с двумя листочками
            top_part = ft.Column(
                spacing=0,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Row(
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=2,
                        controls=[
                            ft.Container(
                                width=22,
                                height=12,
                                bgcolor=leaf_color,
                                border_radius=ft.BorderRadius.only(top_left=12, bottom_right=12),
                            ),
                            ft.Container(
                                width=22,
                                height=12,
                                bgcolor=leaf_color,
                                border_radius=ft.BorderRadius.only(top_right=12, bottom_left=12),
                            ),
                        ],
                    ),
                    ft.Container(width=5, height=28, bgcolor=stem_color, border_radius=2),
                ],
            )
        elif stage == 3:
            # Молодой саженец с веточками
            top_part = ft.Column(
                spacing=0,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Container(width=44, height=34, bgcolor=leaf_color, border_radius=22),
                    ft.Row(
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=4,
                        controls=[
                            ft.Container(width=24, height=14, bgcolor=leaf_color, border_radius=8),
                            ft.Container(width=6, height=38, bgcolor=stem_color, border_radius=3),
                            ft.Container(width=24, height=14, bgcolor=leaf_color, border_radius=8),
                        ],
                    ),
                ],
            )
        elif stage == 4:
            # Пышное деревце
            top_part = ft.Column(
                spacing=-8,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Container(width=76, height=58, bgcolor=leaf_color, border_radius=36),
                    ft.Container(width=10, height=46, bgcolor=pot_rim_color, border_radius=4),
                ],
            )
        elif stage == 5:
            # Цветущее дерево (с золотисто-белыми бутонами)
            blossoms = ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_EVENLY,
                controls=[
                    ft.Container(width=10, height=10, bgcolor="#F4E3B2", border_radius=5),
                    ft.Container(width=12, height=12, bgcolor="#FFFFFF", border_radius=6),
                    ft.Container(width=10, height=10, bgcolor="#F4E3B2", border_radius=5),
                ],
            )
            top_part = ft.Column(
                spacing=-8,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Container(
                        width=96,
                        height=68,
                        bgcolor=leaf_color,
                        border_radius=42,
                        alignment=ft.Alignment.CENTER,
                        content=blossoms,
                    ),
                    ft.Container(width=12, height=48, bgcolor=pot_rim_color, border_radius=4),
                ],
            )
        else:
            # Стадия 6: Древнее Древо Жизни с пышной многоярусной кроной
            crown = ft.Stack(
                width=124,
                height=82,
                controls=[
                    ft.Container(left=4, top=18, width=54, height=54, bgcolor=stem_color, border_radius=27),
                    ft.Container(right=4, top=18, width=54, height=54, bgcolor=stem_color, border_radius=27),
                    ft.Container(
                        left=22,
                        top=2,
                        width=80,
                        height=72,
                        bgcolor=leaf_color,
                        border_radius=38,
                        alignment=ft.Alignment.CENTER,
                        content=ft.Icon(ft.Icons.AUTO_AWESOME, size=24, color="#F4E3B2"),
                    ),
                ],
            )
            top_part = ft.Column(
                spacing=-10,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    crown,
                    ft.Container(width=16, height=48, bgcolor=pot_rim_color, border_radius=5),
                ],
            )

        return ft.Column(
            spacing=0,
            alignment=ft.MainAxisAlignment.END,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[top_part, pot],
        )
    def _rebuild_action_cards(self, state: dict[str, Any]) -> None:
        self.actions_column.controls.clear()

        icons_map = {
            "sun": ft.Icons.WB_SUNNY_OUTLINED,
            "water": ft.Icons.WATER_DROP_OUTLINED,
            "fertilize": ft.Icons.SPA_OUTLINED,
        }

        for key, cfg in PlantConfig.ACTIONS.items():
            used = int(state.get(f"{key}_count_today", 0))
            limit = int(cfg["daily_limit"])
            cost = int(cfg["cost"])
            xp = int(cfg["xp"])

            is_limit_reached = used >= limit
            can_afford = state["coins"] >= cost
            is_enabled = (not is_limit_reached) and can_afford

            cost_label = "Бесплатно" if cost == 0 else f"{cost} монет"
            btn_text = f"{used}/{limit}" if is_limit_reached else cost_label

            action_btn = ft.FilledButton(
                content=ft.Text(btn_text, size=12, weight=ft.FontWeight.W_600),
                disabled=not is_enabled,
                style=ft.ButtonStyle(
                    bgcolor=AppColors.PRIMARY if is_enabled else AppColors.DIVIDER,
                    color="#FFFFFF" if is_enabled else AppColors.TEXT_SECONDARY,
                    shape=ft.RoundedRectangleBorder(radius=10),
                    padding=ft.Padding.symmetric(horizontal=12, vertical=8),
                ),
                on_click=lambda e, k=key: self._handle_care_click(k),
            )

            card = ft.Card(
                content=ft.Container(
                    padding=ft.Padding.symmetric(horizontal=14, vertical=10),
                    content=ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Row(
                                spacing=10,
                                expand=True,
                                controls=[
                                    ft.Container(
                                        width=38,
                                        height=38,
                                        border_radius=10,
                                        bgcolor=AppColors.PRIMARY_LIGHT,
                                        alignment=ft.Alignment.CENTER,
                                        content=ft.Icon(icons_map.get(key, ft.Icons.ECO), size=20, color=AppColors.PRIMARY),
                                    ),
                                    ft.Column(
                                        spacing=2,
                                        expand=True,
                                        controls=[
                                            ft.Text(
                                                f"{cfg['title']} (+{xp} XP)",
                                                size=14,
                                                weight=ft.FontWeight.W_600,
                                                color=AppColors.TEXT_PRIMARY,
                                            ),
                                            ft.Text(
                                                f"{cfg['subtitle']} • Лимит: {used}/{limit}",
                                                size=12,
                                                color=AppColors.TEXT_SECONDARY,
                                            ),
                                        ],
                                    ),
                                ],
                            ),
                            action_btn,
                        ],
                    ),
                )
            )
            self.actions_column.controls.append(card)

    def _handle_care_click(self, action_key: str) -> None:
        success, msg = self.repo.perform_plant_care(action_key)
        self.refresh_data(should_update=True)
        self.app_page.show_dialog(
            ft.SnackBar(
                content=ft.Text(msg, color="#FFFFFF"),
                bgcolor=AppColors.SUCCESS if success else AppColors.WARNING_DELETE,
                duration=1800,
            )
        )

    def _open_rename_dialog(self, e: ft.ControlEvent) -> None:
        name_field = ft.TextField(
            label="Имя вашего растения",
            value=self.plant_name_text.value,
            border_radius=10,
        )

        def save_name(ev: ft.ControlEvent) -> None:
            val = (name_field.value or "").strip()
            if val:
                self.repo.rename_plant(val)
                self.app_page.pop_dialog()
                self.refresh_data(should_update=True)

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Имя растения", size=18, weight=ft.FontWeight.BOLD, color=AppColors.TEXT_PRIMARY),
            content=ft.Container(
                width=300,
                content=ft.Column(
                    tight=True,
                    spacing=12,
                    controls=[
                        name_field,
                        ft.Row(
                            alignment=ft.MainAxisAlignment.END,
                            spacing=8,
                            controls=[
                                ft.TextButton(
                                    content=ft.Text("Отмена", color=AppColors.TEXT_SECONDARY),
                                    on_click=lambda ev: self.app_page.pop_dialog(),
                                ),
                                ft.FilledButton(
                                    content=ft.Text("Сохранить"),
                                    style=ft.ButtonStyle(bgcolor=AppColors.PRIMARY, color="#FFFFFF"),
                                    on_click=save_name,
                                ),
                            ],
                        ),
                    ],
                ),
            ),
            bgcolor=AppColors.CARD_BG,
            shape=ft.RoundedRectangleBorder(radius=16),
        )
        self.app_page.show_dialog(dlg)
