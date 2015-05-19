#!/usr/bin/env python

import os.path
import codecs
import json

import _pathfix
from _pathfix import db_path

from mhapi.db import MHDB


def get_utf8_writer(writer):
    return codecs.getwriter("utf8")(writer)


def set_carve_counts(db, monster_carves):
    monsters = db.get_monsters()
    for m in monsters:
        rewards = db.get_monster_rewards(m.id)
        mc = monster_carves.get(m.name)
        print "===", m.name
        for r in rewards:
            condition = r["condition"]
            if "Carve" not in condition:
                continue
            if mc and condition in mc:
                stack_size = mc[condition]
            elif m["class"] == "Minion":
                stack_size = 1
            elif m["class"] == "Boss":
                if condition == "Body Carve":
                    stack_size = 3
                elif condition == "Tail Carve":
                    stack_size = 1
                else:
                    print "WARN: unknown condition %s.%s" \
                          % (m.name, condition)
            else:
                assert False, "Unknown monster class: %s" % m["class"]
            if r["stack_size"] == stack_size:
                continue
            print "   ", condition, r["stack_size"], "=>", stack_size
            cur = db.cursor()
            cur.execute("""UPDATE hunting_rewards
                           SET stack_size=? WHERE _id=?""",
                        (stack_size, r["_id"]))


def load_carves_json():
    carves_json_path = os.path.join(db_path, "carves.json")
    with open(carves_json_path) as f:
        carves_list = json.load(f)
    monster_carves = {}
    for carves in carves_list:
        for monster_name in carves["monsters"]:
            monster_carves[monster_name] = carves["carves"]
    return monster_carves


if __name__ == '__main__':
    db_file = os.path.join(db_path, "mh4u.db")
    db = MHDB(db_file)

    import sys
    sys.stdout = get_utf8_writer(sys.stdout)
    sys.stderr = get_utf8_writer(sys.stderr)
    monster_carves = load_carves_json()
    set_carve_counts(db, monster_carves)
    db.commit()
    db.close()
