#!/usr/bin/env python3

import sys
import argparse
import json

import _pathfix

from mhapi.db import MHDB
from mhapi.model import ModelJSONEncoder, get_costs


def parse_args(argv):
    parser = argparse.ArgumentParser(description=
        "Determine the different paths for making a weapons and the cost"
        " and parts required for each path."
    )
    parser.add_argument("-j", "--json", action="store_true",
                        default=False,
                        help="output as json instead of plaintext")
    parser.add_argument("weapon",
                        help="Full name of weapon")
    return parser.parse_args(argv)


if __name__ == '__main__':
    args = parse_args(None)

    db = MHDB()

    weapon = db.get_weapon_by_name(args.weapon, True)
    if not weapon:
        raise ValueError("Weapon '%s' not found" % name)
    costs = get_costs(db, weapon)
    if args.json:
        for cost in costs:
            cost["path"] = [dict(name=w.name, id=w.id)
                            for w in cost["path"]]
        json.dump(costs, sys.stdout, cls=ModelJSONEncoder, indent=2)
    else:
        for cost in costs:
            components = cost["components"]
            print("=", ", ".join([w.name for w in cost["path"]]))
            print("  Zenny", cost["zenny"])
            for item_name in sorted(components.keys()):
                print("%20s %2d" % (item_name, components[item_name]))
            print()
