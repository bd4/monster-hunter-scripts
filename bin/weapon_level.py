#!/usr/bin/env python2

import sys
import argparse

import _pathfix

from mhapi.db import MHDB, MHDBX
from mhapi.model import ItemStars


def main():
    db = MHDB(game="gen", include_item_components=True)
    item_stars = ItemStars(db)

    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--item")
    parser.add_argument("-w", "--weapon")

    args = parser.parse_args()
    if args.item:
        item = db.get_item_by_name(args.item)
        if item is None:
            print "Item '%s' not found" % args.item
            sys.exit(1)
        if item.type == "Materials":
            stars = item_stars.get_material_stars(item.id)
        else:
            stars = item_stars.get_item_stars(item.id)
    elif args.weapon:
        weapon = db.get_weapon_by_name(args.weapon)
        if weapon is None:
            print "Weapon '%s' not found" % args.weapon
            sys.exit(1)
        stars = item_stars.get_weapon_stars(weapon)
    else:
        print "Specify -w or -i"
        sys.exit(1)

    for k, v in stars.iteritems():
        print k, v


if __name__ == '__main__':
    main()
