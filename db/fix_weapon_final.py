#!/usr/bin/env python

import sys

import _pathfix

from mhapi.db import MHDB
from mhapi.util import get_utf8_writer


#stdout = get_utf8_writer(sys.stdout)


def set_weapon_final(db, weapon, value):
    #print("weapon_final", weapon.id, weapon.name, value, file=stdout)
    print("weapon_final", weapon.id, weapon.name, value)
    cur = db.cursor()
    cur.execute("""UPDATE weapons SET
                   final=? WHERE _id=?""",
                (value, weapon.id))


if __name__ == '__main__':
    if len(sys.argv) > 1:
        game = sys.argv[1]
    else:
        game = "4u"
    db = MHDB(game=game)

    weapons = db.get_weapons()
    for weapon in weapons:
        children = db.get_weapons_by_parent(weapon.id)
        if children:
            # has children, should not be final
            if weapon["final"] == 1:
                set_weapon_final(db, weapon, 0)
        elif weapon["final"] == 0:
            # else no children, should be final
            set_weapon_final(db, weapon, 1)

    db.commit()
    db.close()
