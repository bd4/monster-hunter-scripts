#!/usr/bin/env python2

import sys

import _pathfix

from mhapi.db import MHDB, MHDBX
from mhapi.model import get_costs


def find_cost_level(db, c):
    monsters = { "HR": set(), "LR": set() }
    materials = { "HR": set(), "LR": set() }
    stars = dict(Village=None, Guild=None, Permit=None, Arena=None)
    for item in c["components"].keys():
        if item.startswith("HR ") or item.startswith("LR "):
            if not item.endswith(" Materials"):
                print "Error: bad item format '%s'" % item
            rank = item[:2]
            item = item[len("HR "):-len(" Materials")]
            monster = db.get_monster_by_name(item)
            if monster:
                monsters[rank].add(monster)
                #print "Monster", rank, monster.name, monster.id
            else:
                materials[rank].add(item)
                #print "Material", rank, item
        else:
            data = db.get_item_by_name(item)
            current_stars = find_item_level(db, data.id)
            # keep track of most 'expensive' item
            for k, v in current_stars.iteritems():
                if v is None:
                    continue
                if stars[k] is None or v > stars[k]:
                    stars[k] = v
    return stars


def find_item_level(db, item_id):
    stars = dict(Village=None, Guild=None, Permit=None, Arena=None)

    quests = db.get_item_quests(item_id)

    gathering = db.get_item_gathering(item_id)
    gather_locations = set()
    for gather in gathering:
        gather_locations.add((gather["location_id"], gather["rank"]))
    for location_id, rank in list(gather_locations):
        gather_quests = db.get_location_quests(location_id, rank)
        quests.extend(gather_quests)

    monsters = db.get_item_monsters(item_id)
    monster_ranks = set()
    for monster in monsters:
        monster_ranks.add((monster["monster_id"], monster["rank"]))
    for monster_id, rank in list(monster_ranks):
        monster_quests = db.get_monster_quests(monster_id, rank)
        quests.extend(monster_quests)

    # find least expensive quest for getting the item
    for quest in quests:
        if quest.stars == 0:
            # ignore training quests
            if "Training" not in quest.name:
                print "Error: non training quest has 0 stars", \
                    quest.id, quest.name
            continue
        if quest.hub in stars:
            current = stars[quest.hub]
            if current is None or quest.stars < current:
                stars[quest.hub] = quest.stars
        else:
            print "Error: unknown hub", quest.hub

    return stars


def main():
    weapon_name = sys.argv[1]
    db = MHDB(game="gen", include_item_components=True)
    weapon = db.get_weapon_by_name(weapon_name)
    if weapon is None:
        print "Weapon '%s' not found" % weapon_name
        sys.exit(1)

    costs = get_costs(db, weapon)
    stars = dict(Village=None, Guild=None, Permit=None, Arena=None)
    # find least 'expensive' path
    for c in costs:
        current_stars = find_cost_level(db, c)
        for k, v in current_stars.iteritems():
            if v is None:
                continue
            if stars[k] is None or v < stars[k]:
                stars[k] = v
    for k, v in stars.iteritems():
        print k, v


if __name__ == '__main__':
    main()
