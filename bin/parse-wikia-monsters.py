#!/usr/bin/env python
# -*- coding: utf8 -*-
"""
Parse monster names and jp names for monster hunter X.
http://monsterhunter.wikia.com/wiki/MHX:_Monsters

Returns list of dict, e.g.:
[
  {
    "name": "Testucabra",
    "name_jp": "...",
    "title_jp": "..."
  },
  ...
]
"""

import sys
import re
import json
from collections import defaultdict, OrderedDict

import requests


#<h3><span class="mw-headline" id="Lance">Lance</span></h3>
#<td style="vertical-align: top; background-color: #ddeeee; font-size:12pt;">Absolute Evasion<br />絶対回避
#</td><td>The hunter's body spins and evades attacks while retreating from the immediate area. Your weapon will always be sheathed after this technique.
SECTION_RE = re.compile('^<h[23]><span class="mw-headline" id="[^"]*">(?:<b>)?([^<]*)(?:</b>)?</span></h[23]>')
NAME_RE = re.compile(
    '^<td style="vertical-align: top; background-color: #ddeeee; font-size:12pt;">([^<]*)<br />(.*)')


MONSTER_RE = re.compile(
    '(?:</td>)?<td style="[^"]*background-color:#EBEBEB;">\s*'
    '<a href="([^"]*)" [^>]* title="([^"]*)"')


JAPANESE_NAME_STR = '<h3 class="pi-data-label pi-secondary-font">Japanese:</h3>'
JAPANESE_NAME_RE = re.compile(
    '<div class="pi-data-value pi-font">([^<]*)')


def parse_wikia_monsters(f):
    section = None
    data = []
    seen = set()
    while True:
        line = f.readline()
        if not line:
            break
        line = line.strip()
        m = SECTION_RE.match(line)
        if m:
            section = m.group(1)
            print >>sys.stderr, "section", section
            continue
        if section != "Large Monsters":
            continue
        m = MONSTER_RE.search(line)
        if m:
            monster = dict(href=m.group(1), name=m.group(2))
            if monster["name"] not in seen:
                data.append(monster)
                seen.add(monster["name"])
    return data


def get_jp_names(monster_path):
    url = "http://monsterhunter.wikia.com" + monster_path
    r = requests.get(url)
    html = r.text
    lines = r.text.split("\n")
    names = []
    while lines:
        line = lines.pop(0).strip()
        if JAPANESE_NAME_STR not in line:
            continue
        line = lines.pop(0).strip()
        while line == "":
            line = lines.pop(0).strip()
        m = JAPANESE_NAME_RE.match(line)
        assert m, "No match: " + line
        names.append(m.group(1))
        if len(names) == 2:
            break
    return names


def _main():
    with open(sys.argv[1]) as f:
        monster_list = parse_wikia_monsters(f)
    for m in monster_list:
        name = m["name"]
        names = get_jp_names(m["href"])
        if len(names) == 0:
            print >>sys.stderr, "ERROR: no names for %s" % name
            names = ["(?)", "(?)"]
        if len(names) == 1:
            names.append("(?)")
        m["name_jp"] = names[0]
        m["title_jp"] = names[1]
    print json.dumps(monster_list, indent=2)


if __name__ == '__main__':
    _main()
