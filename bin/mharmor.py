#!/usr/bin/env python

import sys
import argparse
import difflib

import _pathfix

from mhapi.db import MHDB
from mhapi.model import get_decoration_values
from mhapi.util import get_utf8_writer


def parse_args(argv):
    parser = argparse.ArgumentParser(description=
        "Find armor with the specified skills and sort by"
        " (max points, defense). Takes into account native points"
        " and slots that fit decorations for the first skill."
    )
    parser.add_argument("-g", "--gunner", action="store_true",
                        default=False,
                        help="search for gunner instead of blademaster")
    parser.add_argument("-d", "--min-defense", type=int,
                        help="Only include armors with min defense")
    parser.add_argument("-t", "--type",
                        help="Head, Body, Arms, Waist, or Legs",
                        type=str_title)
    parser.add_argument("-r", "--resist",
                        help="fire, water, thunder, ice, or dragon."
                             " Show and use as secondary sort key instead of"
                             " defense",
                        type=str_lower)
    parser.add_argument("skills", nargs="+",
                        help="One or more armor skills to search for",
                        type=canonical_skill_name)

    return parser.parse_args(argv)


def find_armors(args):
    db = MHDB()

    skills = {}
    skill_ids = [] # preserve arg order
    decorations = {}

    skill_tree_names = []
    skill_tree_id_map = {}
    skill_trees = db.get_skill_trees()
    for tree in skill_trees:
        skill_tree_names.append(tree.name)
        skill_tree_id_map[tree.name] = tree.id

    for i, skill_name in enumerate(args.skills):
        sid = skill_tree_id_map.get(skill_name)
        if sid is None:
            matches = difflib.get_close_matches(skill_name, skill_tree_names,
                                                1, 0.5)
            if matches:
                print "Fuzzy Match:", matches[0]
                sid = skill_tree_id_map.get(matches[0])
                skill_name = matches[0]
                args.skills[i] = skill_name
        if sid is None:
            raise ValueError("Skill '%s' not found" % skill_name)
        skills[skill_name] = sid
        skill_ids.append(sid)
        #print skill_name, sid
        ds = db.get_decorations_by_skills([sid])
        for d in ds:
            d.set_skills(db.get_item_skills(d.id))
        decoration_values = get_decoration_values(sid, ds)[1]
        decorations[sid] = (ds, decoration_values)
        print "%s[%s]:" % (skill_name, sid), ", ".join(d.name for d in ds), \
              decoration_values

    htype = "Gunner" if args.gunner else "Blade"

    armors = db.get_armors_by_skills(skill_ids, htype)

    skill_totals = {}
    for a in armors:
        skills = db.get_item_skills(a.id)
        if not skills:
            print "Error getting skills for '%s' (%d)" % (a.name, a.id)
            sys.exit(1)
        a.set_skills(skills)
        # calculate total using decorations for first skill only. This
        # works great if all skill have same slot values; if not it's
        # very messy to figure out what is 'best'
        total = 0
        first = True
        for sid in skill_ids:
            if first:
                dv = decorations[sid][1]
                first = False
            else:
                dv = []
            total += a.skill(sid, dv)
        skill_totals[a.id] = total

    def sort_key(a):
        if args.resist:
            return (skill_totals[a.id], a[args.resist + "_res"], a.defense)
        else:
            return (skill_totals[a.id], a.defense)

    armors.sort(key=sort_key, reverse=True)

    for a in armors:
        if args.min_defense and a.defense < args.min_defense:
            continue
        if args.type and a.slot != args.type:
            continue
        total = skill_totals[a.id]
        print skill_totals[a.id], a.one_line_u(),
        if args.resist:
            print args.resist.title(), a[args.resist + "_res"]
        else:
            print
        print "  ", a.one_line_skills_u(args.skills)


def str_lower(x):
    return str(x).lower()


def str_title(x):
    return str(x).title()


_SKILL_NAME_SPECIAL = dict(
    steadyhand="SteadyHand",
    freeelemnt="FreeElemnt",
    punishdraw="PunishDraw",
    fastcharge="FastCharge",
    ko="KO",
    lastingpwr="LastingPwr",
    thunderatk="ThunderAtk",
    thunderres="ThunderRes",
    teamplayer="TeamPlayer",
    teamleader="TeamLeader",
    speedsetup="SpeedSetup",
    critelemnt="CritElement",
    critstatus="CritStatus",
    lighteater="LightEater",
    powereater="PowerEater"
)

def canonical_skill_name(skill_name):
    skill_name_lc = skill_name.lower()
    skill_name_lc_nospace = "".join(skill_name_lc.split(" "))
    if skill_name_lc_nospace in _SKILL_NAME_SPECIAL:
        return _SKILL_NAME_SPECIAL[skill_name_lc_nospace]
    else:
        return skill_name_lc.title()


if __name__ == '__main__':
    args = parse_args(None)

    sys.stdout = get_utf8_writer(sys.stdout)
    find_armors(args)
