#!/usr/bin/env python

import sys
import argparse
import json

import _pathfix

from mhapi.db import MHDB
from mhapi.model import ModelJSONEncoder


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


def get_costs(db, weapon):
    """
    Get a list of alternative ways of making a weapon, as a list of dicts
    containing item counts. The dicts also contain special keys _zenny
    for the total zenny needed, and _path for a list of weapons that
    make up the upgrade path.
    """
    costs = []
    if weapon.parent_id:
        parent_weapon = db.get_weapon(weapon.parent_id, True)
        costs = get_costs(db, parent_weapon)
        for cost in costs:
            for item in weapon.upgrade_components:
                if item.type == "Weapon":
                    continue
                if item.name not in cost["components"]:
                    cost["components"][item.name] = 0
                cost["components"][item.name] += item.quantity
            cost["zenny"] += weapon.upgrade_cost
            cost["path"] += [weapon]
    if weapon.creation_cost:
        create_cost = dict(zenny=weapon.creation_cost,
                           path=[weapon],
                           components={})
        for item in weapon.create_components:
            create_cost["components"][item.name] = item.quantity
        costs = [create_cost] + costs
    return costs


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
            print "=", ", ".join([w.name for w in cost["path"]])
            print "  Zenny", cost["zenny"]
            for item_name in sorted(components.iterkeys()):
                print "%20s %2d" % (item_name, components[item_name])
            print
