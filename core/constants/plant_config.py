class PlantConfig:
    # Переключите в False перед финальной сборкой для полноценного годового роста (~365 дней)
    DEBUG_FAST_GROWTH: bool = False

    # Награды в монетах за выполнение задач и целей
    REWARD_DAILY_TASK: int = 100 if DEBUG_FAST_GROWTH else 10
    REWARD_PERFECT_DAY_BONUS: int = 150 if DEBUG_FAST_GROWTH else 20
    REWARD_MONTH_GOAL: int = 300 if DEBUG_FAST_GROWTH else 150
    REWARD_YEAR_GOAL: int = 1000 if DEBUG_FAST_GROWTH else 500

    # Действия ухода за растением: (название, стоимость в монетах, опыт XP, прирост влажности %, лимит в день)
    ACTIONS = {
        "sun": {
            "title": "Солнечный свет",
            "subtitle": "Погладить листья и дать свет",
            "cost": 0,
            "xp": 15 if DEBUG_FAST_GROWTH else 5,
            "hydration": 5,
            "daily_limit": 1,
        },
        "water": {
            "title": "Полить водой",
            "subtitle": "Восстанавливает влажность почвы",
            "cost": 15,
            "xp": 25 if DEBUG_FAST_GROWTH else 12,
            "hydration": 35,
            "daily_limit": 2,
        },
        "fertilize": {
            "title": "Подкормить",
            "subtitle": "Органическое удобрение для роста",
            "cost": 40,
            "xp": 60 if DEBUG_FAST_GROWTH else 30,
            "hydration": 10,
            "daily_limit": 1,
        },
    }

    # 6 стадий эволюции растения (пороги XP для режима отладки и для годового цикла)
    STAGES = [
        {
            "stage": 1,
            "name": "Семечко в горшке",
            "desc": "Маленькое семечко ждёт заботы и первых капель воды.",
            "min_xp": 0,
        },
        {
            "stage": 2,
            "name": "Первый росток",
            "desc": "Из земли показались два нежных зелёных листочка.",
            "min_xp": 30 if DEBUG_FAST_GROWTH else 250,
        },
        {
            "stage": 3,
            "name": "Молодой саженец",
            "desc": "Стебель окреп, появились первые боковые веточки.",
            "min_xp": 80 if DEBUG_FAST_GROWTH else 1200,
        },
        {
            "stage": 4,
            "name": "Пышное деревце",
            "desc": "Крона становится густой и радует насыщенной зеленью.",
            "min_xp": 150 if DEBUG_FAST_GROWTH else 3500,
        },
        {
            "stage": 5,
            "name": "Цветущее дерево",
            "desc": "На ветвях распустились первые нежные бутоны.",
            "min_xp": 240 if DEBUG_FAST_GROWTH else 6800,
        },
        {
            "stage": 6,
            "name": "Древнее Древо Жизни",
            "desc": "Могучее, величественное дерево — символ года вашей дисциплины!",
            "min_xp": 350 if DEBUG_FAST_GROWTH else 10000,
        },
    ]

    @classmethod
    def get_stage_info(cls, xp: int) -> dict:
        """Возвращает текущую стадию, следующую стадию и прогресс между ними."""
        current = cls.STAGES[0]
        next_stage = None

        for idx, st in enumerate(cls.STAGES):
            if xp >= st["min_xp"]:
                current = st
                next_stage = cls.STAGES[idx + 1] if idx + 1 < len(cls.STAGES) else None
            else:
                break

        if next_stage is None:
            progress = 1.0
            xp_in_stage = xp - current["min_xp"]
            xp_needed = 0
        else:
            span = max(1, next_stage["min_xp"] - current["min_xp"])
            xp_in_stage = xp - current["min_xp"]
            xp_needed = next_stage["min_xp"] - xp
            progress = min(max(xp_in_stage / span, 0.0), 1.0)

        return {
            "current": current,
            "next": next_stage,
            "progress": progress,
            "xp_in_stage": xp_in_stage,
            "xp_needed": xp_needed,
        }
