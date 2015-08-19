"""
Shared utility classes and functions.
"""

import codecs


ELEMENTS = """
    Fire
    Water
    Thunder
    Ice
    Dragon
    Poison
    Paralysis
    Sleep
    Blastblight
""".split()


WEAPON_TYPES = [
    "Great Sword",
    "Long Sword",
    "Sword and Shield",
    "Dual Blades",
    "Hammer",
    "Hunting Horn",
    "Lance",
    "Gunlance",
    "Switch Axe",
    "Charge Blade",
    "Insect Glaive",
    "Light Bowgun",
    "Heavy Bowgun",
    "Bow",
]


WTYPE_ABBR = dict(
    GS="Great Sword",
    LS="Long Sword",
    SS="Sword and Shield",
    SNS="Sword and Shield",
    DB="Dual Blades",
    HH="Hunting Horn",
    LA="Lance",
    GL="Gunlance",
    SA="Switch Axe",
    CB="Charge Blade",
    IG="Insect Glave",
    LBG="Light Bowgun",
    HBG="Heavy Bowgun"
)


class EnumBase(object):
    _names = dict()

    @classmethod
    def name(cls, enum_value):
        return cls._names[enum_value]


def get_utf8_writer(writer):
    return codecs.getwriter("utf8")(writer)
