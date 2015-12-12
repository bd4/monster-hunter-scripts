#!/usr/bin/env python
# -*- coding: utf8 -*-
"""
Parse skill tree names and jp names for monster hunter X.
http://monsterhunter.wikia.com/wiki/MHX:_Skill_List

Returns list of dict, e.g.:
[
  {
    "name": "Testucabra",
    "name_jp": "...",
  },
  ...
]
"""

import sys
import re
import json
from collections import defaultdict, OrderedDict

import requests


#<td rowspan="1" style="vertical-align: top; background-color: #ddeeee; font-size:12pt; border-bottom: 2px solid #000000;"><h3><span class="mw-headline" id="Ammo_Saver">Ammo Saver</span></h3>弾薬節約
TREE_RE = re.compile('^<td [^>]*><h[23]><span class="mw-headline" id="[^"]*">(?:<b>)?([^<]*)(?:</b>)?</span></h[23]>([^<]*)')

# <td style="color: #000000;"> Guard +1<br />ガード性能+1
SKILL_RE = re.compile(
    '(?:</td>)?<td style="color: #000000;[^>]*> ([^<]*)<br />(.*)')


def parse_wikia_skill_trees(f):
    strees = []
    skills = []
    seen = set()
    in_tree = 0
    while True:
        line = f.readline()
        if not line:
            break
        line = line.strip()
        if in_tree:
            if not line:
                in_tree -= 1
                continue
            m = SKILL_RE.match(line)
            if m:
                skill = dict(name=m.group(1), name_jp=m.group(2))
                skills.append(skill)
            continue

        m = TREE_RE.match(line)
        if m:
            stree = dict(name=m.group(1), name_jp=m.group(2))
            if stree["name"] not in seen:
                strees.append(stree)
                seen.add(stree["name"])
            # three blank lines divides skill tree rows
            in_tree = 3
    return strees, skills


def _main():
    if len(sys.argv) != 4:
        print "Usage: %s infile out_strees.json out_skills.json" % sys.argv[0]
    with open(sys.argv[1]) as f:
        strees, skills = parse_wikia_skill_trees(f)
    with open(sys.argv[2], "w") as f:
        json.dump(strees, f, indent=2)
        f.write("\n")
    with open(sys.argv[3], "w") as f:
        json.dump(skills, f, indent=2)
        f.write("\n")


if __name__ == '__main__':
    _main()
