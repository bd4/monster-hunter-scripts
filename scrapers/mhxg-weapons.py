#!/usr/bin/env python
# vim: set fileencoding=utf8 :

import urllib
import os
import json

from lxml import etree

import _pathfix

_BASE_URL = "http://wiki.mhxg.org"

_WEAPON_URLS = {
    "Great Sword": ["/data/1900.html", "/data/2882.html"],
    "Long Sword": ["/data/1901.html", "/data/2883.html"],
    "Sword and Shield": ["/data/1902.html", "/data/2884.html"],
    "Dual Blades": ["/data/1903.html", "/data/2885.html"],
    "Hammer": ["/data/1904.html", "/data/2886.html"],
    "Lance": ["/data/1906.html", "/data/2888.html"],
    "Gunlance": ["/data/1907.html", "/data/2889.html"],
    "Switch Axe": ["/data/1908.html", "/data/2890.html"],
    "Charge Blade": ["/data/1909.html"],
    "Insect Glaive": ["/data/1910.html"],
    "Bow": ["/data/1911.html", "/data/2893.html"],
}


_RANGED_TYPES = ["Bow", "Light Bowgun", "Heavy Bowgun"]


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


_GL_SHOT_TYPES = {
    u"通常": "Normal",
    u"放射": "Long",
    u"拡散": "Wide",
}


_SA_PHIAL_TYPES = {
    u"強撃ビン": "Power",
    u"減気ビン": "Exhaust",
    u"滅龍ビン": "Dragon",
    u"強属性ビン": "Element",
    u"毒ビン": "Poison",
    u"麻痺ビン": "Paralysis",
}


_CB_PHIAL_TYPES = {
    u"榴弾ビン": "Impact",
    u"強属性ビン": "Element",
}


_BOW_ARC_TYPES = {
    u"集中型": "Focus",
    u"放散型": "Wide",
    u"爆裂型": "Blast",
}


_BOW_SHOT_TYPES = {
    u"連射": "Rapid",
    u"拡散": "Spread",
    u"貫通": "Pierce",
    u"重射": "Heavy",
}


_BOW_COATINGS = {
    u"強1": "Power 1",
    u"強2": "Power 2",
    u"属1": "Element 1",
    u"属2": "Element 2",
    u"接": "C. Range",
    u"ペ": "Paint",
    u"毒": "Poison",
    u"麻": "Paralysis",
    u"睡": "Sleep",
    u"減": "Exhaust",
    u"爆": "Blast",
}


def extract_weapon_list(wtype, tree):
    weapons = []
    rows = tree.xpath('//*[@id="sorter"]/tbody/tr')
    parent_name = None
    parent_href = None
    for row in rows:
        cells = list(row)
        if len(cells) < 5:
            continue
        name, href, final = _parse_name_td(cells[0])
        attack = int(cells[1].text)
        affinity, defense, elements = _parse_elements_td(cells[2])
        if wtype not in _RANGED_TYPES:
            sharpness = _parse_sharpness_td(cells[-2])
            shots, ammo = None, None
        else:
            sharpness = [None, None]
            if wtype == "Bow":
                shots, ammo = _parse_bow_td(cells[-2])
        slots = _parse_slots_td(cells[-1])
        data = dict(name_jp=name, name=name, wtype=wtype, final=final,
                    sharpness=sharpness[0], sharpness_plus=sharpness[1],
                    attack=attack, num_slots=slots,
                    affinity=affinity, defense=defense,
                    element=None, element_attack=None,
                    awaken=None, element_2=None, element_2_attack=None,
                    phial=None, shelling_type=None, horn_notes=None,
                    arc_type=None, ammo=ammo, shot_types=shots)
        if elements:
            data["element"] = elements[0][0]
            data["element_attack"] = elements[0][1]
            if len(elements) > 1:
                data["element_2"] = elements[1][0]
                data["element_2_attack"] = elements[1][1]
        if len(cells) == 6:
            _add_phial_or_shot_data(data, cells[-3])
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


def _add_phial_or_shot_data(data, td_element):
    text = td_element.text.strip()
    if data["wtype"] == "Charge Blade":
        data["phial"] = _CB_PHIAL_TYPES[text]
    elif data["wtype"] == "Switch Axe":
        data["phial"] = _SA_PHIAL_TYPES[text]
    elif data["wtype"] == "Gunlance":
        shot_type = _GL_SHOT_TYPES[text[:2]]
        data["shelling_type"] = "%s %s" % (shot_type, text[2])
    elif data["wtype"] == "Bow":
        data["arc_type"] = _BOW_ARC_TYPES[text]
    else:
        raise ValueError("Unexpected element for wtype '%s'" % data["wtype"])


def _parse_bow_td(td_element):
    shots = []
    coatings = []
    shot_type_spans = td_element.xpath("./div/span")
    for span in shot_type_spans:
        shot = {}
        if not span.text:
            continue
        text = span.text.strip()
        shot["type"] = _BOW_SHOT_TYPES[text[:2]]
        shot["level"] = text[2]
        shot["requires_loading"] = (span.attrib.get("class") == "b")
        shots.append(shot)
    coatings_span = td_element.xpath("./p/span/span")
    for span in coatings_span:
        text = span.text.strip()
        coatings.append(_BOW_COATINGS[text])
    return shots, coatings


def _parse_elements_td(td_element):
    # 会心<span class="c_r">-20</span>%<br>
    # 防御+5
    # <span class="type_N">氷14</span>
    spans = td_element.xpath('./span')
    affinity = 0
    defense = 0
    elements = []
    for span in spans:
        span_class = span.attrib.get("class")
        if span_class and span_class.startswith("type_"):
            e = _parse_element(span.text.strip())
            elements.append(e)
        else:
            affinity = int(span.text.strip())
    text_lines = td_element.text.strip().split("\n")
    for line in text_lines:
        if line.startswith(u"防御+"):
            defense = int(line[3:])
    return affinity, defense, elements


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
            urllib.urlretrieve(_BASE_URL + url, fpath)
            with open(fpath) as f:
                tree = etree.parse(f, parser)
                wlist = extract_weapon_list(wtype, tree)
            weapon_list.extend(wlist)
    print json.dumps(weapon_list, indent=2)


if __name__ == '__main__':
    _main()
