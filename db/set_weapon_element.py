#!/usr/bin/env python

import sys

import _pathfix

from mhapi.db import MHDB
from mhapi.util import get_utf8_writer

stdout = get_utf8_writer(sys.stdout)


element_map = dict(FI="Fire",
                   WA="Water",
                   IC="Ice",
                   TH="Thunder",
                   DR="Dragon",
                   PO="Poison",
                   PA="Paralysis",
                   SLP="Sleep",
                   SLM="Blastblight",
                   )



def parse_3udb_elemental(s):
    if s is None:
        return None
    if s.startswith("SL"):
        etype = s[:3]
        eattack = s[3:]
    else:
        etype = s[:2]
        eattack = s[2:]
    return (element_map[etype], int(eattack))


def main(db):
    cursor = db.conn.execute("""SELECT * FROM weapons""")
    rows = cursor.fetchall()
    cursor.close()

    cur = db.cursor()
    for row in rows:
        item_id = row["_id"]
        elemental_attack = row["elemental_attack"]
        if elemental_attack:
            parts = elemental_attack.split(", ")
            base = parse_3udb_elemental(parts[0])
            cur.execute("""UPDATE weapons
                           SET element=?, element_attack=? WHERE _id=?""",
                        (base[0], base[1], item_id))
            if len(parts) > 1:
                second = parse_3udb_elemental(parts[1])
                cur.execute("""UPDATE weapons
                               SET element_2=?, element_2_attack=? WHERE _id=?""",
                            (second[0], second[1], item_id))
        awake = parse_3udb_elemental(row["awakened_elemental_attack"])
        if awake:
            cur.execute("""UPDATE weapons
                           SET awaken=?, awaken_attack=? WHERE _id=?""",
                        (awake[0], awake[1], item_id))


if __name__ == '__main__':
    if len(sys.argv) > 1:
        game = sys.argv[1]
    else:
        game = "3u"
    db = MHDB(game=game)

    main(db)
    db.commit()
    db.close()
