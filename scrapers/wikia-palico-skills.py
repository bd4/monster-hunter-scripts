#!/usr/bin/env python2
# vim: set fileencoding=utf8 :

import urllib.request, urllib.parse, urllib.error
import os
import json
import sys

from lxml import etree

import _pathfix

_BASE_URL = "http://monsterhunter.wikia.com/wiki/"

_PAGE = "MHX:_Palico_Skills"

_CIRCLE = "\u26ab"


def extract_arts_and_skills(tree):
    arts = []
    skills = []
    tables = tree.xpath(
        '//*[@id="mw-content-text"]/table[contains(@class, "linetable")]'
    )
    for table in tables:
        category = None
        fields = None
        rows = list(table)
        for row in rows:
            cols, is_header = _get_column_cells_texts(row)
            print(is_header, cols)
            continue
            if is_header:
                if len(cols) == 1:
                    category = cols[0]
                else:
                    fields = [_header_to_field_name(c) for c in cols]
            else:
                if fields[0].startswith("art_"):
                    if category == "Forte Specific (Unteachable)":
                        values = dict(name=cols[0],
                                      name_jp=cols[1],
                                      forte=cols[2],
                                      cost=int(cols[3]),
                                      unlock_requirement=None,
                                      teaching_requirement=None,
                                      description=cols[4],
                                      teachable=False)
                    elif category == "Forte Specific (Teachable)":
                        values = dict(name=cols[0],
                                      name_jp=cols[1],
                                      forte="%s %s" % (cols[2], cols[3]),
                                      cost=int(cols[4]),
                                      unlock_requirement=None,
                                      teaching_requirement=cols[5],
                                      description=cols[6],
                                      teachable=True)
                    else:
                        values = dict(name=cols[0],
                                      name_jp=cols[1],
                                      forte="All",
                                      cost=int(cols[2]),
                                      unlock_requirement=cols[3],
                                      teaching_requirement=None,
                                      description=cols[4],
                                      teachable=True)
                    arts.append(values)
                elif fields[0].startswith("skill_"):
                    values = dict(name=cols[0],
                                  name_jp=cols[1],
                                  req_level=cols[2],
                                  cost=cols[3].count(_CIRCLE),
                                  description=cols[4],
                                  category=category)
                    skills.append(values)
                else:
                    raise ValueError("Unknown table type: %r" % cols[0])
        #print rows[0].text, len(rows)
    return arts, skills


def _get_column_cells_texts(tr_element):
    is_header = True
    cells = tr_element.xpath("./th")
    if not cells:
        is_header = False
        cells = tr_element.xpath("./td")
    texts = []
    for cell in cells:
        texts = [t.strip() for t in cell.xpath("./text()")]
    return texts, is_header


def _header_to_field_name(s):
    return s.lower().replace(" ", "_").replace(".", "")


def _main():
    tmp_path = os.path.join(_pathfix.project_path, "tmp")
    fpath = os.path.join(tmp_path, "wikia-palico-skills.html")
    parser = etree.HTMLParser()
    urllib.request.urlretrieve(_BASE_URL + _PAGE, fpath)
    with open(fpath) as f:
        tree = etree.parse(f, parser)
        arts, skills = extract_arts_and_skills(tree)
    #print json.dumps(weapon_list, indent=2)
    print(json.dumps(arts, indent=2))
    print(json.dumps(skills, indent=2))


if __name__ == '__main__':
    _main()
