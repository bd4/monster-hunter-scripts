#!/usr/bin/env python

import sys
import argparse
import difflib
from itertools import product
from collections import defaultdict
import csv
import operator

import _pathfix

from mhapi.db import MHDB
from mhapi.model import get_decoration_values, Armor
from mhapi.util import get_utf8_writer
from mhapi.armor_builder import ArmorSet

HEAD, BODY, ARMS, WAIST, LEGS = 0, 1, 2, 3, 4

ATYPE_STRINGS = "Head Body Arms Waist Legs".split()


ThreeSlot = Armor(dict(_id=0, name="ThreeSlot", num_slots=3,
                       defense=1, max_defense=2))
ThreeSlot.skills = {}


def parse_args(argv):
    parser = argparse.ArgumentParser(description=
        "Find armor sets with the specified skills"
    )
    parser.add_argument("-g", "--gunner", action="store_true",
                        default=False,
                        help="search for gunner instead of blademaster")
    parser.add_argument("-d", "--min-defense", type=int,
                        help="Only include armors with min defense")
    parser.add_argument("-r", "--resist",
                        help="fire, water, thunder, ice, or dragon."
                             " Show and use as secondary sort key instead of"
                             " defense",
                        type=str_lower)
    parser.add_argument("skills", nargs="+",
                        help="One or more armor skill to search for",
                        type=canonical_skill_name)

    return parser.parse_args(argv)


def find_armor_sets(args, charms):
    db = MHDB(_pathfix.db_path, include_item_components=True)

    wanted_skills = {}
    wanted_stree_points = {}
    wanted_strees = {}
    stree_ids = [] # preserve arg order
    decorations = {}
    decoration_values_by_stree_name = {}

    skill_totals = {}

    stree_names = []
    stree_id_map = {}
    stree_map = {}
    strees = db.get_skill_trees()
    for tree in strees:
        stree_names.append(tree.name)
        stree_id_map[tree.name] = tree.id
        stree_map[tree.id] = tree

    skill_list = db.get_skills()
    skill_names = []
    skill_name_map = {}
    for s in skill_list:
        s.set_skill_tree(stree_map[s.skill_tree_id])
        skill_names.append(s.name)
        skill_name_map[s.name] = s

    for i, skill_name in enumerate(args.skills):
        s = skill_name_map.get(skill_name)
        if s is None:
            matches = difflib.get_close_matches(skill_name, skill_names,
                                                1, 0.5)
            if matches:
                print "Fuzzy Match:", matches[0]
                s = skill_name_map.get(matches[0])
                skill_name = matches[0]
                args.skills[i] = skill_name
        if s is None:
            raise ValueError("Skill '%s' not found" % skill_name)
        wanted_skills[skill_name] = s
        stree_id = s.skill_tree.id
        stree_name = s.skill_tree.name
        stree_ids.append(stree_id)
        wanted_strees[stree_name] = s.skill_tree
        wanted_stree_points[stree_name] = s.required_skill_tree_points
        #print skill_name, sid
        ds = db.get_decorations_by_skills([stree_id])
        ds = [d for d in ds if d.create_components]
        if ds:
            for d in ds:
                d.set_skills(db.get_item_skills(d.id))
            decoration_values = get_decoration_values(stree_id, ds)[1]
            decorations[stree_id] = (ds, decoration_values)
            decoration_values_by_stree_name[stree_name] = decoration_values
            print "%s[%s]:" % (skill_name, stree_id), \
                  ", ".join(d.name for d in ds), decoration_values
        else:
            print "%s[%s]:" % (skill_name, stree_id), \
                  "no craftable decorations"

    torso_up_stree_id = stree_id_map["Torso Up"]

    htype = "Gunner" if args.gunner else "Blade"

    armors = db.get_armors_by_skills(stree_ids, htype)
    armors_by_type = defaultdict(list)

    torso_up_armors = db.get_armors_by_skills([torso_up_stree_id], htype)
    armors.extend(torso_up_armors)
    torso_up_by_type = defaultdict(list)

    for a in armors:
        if args.min_defense and a.defense < args.min_defense:
            continue

        if a.gender == "Male":
            continue

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
        for sid in stree_ids:
            if first:
                dv = decorations[sid][1]
                first = False
            else:
                dv = []
            total += a.skill(sid, dv)
        skill_totals[a.id] = total
        armors_by_type[a.slot].append(a)
        if "Torso Up" in a.skills:
            if len(a.skills) != 2 or a.name.endswith(" of Rage"):
                print "ERROR: not Torso Up", a.name, a.skills
            else:
                torso_up_by_type[a.slot].append(a)

    def sort_key(a):
        if args.resist:
            return (skill_totals[a.id], a[args.resist + "_res"], a.defense)
        else:
            return (skill_totals[a.id], a.defense)

    for type_armors in armors_by_type.itervalues():
        #type_armors.append(ThreeSlot)
        type_armors.sort(key=sort_key, reverse=True)

    for atype, tup_armors in torso_up_by_type.iteritems():
        if not tup_armors:
            continue
        tup_armors.sort(key=sort_key, reverse=True)
        tup_armors[0].name = "Torso Up (%s)" % tup_armors[0].name
        #print atype, [a.name for a in tup_armors]

    for atype in ATYPE_STRINGS:
        subcats = get_armor_subcats(armors_by_type[atype], wanted_strees)
        #for k, avtups in subcats.iteritems():
        #    print k, [(av[0].name, av[0].num_slots, av[1]) for av in avtups]
        armors_by_type[atype] = [avtups[0][0]
                                 for avtups in subcats.itervalues()]

    desired_strees = set(wanted_strees.keys())
    sorted_strees = sorted(wanted_strees.keys())

    found = 0
    max_found = 1000
    atlist = [armors_by_type[atype] + torso_up_by_type[atype][:1]
              for atype in ATYPE_STRINGS]

    useful_charms = [
        charm for charm in charms
        if not desired_strees.isdisjoint(charm.positive_strees)
    ]

    useful_charms += [Charm(dict(slots=3, skill1=None, skill2=None,
                                 points1=0, points2=0))]
    atlist.append(useful_charms)

    counts = [len(at) for at in atlist]
    print "counts:", counts
    print "total:", reduce(operator.mul, counts, 1)
    print "charms:", "; ".join(str(c) for c in useful_charms)
    return

    asets = []
    for armors in product(*atlist):
        aset = ArmorSet(armors)
        #ds = aset.decorate(wanted_stree_points, decoration_values_by_stree_name)
        #if ds is None:
        #    continue
        asets.append(aset)
        if len(asets) >= max_found:
            break

    print "found:", len(asets)
    for aset in asets:
        print ",".join(a.name for a in aset.armors), \
              "Slots(%s)" % ",".join(str(aset.slots[i])
                                     for i in xrange(1, 4)), \
              ";".join("%s=%d" % (k, aset.skills[k]) for k in sorted_strees)


def get_armor_subcats(armor_list, wanted_strees):
    removed = defaultdict(list)
    wanted_stree_names = sorted(wanted_strees.keys())
    avalue_tups = []
    for i, armor in enumerate(armor_list):
        values = [armor.skills.get(s, 0)
                  for s in wanted_stree_names]
        avalue_tups.append((armor, values))
    subcat = defaultdict(list)
    def sort_key(a):
        armor, values = a
        return (values[0], armor.num_slots, armor.max_defense)
    avalue_tups.sort(key=sort_key, reverse=True)

    def is_masked_by(a, b):
        aarmor, avalues = a
        barmor, bvalues = b
        if aarmor.num_slots < barmor.num_slots:
            return False
        if avalues == bvalues:
            # if they are equal on all axes, it's a dup not relevent for
            # search, otherwise a must have more slots or defense to be
            # sorted first.
            return True
        for aval, bval in zip(avalues, bvalues):
            if aval < bval:
                return False
        return True

    i = 0
    while i < len(avalue_tups):
        masker = avalue_tups[i]
        masker_key = masker[0].name
        subcat[masker_key].append(masker)
        j = i+1
        while j < len(avalue_tups):
            cand = avalue_tups[j]

            #print "% 20s" % masker[0].name, masker[0].num_slots, masker[1]
            #print "% 20s" % cand[0].name, cand[0].num_slots, cand[1]
            if is_masked_by(masker, cand):
                #print "MASKED"
                del avalue_tups[j]
                subcat[masker_key].append(cand)
            else:
                j += 1
        i += 1
    return subcat




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


def load_charms(path):
    dialect = csv.Dialect
    with open(path) as csvfile:
        reader = csv.DictReader(csvfile,
                                fieldnames=["slots","skill1","points1",
                                            "skill2","points2"],
                                dialect=CharmDialect)
        # skip comment line
        reader.next()
        return [Charm(d) for d in reader]


class CharmDialect(csv.Dialect):
    delimiter = ","
    doublequote = False
    lineterminator = "\r\n"
    quotechar = None
    quoting = csv.QUOTE_NONE
    strict = False


class Charm(object):
    def __init__(self, d):
        self.slots = int(d["slots"])
        self.skills = {}
        self.positive_strees = set()
        for i in (1, 2):
            skey = "skill%d" % i
            pkey = "points%d" % i
            svalue = d[skey]
            if svalue:
                points = int(d[pkey])
                self.skills[svalue] = points
                if points > 0:
                    self.positive_strees.add(svalue)

    def __str__(self):
        sorted_skills = sorted(self.skills.keys())
        for i in xrange(len(sorted_skills), 2):
            sorted_skills.append("")
        return "%d,%s,%s,%s,%s" % (
            self.slots,
            sorted_skills[0],
            self.skills.get(sorted_skills[0], ""),
            sorted_skills[1],
            self.skills.get(sorted_skills[1], "")
        )

    def __repr__(self):
        return "<Charm '%s'>" % str(self)


class DictObj(object):
    def __init__(self, d):
        for k, v in d.iteritems():
            setattr(self, k, v)


if __name__ == '__main__':
    args = parse_args(None)

    charms = load_charms("mycharms.txt")
    #print charms
    #sys.exit()

    sys.stdout = get_utf8_writer(sys.stdout)
    find_armor_sets(args, charms)
