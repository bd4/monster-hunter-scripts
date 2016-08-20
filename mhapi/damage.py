
from collections import defaultdict
import json
import difflib
import re
import math

from mhapi import skills
from mhapi.model import SharpnessLevel, _break_find


WEAKPART_WEIGHT = 0.5


def floor(x):
    return int(math.floor(x))


def raw_damage(true_raw, sharpness, affinity, monster_hitbox, motion):
    """
    Calculate raw damage to a monster part with the given true raw,
    sharpness, monster raw weakness, and weapon motion value.
    """
    return floor(true_raw
                 * SharpnessLevel.raw_modifier(sharpness)
                 * (1 + (affinity / 400.0))
                 * motion / 100.0
                 * monster_hitbox / 100.0)


def element_damage(raw_element, sharpness, monster_ehitbox):
    """
    Calculate elemental damage to a monster part with the given elemental
    attack, the given sharpness, and the given monster elemental weakness.
    Note that this is independent of the motion value of the attack.
    """
    return floor(raw_element
                 * SharpnessLevel.element_modifier(sharpness)
                 * monster_ehitbox / 100.0)


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
    def __init__(self, weapon_row, monster_row, monster_damage, motion,
                 sharp_plus=False, breakable_parts=None,
                 attack_skill=skills.AttackUp.NONE,
                 critical_eye_skill=skills.CriticalEye.NONE,
                 element_skill=skills.ElementAttackUp.NONE,
                 awaken=False, artillery_level=0, limit_parts=None,
                 frenzy_bonus=0, blunt_power=False, is_true_attack=False):
        self.weapon = weapon_row
        self.monster = monster_row
        self.monster_damage = monster_damage
        self.motion = motion
        self.sharp_plus = sharp_plus
        self.breakable_parts = breakable_parts
        self.attack_skill = attack_skill
        self.critical_eye_skill = critical_eye_skill
        self.element_skill = element_skill
        self.awaken = awaken
        self.artillery_level = artillery_level
        self.blunt_power = blunt_power
        self.is_true_attack = is_true_attack
        self.limit_parts = limit_parts
        # 15 normaly for overcoming the virus, 30 with frenzy res skill
        assert frenzy_bonus in (0, 15, 30)
        self.frenzy_bonus = frenzy_bonus
        self.chaotic = False

        self.damage_map = defaultdict(PartDamage)
        self.average = 0
        self.weakness_weighted = 0
        self.best_weighted = 0
        self.break_weighted = 0

        # map of part -> (map of burst_level -> (raw, ele, burst))
        self.cb_phial_damage = defaultdict(dict)

        self.weapon_type = self.weapon["wtype"]
        if is_true_attack:
            self.true_raw = self.weapon["attack"]
        else:
            self.true_raw = (self.weapon["attack"]
                             / WeaponType.multiplier(self.weapon_type))
        if sharp_plus == 1:
            self.sharpness = self.weapon.sharpness_plus.max
        elif sharp_plus == 2:
            self.sharpness = self.weapon.sharpness_plus2.max
        else:
            self.sharpness = self.weapon.sharpness.max
        #print "sharpness=", self.sharpness
        if self.weapon["affinity"]:
            if (isinstance(self.weapon["affinity"], basestring)
            and "/" in self.weapon["affinity"]):
                self.chaotic = True
                # Handle chaotic gore affinity, e.g. -35/10. This means that
                # 35% of the time it does a negative critical (75% damage)
                # and 10% of the time does a positive critical (125%
                # damage). If frenzied (overcome virus which lasts 45
                # seconds), the negative affinity becomes positive
                # instead (35 + 10 = 45 in the example).
                self.affinity = sum(
                                 abs(int(x)) if self.frenzy_bonus else int(x)
                                 for x in self.weapon["affinity"].split("/"))
            else:
                self.affinity = int(self.weapon["affinity"])
        else:
            self.affinity = 0
        self.affinity += self.frenzy_bonus
        self.damage_type = WeaponType.damage_type(self.weapon_type)
        self.etype = self.weapon["element"]
        self.eattack = self.weapon["element_attack"]
        self.etype2 = self.weapon["element_2"]
        self.eattack2 = self.weapon["element_2_attack"]
        if not self.etype and self.awaken:
            self.etype = self.weapon.awaken
            self.eattack = self.weapon.awaken_attack

        if self.eattack:
            self.eattack = int(self.eattack)
        else:
            self.eattack = 0
        if self.eattack2:
            self.eattack2 = int(self.eattack2)
        else:
            self.eattack2 = 0

        if not self.is_true_attack and self.eattack:
            self.eattack /= 10
            if self.eattack2:
                self.eattack2 /= 10

        self.true_raw = skills.AttackUp.modified(attack_skill,
                                                 self.true_raw)
        self.affinity = skills.CriticalEye.modified(critical_eye_skill,
                                                    self.affinity)
        self.eattack  = skills.ElementAttackUp.modified(element_skill,
                                                        self.eattack)
        self.eattack2 = skills.ElementAttackUp.modified(element_skill,
                                                        self.eattack2)

        if self.blunt_power:
            if self.sharpness in (SharpnessLevel.RED, SharpnessLevel.ORANGE):
                self.true_raw += 30
            elif self.sharpness == SharpnessLevel.YELLOW:
                self.true_raw += 25
            elif self.sharpness == SharpnessLevel.GREEN:
                self.true_raw += 15

        self.parts = []
        self.break_count = 0

        self.averages = dict(
            uniform=0,
            raw=0,
            element=0,
            weakpart_raw=0,
            weakpart_element=0,
        )
        self.max_raw_part = (None, -1)
        self.max_element_part = (None, -1)
        self._calculate_damage()

    @property
    def attack(self):
        if self.is_true_attack:
            return self.true_raw
        return self.true_raw * WeaponType.multiplier(self.weapon_type)

    def _calculate_damage(self):
        for row in self.monster_damage._rows:
            # TODO: refactor to take advantage of new model
            part = row["body_part"]
            alt = None
            m = re.match(r"([^(]+) \(([^)]+)\)", part)
            if m:
                part = m.group(1)
                alt = m.group(2)

            if self.limit_parts is not None and part not in self.limit_parts:
                continue

            if row["cut"] == -1:
                continue

            hitbox = 0
            hitbox_cut = int(row["cut"])
            hitbox_impact = int(row["impact"])
            if self.damage_type == WeaponType.CUT:
                hitbox = hitbox_cut
            elif self.damage_type == WeaponType.IMPACT:
                hitbox = hitbox_impact
            elif self.damage_type == WeaponType.MIXED:
                # Info from /u/ShadyFigure, see
                # https://www.reddit.com/r/MonsterHunter/comments/3fr2u0/124th_weekly_stupid_question_thread/cts3hz8?context=3
                hitbox = max(hitbox_cut, hitbox_impact * .72)

            raw = raw_damage(self.true_raw, self.sharpness, self.affinity,
                             hitbox, self.motion)

            element = 0
            ehitbox = 0
            if self.etype in "Fire Water Ice Thunder Dragon".split():
                ehitbox = int(row[str(self.etype.lower())])
                element = element_damage(self.eattack, self.sharpness, ehitbox)
                if self.etype2:
                    # handle dual blades double element/status
                    element = element / 2.0
                    if self.etype2 in "Fire Water Ice Thunder Dragon".split():
                        ehitbox2 = int(row[str(self.etype2.lower())])
                        element2 = element_damage(self.eattack2,
                                                  self.sharpness, ehitbox2)
                        element += element2 / 2.0

            part_damage = self.damage_map[part]
            part_damage.set_damage(raw, element, hitbox, ehitbox, state=alt)
            if not part_damage.part:
                part_damage.part = part
            if alt is None:
                if (self.breakable_parts
                and _break_find(part, self.monster_damage.parts.keys(),
                                self.breakable_parts)):
                    part_damage.breakable = True
                if hitbox > self.max_raw_part[1]:
                    self.max_raw_part = (part, hitbox)
                if ehitbox > self.max_element_part[1]:
                    self.max_element_part = (part, ehitbox)

        for part in self.damage_map.keys():
            if None not in self.damage_map[part].states:
                #print "Failed to parse part:", part
                del self.damage_map[part]

        for part, d in self.damage_map.iteritems():
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
        self._calculate_cb_phial_damage()

    def _calculate_cb_phial_damage(self):
        if self.weapon_type != "Charge Blade":
            return
        if self.weapon.phial == "Impact":
            fn = cb_impact_phial_damage
        else:
            fn = cb_element_phial_damage
        for part in self.parts:
            part_damage = self.damage_map[part]
            hitbox = part_damage.hitbox
            ehitbox = part_damage.ehitbox
            for level in (0, 1, 2, 3, 5):
                damage_tuple = fn(self.true_raw, self.eattack, self.sharpness,
                                  self.affinity, hitbox, ehitbox, level,
                                  shield_charged=True,
                                  artillery_level=self.artillery_level)
                self.cb_phial_damage[part][level] = damage_tuple

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
        if len(self.parts) == 1:
            other_weight = 0
            weak_weight = 1
        else:
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
        if len(self.parts) == 1:
            other_weight = 0
            weak_weight = 1
        else:
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
            avg = self.average_break(break_weight)
            if self.rage_diff():
                return (self.average_rage(rage_weight) + avg) / 2.0
            return avg
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


def cb_impact_phial_damage(true_raw, element, sharpness, affinity,
                           monster_hitbox, monster_ehitbox,
                           burst_level, artillery_level=0,
                           shield_charged=False):
    """
    @burst_level: 0 for shield thrust, 1 for side chop, 2 for double swing,
                  3 for AED, 5 for super AED w/ 5 phials
    @artillery_level: 1 for Novice, 2 for God or Novice + Felyne Bombardier

    See
    https://www.reddit.com/r/MonsterHunter/comments/391a5i/mh4u_charge_blade_phial_damage/

    Note this contradicts data from the other link, but this is more recent.
    """
    motions = _cb_get_motions(burst_level, shield_charged)
    if burst_level == 5:
        multiplier = 0.33
    elif burst_level == 3:
        multiplier = 0.1
    else:
        multiplier = 0.05

    if artillery_level == 1:
        multiplier *= 1.3
    elif artillery_level == 2:
        multiplier *= 1.4
    elif artillery_level != 0:
        raise ValueError("artillery_level must be 0, 1 (Novice), or 2 (God)")

    if shield_charged and burst_level != 5:
        multiplier *= 1.3

    if shield_charged and burst_level == 0:
        # Shield Thrust gets one blast if shield is charged
        burst_level = 1

    # burst damage is fixed, doesn't depend on monster hitbox
    burst_dmg = true_raw * multiplier * burst_level
    raw_dmg = sum([raw_damage(true_raw, sharpness, affinity, monster_hitbox,
                              motion)
                   for motion in motions])
    ele_dmg = (element_damage(element, sharpness, monster_ehitbox)
               * len(motions))
    return (raw_dmg, ele_dmg, burst_dmg)


def cb_element_phial_damage(true_raw, element, sharpness, affinity,
                            monster_hitbox, monster_ehitbox,
                            burst_level, artillery_level=0,
                            shield_charged=False):
    motions = _cb_get_motions(burst_level, shield_charged)

    if burst_level == 5:
        multiplier = 4.5 * 3
    elif burst_level == 3:
        multiplier = 4.5
    else:
        multiplier = 3

    if shield_charged and burst_level != 5:
        multiplier *= 1.35

    if shield_charged and burst_level == 0:
        # Shield Thrust gets one blast if shield is charged
        burst_level = 1

    burst_dmg = (element / 10.0 * multiplier * burst_level
                 * monster_ehitbox / 100.0)
    raw_dmg = sum([raw_damage(true_raw, sharpness, affinity, monster_hitbox,
                              motion)
                   for motion in motions])
    ele_dmg = (element_damage(element, sharpness, monster_ehitbox)
               * len(motions))
    return (raw_dmg, ele_dmg, burst_dmg)


def _cb_get_motions(burst_level, shield_charged):
    # See https://www.reddit.com/r/MonsterHunter/comments/2ue8qw/charge_blade_attack_motion_values/
    if burst_level == 0:
        # Shield Thrust
        motions = [8, 12]
    elif burst_level == 1:
        # Burst Side Chop
        motions = [31] if shield_charged else [26]
    elif burst_level == 2:
        # Double Side Swing
        motions = [21, 96] if shield_charged else [18, 80]
    elif burst_level == 3:
        # AED or Super Burst
        motions = [108] if shield_charged else [90]
    elif burst_level == 5:
        # super AED or Ultra Burst, 5 phials filled
        # Note: w/o phials it's [17, 90], but that is very rarely used
        motions = [25, 99, 100]
    else:
        raise ValueError("burst_level must be 0, 1, 2, 3, or 5 (Super AED)")
    return motions
