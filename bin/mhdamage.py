#!/usr/bin/env python3

import sys
import argparse
import shlex
import copy
import codecs
import os
import os.path
from collections import defaultdict

import _pathfix


from prettytable import prettytable
import colorama
from colorama import Fore

from mhapi.db import MHDB, MHDBX
from mhapi.damage import MotionValueDB, WeaponMonsterDamage
from mhapi.damage import WeaponType, WeaponTypeMotionValues
from mhapi.model import SharpnessLevel, Weapon, ItemStars
from mhapi import skills
from mhapi.util import ELEMENTS, WEAPON_TYPES, WTYPE_ABBR, DAMAGE_TYPES


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


ANY = object()
def parse_stars(arg):
    if arg is None:
        return None
    arg = arg.lower()
    if arg in ("*", "any"):
        return ANY
    if arg in ("none", ""):
        return None
    return int(arg)


def quest_level_tuple(arg):
    parts = arg.split(",")
    while len(parts) < 4:
        parts.append(None)
    return [parse_stars(p) for p in parts]


def crit_boost(level):
    assert(level >= 0 and level <= 3)
    return 25 + 5 * level


def wex_affinity(level):
    if level == 0:
        return 0
    elif level == 1:
        return 15
    elif level == 2:
        return 30
    elif level == 3:
        return 50
    assert(False)


def _make_db_sharpness_string(level_string):
    #print "level string", level_string
    level_value = SharpnessLevel.__dict__[level_string.upper()]
    #print "level value", level_value
    values = []
    for i in range(SharpnessLevel.PURPLE+1):
        if i <= level_value:
            values.append("1")
        else:
            values.append("0")
    #print "sharp values %r" % values
    return " ".join([".".join(values)] * 2)


def weapon_stats_tuple(arg):
    parts = arg.split(",")
    #print("parts %r" % parts)
    if len(parts) < 4:
        print("not enough parts")
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
            "Blunt Power" if args.blunt_power else "",
            "CritBoost +%d" % args.crit_boost
                if args.crit_boost else ""]


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
                        type=int, choices=list(range(0, 5)), default=0,
                        help="1-4 for AuS, M, L, XL")
    parser.add_argument("-c", "--critical-eye",
                        type=int, choices=list(range(0, 8)), default=0,
                        help="1-4(7) for CE+1, +2, +3 and Critical God")
    parser.add_argument("-e", "--element-up",
                        type=int, choices=list(range(0, 6)), default=0,
                        help="1-5 for (element) Atk +1, +2, +3 and"
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
    parser.add_argument("-o", "--motion", type=int,
                        help="Use specified motion value instead of weapon "
                            +"average")
    parser.add_argument("--match-motion", type=str,
                        help="Use average of matching motion names")
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
    parser.add_argument("-g", "--monster-hunter-gen", action="store_true",
                        default=False,
                        help="Assume weapons are true attack, use MHGen values")
    parser.add_argument("--mhw", "--monster-hunter-world", action="store_true",
                        default=False,
                        help="Adjusted attack, use MHWorld values")
    parser.add_argument("--mh3u", "--monster-hunter-3u", action="store_true",
                        default=False,
                        help="Monster hunter 3 Ultimate")
    parser.add_argument("--mhr", "--monster-hunter-rise", action="store_true",
                        default=False,
                        help="True attack, use MHRise values")
    parser.add_argument("--anti-species", action="store_true",
                        default=False,
                        help="Add 5% anti-species true raw boost for rampage 2+ slots")
    parser.add_argument("--crit-boost", "--cb", type=int, default=0,
                        help="critical boost skill level", choices=[0, 1, 2, 3])
    parser.add_argument("--weakness-exploit", "--wex", type=int, default=0,
                        help="weakness exploit skill level", choices=[0, 1, 2, 3])
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
                        type=weapon_match_tuple, default=[],
                        action="append")
    parser.add_argument("-w", "--weapon-custom", nargs="*",
                    help="NAME,WEAPON_TYPE,TRUE_RAW,AFFINITY,SHARPNESS"
                        +"ELEMENT_TYPE,ELEMENT_ATTACK"
                        +" Add weapon based on stats."
                        +" Examples: 'DinoSnS,SnS,190,0,Blue,Fire,30'"
                        +" 'AkantorHam,Hammer,240,25,Green'",
                        type=weapon_stats_tuple, default=[],
                        action="append")
    parser.add_argument("-q", "--quest-level",
                        help="village,guild[,permit[,arena]]",
                        type=quest_level_tuple)
    parser.add_argument("-r", "--rarity",
                        help="include weapons of given type with max rarity",
                        type=int, nargs="?")
    parser.add_argument("--html-out",
                        help="Write table of values as HTML and save to path")
    parser.add_argument("--html-site",
                        help="Write entire site of all monster & quest levels")
    parser.add_argument("-n", "--monster", help="Full name of monster")
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
        print("%-20s:" % name, end=' ')
        damage_map = weapon_damage_map[name]
        print("%0.2f" % avg_phial(damage_map, level=level), end=' ')
        for part in parts:
            part_damage = damage_map[part]
            #print "%0.2f" % sum(damage_map.cb_phial_damage[part][level]),
            print("%0.2f:%0.2f:%0.2f" % damage_map.cb_phial_damage[part][level], end=' ')
        print()


def _print_headers(parts, damage_map_base, maxlen=4):
    print()
    cols = _get_part_headers(parts, damage_map_base, maxlen=maxlen)
    print(" | ".join(cols))


def _get_part_headers(parts, damage_map_base, maxlen=4):
    avg_hitbox = (sum(damage_map_base[part].hitbox for part in parts)
                  / float(len(parts)))
    cols = ["%s (%d)" % (part[:maxlen], damage_map_base[part].hitbox)
            for part in parts]
    cols = ["%s (%d)" % ("Avg", avg_hitbox)] + cols
    return cols


def write_damage_html(path, monster, monster_damage, quest_level, names,
                      damage_map_base, weapon_damage_map, parts,
                      part_max_damage, monster_breaks, monster_stars):
    print(path)
    def uniform_average(weapon):
        return weapon_damage_map[weapon].averages["uniform"]

    names_sorted = list(names)
    names_sorted.sort(key=uniform_average, reverse=True)

    from mako.lookup import TemplateLookup
    from mako.runtime import Context

    tlookup = TemplateLookup(directories=["templates/damage"],
                             output_encoding="utf-8",
                             input_encoding="utf-8")
    damage_template = tlookup.get_template("/monster_damage.html")

    wtype = damage_map_base.weapon.wtype
    weapon_damage_type = WeaponType.damage_type(wtype)
    damage_types = list(DAMAGE_TYPES)

    weapon_types = list(WEAPON_TYPES)
    weapon_types.remove("Bow")
    weapon_types.remove("Light Bowgun")
    weapon_types.remove("Heavy Bowgun")

    with codecs.open(path, "w", "utf8") as f:
        template_args = dict(
            monster=monster.name,
            monster_damage=monster_damage,
            damage_types=DAMAGE_TYPES,
            weapon_types=weapon_types,
            weapon_type=wtype,
            weapon_damage_type=weapon_damage_type,
            village_stars=quest_level[0],
            guild_stars=quest_level[1],
            part_names=parts,
            part_max_damage=part_max_damage,
            weapon_names=names_sorted,
            weapon_damage_map=weapon_damage_map,
            monster_breaks=set(monster_breaks),
            monster_stars=monster_stars
        )
        ctx = Context(f, **template_args)
        damage_template.render_context(ctx)


def write_damage_html_by_rarity(path, rarity, monster, monster_damage, names,
                                damage_map_base, weapon_damage_map, parts,
                                part_max_damage):
    print(path)
    def uniform_average(weapon):
        return weapon_damage_map[weapon].averages["uniform"]

    names_sorted = list(names)
    names_sorted.sort(key=uniform_average, reverse=True)

    from mako.lookup import TemplateLookup
    from mako.runtime import Context

    tlookup = TemplateLookup(directories=["templates/damage"],
                             output_encoding="utf-8",
                             input_encoding="utf-8")
    damage_template = tlookup.get_template("/monster_damage_by_rarity.html")

    wtype = damage_map_base.weapon.wtype
    weapon_damage_type = WeaponType.damage_type(wtype)
    damage_types = list(DAMAGE_TYPES)

    weapon_types = list(WEAPON_TYPES)
    weapon_types.remove("Bow")
    weapon_types.remove("Light Bowgun")
    weapon_types.remove("Heavy Bowgun")

    with codecs.open(path, "w", "utf8") as f:
        template_args = dict(
            monster=monster.name,
            monster_damage=monster_damage,
            rarity=rarity,
            damage_types=DAMAGE_TYPES,
            weapon_types=weapon_types,
            weapon_type=wtype,
            weapon_damage_type=weapon_damage_type,
            part_names=parts,
            part_max_damage=part_max_damage,
            weapon_names=names_sorted,
            weapon_damage_map=weapon_damage_map,
        )
        ctx = Context(f, **template_args)
        damage_template.render_context(ctx)


def print_sorted_damage(names, damage_map_base, weapon_damage_map, parts):
    def uniform_average(weapon):
        wd_list = weapon_damage_map[weapon]
        return sum(wd.averages["uniform"] for wd in wd_list) / len(wd_list)

    names_sorted = list(names)
    names_sorted.sort(key=uniform_average, reverse=True)

    maxlen = 4
    headers = ["Name", "Avg"] + [p[:maxlen] for p in parts]
    avg_hitbox = (sum(damage_map_base[part].hitbox for part in parts)
                  / float(len(parts)))
    first_row = (["", avg_hitbox] +
                 [damage_map_base[part].hitbox for part in parts])

    t = prettytable.PrettyTable(border=True,
                                field_names=headers,
                                hrules=prettytable.HEADER,
                                vrules=prettytable.NONE,
                                float_format="5.1",
                                padding_width=1)
    t.align["Name"] = "l"
    for c in headers[1:]:
        t.align[c] = "r"

    t.add_row(first_row)

    #_print_headers(parts, damage_map_base)

    #print
    #print " | ".join(["%-15s" % "Avg"] + parts)
    #print " | ".join(["   "] + [str(damage_map_base[part].hitbox)
    #                            for part in parts])

    """
    for name in names_sorted:
        print("%-20s:" % name, end=' ')
        average = uniform_average(name)
        damage_maps = weapon_damage_map[name]
        print("%0.2f" % average, end=' ')
        for part in parts:
            # for wd in damage_maps:
            #    print(name, wd.motion.name, part, wd[part].average())
            part_avg = sum(wd[part].average() for wd in damage_maps) / len(damage_maps)
            print("% 2d" % part_avg, end=' ')
        print()
    """
    for name in names_sorted:
        average = uniform_average(name)
        damage_maps = weapon_damage_map[name]
        row = [name, average]
        for part in parts:
            # for wd in damage_maps:
            #    print(name, wd.motion.name, part, wd[part].average())
            part_avg = sum(wd[part].average() for wd in damage_maps) / len(damage_maps)
            row.append(round(part_avg))
        t.add_row(row)

    print(t)

    # this is super buggy
    if False and len(names) > 1:
        w1 = weapon_damage_map[names_sorted[0]]
        w2 = weapon_damage_map[names_sorted[1]]
        m, ratio = w1.compare_break_even(w2)
        print()
        print("Comparison of '%s' and '%s'" % (
            names_sorted[0], names_sorted[1]))
        print("Hitbox ratio:", m, "%0.2f" % ratio)

        if w1.etype:
            re_ratios = w1.get_raw_element_ratios()
        else:
            re_ratios = w2.get_raw_element_ratios()
        for line in re_ratios:
            line = list(line)
            if m*line[3] > m*ratio:
                line.append(names_sorted[0])
            else:
                line.append(names_sorted[1])
            # (part, raw, element, ratio)
            print("%-22s   %02d  %02d  %0.2f  %s" % tuple(line))


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
        print("%22s%s h%02d %0.2f (%s) h%02d %0.2f (%s) %+0.2f (%s)" \
            % (part, "*" if damage.is_breakable() else " ",
               damage.hitbox,
               damage.total,
               tdiff_s,
               damage.ehitbox,
               damage.element,
               ediff_s,
               damage.break_diff(),
               bdiff_s))
        if weapon_type == "Charge Blade":
            for level in (0, 1, 2, 3, 5):
                print(" " * 20, level, end=' ')
                for wname in names:
                    wd = weapon_damage_map[wname]
                    damage = wd.cb_phial_damage[part][level]
                    print("(%0.f, %0.f, %0.f);" % damage, end=' ')
                print()

    print("            --------------------")

    for avg_type in "uniform raw weakpart_raw element weakpart_element break_raw break_element break_only".split():
        base = damage_map_base.averages[avg_type]
        diffs = [percent_change(
                    base,
                    weapon_damage_map[w].averages[avg_type]
                 )
                 for w in names[1:]]

        diff_s = ",".join("%+0.1f%%" % i for i in diffs)

        print("%22s %0.2f (%s)" % (avg_type, base, diff_s))


def match_quest_level(match_level, weapon_level):
    #print match_level, weapon_level
    if match_level is ANY:
        return True
    if match_level is None:
        if weapon_level is not None:
            return False
        return True
    if weapon_level is None or weapon_level > match_level:
        return False
    return True


def run_comparison(args, db, motiondb, game_uses_true_raw, item_stars=None):
    monster = db.get_monster_by_name(args.monster)
    if not monster:
        raise ValueError("Monster '%s' not found" % args.monster)
    monster_damage = db.get_monster_damage(monster.id)

    if not monster_damage.is_valid():
        print("WARN: invalid damage data for monster '%s'" % args.monster)
        return

    if item_stars is None:
        item_stars = ItemStars(db)

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

    #print("args match", args.match)
    for match_tuple in args.match:
        # TODO: better validation
        if isinstance(match_tuple, list):
            # TODO: is this a bug in argparse!!!????
            match_tuple = match_tuple[0]
        wtype, element = match_tuple
        if args.quest_level or args.rarity:
            final=None
        else:
            final=1
        match_weapons = db.get_weapons_by_query(wtype=wtype, element=element,
                                                final=final)
        for w in match_weapons:
            # skip weapons already explicitly names in arg list.
            # Especially useful in diff mode.
            if w.name in names_set:
                continue
            weapons.append(w)
            names_set.add(w.name)

    if args.weapon_custom:
        weapons.extend([w[0] for w in args.weapon_custom])

    if not weapons:
        print("Err: no matching weapons")
        sys.exit(1)

    names = [w.name for w in weapons]

    monster_breaks = db.get_monster_breaks(monster.id)
    part_names = list(monster_damage.keys())

    for i in range(len(monster_breaks)):
        if monster_breaks[i] not in monster_damage:
            plural = monster_breaks[i] + "s"
            if plural in monster_damage:
                monster_breaks[i] = plural

    states = monster_damage.state_names()
    print("States:", states)
    print("Parts: ", part_names)
    print()

    hitbox_table_fields = [monster.name] + [p[:4] for p in part_names]
    t = prettytable.PrettyTable(border=True,
                                field_names=hitbox_table_fields,
                                hrules=prettytable.HEADER,
                                vrules=prettytable.NONE,
                                padding_width=0)
    t.align[monster.name] = "r"
    for c in hitbox_table_fields[1:]:
        t.align[c] = "r"

    for dtype in DAMAGE_TYPES:
        row = [dtype] + [d[dtype] for d in monster_damage.values()]
        t.add_row(row)
    print(t)
    print()

    weapon_type = weapons[0]["wtype"]
    if args.phial and weapon_type != "Charge Blade":
        print("ERROR: phial option is only supported for Charge Blade")
        sys.exit(1)
    motions = motiondb[weapon_type]
    print("Weapon Type: %s" % weapon_type)
    print("Average Motion: %0.1f" % motions.average)
    if args.motion:
        motions = WeaponTypeMotionValues(weapon_type, [
            dict(type=[0], name="Custom", power=[args.motion]),
        ])
        print("Specified Motion: %0.1f" % motions.average)
    if args.match_motion:
        motion_list = motions.get_matching_motions(args.match_motion)
        print("Matching Motions:")
        total_raw = 0
        total_ele_mod = 0
        for motion in motion_list:
            total_raw += motion.total
            total_ele_mod += sum(motion.ele_mod) / len(motion.ele_mod)
            print(" ", motion.name,
                  ",".join([str(pair) for pair in zip(motion.powers, motion.ele_mod)]))
        print(" ", "Average", "(" + str(total_raw/len(motion_list)) + ", "
              + str(total_ele_mod/len(motion_list)) + ")")
    else:
        motion_list = [motions.get_average_mv()]
    print("Monster Breaks: %s" % ", ".join(monster_breaks))
    skill_names = get_skill_names(args)
    print("Common Skills:", ", ".join(skill for skill in skill_names if skill))

    if args.parts:
        limit_parts = args.parts.split(",")
    else:
        limit_parts = None

    if args.quest_level:
        village, guild, permit, arena = args.quest_level
        print("Filter by Quest Levels:", args.quest_level)
        weapons2 = dict()
        for w in weapons:
            if "village_stars" in w:
                stars = dict(Village=w["village_stars"],
                             Guild=w["guild_stars"],
                             Permit=w["permit_stars"],
                             Arena=w["arena_stars"])
            else:
                stars = item_stars.get_weapon_stars(w)
            if (not match_quest_level(village, stars["Village"])
                    and not match_quest_level(guild, stars["Guild"])):
                continue
            if not match_quest_level(permit, stars["Permit"]):
                continue
            if not match_quest_level(arena, stars["Arena"]):
                continue
            weapons2[w.id] = w
        parent_ids = set(w.parent_id for w in weapons2.values())
        for wid in list(weapons2.keys()):
            if wid in parent_ids:
                del weapons2[wid]
        weapons = list(weapons2.values())
        names = [w.name for w in weapons]

    if args.rarity:
        print("Filter by max rarity:", args.rarity)
        weapons2 = dict()
        by_name = dict()
        for w in weapons:
            if w.rarity <= args.rarity:
                weapons2[w.id] = w
                by_name[w.name] = w
        # TODO: don't have parent ids for mhrise yet
        if False and args.mhr:
            # hack to remove most common dups
            for wname in list(by_name.keys()):
                if wname.endswith("+"):
                    base = wname[:-1]
                    suffix = "+"
                else:
                    parts = wname.rsplit(" ", maxsplit=1)
                    if len(parts) == 1:
                        continue
                    base, suffix = parts
                parent_name = None
                if suffix == "+" or base.endswith("+"):
                    parent_name = base.rstrip("+")
                elif suffix in ("II", "III", "VI", "VII"):
                    parent_name = wname[:-1]
                elif suffix == "IV":
                    parent_name = base + " III"
                elif suffix == "V":
                    parent_name = base + " IV"
                if parent_name:
                    print("parent", parent_name)
                    if parent_name in by_name:
                        del weapons2[by_name[parent_name].id]
        else:
            parent_ids = set(w.parent_id for w in weapons2.values())
            for wid in list(weapons2.keys()):
                if wid in parent_ids:
                    del weapons2[wid]
        weapons = list(weapons2.values())
        names = [w.name for w in weapons]

    part_max_damage = defaultdict(int)
    weapon_damage_map = dict()
    weapon_table = []
    col_names = ["Name", "EFR", "Atk", "Aff", "Ele",
                 "Shp", "Skills"]
    for row in weapons:
        name = row["name"]
        row_type = row["wtype"]
        if row_type != weapon_type:
            raise ValueError(
                    "Weapon '%s' is different type, got '%s' expected '%s'"
                    % (name, row_type, weapon_type))
        #print(name, row)
        try:
            skill_args = skill_args_map.get(name, args)
            wd_list = []
            for motion in motion_list:
                wd = WeaponMonsterDamage(row,
                                         monster, monster_damage, motion,
                                         skill_args.sharpness_plus,
                                         monster_breaks,
                                         attack_skill=skill_args.attack_up,
                                         critical_eye_skill=skill_args.critical_eye,
                                         element_skill=skill_args.element_up,
                                         awaken=skill_args.awaken,
                                         artillery_level=skill_args.artillery,
                                         limit_parts=args.parts,
                                         frenzy_bonus=skill_args.frenzy,
                                         is_true_attack=game_uses_true_raw,
                                         blunt_power=skill_args.blunt_power,
                                         anti_species=args.anti_species,
                                         crit_boost=crit_boost(args.crit_boost),
                                         wex_affinity=wex_affinity(args.weakness_exploit),
                                         game=db.game)
                wd_list.append(wd)
            wd = wd_list[0]
            estring = ""
            if wd.etype:
                if wd.etype2:
                    estring = ("% 4.0f %s, %4.0f %s" 
                        % (wd.eattack, wd.etype[:3], wd.eattack2, wd.etype2[:3]))
                else:
                    estring = ("% 4.0f %s" % (wd.eattack, wd.etype[:3]))
            sstring = "%s %2d" % (SharpnessLevel.name(wd.sharpness)[:3],
                                   wd.sharpness_points)
            data = dict(Name=name,
                        EFR=wd.efr,
                        Atk=wd.attack,
                        Aff=wd.affinity,
                        Ele=estring,
                        Shp=sstring,
                        Skills="")
            skill_names = []
            if wd.species_boost:
                skill_names.append("Anti-Species")
            if skill_args != args:
                skill_names.extend([sn for sn in get_skill_names(skill_args) if sn])
            if skill_names:
                data["Skills"] = ",".join(skill_names)
            weapon_table.append(data)
            for part in wd.parts:
                if wd[part].average() > part_max_damage[part]:
                    part_max_damage[part] = wd[part].average()
            weapon_damage_map[name] = wd_list
        except ValueError as e:
            print(str(e))
            sys.exit(1)

    weapon_table.sort(key=lambda d: d["EFR"], reverse=True)
    #print(tabulate(weapon_table, headers="keys"))
    t = prettytable.PrettyTable(border=True,
                                field_names=col_names,
                                float_format="5.1",
                                hrules=prettytable.HEADER,
                                vrules=prettytable.NONE)
    t.align["Name"] = "l"
    t.align["Aff"] = "r"
    for d in weapon_table:
        t.add_row([d[k] for k in col_names])
    print()
    print(t)
    print()

    damage_map_base = weapon_damage_map[names[0]][0]

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

    if args.html_out:
        if args.mhr:
            if not args.rarity:
                print("Error: --html-out with --mrh requires --rarity")
                sys.exit(1)
            write_damage_html_by_rarity(args.html_out, args.rarity,
                                        monster, monster_damage,
                                        names, damage_map_base,
                                        weapon_damage_map, parts,
                                        part_max_damage)
        else:
            if not args.quest_level:
                print("Error: --html-out requires quest level (-q)")
                sys.exit(1)
            monster_stars = item_stars.get_monster_stars(monster.id)
            write_damage_html(args.html_out, monster, monster_damage,
                              args.quest_level, names,
                              damage_map_base, weapon_damage_map, parts,
                              part_max_damage, monster_breaks,
                              monster_stars)


def write_html_site(args, db, motiondb, game_uses_true_raw):
    if db.game == "4u":
        village_max = 5
        guild_max = 2
    else:
        raise ValueError("Not implemented")

    monsters = db.get_monsters("Boss")
    monster_names = [monster.name for monster in monsters]
    weapon_types = db.get_weapon_types()

    item_stars = ItemStars(db)
    monster_stars = {}
    for monster in monsters:
        monster_stars[monster.id] = item_stars.get_monster_stars(monster.id)

    n = 0
    base_dir = args.html_site
    for monster in monsters:
        stars = monster_stars[monster.id]
        if stars["Village"] is None:
            vrange = [0]
        else:
            if stars["Village"] > 2:
                start = stars["Village"] - 1
            else:
                start = stars["Village"]
            vrange = list(range(start, 11))
            if start > 2:
                vrange = [0] + vrange
        if stars["Guild"] is None:
            grange = [0]
        else:
            if stars["Guild"] > 1:
                start = stars["Guild"] - 1
            else:
                start = stars["Guild"]
            grange = list(range(start, 11))
            if start > 1:
                grange = [0] + grange
        for v in vrange:
            for g in grange:
                if v == 0:
                    if g == 0:
                        continue
                    v = 1
                if g == 0:
                    g = 1
                quest_dir = "v{}g{}".format(v, g)
                quest_path = os.path.join(base_dir, monster.name, quest_dir)
                if not os.path.isdir(quest_path):
                    os.makedirs(quest_path)
                for wtype in weapon_types:
                    if "Bowgun" in wtype or wtype == "Bow":
                        continue
                    args.html_out = os.path.join(quest_path, wtype + ".html")
                    if os.path.isfile(args.html_out):
                        print(args.html_out, " exists, skipping")
                        continue
                    args.html_site = None
                    n += 1
                    args.monster = monster.name
                    args.quest_level = (v if v else 1, g if g else 1,
                                        None, None)
                    args.match = [(wtype, None)]
                    run_comparison(args, db, motiondb, game_uses_true_raw,
                                   item_stars=item_stars)
    print("n =", n)


def write_html_site_rise(args, db, motiondb, game_uses_true_raw=True):
    monsters = db.get_monsters()
    weapon_types = db.get_weapon_types()

    n = 0
    base_dir = args.html_site
    for monster in monsters:
        for rarity in range(1, 11):
            args.rarity = rarity
            rarity_dir = "r{}".format(rarity)
            mpath = os.path.join(base_dir, monster.name, rarity_dir)
            if not os.path.isdir(mpath):
                os.makedirs(mpath)
            for wtype in weapon_types:
                if "Bowgun" in wtype or wtype == "Bow":
                    continue
                args.html_out = os.path.join(mpath, wtype + ".html")
                if os.path.isfile(args.html_out):
                    print(args.html_out, " exists, skipping")
                    continue
                args.html_site = None
                n += 1
                args.monster = monster.name
                args.match = [(wtype, None)]
                print(rarity, wtype)
                run_comparison(args, db, motiondb, game_uses_true_raw)
    print("n =", n)


def main():
    args = parse_args(None)
    game = "4u"

    game_uses_true_raw = False
    if args.quest_level or args.html_site:
        comps = True
    else:
        comps = False

    if args.monster_hunter_cross:
        db = MHDBX()
        game_uses_true_raw = True
    elif args.monster_hunter_gen:
        db = MHDB(game="gu", include_item_components=comps)
        game_uses_true_raw = True
    elif args.mhw:
        db = MHDBX(game="mhw")
        game_uses_true_raw = False
        SharpnessLevel._modifier = SharpnessLevel._modifier_mhw
        skills.CriticalEye._modifier = skills.CriticalEye._modifier_mhw
        game = "mhw"
    elif args.mhr:
        db = MHDBX(game="mhr")
        game_uses_true_raw = True
        SharpnessLevel._modifier = SharpnessLevel._modifier_mhw
        skills.CriticalEye._modifier = skills.CriticalEye._modifier_mhw
        game = "mhr"
    elif args.mh3u:
        db = MHDB(game="3u", include_item_components=comps)
        game_uses_true_raw = False
        game = "3u"
    else:
        db = MHDB(game="4u", include_item_components=comps)

    game_motion_db_path = os.path.join(_pathfix.project_path, "db", game,
                                       "motion_values.json")
    if not os.path.exists(game_motion_db_path):
        game_motion_db_path = _pathfix.motion_values_path
    motiondb = MotionValueDB(game_motion_db_path)

    if args.html_site:
        if args.mhr:
            write_html_site_rise(args, db, motiondb, game_uses_true_raw)
        else:
            write_html_site(args, db, motiondb, game_uses_true_raw)
    else:
        run_comparison(args, db, motiondb, game_uses_true_raw)


if __name__ == '__main__':
    main()
