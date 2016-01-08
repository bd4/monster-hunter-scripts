#!/usr/bin/env python2
# vim: set fileencoding=utf8 :

import urllib
import os
import json
import sys

from lxml import etree

import _pathfix

_BASE_URL = "http://monsterhunter.wikia.com/wiki/"

_PAGE = "MHX:_Monster_Material_List"

_CIRCLE = u"\u26ab"


def extract_names_and_icons(tree):
    carves = []
    tables = tree.xpath(
        '//*[@id="mw-content-text"]/table[contains(@class, "linetable")]'
    )
    for table in tables:
        rows = list(table)
        for row in rows:
            cells = row.xpath("./td")
            if not cells:
                continue
            icon_img = cells[0].xpath(".//*/img")
            if not icon_img:
                continue
            icon_name = icon_img[0].attrib["alt"]
            if icon_name == "Wiki":
                continue
            name, name_jp = [t.strip() for t in cells[1].xpath("./text()")]
            carves.append(dict(
                name=name,
                name_jp=name_jp,
                icon_name=_translate_icon_name(icon_name))
            )
    return carves


_SHAPE_MAP = {
    "Monster Parts": "Carapace",
    "Carapace": "Shell",
    "Claw": "Fang",
    "Ball": "Monster-Jewel",
    "Medicine": "Liquid",
}
_COLOR_MAP = {
    "Dark Purple": "Purple",
    "Dark Green": "DarkGreen",
    "Light Green": "YellowGreen",
    "Dark Red": "Red",
    "Dark Blue": "Blue",
    "Light Blue": "Cyan",
    "Brown": "Yellow",
}
def _translate_icon_name(s):
    """
    Translate from wikia icon names to MH4U db icon names.
    """
    prefix, name = s.split("-", 1)
    shape, color = name.split(" Icon ")
    if shape in _SHAPE_MAP:
        shape = _SHAPE_MAP[shape]
    if color in _COLOR_MAP:
        color = _COLOR_MAP[color]
    return "%s-%s.png" % (shape, color)


def _main():
    tmp_path = os.path.join(_pathfix.project_path, "tmp")
    fpath = os.path.join(tmp_path, "wikia-monster-carves.html")
    parser = etree.HTMLParser()
    urllib.urlretrieve(_BASE_URL + _PAGE, fpath)
    with open(fpath) as f:
        tree = etree.parse(f, parser)
        carves = extract_names_and_icons(tree)
    #print json.dumps(weapon_list, indent=2)
    print json.dumps(carves, indent=2)


if __name__ == '__main__':
    _main()
