#!/usr/bin/env python

import sys
import argparse

import _pathfix

from mhapi.db import MHDB
from mhapi.damage import MotionValueDB, WeaponMonsterDamage
from mhapi.model import SharpnessLevel
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


def percent_change(a, b):
    if a == 0:
        return b
    return (100.0 * (b-a) / a)


def parse_args(argv):
    parser = argparse.ArgumentParser(description=
        "Calculate damage to monster from different weapons of the"
        " same class. The average motion value for the weapon class"
        " is used for raw damage calculations, to get a rough idea of"
        " the relative damage from raw vs element when comparing."
    )
    parser.add_argument("-s", "--sharpness-plus-one", action="store_true",
                        default=False,
                        help="add Sharpness +1 skill, default off")
    parser.add_argument("-f", "--awaken", action="store_true",
                        default=False,
                        help="add Awaken (FreeElement), default off")
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
    parser.add_argument("-p", "--parts",
                        help="Limit analysis to specified parts"
                            +" (comma separated list)")
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
    parser.add_argument("monster",
                        help="Full name of monster")
    parser.add_argument("weapon", nargs="*",
                        help="One or more weapons of same class to compare,"
                             " full names")

    return parser.parse_args(argv)


if __name__ == '__main__':
    args = parse_args(None)

    db = MHDB(_pathfix.db_path)
    motiondb = MotionValueDB(_pathfix.motion_values_path)

    monster = db.get_monster_by_name(args.monster)
    if not monster:
        raise ValueError("Monster '%s' not found" % args.monster)
    monster_damage = db.get_monster_damage(monster.id)

    weapons = []
    weapon_type = None

    for match_tuple in args.match:
        # TODO: better validation
        wtype, element = match_tuple
        match_weapons = db.get_weapons_by_query(wtype=wtype, element=element,
                                                final=1)
        weapons.extend(match_weapons)

    for name in args.weapon:
        weapon = db.get_weapon_by_name(name)
        if not weapon:
            raise ValueError("Weapon '%s' not found" % name)
        weapons.append(weapon)

    if not weapons:
        print "Err: no matching weapons"
        sys.exit(1)

    names = [w.name for w in weapons]

    monster_breaks = db.get_monster_breaks(monster.id)
    weapon_type = weapons[0]["wtype"]
    motion = motiondb[weapon_type].average
    print "Weapon Type: %s" % weapon_type
    print "Average Motion: %0.1f" % motion
    print "Monster Breaks: %s" % ", ".join(monster_breaks)
    skill_names = ["Sharpness +1" if args.sharpness_plus_one else "",
                   "Awaken" if args.awaken else "",
                   skills.AttackUp.name(args.attack_up),
                   skills.CriticalEye.name(args.critical_eye),
                   skills.ElementAttackUp.name(args.element_up)]
    print "Skills:", ", ".join(skill for skill in skill_names if skill)

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
            wd = WeaponMonsterDamage(row,
                                     monster, monster_damage,
                                     motion, args.sharpness_plus_one,
                                     monster_breaks,
                                     attack_skill=args.attack_up,
                                     critical_eye_skill=args.critical_eye,
                                     element_skill=args.element_up,
                                     awaken=args.awaken,
                                     artillery_level=args.artillery,
                                     limit_parts=args.parts)
            print "%-20s: %4.0f %2.0f%%" % (name, wd.attack, wd.affinity),
            if wd.etype:
                if wd.etype2:
                    print "(%4.0f %s, %4.0f %s)" \
                        % (wd.eattack, wd.etype, wd.eattack2, wd.etype2),
                else:
                    print "(%4.0f %s)" % (wd.eattack, wd.etype),
            print SharpnessLevel.name(wd.sharpness)
            weapon_damage_map[name] = wd
        except ValueError as e:
            print str(e)
            sys.exit(1)

    damage_map_base = weapon_damage_map[weapons[0].name]

    if limit_parts:
        parts = limit_parts
    else:
        parts = damage_map_base.parts

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
