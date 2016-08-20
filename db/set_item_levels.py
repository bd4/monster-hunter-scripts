#!/usr/bin/env python2

import sys
import argparse

import sqlite3

import _pathfix

from mhapi.db import MHDB, MHDBX
from mhapi.model import ItemStars


def _add_column(cursor, table, column_spec):
    q = "ALTER TABLE %s ADD COLUMN %s" % (table, column_spec)
    try:
        rval = cursor.execute(q)
    except sqlite3.OperationalError as e:
        if "duplicate column" not in e.args[0]:
            raise
        return False
    return True


def _set_stars(cursor, item_id, stars):
    for k in stars.keys():
        col = k.lower() + "_stars"
        q = "UPDATE items SET %s=? WHERE _id=?" % col
        cursor.execute(q, (stars[k], item_id))


def main():
    db = MHDB(game="gen", include_item_components=True)
    item_stars = ItemStars(db)

    c = db.cursor()
    for col_name in ("village_stars", "guild_stars",
                     "permit_stars", "arena_stars"):
        col_spec = "%s integer DEFAULT NULL" % col_name
        _add_column(c, "items", col_spec)
    db.commit()

    c = db.cursor()

    items = db.get_items(exclude_types=["", "Armor", "Palico Weapon",
                                        "Decoration"])
    for item in items:
        print item.id, item.type, item.name
        if item.type == "Materials":
            stars = item_stars.get_material_stars(item.id)
        elif item.type == "Weapon":
            weapon = db.get_weapon(item.id)
            stars = item_stars.get_weapon_stars(weapon)
        else:
            stars = item_stars.get_item_stars(item.id)
        _set_stars(c, item.id, stars)

    db.commit()


if __name__ == '__main__':
    main()
