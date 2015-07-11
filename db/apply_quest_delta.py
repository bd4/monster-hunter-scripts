#!/usr/bin/env python

import os.path
import codecs
import csv

import _pathfix

from mhapi.db import MHDB


def apply_update(db, row):
    quest = db.get_quest(row["id"])
    if quest.goal == row["goal"]:
        print "quest", row["id"], row["name"], "already updated, skipping"
        return
    cur = db.cursor()
    cur.execute("""UPDATE quests SET
                   goal=?
                   WHERE _id=?
                     AND name=?""",
                (row["goal"], row["id"], row["name"]))
    if cur.rowcount == 1:
        print "quest", row["id"], row["name"], "goal updated:", row["goal"]
    else:
        print "ERROR", "quest", row["id"], row["name"], "update failed"


if __name__ == '__main__':
    db = MHDB()
    delta_file_path = os.path.join(_pathfix.db_path, "delta",
                                   "quests.csv")

    with open(delta_file_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            apply_update(db, row)

    db.commit()
    db.close()
