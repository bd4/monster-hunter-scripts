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


def parse_wikia_skill_trees(f):
    data = []
    seen = set()
    while True:
        line = f.readline()
        if not line:
            break
        line = line.strip()
        m = TREE_RE.match(line)
        if m:
            stree = dict(name=m.group(1), name_jp=m.group(2))
            if stree["name"] not in seen:
                data.append(stree)
                seen.add(stree["name"])
    return data


def _main():
    with open(sys.argv[1]) as f:
        stree_list = parse_wikia_skill_trees(f)
    print json.dumps(stree_list, indent=2)


if __name__ == '__main__':
    _main()
