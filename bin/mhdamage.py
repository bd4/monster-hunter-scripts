#!/usr/bin/env python

import sys
import os

import _pathfix

from mhapi.db import MHDB
from mhapi.damage import MotionValueDB, WeaponMonsterDamage


def percent_change(a, b):
    if a == 0:
        return b
    return (100.0 * (b-a) / a)


if __name__ == '__main__':
    if len(sys.argv) < 4:
        print "Usage: %s 'monster name' 'weapon name'+" % sys.argv[0]
        sys.exit(os.EX_USAGE)

    sharp_plus = bool(int(sys.argv[1]))
    monster_name = sys.argv[2]
    weapon_names = sys.argv[3:]

    db = MHDB(_pathfix.db_path)
    motiondb = MotionValueDB(_pathfix.motion_values_path)

    monster = db.get_monster_by_name(monster_name)
    if not monster:
        raise ValueError("Monster '%s' not found" % monster_name)
    monster_damage = db.get_monster_damage(monster["_id"])
    weapons = []
    for name in weapon_names:
        weapon = db.get_weapon_by_name(name)
        if not weapon:
            raise ValueError("Weapon '%s' not found" % name)
        weapons.append(weapon)

    monster_breaks = db.get_monster_breaks(monster["_id"])
    weapon_type = weapons[0]["wtype"]
    motion = motiondb[weapon_type].average
    print "Weapon Type: %s" % weapon_type
    print "Average Motion: %0.1f" % motion
    print "Monster Breaks: %s" % ", ".join(monster_breaks)
    weapon_damage_map = dict()
    for name, row in zip(weapon_names, weapons):
        row_type = row["wtype"]
        if row_type != weapon_type:
            raise ValueError("Weapon '%s' is different type" % name)
        try:
            weapon_damage_map[name] = WeaponMonsterDamage(row,
                                            monster, monster_damage,
                                            motion, sharp_plus,
                                            monster_breaks)
        except ValueError as e:
            print str(e)
            sys.exit(1)

    damage_map_base = weapon_damage_map[weapon_names[0]]
    parts = damage_map_base.parts

    for part in parts:
        tdiffs = [percent_change(
                    damage_map_base[part].total,
                    weapon_damage_map[w][part].total
                  )
                  for w in weapon_names[1:]]
        ediffs = [percent_change(
                    damage_map_base[part].element,
                    weapon_damage_map[w][part].element
                  )
                  for w in weapon_names[1:]]
        bdiffs = [percent_change(
                    damage_map_base[part].break_diff(),
                    weapon_damage_map[w][part].break_diff()
                  )
                  for w in weapon_names[1:]]
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
                 for w in weapon_names[1:]]

        diff_s = ",".join("%+0.1f%%" % i for i in diffs)

        print "%22s %0.2f (%s)" % (avg_type, base, diff_s)
