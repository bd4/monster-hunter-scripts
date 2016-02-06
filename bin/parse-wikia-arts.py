#!/usr/bin/env python
# -*- coding: utf8 -*-
"""
Parse hunter arts name, name_jp, and description from wikia:
http://monsterhunter.wikia.com/wiki/MHX:_Hunter_Arts

Returns list of dict, e.g.:
[
  {
    "section": "Heavy Bowgun",
    "description": "",
    "name": "Acceleration Shower I",
    "name_jp": "\u30a2\u30af\u30bb\u30eb\u30b7\u30e3\u30ef\u30fc I"
  },
  ...
]
"""

import sys
import re
import json
from collections import defaultdict, OrderedDict


#<h3><span class="mw-headline" id="Lance">Lance</span></h3>
#<td style="vertical-align: top; background-color: #ddeeee; font-size:12pt;">Absolute Evasion<br />絶対回避
#</td><td>The hunter's body spins and evades attacks while retreating from the immediate area. Your weapon will always be sheathed after this technique.
SECTION_RE = re.compile('^<h[23]><span class="mw-headline" id="[^"]*">([^<]*)</span></h[23]>')
NAME_RE = re.compile(
    '^<td style="vertical-align: top; background-color: #ddeeee; font-size:12pt;">([^<]*)<br />(.*)')

def parse_wikia_hunter_arts(f):
    section = None
    data = []
    skill = {}
    while True:
        line = f.readline()
        if not line:
            break
        line = line.strip()
        m = SECTION_RE.match(line)
        if m:
            section = m.group(1)
            continue
        m = NAME_RE.match(line)
        if m:
            skill["section"] = section
            skill["name"] = m.group(1)
            if skill["name"].endswith("II"):
                # don't need to translate I-III multiple times, and
                # descriptions are also the same
                continue
            skill["name_jp"] = m.group(2)
            # next line is description
            description = f.readline().strip().replace("</td><td>", "")
            skill["description"] = description
            data.append(skill)
            skill = {}
    return data


def _main():
    with open(sys.argv[1]) as f:
        data = parse_wikia_hunter_arts(f)
    print json.dumps(data, indent=2)


if __name__ == '__main__':
    _main()
