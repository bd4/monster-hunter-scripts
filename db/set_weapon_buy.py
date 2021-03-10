#!/usr/bin/env python2

import os.path
import codecs
import csv

import _pathfix

from mhapi.db import MHDB


def set_buy(db, item_id, buy):
    print "buy", item_id, buy
    cur = db.cursor()
    cur.execute("""UPDATE items SET
                   buy=? WHERE _id=?""",
                (buy, item_id))

def set_buy_by_name(db, name, buy):
    cur = db.cursor()
    cur.execute("""UPDATE items SET
                   buy=? WHERE name=?""",
                (buy, name))
    rowid = cur.lastrowid
    print "buy", rowid, name, buy

if __name__ == '__main__':
    db = MHDB(game="4u")
    delta_file_path = os.path.join(_pathfix.db_path, "mh4u", "weapon_shop.csv")

    with open(delta_file_path) as f:
        reader = csv.reader(f)
        for row in reader:
            name = row[0]
            value = int(row[1])
            set_buy_by_name(db, name, value)

    db.commit()
    db.close()
