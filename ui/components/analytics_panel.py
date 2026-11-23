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
        self.selected_chart = "pie"

        # Иконка сворачивания/разворачивания
        self.expand_icon = ft.Icon(
            ft.Icons.EXPAND_MORE,
            color=AppColors.TEXT_SECONDARY,
        )

        # Заголовок с процентом выполнения
        self.summary_label = ft.Text(
            "Аналитика • 0%",
            size=14,
            weight=ft.FontWeight.W_600,
            color=AppColors.TEXT_PRIMARY,
        )

        # Переключатель типа графика (list вместо set для Flet 1.0+)
        self.chart_selector = ft.SegmentedButton(
            selected=[self.selected_chart],
            allow_multiple_selection=False,
            on_change=self._on_chart_type_change,
            segments=[
                ft.Segment(value="pie", label=ft.Text("Итог")),
                ft.Segment(value="bar", label=ft.Text("Задачи")),
                ft.Segment(value="line", label=ft.Text("Числа")),
            ],
        )

        # Контейнер для отрисовки выбранного графика
        self.chart_holder = ft.Container(
            height=175,
            alignment=ft.Alignment.CENTER,
            padding=ft.Padding.only(top=8),
        )

        # Раскрываемая часть карточки
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

        # Кликабельная шапка панели
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
            self._render_active_chart()
        try:
            self.update()
        except RuntimeError:
            pass

    def _on_chart_type_change(self, e: ft.ControlEvent) -> None:
        if e.control.selected:
            self.selected_chart = next(iter(e.control.selected))
            self._render_active_chart()
            try:
                self.chart_holder.update()
            except RuntimeError:
                pass

    def refresh_charts(self, period_identifier: str, should_update: bool = True) -> None:
        self.period_identifier = period_identifier
        stats = self.repo.get_period_summary_stats(self.period_type, self.period_identifier)
        self.summary_label.value = f"Аналитика • {stats['percent']}% выполнено"

        if self.is_expanded:
            self._render_active_chart()

        if should_update:
            try:
                self.update()
            except RuntimeError:
                pass

    def _render_active_chart(self) -> None:
        if self.selected_chart == "pie":
            self.chart_holder.content = self._build_pie_chart()
        elif self.selected_chart == "bar":
            self.chart_holder.content = self._build_bar_chart()
        else:
            self.chart_holder.content = self._build_line_chart()

    def _build_pie_chart(self) -> ft.Control:
        stats = self.repo.get_period_summary_stats(self.period_type, self.period_identifier)
        total = stats["total"]
        completed = stats["completed"]
        remaining = stats["remaining"]

        if total == 0:
            return ft.Text("Нет задач для расчёта", size=13, color=AppColors.TEXT_SECONDARY)

        pie = fch.PieChart(
            sections_space=2,
            center_space_radius=32,
            width=140,
            height=140,
            sections=[
                fch.PieChartSection(
                    value=float(completed),
                    color=AppColors.SUCCESS,
                    radius=24,
                    title="",
                ),
                fch.PieChartSection(
                    value=float(remaining),
                    color=AppColors.SURFACE_VARIANT,
                    radius=22,
                    title="",
                ),
            ],
        )


        legend = ft.Column(
            spacing=8,
            alignment=ft.MainAxisAlignment.CENTER,
            controls=[
                ft.Row(
                    spacing=6,
                    controls=[
                        ft.Container(width=12, height=12, bgcolor=AppColors.SUCCESS, border_radius=3),
                        ft.Text(f"Выполнено: {completed}", size=13, color=AppColors.TEXT_PRIMARY),
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

        return ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_EVENLY,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[pie, legend],
        )

    def _build_bar_chart(self) -> ft.Control:
        history = self.repo.get_historical_completion(self.period_type, limit=6)
        if not history:
            return ft.Text("История выполнения пока пуста", size=13, color=AppColors.TEXT_SECONDARY)

        max_val = max((item["completed_count"] or 0) for item in history)
        max_y = float(max(max_val + 1, 2))

        groups: list[fch.BarChartGroup] = []
        bottom_labels: list[fch.ChartAxisLabel] = []

        for idx, item in enumerate(history):
            val = float(item["completed_count"] or 0)
            # Сокращаем подпись периода (например, '2026-W47' -> 'W47')
            short_label = item["period_identifier"].split("-")[-1]

            groups.append(
                fch.BarChartGroup(
                    x=idx,
                    rods=[
                        fch.BarChartRod(
                            from_y=0,
                            to_y=val,
                            width=18,
                            color=AppColors.PRIMARY,
                            border_radius=ft.BorderRadius.only(top_left=6, top_right=6),
                        )
                    ],
                )
            )
            bottom_labels.append(
                fch.ChartAxisLabel(
                    value=idx,
                    label=ft.Text(short_label, size=11, color=AppColors.TEXT_SECONDARY),
                )
            )

        return fch.BarChart(
            groups=groups,
            max_y=max_y,
            border=ft.Border(
                bottom=ft.BorderSide(1, AppColors.DIVIDER),
            ),
            bottom_axis=fch.ChartAxis(labels=bottom_labels, label_size=24),
            left_axis=fch.ChartAxis(label_size=28),
            horizontal_grid_lines=fch.ChartGridLines(color=AppColors.DIVIDER, width=0.5),
            expand=True,
        )


    def _build_line_chart(self) -> ft.Control:
        history = self.repo.get_historical_completion(self.period_type, limit=6)
        if not history:
            return ft.Text("Нет числовых данных за периоды", size=13, color=AppColors.TEXT_SECONDARY)

        points: list[fch.LineChartDataPoint] = []
        bottom_labels: list[fch.ChartAxisLabel] = []
        max_val = 0.0

        for idx, item in enumerate(history):
            val = float(item["total_numeric"] or 0.0)
            if val > max_val:
                max_val = val
            short_label = item["period_identifier"].split("-")[-1]

            points.append(fch.LineChartDataPoint(x=float(idx), y=val))
            bottom_labels.append(
                fch.ChartAxisLabel(
                    value=idx,
                    label=ft.Text(short_label, size=11, color=AppColors.TEXT_SECONDARY),
                )
            )

        if max_val == 0:
            return ft.Text("Числовые показатели пока равны 0", size=13, color=AppColors.TEXT_SECONDARY)

        return fch.LineChart(
            min_y=0,
            max_y=max_val * 1.2,
            min_x=0,
            max_x=float(max(len(points) - 1, 1)),
            data_series=[
                fch.LineChartData(
                    points=points,
                    stroke_width=3,
                    color=AppColors.SUCCESS,
                    curved=True,
                    point=True,
                )
            ],
            bottom_axis=fch.ChartAxis(labels=bottom_labels, label_size=24),
            left_axis=fch.ChartAxis(label_size=34),
            horizontal_grid_lines=fch.ChartGridLines(color=AppColors.DIVIDER, width=0.5),
            expand=True,
        )
