#!/usr/bin/env python

import codecs

import _pathfix

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

    item_name = " ".join(sys.argv[1].lower().split()).title()

    out = get_utf8_writer(sys.stdout)
    err_out = get_utf8_writer(sys.stderr)

    db = MHDB(_pathfix.db_path)

    item_row = rewards.find_item(db, item_name, err_out)
    if item_row is None:
        sys.exit(os.EX_DATAERR)
    ir = rewards.ItemRewards(db, item_row)
    ir.print_all(out)
