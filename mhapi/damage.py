
from collections import defaultdict
import json
import difflib
import re


WEAKPART_WEIGHT = 0.5


def raw_damage(true_raw, sharpness, affinity, monster_hitbox, motion):
    """
    Calculate raw damage to a monster part with the given true raw,
    sharpness, monster raw weakness, and weapon motion value.
    """
    return (true_raw
            * Sharpness.raw_modifier(sharpness)
            * (1 + (affinity / 400.0))
            * motion / 100.0
            * monster_hitbox / 100.0)


def element_damage(element, sharpness, monster_ehitbox):
    """
    Calculate elemental damage to a monster part with the given elemental
    attack, the given sharpness, and the given monster elemental weakness.
    Note that this is independent of the motion value of the attack.
    """
    return (element / 10.0
            * Sharpness.element_modifier(sharpness)
            * monster_ehitbox / 100.0)


class Sharpness(object):
    """
    Enumeration for weapon sharpness.
    """

    RED = 0
    ORANGE = 1
    YELLOW = 2
    GREEN = 3
    BLUE = 4
    WHITE = 5
    PURPLE = 6

    ALL = range(0, PURPLE + 1)

    _modifier = {
        RED:    (0.50, 0.25),
        ORANGE: (0.75, 0.50),
        YELLOW: (1.00, 0.75),
        GREEN:  (1.05, 1.00),
        BLUE:   (1.20, 1.06),
        WHITE:  (1.32, 1.12),
        PURPLE: (1.44, 1.20),
    }

    @classmethod
    def raw_modifier(cls, sharpness):
        return cls._modifier[sharpness][0]

    @classmethod
    def element_modifier(cls, sharpness):
        return cls._modifier[sharpness][1]


class MotionType(object):
    CUT = "cut"
    IMPACT = "impact"
    FIXED = "fixed"


class MotionValue(object):
    def __init__(self, name, types, powers):
        self.name = name
        self.types = types
        self.powers = powers
        self.average = sum(self.powers) / len(self.powers)


class WeaponTypeMotionValues(object):
    def __init__(self, weapon_type, motion_data):
        self.weapon_type = weapon_type
        self.motion_values = dict()
        for d in motion_data:
            name = d["name"]
            self.motion_values[name] = MotionValue(name, d["type"], d["power"])

        self.average = (sum(mv.average
                            for mv in self.motion_values.itervalues())
                        / len(self))

    def __len__(self):
        return len(self.motion_values)

    def keys(self):
        return self.motion_values.keys()

    def __getitem__(self, key):
        return self.motion_values[key]


class MotionValueDB(object):
    def __init__(self, json_path):
        with open(json_path) as f:
            self._raw_data = json.load(f)

        self.motion_values_map = dict()

        for d in self._raw_data:
            wtype = d["name"]
            if wtype == "Sword":
                wtype = "Sword and Shield"
            self.motion_values_map[wtype] = WeaponTypeMotionValues(wtype,
                                                              d["motions"])

    def __getitem__(self, weapon_type):
        return self.motion_values_map[weapon_type]

    def keys(self):
        return self.motion_values_map.keys()

    def __len__(self):
        return len(self.motion_values_map)


class WeaponType(object):
    """
    Enumeration for weapon types.
    """
    SWITCH_AXE = "Switch Axe"
    HAMMER = "Hammer"
    HUNTING_HORN = "Hunting Horn"
    GREAT_SWORD = "Great Sword"
    CHARGE_BLADE = "Charge Blade"
    LONG_SWORD = "Long Sword"
    INSECT_GLAIVE = "Insect Glaive"
    LANCE = "Lance"
    GUNLANCE = "Gunlance"
    HEAVY_BOWGUN = "Heavy Bowgun"
    SWORD_AND_SHIELD = "Sword and Shield"
    DUAL_BLADES = "Dual Blades"
    LIGHT_BOWGUN = "Light Bowgun"
    BOW = "Bow"

    IMPACT = "impact"
    CUT = "cut"
    SHOT = "shot"
    MIXED = "cut/impact"

    _multiplier = {
        "Switch Axe": 5.4,
        "Hammer": 5.2,
        "Hunting Horn": 5.2,
        "Great Sword": 4.8,
        "Charge Blade": 3.6,
        "Long Sword": 3.3,
        "Insect Glaive": 3.1,
        "Lance": 2.3,
        "Gunlance": 2.3,
        "Heavy Bowgun": 1.5,
        "Sword and Shield": 1.4,
        "Dual Blades": 1.4,
        "Light Bowgun": 1.3,
        "Bow": 1.2,
    }

    @classmethod
    def all(cls):
        return cls._multiplier.keys()

    @classmethod
    def damage_type(cls, weapon_type):
        if weapon_type in (cls.HAMMER, cls.HUNTING_HORN):
            return cls.IMPACT
        elif weapon_type == cls.LANCE:
            return cls.MIXED
        elif weapon_type in (cls.LIGHT_BOWGUN, cls.HEAVY_BOWGUN, cls.BOW):
            return cls.SHOT
        else:
            return cls.CUT

    @classmethod
    def multiplier(cls, weapon_type):
        return cls._multiplier[weapon_type]


class WeaponMonsterDamage(object):
    """
    Class for calculating how much damage a weapon does to a monster.
    Does not include overall monster defense.
    """
    def __init__(self, weapon_row, monster_row, monster_damage_rows, motion,
                 sharp_plus=False, breakable_parts=None):
        self.weapon = weapon_row
        self.monster = monster_row
        self.monster_damage = monster_damage_rows
        self.motion = motion
        self.sharp_plus = sharp_plus
        self.breakable_parts = breakable_parts

        self.damage_map = defaultdict(PartDamage)
        self.average = 0
        self.weakness_weighted = 0
        self.best_weighted = 0
        self.break_weighted = 0

        self.weapon_type = self.weapon["wtype"]
        self.true_raw = (self.weapon["attack"]
                         / WeaponType.multiplier(self.weapon_type))
        sharp = _parse_sharpness(self.weapon)
        if sharp_plus:
            self.sharpness = sharp[1]
        else:
            self.sharpness = sharp[0]
        #print "sharpness=", self.sharpness
        self.affinity = int(self.weapon["affinity"] or 0)
        self.damage_type = WeaponType.damage_type(self.weapon_type)
        self.etype = self.weapon["element"]
        self.eattack = self.weapon["element_attack"]

        self.parts = []
        self.break_count = 0

        self.averages = dict(
            uniform=0,
            raw=0,
            element=0,
            weakpart_raw=0,
            weakpart_element=0,
        )
        self.max_raw_part = (None, 0)
        self.max_element_part = (None, 0)
        self._calculate_damage()

    def _calculate_damage(self):
        for row in self.monster_damage:
            part = row["body_part"]
            alt = None
            m = re.match(r"([^(]+) \(([^)]+)\)", part)
            if m:
                part = m.group(1)
                alt = m.group(2)
            #print part, alt
            hitbox = 0
            hitbox_cut = int(row["cut"])
            hitbox_impact = int(row["impact"])
            if self.damage_type == WeaponType.CUT:
                hitbox = hitbox_cut
            elif self.damage_type == WeaponType.IMPACT:
                hitbox = hitbox_impact
            elif self.damage_type == WeaponType.MIXED:
                hitbox = max(hitbox_cut, hitbox_impact)

            raw = raw_damage(self.true_raw, self.sharpness, self.affinity,
                             hitbox, self.motion)

            element = 0
            ehitbox = 0
            if self.etype in "Fire Water Ice Thunder Dragon".split():
                ehitbox = int(row[str(self.etype.lower())])
                element = element_damage(self.eattack, self.sharpness, ehitbox)

            part_damage = self.damage_map[part]
            part_damage.set_damage(raw, element, hitbox, ehitbox, state=alt)
            if not part_damage.part:
                part_damage.part = part
            if alt is None:
                if (self.breakable_parts
                and _part_find(part, self.breakable_parts)):
                    part_damage.breakable = True
                if hitbox > self.max_raw_part[1]:
                    self.max_raw_part = (part, hitbox)
                if ehitbox > self.max_element_part[1]:
                    self.max_element_part = (part, ehitbox)
        for d in self.damage_map.values():
            if d.is_breakable():
                self.break_count += 1
        self.parts = self.damage_map.keys()
        self.averages["uniform"] = self.uniform()
        self.averages["raw"] = self.weighted_raw()
        self.averages["element"] = self.weighted_element()
        self.averages["weakpart_raw"] = self.weakpart_weighted_raw()
        self.averages["weakpart_element"] = self.weakpart_weighted_element()
        self.averages["break_raw"] = self.break_weakpart_raw()
        self.averages["break_element"] = self.break_weakpart_element()
        self.averages["break_only"] = self.break_only()

    def uniform(self):
        average = 0.0
        for part, damage in self.damage_map.iteritems():
            average += damage.average()
        return average / len(self.damage_map)

    def weighted_raw(self):
        """
        Average damage weighted by non-broken raw hitbox. For each part the
        damage is averaged across broken vs non-broken, weighted by the
        default of broken for 25% of the hits.
        """
        average = 0.0
        total_hitbox = 0.0
        for part, damage in self.damage_map.iteritems():
            average += damage.average() * damage.hitbox
            total_hitbox += damage.hitbox
        if total_hitbox == 0:
            return 0
        return average / total_hitbox

    def weighted_element(self):
        """
        Average damage weighted by non-broken element hitbox.
        """
        average = 0.0
        total_ehitbox = 0.0
        for part, damage in self.damage_map.iteritems():
            average += damage.average() * damage.ehitbox
            total_ehitbox += damage.ehitbox
        if total_ehitbox == 0:
            return 0
        return average / total_ehitbox

    def weakpart_weighted_raw(self, weak_weight=WEAKPART_WEIGHT):
        other_weight = (1 - weak_weight) / (len(self.parts) - 1)
        average = 0
        for part, damage in self.damage_map.iteritems():
            if part == self.max_raw_part[0]:
                weight = weak_weight
            else:
                weight = other_weight
            average += damage.average() * weight
        return average

    def weakpart_weighted_element(self, weak_weight=WEAKPART_WEIGHT):
        other_weight = (1 - weak_weight) / (len(self.parts) - 1)
        average = 0
        for part, damage in self.damage_map.iteritems():
            if part == self.max_element_part[0]:
                weight = weak_weight
            else:
                weight = other_weight
            average += damage.average() * weight
        return average

    def break_weakpart_raw(self):
        """
        Split evenly among break parts and weakest raw part.
        """
        if not self.break_count:
            return 0
        average = 0.0
        count = self.break_count + 1
        for part, damage in self.damage_map.iteritems():
            if part == self.max_raw_part[0]:
                average += damage.average()
                if damage.is_breakable():
                    count -= 1
            elif damage.is_breakable():
                # for breaks, assume attack until broken, unless it's a
                # weak part and covered above
                average += damage.total
        return average / count

    def break_weakpart_element(self):
        """
        Split evenly among break parts and weakest element part.
        """
        if not self.break_count:
            return 0
        average = 0.0
        count = self.break_count + 1
        for part, damage in self.damage_map.iteritems():
            if part == self.max_element_part[0]:
                # If weakpart is also a break, assume continue attacking
                # even after broken
                average += damage.average()
                if damage.is_breakable():
                    count -= 1
            elif damage.is_breakable():
                # for breaks that aren't the weakpart, assume attack until
                # broken and then go back to weakpart
                average += damage.total
        return average / count

    def break_only(self):
        """
        Split evenly among break parts. If there are breaks that are weak
        to element but not to raw or vice versa, this will represent that
        when comparing weapons.
        """
        if not self.break_count:
            return 0
        average = 0.0
        for part, damage in self.damage_map.iteritems():
            if damage.is_breakable():
                # attack until broken, then move to next break
                average += damage.total
        return average / self.break_count

    def __getitem__(self, key):
        return self.damage_map[key]

    def keys(self):
        return self.parts


class PartDamageState(object):
    def __init__(self, raw, element, hitbox, ehitbox, state=None):
        self.raw = raw
        self.element = element
        self.hitbox = hitbox
        self.ehitbox = ehitbox
        self.state = state


class PartDamage(object):
    """
    Class to represent the damage done to a single hitzone on a monster,
    default state and alternate state (broken, enraged, etc).
    """
    def __init__(self):
        self.states = dict()
        self.part = None
        self.breakable = False

    @property
    def raw(self):
        return self.states[None].raw

    @property
    def element(self):
        return self.states[None].element

    @property
    def hitbox(self):
        return self.states[None].hitbox

    @property
    def ehitbox(self):
        return self.states[None].ehitbox

    @property
    def break_raw(self):
        if "Break Part" in self.states:
            return self.states["Break Part"].raw
        else:
            return self.raw

    @property
    def break_element(self):
        if "Break Part" in self.states:
            return self.states["Break Part"].element
        else:
            return self.element

    @property
    def rage_raw(self):
        if "Enraged" in self.states:
            return self.states["Enraged"].raw
        else:
            return self.raw

    @property
    def rage_element(self):
        if "Enraged" in self.states:
            return self.states["Enraged"].element
        else:
            return self.element

    @property
    def total(self):
        return self.raw + self.element

    @property
    def total_break(self):
        return self.break_raw + self.break_element

    @property
    def total_rage(self):
        return self.rage_raw + self.rage_element

    def break_diff(self):
        return self.total_break - self.total

    def rage_diff(self):
        return self.total_rage - self.total

    def is_breakable(self):
        # If the part has a hitbox with different damage in the break
        # rows from the db, or if it's explicitly marked as breakable
        # (done by checking hunt rewards for breaks).
        return self.break_diff() > 0 or self.breakable

    def average(self, break_weight=0.25, rage_weight=0.5):
        if self.break_diff():
            assert not self.rage_diff()
            return self.average_break(break_weight)
        else:
            return self.average_rage(rage_weight)

    def average_break(self, break_weight=0.25):
        return (self.total_break * break_weight
                + self.total * (1 - break_weight))

    def average_rage(self, rage_weight=0.5):
        return (self.total_rage * rage_weight
                + self.total * (1 - rage_weight))

    def set_damage(self, raw, element, hitbox, ehitbox, state=None):
        if state == "Without Hide":
            state = "Break Part"
        self.states[state] = PartDamageState(raw, element,
                                             hitbox, ehitbox, state)


def _part_find(part, breaks):
    if (part == "Wing" and "Wing" not in breaks
    and "Talon" in breaks):
        # for Teostra
        return "Talon"
    if (part == "Head" and "Head" not in breaks
    and "Horn" in breaks):
        # for Fatalis
        return "Horn"
    if (part == "Winglegs" and "Winglegs" not in breaks
    and "Wing Leg" in breaks):
        # for Gore
        return "Wing Leg"
    #print "part_find", part, breaks
    matches = difflib.get_close_matches(part, breaks, 1, 0.8)
    if matches:
        return matches[0]
    return None


def element_attack_up(value):
    return value * 1.1


def element_x_attack_up(value, level=1):
    value = value * (1 + .05 * level)
    if level == 1:
        value += 40
    elif level == 2:
        value += 60
    elif level == 3:
        value += 90
    else:
        raise ValueError("level must be 1, 2, or 3")


def _parse_sharpness(weapon_row):
    """
    Parse the sharpness field from a weapon row, to determine
    the max sharpness of the weapon with and without sharpness +1.
    """
    db_values = weapon_row["sharpness"].split(" ")
    sharpness = [Sharpness.RED, Sharpness.RED]
    for i, db_value in enumerate(db_values):
        values = [int(s) for s in db_value.split(".")]
        for s in Sharpness.ALL:
            if values[s] > 0:
                sharpness[i] = s
    return sharpness
