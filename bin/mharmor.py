#!/usr/bin/env python

import sys
import argparse
import codecs

import _pathfix

from mhapi.db import MHDB

def get_utf8_writer(writer):
    return codecs.getwriter("utf8")(writer)

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
                        help="Head, Body, Arms, Waist, or Legs")
    parser.add_argument("skills", nargs="+",
                        help="One or more armor skills to search for")

    return parser.parse_args(argv)


def find_armors(args):
    db = MHDB(_pathfix.db_path)

    skills = {}
    skill_ids = [] # preserve arg order
    decorations = {}
    for skill_name in args.skills:
        sid = db.get_skill_tree_id(skill_name)
        if sid is None:
            raise ValueError("Skill '%s' not found" % skill_name)
        skills[skill_name] = sid
        skill_ids.append(sid)
        #print skill_name, sid
        ds = db.get_decorations_by_skills([sid])
        for d in ds:
            d.set_skills(db.get_item_skills(d.id))
        decoration_values = get_decoration_values(sid, ds)
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
        # works great if all skill shave same slot values; if not it's
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

    armors.sort(key=lambda a: (skill_totals[a.id], a.defense), reverse=True)

    for a in armors:
        if args.min_defense and a.defense < args.min_defense:
            continue
        if args.type and a.slot != args.type:
            continue
        total = skill_totals[a.id]
        print a.id, skill_totals[a.id], a.one_line_u()
        print "  ", a.one_line_skills_u(args.skills)


def get_decoration_values(skill_id, decorations):
    # TODO: write script to compute this and shove innto skill_tree table
    values = [0, 0, 0]
    for d in decorations:
        assert d.num_slots is not None
        # some skills like Handicraft have multiple decorations with
        # same number of slots - use the best one
        new = d.skills[skill_id]
        current = values[d.num_slots-1]
        if new > current:
            values[d.num_slots-1] = new
    return values


if __name__ == '__main__':
    args = parse_args(None)

    sys.stdout = get_utf8_writer(sys.stdout)
    find_armors(args)
