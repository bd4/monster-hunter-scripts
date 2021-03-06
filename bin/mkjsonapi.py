#!/usr/bin/env python3

import os
import json
import sys
import errno
import urllib.request, urllib.parse, urllib.error
import argparse

import _pathfix

from mhapi.db import MHDB
from mhapi import model

ENTITIES = """item weapon monster armor
              skilltree skill decoration
              horn_melody wyporium""".split()

def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=
        "Create static JSON files that mimic a REST API for monster hunter data"
    )
    parser.add_argument("-o", "--outpath",
                        help="output base directory, defaults to web/jsonapi/"
                             " in project root")
    parser.add_argument("-g", "--game", help="game, one of 4u, gu, gen")
    parser.add_argument("entities", nargs="*",
                        help=", ".join(ENTITIES))
    return parser.parse_args(argv)


def mkdirs_p(path):
    try:
        os.makedirs(path)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise


SAFE_CHARS = " &'+\""


def file_path(path, model_object, alt_name_field=None):
    if alt_name_field:
        key = urllib.parse.quote(model_object[alt_name_field].encode("utf8"),
                           SAFE_CHARS)
    else:
        key = str(model_object.id)
    return os.path.join(path, "%s.json" % key)


def write_list_file(path, model_list):
    list_path = os.path.join(path, "_list.json")
    with open(list_path, "w") as f:
        json.dump([o.as_list_data() for o in model_list],
                  f, cls=model.ModelJSONEncoder, indent=2)


def write_index_file(path, indexes):
    for key, data in indexes.items():
        index_path = os.path.join(path, "_index_%s.json" % key)
        with open(index_path, "w") as f:
            json.dump(data, f, cls=model.ModelJSONEncoder, indent=2)


def write_all_file(path, all_data):
    all_path = os.path.join(path, "_all.json")
    with open(all_path, "w") as f:
        json.dump(all_data, f, cls=model.ModelJSONEncoder, indent=2)


def write_map_file(path, map_data):
    map_path = os.path.join(path, "_map.json")
    with open(map_path, "w") as f:
        json.dump(map_data, f, cls=model.ModelJSONEncoder, indent=2)


def monster_json(db, path):
    monsters = db.get_monsters()
    mkdirs_p(path)
    write_list_file(path, monsters)

    indexes = {}
    for m in monsters:
        monster_path = file_path(path, m)
        m.update_indexes(indexes)
        data = m.as_data()
        damage = db.get_monster_damage(m.id)
        damage.set_breakable(db.get_monster_breaks(m.id))
        data["damage"] = damage.as_data()
        with open(monster_path, "w") as f:
            json.dump(data, f, cls=model.ModelJSONEncoder, indent=2)

    write_index_file(path, indexes)


def armor_json(db, path):
    armors = db.get_armors()
    mkdirs_p(path)
    write_list_file(path, armors)
    all_data = []

    indexes = {}
    for a in armors:
        armor_path = file_path(path, a)
        a.update_indexes(indexes)
        skills = db.get_item_skills(a.id)
        if not skills:
            print("WARN: armor '%s' (%d) has no skills" % (a.name, a.id))
        a.set_skills(skills)

        all_data.append(a.as_data())

        with open(armor_path, "w") as f:
            a.json_dump(f)

    write_index_file(path, indexes)
    write_all_file(path, all_data)


def decoration_json(db, path):
    decorations = db.get_decorations()
    mkdirs_p(path)
    write_list_file(path, decorations)
    all_data = []

    indexes = {}
    for a in decorations:
        decoration_path = file_path(path, a)
        a.update_indexes(indexes)
        skills = db.get_item_skills(a.id)
        if not skills:
            print("WARN: decoration '%s' (%d) has no skills" % (a.name, a.id))
        a.set_skills(skills)

        all_data.append(a.as_data())

        with open(decoration_path, "w") as f:
            a.json_dump(f)

    write_index_file(path, indexes)
    write_all_file(path, all_data)


def skill_json(db, path):
    skills = db.get_skills()
    mkdirs_p(path)
    write_list_file(path, skills)

    indexes = {}
    for s in skills:
        s.update_indexes(indexes)
        skill_path = file_path(path, s)
        with open(skill_path, "w") as f:
            s.json_dump(f)

    write_index_file(path, indexes)


def skilltree_json(db, path):
    skill_trees = db.get_skill_trees()
    mkdirs_p(path)
    write_list_file(path, skill_trees)

    all_data = {}
    for st in skill_trees:
        ds = db.get_decorations_by_skills([st.id])
        for d in ds:
            d.set_skills(db.get_item_skills(d.id))
        st.set_decorations(ds)
        skilltree_path = file_path(path, st)
        all_data[st.name] = st
        with open(skilltree_path, "w") as f:
            st.json_dump(f)

    write_all_file(path, all_data)


def weapon_json(db, path):
    weapons = db.get_weapons()
    mkdirs_p(path)
    write_list_file(path, weapons)

    item_stars = model.ItemStars(db)

    all_data = []
    melodies = {}
    indexes = {}
    for w in weapons:
        weapon_path = file_path(path, w)
        w.update_indexes(indexes)
        data = w.as_data()

        child_weapons = db.get_weapons_by_parent(w.id)
        data["children"] = [dict(id=c.id, name=c.name) for c in child_weapons]

        if w.horn_notes:
            if w.horn_notes not in melodies:
                melodies[w.horn_notes] = [
                    dict(song=melody.song, effect1=melody.effect1)
                    for melody in db.get_horn_melodies_by_notes(w.horn_notes)
                ]
            data["horn_melodies"] = melodies[w.horn_notes]

        stars = item_stars.get_weapon_stars(w)
        data["village_stars"] = stars["Village"]
        data["guild_stars"] = stars["Guild"]
        data["permit_stars"] = stars["Permit"]
        data["arena_stars"] = stars["Arena"]

        all_data.append(data)

        with open(weapon_path, "w") as f:
            json.dump(data, f, cls=model.ModelJSONEncoder, indent=2)

        tree_path = os.path.join(path, "%s_tree.json" % w.id)
        costs = model.get_costs(db, w)
        for cost in costs:
            cost["path"] = [dict(name=w.name, id=w.id)
                            for w in cost["path"]]
        with open(tree_path, "w") as f:
            json.dump(costs, f, cls=model.ModelJSONEncoder, indent=2)

    write_index_file(path, indexes)
    write_all_file(path, all_data)


def item_json(db, path):
    if db.game == "4u":
        items = db.get_items(wyporium=True)
    else:
        items = db.get_items()
    mkdirs_p(path)
    write_list_file(path, items)


    indexes = {}
    for item in items:
        item_path = file_path(path, item)
        item.update_indexes(indexes)
        with open(item_path, "w") as f:
            item.json_dump(f)

    write_index_file(path, indexes)


def wyporium_json(db, path):
    trade_map = {}
    for item in db.get_wyporium_trades():
        trade_map[item.id] = dict(id=item.id,
                                  name=item.name)
        all_data = item.as_data()
        for k in all_data.keys():
            if not k.startswith("wyporium"):
                continue
            trade_map[item.id][k] = all_data[k]
        print(trade_map)
    mkdirs_p(path)
    write_map_file(path, trade_map)


def horn_melody_json(db, path):
    # only 143 rows, just do index with all data
    melodies = db.get_horn_melodies()
    mkdirs_p(path)

    indexes = {}
    for melody in melodies:
        melody.update_indexes(indexes)

    write_index_file(path, indexes)


def main():
    args = parse_args()

    db = MHDB(game=args.game, include_item_components=True)

    if not args.outpath:
        args.outpath = os.path.join(_pathfix.web_path, "jsonapi")

    if args.entities:
        for entity in args.entities:
            if entity not in ENTITIES:
                print("Unknown entity: %s" % entity)
                sys.exit(1)
    else:
        args.entities = ENTITIES

    if db.game != "4u":
        args.entities.remove("wyporium")

    for entity in args.entities:
        fn = globals()["%s_json" % entity]
        fn(db, os.path.join(args.outpath, entity))


if __name__ == '__main__':
    main()
