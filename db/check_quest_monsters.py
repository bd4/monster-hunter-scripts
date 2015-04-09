#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
This is a messy heuristic script for parsing monster names from quest and
sub quest goals and comparing that with the monster_to_quest table in the db.
"""

import os.path
import codecs
from collections import namedtuple
import difflib

import _pathfix

from mhapi.db import MHDB, Quest

QuestMonster = namedtuple("QuestMonster", "id name")

ALL_NAMES = None


def get_utf8_writer(writer):
    return codecs.getwriter("utf8")(writer)


def set_unstable(db, quest_id, monster_id, value):
    if value not in ("yes", "no"):
        raise ValueError("unstable must be 'yes' or 'no'")
    cur = db.cursor()
    cur.execute("""
        UPDATE monster_to_quest
        SET unstable=?
        WHERE quest_id=? AND monster_id=?
    """, (value, quest_id, monster_id))


def check_quests(db):
    quests = db.get_quests()
    for quest_row in quests:
        quest = Quest(quest_row)
        if not quest.name:
            assert quest.hub == "Event"
            #print "WARN: skipping non localized event quest: %d" \
            #    % quest_row["_id"]
            continue
        if quest.goal.startswith("Deliver "):
            continue
        if quest.goal.startswith("Survive until "):
            continue
        if quest.goal.startswith("Return on "):
            continue
        check_hunts(db, quest)


def lstrip(s, prefix):
    if s.startswith(prefix):
        return s[len(prefix):]
    return s

def rstrip(s, postfix):
    if s.endswith(postfix):
        return s[:-len(postfix)]
    return s

def _parse_monster(name):
    name = name.strip()
    #print name,

    name = lstrip(name, "and ")
    name = lstrip(name, "a ")
    name = lstrip(name, "an ")
    while name[0].isdigit():
        name = name[1:]
    name = name.strip()
    name = lstrip(name, "Frenzied ")

    name = rstrip(name, " Frenzy")

    name = rstrip(name, " or repel it")
    name = rstrip(name, " before time expires or deliver a Paw Pass Ticket")

    # Break/Wound subquests
    name = rstrip(name, " head")
    name = rstrip(name, " back")
    name = rstrip(name, " chest")
    name = rstrip(name, " tail")
    name = rstrip(name, " leg claw")
    name = rstrip(name, " claw")
    name = rstrip(name, " front leg")
    name = rstrip(name, " wingtalon")
    name = rstrip(name, " right wingarm")
    name = rstrip(name, " left wingarm")
    name = rstrip(name, " wingarm")
    name = rstrip(name, " wing arm")
    name = rstrip(name, " horn")
    name = rstrip(name, " chin")
    name = rstrip(name, " Jaw")
    name = rstrip(name, " jaw")
    name = rstrip(name, " wing")
    name = rstrip(name, " Wing")
    name = rstrip(name, " wings")
    name = rstrip(name, " horn")
    name = rstrip(name, " horns")
    name = rstrip(name, " outer hide")
    name = rstrip(name, " hide")
    name = rstrip(name, " crest")
    name = rstrip(name, " poison spikes")
    name = rstrip(name, " dorsal fin")
    name = rstrip(name, " top fin")
    name = rstrip(name, " fin")
    name = rstrip(name, " comb")
    name = rstrip(name, " body")
    name = rstrip(name, " feelers")
    name = rstrip(name, " blowhole")
    name = rstrip(name, " ear")
    name = rstrip(name, " ears")
    name = rstrip(name, " hind leg")
    name = rstrip(name, " shell")

    name = lstrip(name, "the ")

    name = rstrip(name, "'s")
    name = rstrip(name, "'")
    name = rstrip(name, u"’")
    name = rstrip(name, u"’s")

    #print "=>", name

    return name


def parse_goal_monster_names(goal, errors):
    if goal == "None":
        return []
    if "Severthe " in goal or "Hunta " in goal:
        goal2 = goal.replace("Severthe ", "Sever the ")
        goal2 = goal2.replace("Hunta ", "Hunt a ")
        errors.append("Spelling: '%s' => '%s'" % (goal, goal2))
        goal = goal2
    if goal.startswith("Deliver ") or goal.startswith("Topple "):
        # TODO: subquest, could parse the item and look up which monster
        # it's from
        return []
    if goal == "Suppress its Frenzy (2x)":
        return []
    goal = lstrip(goal, "Hunt ")
    # type in 253
    goal = lstrip(goal, "Hunta ")
    goal = lstrip(goal, "Slay ")
    goal = lstrip(goal, "Capture ")
    goal = lstrip(goal, "Repel ")

    # sub quests
    goal = lstrip(goal, "Wound ")
    goal = lstrip(goal, "Sever ")
    goal = lstrip(goal, "Break ")
    goal = lstrip(goal, "Suppress ")

    if ", and" in goal:
        parts = goal.split(",")
    else:
        parts = goal.split(" and ")
    return [_parse_monster(p) for p in parts]


def get_goal_monsters(db, goal, errors):
    names = parse_goal_monster_names(goal, errors)
    #print quest.goal, names
    monsters = []
    for name in names:
        if name == "all large monsters":
            continue
        elif name == "monster":
            continue
        m = db.get_monster_by_name(name)
        if m is None and name.endswith("s"):
            name2 = name.rstrip("s")
            m = db.get_monster_by_name(name2)
            if m is not None:
                name = name2
        if m is None:
            name2 = fuzzy_find(name)
            if name2:
                m = db.get_monster_by_name(name2)
                if m is not None:
                    errors.append("Fuzzy match: %s => %s" % (name, name2))
                    name = name2
        if m is None:
            errors.append("ERROR: can't find monster '%s'" % name)
            continue
        monsters.append(QuestMonster(m["_id"], name))
    return monsters


def fuzzy_find(name):
    matches = difflib.get_close_matches(name, ALL_NAMES, 1)
    if matches:
        return matches[0]
    return None


def check_hunts(db, quest):
    print ">", quest.id, quest.name,

    monsters_match = False

    all_names = db.get_monster_names()

    db_expected = set()
    db_expected_unstable = set()

    errors = []
    goal_expected = set(get_goal_monsters(db, quest.goal, errors))
    sub_expected = set(get_goal_monsters(db, quest.sub_goal, errors))

    monsters = db.get_quest_monsters(quest.id)
    for m in monsters:
        monster = db.get_monster(m["monster_id"])
        qm = QuestMonster(monster["_id"], monster["name"])
        if m["unstable"] == "yes":
            db_expected_unstable.add(qm)
        else:
            db_expected.add(qm)
    if goal_expected != db_expected:
        missing = goal_expected - db_expected
        if (len(goal_expected) == 1 and len(db_expected) == 1):
            # handle subspecious and Apex - e.g. when the goal lists the
            # bare name, but in the db it's listed as Apex NAME, assume
            # the db data is correct. When this happens, the
            # susbspecious / apex id is 1 greater than the normal
            # monster id.
            goal = next(iter(goal_expected))
            db = next(iter(db_expected))
            if goal[0] == db[0] - 1 and db[1].endswith(goal[1]):
                monsters_match = True
    else:
        monsters_match = True

    if monsters_match and not errors:
        # useful for doing grep -v on output
        print " *OK*"
    elif monsters_match:
        print " *MISSPELLING*"
        print " goal:", quest.goal
        print "  sub:", quest.sub_goal
        for err in errors:
            print " ", err
    else:
        print " *MISMATCH*",
        if errors:
            print " *MISSPELLING*",
        print
        for err in errors:
            print " ", err
        print " goal:", quest.goal
        print "  sub:", quest.sub_goal
        print "   parsed:", goal_expected
        if sub_expected and not sub_expected < goal_expected:
            # print if sub monster looks like it's not one of the
            # main  monsters. This will false positive when main quest
            # is hunt all large monsters.
            print " sub prsd:", sub_expected
        print "       db:", db_expected
        print " db unstb:", db_expected_unstable


if __name__ == '__main__':
    from _pathfix import db_path
    db_file = os.path.join(db_path, "mh4u.db")
    db = MHDB(db_file)

    ALL_NAMES = [row["name"] for row in db.get_monster_names()]

    import sys
    sys.stdout = get_utf8_writer(sys.stdout)
    sys.stderr = get_utf8_writer(sys.stderr)

    check_quests(db)
