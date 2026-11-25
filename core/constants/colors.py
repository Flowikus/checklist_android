class AppColors:
    # Текущие активные цвета (по умолчанию — Морская)
    BACKGROUND = "#F6F8F8"
    CARD_BG = "#FFFFFF"
    SURFACE_VARIANT = "#EBF0F0"

    TEXT_PRIMARY = "#222B2E"
    TEXT_SECONDARY = "#68787D"

    PRIMARY = "#3D7A7A"
    PRIMARY_LIGHT = "#D5E6E6"
    PRIMARY_MUTED = "#8FB5B5"
    SUCCESS = "#2B6666"
    WARNING_DELETE = "#3D7A7A"
    NEUTRAL_ACCENT = "#85786A"

    DIVIDER = "#DCE3E5"

    THEMES: dict[str, dict[str, str]] = {
        "teal": {
            "name": "Морская",
            "primary": "#3D7A7A",
            "primary_light": "#D5E6E6",
            "primary_muted": "#8FB5B5",
            "success": "#2B6666",
            "background": "#F6F8F8",
            "surface_variant": "#EBF0F0",
            "divider": "#DCE3E5",
        },
        "lavender": {
            "name": "Лавандовая",
            "primary": "#6B5B95",
            "primary_light": "#E7E2F3",
            "primary_muted": "#AEA2CC",
            "success": "#52417D",
            "background": "#F7F6FA",
            "surface_variant": "#ECE9F4",
            "divider": "#DFDCE8",
        },
        "indigo": {
            "name": "Индиго",
            "primary": "#3F5185",
            "primary_light": "#DCE2F2",
            "primary_muted": "#92A0C7",
            "success": "#2B3C6E",
            "background": "#F5F7FA",
            "surface_variant": "#E8ECF4",
            "divider": "#D8DFEB",
        },
        "wheat": {
            "name": "Пшеничная",
            "primary": "#9C7A3C",
            "primary_light": "#F3EBD8",
            "primary_muted": "#CBB68E",
            "success": "#806026",
            "background": "#FAF8F4",
            "surface_variant": "#F1ECE1",
            "divider": "#E5DEC9",
        },
    }

    @classmethod
    def apply_theme(cls, theme_key: str) -> str:
        """Применяет выбранную палитру ко всем константам AppColors. Возвращает валидный ключ."""
        key = theme_key if theme_key in cls.THEMES else "teal"
        palette = cls.THEMES[key]
        cls.PRIMARY = palette["primary"]
        cls.PRIMARY_LIGHT = palette["primary_light"]
        cls.PRIMARY_MUTED = palette["primary_muted"]
        cls.SUCCESS = palette["success"]
        cls.WARNING_DELETE = palette["primary"]
        cls.BACKGROUND = palette["background"]
        cls.SURFACE_VARIANT = palette["surface_variant"]
        cls.DIVIDER = palette["divider"]
        return key
