#!/usr/bin/env python3
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
# <td style="color: #ff0000; border-bottom: 2px solid #000000;"> Cold Surge<br />寒さ倍加
# </td><td style="color: #000000; border-bottom: 2px solid #000000;"> Charm Up <img src="data:image/gif;base64,R0lGODlhAQABAIABAAAAAP///yH5BAEAAAEALAAAAAABAAEAQAICTAEAOw%3D%3D" 	 alt="New"  	class="lzy lzyPlcHld " 	 	data-image-key="New.gif" 	data-image-name="New.gif" 	 data-src="https://vignette1.wikia.nocookie.net/monsterhunter/images/e/e0/New.gif/revision/latest?cb=20111022174959"  	 width="46"  	 height="12"  	 	 	 onload="if(typeof ImgLzy===&#39;object&#39;){ImgLzy.load(this)}"  	><noscript><img src="https://vignette1.wikia.nocookie.net/monsterhunter/images/e/e0/New.gif/revision/latest?cb=20111022174959" 	 alt="New"  	class="" 	 	data-image-key="New.gif" 	data-image-name="New.gif" 	 	 width="46"  	 height="12"  	 	 	 	></noscript><br />護石系統倍加
SKILL_RE = re.compile(
    '(?:</td>)?<td style="color: #[0f][0f]0000;[^>]*>([^<>]+)((?:<img[^>]* alt="New" [^>]*>)?)(?:<[^>]+>)*<br />(.*)')


def parse_wikia_skill_trees(f):
    strees = []
    skills = []
    seen = set()
    in_tree = 0
    is_new = False
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
                assert len(m.groups()) == 3
                is_new = len(m.group(2)) > 0
                stree = strees[-1]
                skill = dict(name=m.group(1).strip(), new=is_new,
                             name_jp=m.group(3).strip(),
                             tree=stree["name"],
                             tree_jp=stree["name_jp"])
                skills.append(skill)
                if is_new:
                    stree["new"] = True
                else:
                    stree["new"] = False
                # next line should be number of points
                next_line = f.readline()
                points = next_line[next_line.rfind('>')+1:].strip()
                skill["points"] = points
            continue

        m = TREE_RE.match(line)
        if m:
            stree = dict(name=m.group(1).strip(), name_jp=m.group(2).strip())
            if stree["name"] not in seen:
                strees.append(stree)
                seen.add(stree["name"])
            # three blank lines divides skill tree rows
            in_tree = 3
            is_new = False
    return strees, skills


def _main():
    if len(sys.argv) != 4:
        print("Usage: %s infile out_strees.json out_skills.json" % sys.argv[0])
        sys.exit(1)
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
