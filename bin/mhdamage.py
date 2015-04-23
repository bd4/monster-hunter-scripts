#!/usr/bin/env python

import sys
import argparse

import _pathfix

from mhapi.db import MHDB
from mhapi.damage import MotionValueDB, WeaponMonsterDamage
from mhapi.model import SharpnessLevel
from mhapi import skills


def percent_change(a, b):
    if a == 0:
        return b
    return (100.0 * (b-a) / a)


def parse_args(argv):
    parser = argparse.ArgumentParser(
        "Calculate damage to monster from different weapons of the"
        " same class"
    )
    parser.add_argument("-s", "--sharpness-plus-one", action="store_true",
                        default=False,
                        help="add Sharpness +1 skill, default off")
    parser.add_argument("-f", "--awaken", action="store_true",
                        default=False,
                        help="add Awaken (FreeElement), default off")
    parser.add_argument("-a", "--attack-up",
                        type=int, choices=xrange(0, 5), default=0,
                        help="1-4 for AuS, M, L, XL")
    parser.add_argument("-c", "--critical-eye",
                        type=int, choices=xrange(0, 5), default=0,
                        help="1-4 for CE+1, +2, +3 and Critical God")
    parser.add_argument("-e", "--element-up",
                        type=int, choices=xrange(0, 5), default=0,
                        help="1-4 for (element) Atk +1, +2, +3 and"
                             " Element Attack Up")
    parser.add_argument("monster",
                        help="Full name of monster")
    parser.add_argument("weapon", nargs="+",
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
    for name in args.weapon:
        weapon = db.get_weapon_by_name(name)
        if not weapon:
            raise ValueError("Weapon '%s' not found" % name)
        weapons.append(weapon)

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
    weapon_damage_map = dict()
    for name, row in zip(args.weapon, weapons):
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
                                     awaken=args.awaken)
            print "%-20s: %4.0f %2.0f%%" % (name, wd.attack, wd.affinity),
            if wd.etype:
                print "(%4.0f %s)" % (wd.eattack, wd.etype),
            print SharpnessLevel.name(wd.sharpness)
            weapon_damage_map[name] = wd
        except ValueError as e:
            print str(e)
            sys.exit(1)

    damage_map_base = weapon_damage_map[args.weapon[0]]
    parts = damage_map_base.parts

    for part in parts:
        tdiffs = [percent_change(
                    damage_map_base[part].total,
                    weapon_damage_map[w][part].total
                  )
                  for w in args.weapon[1:]]
        ediffs = [percent_change(
                    damage_map_base[part].element,
                    weapon_damage_map[w][part].element
                  )
                  for w in args.weapon[1:]]
        bdiffs = [percent_change(
                    damage_map_base[part].break_diff(),
                    weapon_damage_map[w][part].break_diff()
                  )
                  for w in args.weapon[1:]]
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

    print "            --------------------"

    for avg_type in "uniform raw weakpart_raw element weakpart_element break_raw break_element break_only".split():
        base = damage_map_base.averages[avg_type]
        diffs = [percent_change(
                    base,
                    weapon_damage_map[w].averages[avg_type]
                 )
                 for w in args.weapon[1:]]

        diff_s = ",".join("%+0.1f%%" % i for i in diffs)

        print "%22s %0.2f (%s)" % (avg_type, base, diff_s)
