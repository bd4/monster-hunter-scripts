#!/usr/bin/env python

import sys
import argparse
import shlex
import copy

import _pathfix

from mhapi.db import MHDB, MHDBX
from mhapi.damage import MotionValueDB, WeaponMonsterDamage
from mhapi.model import SharpnessLevel, Weapon
from mhapi import skills
from mhapi.util import ELEMENTS, WEAPON_TYPES, WTYPE_ABBR


def weapon_match_tuple(arg):
    parts = arg.split(",")
    if len(parts) == 1:
        wtype = parts[0]
        element = None
    elif len(parts) == 2:
        wtype = parts[0]
        element = parts[1]
    else:
        raise ValueError("Bad arg, use 'weapon_type,element_or_status'")
    wtype = get_wtype_match(wtype)
    if element is not None:
        element = get_element_match(element)
    return (wtype, element)


def _make_db_sharpness_string(level_string):
    #print "level string", level_string
    level_value = SharpnessLevel.__dict__[level_string.upper()]
    #print "level value", level_value
    values = []
    for i in xrange(SharpnessLevel.PURPLE+1):
        if i <= level_value:
            values.append("1")
        else:
            values.append("0")
    #print "sharp values %r" % values
    return " ".join([".".join(values)] * 2)


def weapon_stats_tuple(arg):
    parts = arg.split(",")
    #print "parts %r" % parts
    if len(parts) < 4:
        print "not enough parts"
        raise ValueError("Bad arg, use 'name,weapon_type,sharpness,raw'")
    weapon = {}
    weapon["name"] = parts[0]
    weapon["wtype"] = get_wtype_match(parts[1])
    weapon["attack"] = int(parts[2])
    weapon["affinity"] = parts[3]
    weapon["sharpness"] = _make_db_sharpness_string(parts[4])
    if len(parts) == 5:
        weapon["element"] = None
        weapon["element_attack"] = None
    if len(parts) == 7:
        weapon["element"] = get_element_match(parts[5])
        weapon["element_attack"] = int(parts[6])
    else:
        #print "bad part number"
        raise ValueError("Bad arg, use 'name,weapon_type,sharpness,raw'")
    weapon["element_2"] = None
    weapon["awaken"] = None
    weapon["element_2_attack"] = None
    weapon["_id"] = -1
    #print "making model"
    return Weapon(weapon)


def get_wtype_match(term):
    abbr_result = WTYPE_ABBR.get(term.upper())
    if abbr_result is not None:
        return abbr_result
    term = term.title()
    for wtype in WEAPON_TYPES:
        if wtype.startswith(term):
            return wtype
    raise ValueError("Unknown weapon type: %s" % term)


def get_element_match(term):
    term = term.title()
    for element in ELEMENTS:
        if element.startswith(term):
            return element
    if term.lower() == "raw":
        return "Raw"
    raise ValueError("Unknown element or status: %s" % term)


def parse_weapon_arg(arg, base_args):
    """
    Return (name, skill_args), where skill_args is None if not specified.
    """
    parts = arg.split(";")
    if len(parts) == 1:
        return parts[0], None
    elif len(parts) == 2:
        parser = argparse.ArgumentParser(description="Parse per-weapon skills")
        _add_skill_args(parser)
        skill_args = shlex.split(parts[1])
        base_copy = copy.copy(base_args)
        return parts[0], parser.parse_args(skill_args, namespace=base_copy)
    else:
        raise ValueError("invalid weapon-skills arg: " + arg)



def get_skill_names(args):
    return ["Sharpness +%d" % args.sharpness_plus
                if args.sharpness_plus else "",
            "Awaken" if args.awaken else "",
            skills.AttackUp.name(args.attack_up),
            skills.CriticalEye.name(args.critical_eye),
            skills.ElementAttackUp.name(args.element_up),
            "Blunt Power" if args.blunt_power else ""]


def percent_change(a, b):
    if a == 0:
        return b
    return (100.0 * (b-a) / a)


def _add_skill_args(parser):
    parser.add_argument("-s", "--sharpness-plus", type=int,
                        default=False,
                        help="add Sharpness +1 or +2 skill, default off")
    parser.add_argument("-f", "--awaken", action="store_true",
                        default=False,
                        help="add Awaken (FreeElemnt), default off")
    parser.add_argument("-a", "--attack-up",
                        type=int, choices=range(0, 5), default=0,
                        help="1-4 for AuS, M, L, XL")
    parser.add_argument("-c", "--critical-eye",
                        type=int, choices=range(0, 5), default=0,
                        help="1-4 for CE+1, +2, +3 and Critical God")
    parser.add_argument("-e", "--element-up",
                        type=int, choices=range(0, 5), default=0,
                        help="1-4 for (element) Atk +1, +2, +3 and"
                             " Element Attack Up")
    parser.add_argument("-t", "--artillery",
                        type=int, choices=[0,1,2], default=0,
                        help="0-2 for no artillery, novice, god")
    parser.add_argument("-z", "--frenzy",
                        help="With virus affinity boost, must be either"
                            +" 15 (normal) or 30 (with Frenzy Res skill)",
                        type=int, choices=[0, 15, 30], default=0)
    parser.add_argument("-b", "--blunt-power", action="store_true",
                        default=False,
                        help="Blunt Power (MHX), default off")


def parse_args(argv):
    parser = argparse.ArgumentParser(description=
        "Calculate damage to monster from different weapons of the"
        " same class. The average motion value for the weapon class"
        " is used for raw damage calculations, to get a rough idea of"
        " the relative damage from raw vs element when comparing."
    )
    _add_skill_args(parser)
    parser.add_argument("-p", "--parts",
                        help="Limit analysis to specified parts"
                            +" (comma separated list)")
    parser.add_argument("-l", "--phial",
                        help="Show CB phial damage at the sepcified level"
                            +" (1, 2, 3, 5=ultra) instead of normal motion"
                            +" values.",
                        type=int, choices=[0, 1, 2, 3, 5], default=0)
    parser.add_argument("-d", "--diff", action="store_true", default=False,
                        help="Show percent difference in damage to each part"
                            +" from first weapon in list.")
    parser.add_argument("-x", "--monster-hunter-cross", action="store_true",
                        default=False,
                        help="Assume weapons are true attack, use MHX values")
    parser.add_argument("-m", "--match", nargs="*",
                    help="WEAPON_TYPE,ELEMENT_OR_STATUS_OR_RAW"
                        +" Include all matching weapons in their final form."
                        +" Supports abbreviations like LS for Long Sword"
                        +" and Para for Paralysis or Blast for Blastblight."
                        +" If just WEAPON_TYPE is given, include all final"
                        +" weapons of that type."
                        +" Examples: 'Great Sword,Raw'"
                        +" 'Sword and Shield,Para'"
                        +" 'HH,Blast' 'Hammer'",
                        type=weapon_match_tuple, default=[])
    parser.add_argument("-w", "--weapon-custom", nargs="*",
                    help="NAME,WEAPON_TYPE,TRUE_RAW,AFFINITY,SHARPNESS"
                        +"ELEMENT_TYPE,ELEMENT_ATTACK"
                        +" Add weapon based on stats."
                        +" Examples: 'DinoSnS,SnS,190,0,Blue,Fire,30'"
                        +" 'AkantorHam,Hammer,240,25,Green'",
                        type=weapon_stats_tuple, default=[])
    parser.add_argument("monster",
                        help="Full name of monster")
    parser.add_argument("weapon", nargs="*",
                        help="One or more weapons of same class to compare,"
                             " full names")

    return parser.parse_args(argv)


def print_sorted_phial_damage(names, damage_map_base, weapon_damage_map, parts,
                              level):
    def cb_levelN(weapon):
        return avg_phial(weapon_damage_map[weapon], level=level)

    def avg_phial(wd, level=5):
        total = 0.0
        for part in parts:
            total += sum(wd.cb_phial_damage[part][level])
        return total / len(parts)

    names_sorted = list(names)
    names_sorted.sort(key=cb_levelN, reverse=True)

    _print_headers(parts, damage_map_base)

    for name in names_sorted:
        print "%-20s:" % name,
        damage_map = weapon_damage_map[name]
        print "%0.2f" % avg_phial(damage_map, level=level),
        for part in parts:
            part_damage = damage_map[part]
            #print "%0.2f" % sum(damage_map.cb_phial_damage[part][level]),
            print "%0.2f:%0.2f:%0.2f" % damage_map.cb_phial_damage[part][level],
        print


def _print_headers(parts, damage_map_base):
    print
    avg_hitbox = (sum(damage_map_base[part].hitbox for part in parts)
                  / float(len(parts)))
    cols = ["%s (%d)" % (part, damage_map_base[part].hitbox)
            for part in parts]
    cols = ["%s (%d)" % ("Avg", avg_hitbox)] + cols
    print " | ".join(cols)


def print_sorted_damage(names, damage_map_base, weapon_damage_map, parts):
    def uniform_average(weapon):
        return weapon_damage_map[weapon].averages["uniform"]

    names_sorted = list(names)
    names_sorted.sort(key=uniform_average, reverse=True)

    _print_headers(parts, damage_map_base)

    #print
    #print " | ".join(["%-15s" % "Avg"] + parts)
    #print " | ".join(["   "] + [str(damage_map_base[part].hitbox)
    #                            for part in parts])

    for name in names_sorted:
        print "%-20s:" % name,
        damage_map = weapon_damage_map[name]
        print "%0.2f" % damage_map.averages["uniform"],
        for part in parts:
            part_damage = damage_map[part]
            print "% 2d" % part_damage.average(),
        print


def print_damage_percent_diff(names, damage_map_base, weapon_damage_map, parts):
    for part in parts:
        tdiffs = [percent_change(
                    damage_map_base[part].total,
                    weapon_damage_map[w][part].total
                  )
                  for w in names[1:]]
        ediffs = [percent_change(
                    damage_map_base[part].element,
                    weapon_damage_map[w][part].element
                  )
                  for w in names[1:]]
        bdiffs = [percent_change(
                    damage_map_base[part].break_diff(),
                    weapon_damage_map[w][part].break_diff()
                  )
                  for w in names[1:]]
        tdiff_s = ",".join("%+0.1f%%" % i for i in tdiffs)
        ediff_s = ",".join("%+0.1f%%" % i for i in ediffs)
        bdiff_s = ",".join("%+0.1f%%" % i for i in bdiffs)
        damage = damage_map_base[part]
        print "%22s%s h%02d %0.2f (%s) h%02d %0.2f (%s) %+0.2f (%s)" \
            % (part, "*" if damage.is_breakable() else " ",
               damage.hitbox,
               damage.total,
               tdiff_s,
               damage.ehitbox,
               damage.element,
               ediff_s,
               damage.break_diff(),
               bdiff_s)
        if weapon_type == "Charge Blade":
            for level in (0, 1, 2, 3, 5):
                print " " * 20, level,
                for wname in names:
                    wd = weapon_damage_map[wname]
                    damage = wd.cb_phial_damage[part][level]
                    print "(%0.f, %0.f, %0.f);" % damage,
                print

    print "            --------------------"

    for avg_type in "uniform raw weakpart_raw element weakpart_element break_raw break_element break_only".split():
        base = damage_map_base.averages[avg_type]
        diffs = [percent_change(
                    base,
                    weapon_damage_map[w].averages[avg_type]
                 )
                 for w in names[1:]]

        diff_s = ",".join("%+0.1f%%" % i for i in diffs)

        print "%22s %0.2f (%s)" % (avg_type, base, diff_s)


if __name__ == '__main__':
    args = parse_args(None)

    if args.monster_hunter_cross:
        db = MHDBX()
    else:
        db = MHDB()
    motiondb = MotionValueDB(_pathfix.motion_values_path)

    monster = db.get_monster_by_name(args.monster)
    if not monster:
        raise ValueError("Monster '%s' not found" % args.monster)
    monster_damage = db.get_monster_damage(monster.id)

    weapons = []
    weapon_type = None
    names_set = set()

    skill_args_map = {}

    for name_skills in args.weapon:
        name, skill_args = parse_weapon_arg(name_skills, args)
        weapon = db.get_weapon_by_name(name)
        if not weapon:
            raise ValueError("Weapon '%s' not found" % name)
        names_set.add(name)
        weapons.append(weapon)
        if skill_args:
            skill_args_map[name] = skill_args

    for match_tuple in args.match:
        # TODO: better validation
        wtype, element = match_tuple
        match_weapons = db.get_weapons_by_query(wtype=wtype, element=element,
                                                final=1)
        for w in match_weapons:
            # skip weapons already explicitly names in arg list.
            # Especially useful in diff mode.
            if w.name in names_set:
                continue
            weapons.append(w)
            names_set.add(w.name)

    if args.weapon_custom:
        weapons.extend(args.weapon_custom)

    if not weapons:
        print "Err: no matching weapons"
        sys.exit(1)

    names = [w.name for w in weapons]

    monster_breaks = db.get_monster_breaks(monster.id)
    weapon_type = weapons[0]["wtype"]
    if args.phial and weapon_type != "Charge Blade":
        print "ERROR: phial option is only supported for Charge Blade"
        sys.exit(1)
    motion = motiondb[weapon_type].average
    print "Weapon Type: %s" % weapon_type
    print "Average Motion: %0.1f" % motion
    print "Monster Breaks: %s" % ", ".join(monster_breaks)
    skill_names = get_skill_names(args)
    print "Common Skills:", ", ".join(skill for skill in skill_names if skill)

    if args.parts:
        limit_parts = args.parts.split(",")
    else:
        limit_parts = None

    weapon_damage_map = dict()
    for row in weapons:
        name = row["name"]
        row_type = row["wtype"]
        if row_type != weapon_type:
            raise ValueError("Weapon '%s' is different type" % name)
        try:
            skill_args = skill_args_map.get(name, args)
            wd = WeaponMonsterDamage(row,
                                     monster, monster_damage,
                                     motion, skill_args.sharpness_plus,
                                     monster_breaks,
                                     attack_skill=skill_args.attack_up,
                                     critical_eye_skill=skill_args.critical_eye,
                                     element_skill=skill_args.element_up,
                                     awaken=skill_args.awaken,
                                     artillery_level=skill_args.artillery,
                                     limit_parts=args.parts,
                                     frenzy_bonus=skill_args.frenzy,
                                     is_true_attack=args.monster_hunter_cross,
                                     blunt_power=skill_args.blunt_power)
            print "%-20s: %4.0f %2.0f%%" % (name, wd.attack, wd.affinity),
            if wd.etype:
                if wd.etype2:
                    print "(%4.0f %s, %4.0f %s)" \
                        % (wd.eattack, wd.etype, wd.eattack2, wd.etype2),
                else:
                    print "(%4.0f %s)" % (wd.eattack, wd.etype),
            print SharpnessLevel.name(wd.sharpness),
            if skill_args != args:
                print "{%s}" % ",".join(sn
                                        for sn in get_skill_names(skill_args)
                                        if sn)
            else:
                print
            weapon_damage_map[name] = wd
        except ValueError as e:
            print str(e)
            sys.exit(1)

    damage_map_base = weapon_damage_map[names[0]]

    if limit_parts:
        parts = limit_parts
    else:
        parts = damage_map_base.parts

    if args.diff:
        print_damage_percent_diff(names, damage_map_base,
                                  weapon_damage_map, parts)
    elif args.phial:
        print_sorted_phial_damage(names, damage_map_base,
                                  weapon_damage_map, parts,
                                  level=args.phial)
    else:
        print_sorted_damage(names, damage_map_base,
                            weapon_damage_map, parts)

