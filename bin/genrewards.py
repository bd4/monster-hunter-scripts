#!/usr/bin/env python
"""
Script to generate static rewards files for all items.
"""

import codecs
import urllib

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
        print("Usage: %s outdir" % sys.argv[0])
        sys.exit(os.EX_USAGE)

    outdir = sys.argv[1]
    err_out = get_utf8_writer(sys.stderr)

    # TODO: doesn't work if script is symlinked
    db_path = os.path.dirname(sys.argv[0])
    db_path = os.path.join(db_path, "..", "db", "mh4u.db")
    db = MHDB(db_path)

    items = db.get_item_names()

    # write all names json to /items.json
    items_file = os.path.join(outdir, "items.json")
    print "Writing", items_file
    with open(items_file, "w") as f:
        out = get_utf8_writer(f)
        out.write("[")
        first = True
        for item in items:
            if first:
                first = False
            else:
                out.write(", ")
            out.write('"')
            out.write(item["name"])
            out.write('"')
        out.write("]")

    for item in items:
        name = item["name"]
        item_id = item["_id"]
        encoded_name = name.encode("utf8")
        item_file = os.path.join(outdir, encoded_name + ".txt")
        print "Writing", item_id, item_file
        with open(item_file, "w") as f:
            out = get_utf8_writer(f)
            item_row = rewards.find_item(db, name, err_out)
            if item_row is None:
                sys.exit(os.EX_DATAERR)
            ir = rewards.ItemRewards(db, item_row)
            ir.print_all(out)
