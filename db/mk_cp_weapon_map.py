#!/usr/bin/env python
"""
Parse the weapon list data from calculating palico, and use it to
generate another JSON file mapping the weapon name to the the weapon
class qualified id (CLASS.WEAPON_ID) that is used when passing weapon
setups in the query parameter.

See https://github.com/mrmin123/the-calculating-palico
"""

import os.path
import json

import _pathfix
from _pathfix import db_path, project_path

if __name__ == '__main__':
    inpath = os.path.join(db_path, "calculating_palico_weapon_list.json")
    outpath = os.path.join(project_path, "web", "data",
                           "calculating_palico_weapon_map.json")

    with open(inpath) as f:
        weapon_list = json.load(f)
    weapon_map = dict()
    for weapon in weapon_list:
        weapon_map[weapon["name"]] = "%s.%s" % (weapon["class"], weapon["id"])
    with open(outpath, "w") as f:
        json.dump(weapon_map, f)
