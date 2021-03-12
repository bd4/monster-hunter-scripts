#!/usr/bin/env python

import os.path
import codecs
import csv

import _pathfix

from mhapi.db import MHDB


def set_upgrade_cost(db, item_id, upgrade_cost):
    print("upgrade_cost", item_id, upgrade_cost)
    cur = db.cursor()
    cur.execute("""UPDATE weapons SET
                   upgrade_cost=? WHERE _id=?""",
                (upgrade_cost, item_id))


def set_creation_cost(db, item_id, creation_cost):
    print("creation_cost", item_id, creation_cost)
    cur = db.cursor()
    cur.execute("""UPDATE weapons SET
                   creation_cost=? WHERE _id=?""",
                (creation_cost, item_id))


if __name__ == '__main__':
    db = MHDB()
    delta_file_path = os.path.join(_pathfix.db_path, "delta", "weapons.csv")

    with open(delta_file_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            item_id = row["id"]
            creation_cost = row["creation_cost"]
            upgrade_cost = row["upgrade_cost"]
            if creation_cost:
                set_creation_cost(db, item_id, creation_cost)
            if upgrade_cost:
                set_upgrade_cost(db, item_id, upgrade_cost)

    db.commit()
    db.close()
