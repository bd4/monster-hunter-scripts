#!/usr/bin/env python
# vim: set fileencoding=utf8 :

import urllib
import os
import json

from lxml import etree

import _pathfix


_WEAPON_URLS = {
    "Hammer": ["http://wiki.mhxg.org/data/1904.html",
               "http://wiki.mhxg.org/data/2886.html"],
}


_ELEMENT_MAP = {
    u"火": "Fire",
    u"水": "Water",
    u"雷": "Thunder",
    u"氷": "Ice",
    u"龍": "Dragon",
    u"毒": "Poison",
    u"麻痺": "Paralysis",
    u"睡眠": "Sleep",
    u"爆破": "Blast",
}


def extract_weapon_list(wtype, tree):
    weapons = []
    rows = tree.xpath('//*[@id="sorter"]/tbody/tr')
    i = 0
    parent_name = None
    parent_href = None
    for row in rows:
        cells = list(row)
        if len(cells) != 5:
            continue
        name, href, final = _parse_name_td(cells[0])
        attack = int(cells[1].text)
        affinity, defense, element, element_attack = _parse_extra_td(cells[2])
        sharpness = _parse_sharpness_td(cells[3])
        slots = _parse_slots_td(cells[4])
        data = dict(name_jp=name, name=name, wtype=wtype, final=final,
                    sharpness=sharpness[0], sharpness_plus=sharpness[1],
                    attack=attack, num_slots=slots,
                    affinity=affinity, defense=defense,
                    element=element, element_attack=element_attack)
        if href is None or href == parent_href:
            data["parent"] = parent_name
            data["href"] = parent_href
        else:
            data["href"] = href
            data["parent"] = None
            parent_name = name
            parent_href = href
        data["url"] = "http://wiki.mhxg.org" + data["href"]
        weapons.append(data)
    return weapons


def _parse_extra_td(td_element):
    # 会心<span class="c_r">-20</span>%<br>
    # 防御+5
    spans = td_element.xpath('./span')
    affinity = 0
    defense = 0
    element = None
    element_attack = None
    for span in spans:
        span_class = span.attrib.get("class")
        if span_class and span_class.startswith("type_"):
            element, element_attack = _parse_element(span.text.strip())
        else:
            affinity = int(span.text.strip())
    text_lines = td_element.text.strip().split("\n")
    for line in text_lines:
        if line.startswith(u"防御+"):
            defense = int(line[3:])
    return affinity, defense, element, element_attack


def _parse_element(text):
    for jp_element in sorted(_ELEMENT_MAP.keys(), key=lambda s: len(s),
                             reverse=True):
        if text.startswith(jp_element):
            value = int(text[len(jp_element):])
            element = _ELEMENT_MAP[jp_element]
            return element, value
    raise ValueError("Bad element: %r" % text)


def _parse_name_td(td_element):
    href = None
    name = None
    final = 0
    links = td_element.xpath('.//a')
    if links:
        assert len(links) == 1
        href = links[0].attrib["href"]
        name = links[0].text
        style = td_element.xpath('./span[@class="b"]/@style')
        if style and "background-color:#eec3e6;" in style:
            final = 1
    else:
        img_element = td_element.xpath('./img')[0]
        name = img_element.tail.strip()
    if name.endswith("10"):
        final = 1
    return name, href, final


def _parse_slots_td(td_element):
    text = td_element.text
    if text:
        return text.count(u"◯")
    return 0


def _parse_sharpness_td(td_element):
    div = td_element[0]
    subs = list(div)
    sharpness, sharpness_plus = [], []
    current = sharpness
    for sub in subs:
        if sub.tag == "br":
            current = sharpness_plus
            continue
        assert sub.tag == "span", sub.tag
        if sub.attrib["class"] == "kr7":
            continue
        if sub.text is None:
            continue
        current.append(sub.text.count("."))
    for i in xrange(len(sharpness), 6):
        sharpness.append(0)
    for i in xrange(len(sharpness_plus), 6):
        sharpness_plus.append(0)
    return sharpness, sharpness_plus


def _main():
    tmp_path = os.path.join(_pathfix.project_path, "tmp")
    weapon_list = []
    parser = etree.HTMLParser()
    for wtype, urls in _WEAPON_URLS.iteritems():
        for i, url in enumerate(urls):
            fpath = os.path.join(tmp_path, "%s-%d.html" % (wtype, i))
            urllib.urlretrieve(url, fpath)
            with open(fpath) as f:
                tree = etree.parse(f, parser)
                wlist = extract_weapon_list(wtype, tree)
            weapon_list.extend(wlist)
    print json.dumps(weapon_list, indent=2)


if __name__ == '__main__':
    _main()
