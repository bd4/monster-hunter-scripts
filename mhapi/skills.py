
from mhapi.util import EnumBase


class CapSkill(EnumBase):
    NONE = 0
    EXPERT = 1
    MASTER = 2
    GOD = 3

    _names = { NONE: "No skills",
               EXPERT: "Capture Expert",
               MASTER: "Capture Master",
               GOD: "Capture God" }


class LuckSkill(EnumBase):
    NONE = 0
    GOOD = 1
    GREAT = 2
    AMAZING = 3

    _names = { NONE: "No skills",
               GOOD: "Good Luck",
               GREAT: "Great Luck",
               AMAZING: "Amazing Luck" }


class CarvingSkill(EnumBase):
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


class CriticalEye(EnumBase):
    NONE = 0
    ONE = 1
    TWO = 2
    THREE = 3
    GOD = 4

    _names = { NONE: "",
               ONE: "Critical Eye +1",
               TWO: "Critical Eye +2",
               THREE: "Critical Eye +3",
               GOD: "Critical God" }

    _modifier = { NONE: 0,
                  ONE: 10,
                  TWO: 15,
                  THREE: 20,
                  GOD: 30 }

    _modifier_mhw = { 0: 0,
                      1: 5,
                      2: 10,
                      3: 15,
                      4: 20,
                      5: 25,
                      6: 30,
                      7: 40 }

    @classmethod
    def affinity_modifier(cls, skill):
        return cls._modifier[skill]

    @classmethod
    def modified(cls, skill, affinity):
        return affinity + cls.affinity_modifier(skill)

    @classmethod
    def name(cls, enum_value):
        return cls._names.get(enum_value, "CE +" + str(enum_value))


class AttackUp(EnumBase):
    NONE = 0
    SMALL = 1
    MEDIUM = 2
    LARGE = 3
    XLARGE = 4

    _names = { NONE: "",
               SMALL: "Attack Up (S)",
               MEDIUM: "Attack Up (M)",
               LARGE: "Attack Up (L)",
               XLARGE: "Attack Up (XL)" }

    _modifier = { NONE: 0,
                  SMALL: 10,
                  MEDIUM: 15,
                  LARGE: 20,
                  XLARGE: 25 }

    @classmethod
    def true_attack_modifier(cls, skill):
        return cls._modifier[skill]

    @classmethod
    def modified(cls, skill, true_attack):
        return true_attack + cls.true_attack_modifier(skill)


class ElementAttackUp(EnumBase):
    NONE = 0
    ONE = 1
    TWO = 2
    THREE = 3
    ELEMENT = 4

    _names = { NONE: "",
               ONE: "(element) Atk +1",
               TWO: "(element) Atk +2",
               THREE: "(element) Atk +3",
               ELEMENT: "Element Atk Up" }


    @classmethod
    def modified(cls, skill, element):
        if skill == cls.NONE:
            return element
        elif skill in (cls.ONE, cls.TWO, cls.THREE):
            element = element * (1 + .05 * skill)
            if skill == cls.ONE:
                element += 40
            elif skill == cls.TWO:
                element += 60
            elif skill == cls.THREE:
                element += 90
        elif skill == cls.ELEMENT:
            element *= 1.1
        else:
            raise ValueError("Unknown element skill %s" % skill)
        return element
