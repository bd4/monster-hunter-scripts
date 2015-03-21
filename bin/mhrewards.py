#!/usr/bin/env python

import codecs

from mhapi.db import MHDB
from mhapi import rewards


def get_utf8_writer(writer):
    return codecs.getwriter("utf8")(writer)


if __name__ == '__main__':
    import sys
    import os
    import os.path

    if len(sys.argv) != 2:
        print("Usage: %s 'item name'" % sys.argv[0])
        sys.exit(os.EX_USAGE)

    item_name = sys.argv[1]

    out = get_utf8_writer(sys.stdout)
    err_out = get_utf8_writer(sys.stderr)

    # TODO: doesn't work if script is symlinked
    db_path = os.path.dirname(sys.argv[0])
    db_path = os.path.join(db_path, "..", "db", "mh4u.db")
    db = MHDB(db_path)

    item_row = rewards.find_item(db, item_name, err_out)
    if item_row is None:
        sys.exit(os.EX_DATAERR)
    rewards.print_quests_and_rewards(db, item_row, out)
