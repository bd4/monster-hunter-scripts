

class SkillEnum(object):
    _names = dict()

    @classmethod
    def name(cls, skill_id):
        return cls._names[skill_id]


class CapSkill(SkillEnum):
    NONE = 0
    EXPERT = 1
    MASTER = 2
    GOD = 3

    _names = { NONE: "No skills",
               EXPERT: "Capture Expert",
               MASTER: "Capture Master",
               GOD: "Capture God" }


class LuckSkill(SkillEnum):
    NONE = 0
    GOOD = 1
    GREAT = 2
    AMAZING = 3

    _names = { NONE: "No skills",
               GOOD: "Good Luck",
               GREAT: "Great Luck",
               AMAZING: "Magnificent Luck" }


class CarvingSkill(SkillEnum):
    NONE = 0
    PRO = 0 # prevent knockbacks but no extra carves
    FELYNE_LOW = 1
    FELYNE_HI = 2
    CELEBRITY = 3
    GOD = 4

    _names = { NONE: "No skills",
               FELYNE_LOW: "Felyne Carver Lo",
               FELYNE_HI: "Felyne Carver Hi",
               CELEBRITY: "Carving Celebrity",
               GOD: "Carving God" }


QUEST_A = "A"
QUEST_B = "B"
QUEST_SUB = "Sub"

