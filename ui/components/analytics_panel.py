import flet as ft
import flet_charts as fch
from core.constants.colors import AppColors
from core.database.repository import ChecklistRepository


class AnalyticsPanel(ft.Card):
    def __init__(
        self,
        repo: ChecklistRepository,
        period_type: str,
        period_identifier: str,
    ):
        super().__init__()
        self.repo = repo
        self.period_type = period_type
        self.period_identifier = period_identifier
        self.is_expanded = False
        self.selected_tab = "summary"

        self.expand_icon = ft.Icon(
            ft.Icons.EXPAND_MORE,
            color=AppColors.TEXT_SECONDARY,
        )

        self.summary_label = ft.Text(
            "Аналитика • 0%",
            size=14,
            weight=ft.FontWeight.W_600,
            color=AppColors.TEXT_PRIMARY,
        )

        is_goal_tab = self.period_type in ("month", "year")

        self.chart_selector = ft.SegmentedButton(
            selected=[self.selected_tab],
            allow_multiple_selection=False,
            on_change=self._on_tab_change,
            segments=[
                ft.Segment(
                    value="summary",
                    label=ft.Text("Сводка" if is_goal_tab else "Сегодня"),
                ),
                ft.Segment(
                    value="details",
                    label=ft.Text("По целям" if is_goal_tab else "Неделя (Пн–Вс)"),
                ),
            ],
        )

        self.chart_holder = ft.Container(
            alignment=ft.Alignment.CENTER,
            padding=ft.Padding.only(top=10, right=8, left=4),
        )

        self.details_container = ft.Container(
            visible=self.is_expanded,
            padding=ft.Padding.only(top=10),
            content=ft.Column(
                spacing=8,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    self.chart_selector,
                    self.chart_holder,
                ],
            ),
        )

        header_row = ft.GestureDetector(
            on_tap=self._toggle_expand,
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Row(
                        spacing=8,
                        controls=[
                            ft.Icon(ft.Icons.INSIGHTS, size=20, color=AppColors.PRIMARY),
                            self.summary_label,
                        ],
                    ),
                    self.expand_icon,
                ],
            ),
        )

        self.content = ft.Container(
            padding=ft.Padding.symmetric(horizontal=14, vertical=10),
            content=ft.Column(
                spacing=0,
                controls=[
                    header_row,
                    self.details_container,
                ],
            ),
        )

        self.refresh_charts(period_identifier, should_update=False)

    def _toggle_expand(self, e: ft.ControlEvent) -> None:
        self.is_expanded = not self.is_expanded
        self.details_container.visible = self.is_expanded
        self.expand_icon.icon = ft.Icons.EXPAND_LESS if self.is_expanded else ft.Icons.EXPAND_MORE
        if self.is_expanded:
            self._render_active_view()
        try:
            self.update()
        except RuntimeError:
            pass

    def _on_tab_change(self, e: ft.ControlEvent) -> None:
        if e.control.selected:
            self.selected_tab = next(iter(e.control.selected))
            self._render_active_view()
            try:
                self.chart_holder.update()
            except RuntimeError:
                pass

    def refresh_charts(self, period_identifier: str, should_update: bool = True) -> None:
        self.period_identifier = period_identifier
        stats = self.repo.get_period_summary_stats(self.period_type, self.period_identifier)
        self.summary_label.value = f"Аналитика • {stats['percent']}% выполнено"

        if self.is_expanded:
            self._render_active_view()

        if should_update:
            try:
                self.update()
            except RuntimeError:
                pass

    def _render_active_view(self) -> None:
        if self.selected_tab == "summary":
            self.chart_holder.content = self._build_pie_chart()
        elif self.period_type == "day":
            self.chart_holder.content = self._build_week_bar_chart()
        else:
            self.chart_holder.content = self._build_goals_breakdown()
    def _build_pie_chart(self) -> ft.Control:
        stats = self.repo.get_period_summary_stats(self.period_type, self.period_identifier)
        total = stats["total"]
        completed = stats["completed"]
        remaining = stats["remaining"]

        if total == 0:
            return ft.Container(
                padding=ft.Padding.symmetric(vertical=24),
                content=ft.Text("Нет данных для расчёта", size=13, color=AppColors.TEXT_SECONDARY),
            )

        pie = fch.PieChart(
            sections_space=2,
            center_space_radius=30,
            width=130,
            height=130,
            sections=[
                fch.PieChartSection(
                    value=float(completed),
                    color=AppColors.SUCCESS,
                    radius=22,
                    title="",
                ),
                fch.PieChartSection(
                    value=float(remaining),
                    color=AppColors.SURFACE_VARIANT,
                    radius=20,
                    title="",
                ),
            ],
        )

        done_label = "Достигнуто" if self.period_type in ("month", "year") else "Выполнено"

        legend = ft.Column(
            spacing=8,
            alignment=ft.MainAxisAlignment.CENTER,
            controls=[
                ft.Row(
                    spacing=6,
                    controls=[
                        ft.Container(width=12, height=12, bgcolor=AppColors.SUCCESS, border_radius=3),
                        ft.Text(f"{done_label}: {completed}", size=13, color=AppColors.TEXT_PRIMARY),
                    ],
                ),
                ft.Row(
                    spacing=6,
                    controls=[
                        ft.Container(width=12, height=12, bgcolor=AppColors.SURFACE_VARIANT, border_radius=3),
                        ft.Text(f"Осталось: {remaining}", size=13, color=AppColors.TEXT_SECONDARY),
                    ],
                ),
            ],
        )

        return ft.Container(
            height=150,
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_EVENLY,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[pie, legend],
            ),
        )
    def _build_week_bar_chart(self) -> ft.Control:
        week_stats = self.repo.get_current_week_daily_stats()
        if not week_stats or all(d["total"] == 0 for d in week_stats):
            return ft.Container(
                padding=ft.Padding.symmetric(vertical=24),
                content=ft.Text("На эту неделю задач пока нет", size=13, color=AppColors.TEXT_SECONDARY),
            )

        groups: list[fch.BarChartGroup] = []
        bottom_labels: list[fch.ChartAxisLabel] = []

        for idx, item in enumerate(week_stats):
            pct = float(item["percent"])
            is_today = item["is_today"]
            bar_color = AppColors.SUCCESS if is_today else AppColors.PRIMARY_MUTED

            groups.append(
                fch.BarChartGroup(
                    x=idx,
                    rods=[
                        fch.BarChartRod(
                            from_y=0,
                            to_y=pct,
                            width=18,
                            color=bar_color,
                            border_radius=ft.BorderRadius.only(top_left=6, top_right=6),
                            tooltip=fch.BarChartRodTooltip(
                                text=f"{int(pct)}%",
                                text_style=ft.TextStyle(
                                    color="#FFFFFF",
                                    size=12,
                                    weight=ft.FontWeight.BOLD,
                                ),
                            ),
                        )
                    ],
                )
            )
            bottom_labels.append(
                fch.ChartAxisLabel(
                    value=idx,
                    label=ft.Text(
                        item["day_label"],
                        size=11,
                        weight=ft.FontWeight.BOLD if is_today else ft.FontWeight.NORMAL,
                        color=AppColors.PRIMARY if is_today else AppColors.TEXT_SECONDARY,
                    ),
                )
            )

        left_labels = [
            fch.ChartAxisLabel(
                value=float(v),
                label=ft.Container(
                    alignment=ft.Alignment.CENTER_RIGHT,
                    padding=ft.Padding.only(right=6),
                    content=ft.Text(f"{v}%", size=10, color=AppColors.TEXT_SECONDARY),
                ),
            )
            for v in (0, 50, 100)
        ]

        return ft.Container(
            height=180,
            padding=ft.Padding.only(top=24, right=8),
            content=fch.BarChart(
                groups=groups,
                max_y=100,
                tooltip=fch.BarChartTooltip(
                    bgcolor=AppColors.TEXT_PRIMARY,
                    border_radius=8,
                    padding=ft.Padding.symmetric(horizontal=8, vertical=4),
                ),
                border=ft.Border(bottom=ft.BorderSide(1, AppColors.DIVIDER)),
                bottom_axis=fch.ChartAxis(labels=bottom_labels, label_size=22),
                left_axis=fch.ChartAxis(labels=left_labels, label_size=38, show_labels=True),
                horizontal_grid_lines=fch.ChartGridLines(color=AppColors.DIVIDER, width=0.5),
                expand=True,
            ),
        )


    def _build_goals_breakdown(self) -> ft.Control:
        goals = self.repo.get_goals_with_progress(self.period_type, self.period_identifier)
        if not goals:
            return ft.Container(
                padding=ft.Padding.symmetric(vertical=24),
                content=ft.Text("Целей для этого периода пока нет", size=13, color=AppColors.TEXT_SECONDARY),
            )

        rows: list[ft.Control] = []
        for g in goals:
            is_done = bool(g["is_completed"] == 1)
            g_type = g.get("goal_type") or "numeric"
            status_color = AppColors.SUCCESS if is_done else AppColors.PRIMARY

            if g_type == "boolean":
                progress = 1.0 if is_done else 0.0
                right_label = "Выполнено" if is_done else "В процессе"
            else:
                cur = float(g.get("numeric_value") or 0.0)
                target = float(g.get("target_value") or 0.0)
                unit = g.get("unit_name") or ""
                progress = min(cur / target, 1.0) if target > 0 else 0.0
                pct = round((cur / target) * 100) if target > 0 else 0
                cur_fmt = int(cur) if cur.is_integer() else round(cur, 1)
                target_fmt = int(target) if target.is_integer() else target
                right_label = f"{cur_fmt}/{target_fmt} {unit} ({pct}%)".strip()

            rows.append(
                ft.Column(
                    spacing=4,
                    controls=[
                        ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            controls=[
                                ft.Text(
                                    g["title"],
                                    size=13,
                                    weight=ft.FontWeight.W_600,
                                    color=AppColors.TEXT_PRIMARY,
                                    expand=True,
                                ),
                                ft.Text(
                                    right_label,
                                    size=12,
                                    weight=ft.FontWeight.W_600,
                                    color=status_color,
                                ),
                            ],
                        ),
                        ft.ProgressBar(
                            value=progress,
                            color=status_color,
                            bgcolor=AppColors.DIVIDER,
                            height=6,
                            border_radius=3,
                        ),
                    ],
                )
            )

        return ft.Container(
            padding=ft.Padding.symmetric(vertical=6),
            content=ft.Column(spacing=12, controls=rows),
        )
