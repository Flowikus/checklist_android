from datetime import datetime
from core.constants.strings import AppStrings
from core.database.repository import ChecklistRepository


class PeriodHelper:
    @staticmethod
    def get_current_period_id(period_type: str, dt: datetime | None = None) -> str:
        """Возвращает уникальный код текущего периода для записи в БД."""
        now = dt or datetime.now()
        if period_type == AppStrings.PERIOD_WEEK:
            iso_year, iso_week, _ = now.isocalendar()
            return f"{iso_year}-W{iso_week:02d}"
        elif period_type == AppStrings.PERIOD_MONTH:
            return now.strftime("%Y-%m")
        elif period_type == AppStrings.PERIOD_YEAR:
            return now.strftime("%Y")
        raise ValueError(f"Неизвестный тип периода: {period_type}")

    @staticmethod
    def get_period_display_name(period_type: str, dt: datetime | None = None) -> str:
        """Возвращает человекочитаемый заголовок периода для экрана."""
        now = dt or datetime.now()
        months_ru = [
            "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
            "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
        ]
        if period_type == AppStrings.PERIOD_WEEK:
            _, iso_week, _ = now.isocalendar()
            return f"Неделя №{iso_week} ({now.year})"
        elif period_type == AppStrings.PERIOD_MONTH:
            return f"{months_ru[now.month - 1]} {now.year}"
        elif period_type == AppStrings.PERIOD_YEAR:
            return f"{now.year} год"
        return ""

    @staticmethod
    def get_period_label_nominative(period_type: str) -> str:
        """Название периода для текста диалога обновления."""
        mapping = {
            AppStrings.PERIOD_WEEK: "новая неделя",
            AppStrings.PERIOD_MONTH: "новый месяц",
            AppStrings.PERIOD_YEAR: "новый год",
        }
        return mapping.get(period_type, "новый период")

    @classmethod
    def check_periods_needing_renewal(cls, repo: ChecklistRepository) -> list[str]:
        """
        Проверяет все 3 типа периодов.
        - При самом первом запуске фиксирует текущий период без показа диалога.
        - Если период сменился И по нему есть активные задачи — возвращает его в списке.
        """
        periods_to_prompt: list[str] = []
        all_periods = [
            AppStrings.PERIOD_WEEK,
            AppStrings.PERIOD_MONTH,
            AppStrings.PERIOD_YEAR,
        ]

        for p_type in all_periods:
            current_id = cls.get_current_period_id(p_type)
            last_prompted = repo.get_last_prompted_period(p_type)

            if last_prompted is None:
                # Первый запуск приложения — просто запоминаем текущий период
                repo.set_last_prompted_period(p_type, current_id)
            elif last_prompted != current_id:
                # Период сменился. Спрашиваем пользователя, только если в списке есть задачи
                existing_items = repo.get_all_items(period_type=p_type, only_active=True)
                if existing_items:
                    periods_to_prompt.append(p_type)
                else:
                    repo.set_last_prompted_period(p_type, current_id)

        return periods_to_prompt
