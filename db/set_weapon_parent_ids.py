#!/usr/bin/env python

import sys

import _pathfix

from mhapi.db import MHDB
from mhapi.util import get_utf8_writer

stdout = get_utf8_writer(sys.stdout)


def main(db):
    cursor = db.conn.execute("""SELECT components.created_item_id,
                                       components.component_item_id
                                FROM components
                                JOIN weapons
                                ON weapons._id = components.component_item_id
                                WHERE components.type == 'Improve'""")
    rows = cursor.fetchall()
    cursor.close()

    cur = db.cursor()
    for row in rows:
        item_id = row["created_item_id"]
        parent_id = row["component_item_id"]
        cur.execute("""UPDATE weapons
                       SET parent_id=? WHERE _id=?""",
                    (parent_id, item_id))


if __name__ == '__main__':
    if len(sys.argv) > 1:
        game = sys.argv[1]
    else:
        game = "3u"
    db = MHDB(game=game)

    main(db)
    db.commit()
    db.close()
