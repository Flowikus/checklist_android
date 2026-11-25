from datetime import datetime, timedelta
from core.constants.strings import AppStrings
from core.database.repository import ChecklistRepository


class PeriodHelper:
    PERIOD_DAY = getattr(AppStrings, "PERIOD_DAY", "day")

    @classmethod
    def get_current_period_id(cls, period_type: str, dt: datetime | None = None) -> str:
        now = dt or datetime.now()
        if period_type == cls.PERIOD_DAY:
            return now.strftime("%Y-%m-%d")
        elif period_type == AppStrings.PERIOD_WEEK:
            iso_year, iso_week, _ = now.isocalendar()
            return f"{iso_year}-W{iso_week:02d}"
        elif period_type == AppStrings.PERIOD_MONTH:
            return now.strftime("%Y-%m")
        elif period_type == AppStrings.PERIOD_YEAR:
            return now.strftime("%Y")
        raise ValueError(f"Неизвестный тип периода: {period_type}")

    @staticmethod
    def get_current_day_of_week(dt: datetime | None = None) -> int:
        """Возвращает номер текущего дня недели: 1 (Пн) .. 7 (Вс)."""
        now = dt or datetime.now()
        return now.isoweekday()

    @staticmethod
    def get_date_for_weekday_in_current_week(target_weekday: int, dt: datetime | None = None) -> datetime:
        """Возвращает объект datetime для выбранного дня (1..7) текущей недели."""
        now = dt or datetime.now()
        current_weekday = now.isoweekday()
        delta_days = target_weekday - current_weekday
        return now + timedelta(days=delta_days)

    @classmethod
    def get_period_display_name(cls, period_type: str, dt: datetime | None = None) -> str:
        now = dt or datetime.now()
        months_ru = [
            "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
            "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
        ]
        months_genitive_ru = [
            "января", "февраля", "марта", "апреля", "мая", "июня",
            "июля", "августа", "сентября", "октября", "ноября", "декабря"
        ]
        days_short_ru = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]

        if period_type == cls.PERIOD_DAY:
            day_name = days_short_ru[now.weekday()]
            prefix = "Сегодня, " if now.date() == datetime.now().date() else ""
            return f"{prefix}{now.day} {months_genitive_ru[now.month - 1]} ({day_name})"
        elif period_type == AppStrings.PERIOD_WEEK:
            _, iso_week, _ = now.isocalendar()
            return f"Неделя №{iso_week} ({now.year})"
        elif period_type == AppStrings.PERIOD_MONTH:
            return f"{months_ru[now.month - 1]} {now.year}"
        elif period_type == AppStrings.PERIOD_YEAR:
            return f"{now.year} год"
        return ""

    @staticmethod
    def get_period_label_nominative(period_type: str) -> str:
        mapping = {
            AppStrings.PERIOD_WEEK: "новая неделя",
            AppStrings.PERIOD_MONTH: "новый месяц",
            AppStrings.PERIOD_YEAR: "новый год",
        }
        return mapping.get(period_type, "новый период")

    @classmethod
    def check_periods_needing_renewal(cls, repo: ChecklistRepository) -> list[str]:
        current_day_id = cls.get_current_period_id(cls.PERIOD_DAY)
        last_day = repo.get_last_prompted_period(cls.PERIOD_DAY)
        if last_day != current_day_id:
            repo.set_last_prompted_period(cls.PERIOD_DAY, current_day_id)

        periods_to_prompt: list[str] = []
        prompt_periods = [
            AppStrings.PERIOD_WEEK,
            AppStrings.PERIOD_MONTH,
            AppStrings.PERIOD_YEAR,
        ]

        for p_type in prompt_periods:
            current_id = cls.get_current_period_id(p_type)
            last_prompted = repo.get_last_prompted_period(p_type)

            if last_prompted is None:
                repo.set_last_prompted_period(p_type, current_id)
            elif last_prompted != current_id:
                existing_items = repo.get_all_items(period_type=p_type, only_active=True)
                if existing_items:
                    periods_to_prompt.append(p_type)
                else:
                    repo.set_last_prompted_period(p_type, current_id)

        return periods_to_prompt
