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

SKILL_RE = re.compile(
    '</td><td style="color: #000000;[^>]*> ([^<]*)<br />(.*)')

TREE_END = '</td></tr>'


def parse_wikia_skill_trees(f):
    strees = []
    skills = []
    seen = set()
    in_tree = False
    while True:
        line = f.readline()
        if not line:
            break
        line = line.strip()
        if in_tree:
            if line == TREE_END:
                in_tree = False
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
            in_tree = True
    return strees, skills


def _main():
    with open(sys.argv[1]) as f:
        strees, skills = parse_wikia_skill_trees(f)
    print json.dumps(strees, indent=2)
    print json.dumps(skills, indent=2)


if __name__ == '__main__':
    _main()
