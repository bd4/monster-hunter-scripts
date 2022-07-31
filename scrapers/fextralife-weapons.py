#!/usr/bin/env python3

import os.path
import sys
import re
import json
import lxml.etree

import requests

#WTYPES = ["Great Sword", "Long Sword", "Sword and Shield", "Dual Blades", "Lance", "Gunlance", "Hammer"]
WTYPES = ["Great Sword", "Lance", "Hammer"]

WIDTH_RE = re.compile(r'width: *(\d+)%;')

PART_RE = re.compile(r'(.*) x(\d+)( Points)?')

# MR Bone 20 pts.
PART_RE_MR = re.compile(r'(.*) (\d+) +pts\.?')


"""
<div class="progress" style="max-width: 100%; min-width: 100px;"> 
      <div class="progress-bar danger-color-dark" style="width: 11%;">
        &nbsp; 
      </div> 
      <div class="progress-bar warning-color-dark" style="width: 20%;">
        &nbsp; 
      </div> 
      <div class="progress-bar warning-color" style="width: 12%;">
        &nbsp; 
      </div> 
      <div class="progress-bar success-color" style="width: 0%;">
        &nbsp; 
      </div> 
      <div class="progress-bar primary-color-dark" style="width: 0%;">
        &nbsp; 
      </div> 
      <div class="progress-bar white" style="width: 0%;">
        &nbsp; 
      </div> 
</div> 
"""
def parse_sharpness(div):
    values = []
    divs = div.xpath('div')
    for div in divs:
        style = div.get("style")
        m = WIDTH_RE.match(style)
        if m:
            values.append(int(m.group(1)))

    return values


def parse_rampage(td):
    return td.xpath('ul/li/a/text()')


def parse_crafting(td):
    materials = {}
    for li in td.xpath('ul/li'):
        atext = li.xpath('a/text()')
        litext = li.xpath('text()')
        if litext:
            litext = litext[0].strip()
        else:
            print("Unknown format: ", lxml.etree.tostring(td))
            return {}

        if litext.endswith('\xa0'):
            litext = litext.rstrip('\xa0')
        if litext.endswith('.'):
            litext = litext.rstrip('.')

        if litext.endswith('l'):
            litext = litext[:-1] + '1'

        if litext.startswith('+ '):
            atext += '+'
            litext = litext[2:]

        if litext.startswith('x'):
            litext = litext[1:]

        if atext:
            atext = atext[0].strip()
            if litext.endswith(" Points"):
                litext = litext.rstrip(" Points")
                atext += " Points"
            #print("atext '" + atext + "' '" + litext + "'")
            try:
                materials[atext] = clean_int(litext)
            except Exception as e:
                print("WARN: failed parsing ", atext, litext)
                if litext == 'l':
                    materials[atext] = 1
        elif litext.isdigit():
            materials['zenny'] = clean_int(litext)
        else:
            m = PART_RE.match(litext)
            if not m:
                m = PART_RE_MR.match(litext)
                if m:
                    materials[m.group(1) + ' Points'] = int(m.group(2))
            elif m.group(2):
                materials[m.group(1) + ' Points'] = int(m.group(2))
            else:
                materials[m.group(1)] = int(m.group(2))
    return materials


def clean_text(t):
    t = t.strip()
    t = t.rstrip('\xa0')
    return t


def clean_int(s):
    s = clean_text(s)
    if not s:
        return 0
    return int(s)


def parse_element(td):
    #pp("td", td)
    etype = td.xpath('a/text()')
    if etype:
        values = td.xpath('./text()')
        if values:
            value = clean_int(values[0].strip())
            return dict(type=etype[0], attack=value)
    return dict(type=None, attack=None)


def parse_rarity(td):
    text = td.xpath('.//text()')
    if text:
        parts = text[0].split()
        if len(parts) > 1:
            return clean_int(text[0].split()[1])
    return 8


def parse_slots(td):
    slots = []
    for img in td.xpath('.//img'):
        title = img.get("title")
        if title and title.startswith('gem_'):
            parts = title.split("_")
            level = int(parts[2])
            slots.append(level)
    return slots


def adjust_slots_rampage(data):
    if data['rarity'] >= 8:
        data['rampage_slot'] = data['slots'][-1]
        data['slots'] = data['slots'][:-1]
    else:
        data['rampage_slot'] = 0


def gl_parse_tr(tr):
    data = {}
    cells = tr.xpath('td')
    #print(lxml.etree.tostring(cells[9]))

    # Name
    name = cells[0]
    #print(name)
    data['name'] = name.xpath('a/text()')[0]
    data['slots'] = parse_slots(name)
    data['sharpness'] = parse_sharpness(name.xpath('div')[0])
    data['attack'] = clean_int(cells[1].text)
    element = parse_element(cells[2])
    data['element'] = element['type']
    data['element_attack'] = element['attack']
    data['element_2'] = None
    data['element_2_attack'] = None
    data['affinity'] = clean_int(cells[3].text.rstrip('%'))
    data['defense'] = clean_int(cells[4].text)
    data['shot_type'] = cells[5].text
    data['level'] = clean_int(cells[6].text.split()[1])
    data['rarity'] = parse_rarity(cells[7])
    data['rampage_skills'] = parse_rampage(cells[8])
    data['crafting'] = parse_crafting(cells[9])

    adjust_slots_rampage(data)

    return data


def default_parse_tr(tr):
    data = {}
    cells = tr.xpath('td')
    #print(lxml.etree.tostring(cells[9]))

    if len(cells) == 10:
        return gl_parse_tr(tr)

    #print("cels", [c.text for c in cells])

    # Name
    name = cells[0]
    data['name'] = name.xpath('a/text()')[0]
    data['slots'] = parse_slots(name)
    data['sharpness'] = parse_sharpness(name.xpath('div')[0])
    data['attack'] = clean_int(cells[1].text)
    element = parse_element(cells[2])
    data['element'] = element['type']
    data['element_attack'] = element['attack']
    data['element_2'] = None
    data['element_2_attack'] = None
    data['affinity'] = clean_int(cells[3].text.rstrip('%'))
    data['defense'] = clean_int(cells[4].text)
    data['rarity'] = parse_rarity(cells[5])
    data['rampage_skills'] = parse_rampage(cells[6])
    data['crafting'] = parse_crafting(cells[7])

    adjust_slots_rampage(data)

    return data



def parse_fextralife_weapons(text):
    root = lxml.etree.HTML(text)
    weapons = []

    table = root.xpath('//div[@id="wiki-content-block"]//table')[0]
    rows = table.xpath('tbody/tr')
    #print("nrows", len(rows))
    for tr in rows:
        data = default_parse_tr(tr)
        weapons.append(data)
    return weapons


def pp(name, e):
    if isinstance(e, list):
        for i, ei in enumerate(e):
            pp(name + "[" + str(i) + "]", ei)
    else:
        print(name, e.tag)
        print(lxml.etree.tostring(e, pretty_print=True))


def _main():
    indir = sys.argv[1]
    outpath = sys.argv[2]
    weapon_list_all = []
    for wtype in WTYPES:
        print(wtype)
        fpath = os.path.join(indir, wtype + ".html")
        with open(fpath) as f:
            text = f.read()
        weapon_list = parse_fextralife_weapons(text)
        for w in weapon_list:
            w["wtype"] = wtype
        weapon_list_all.extend(weapon_list)
    with open(outpath, "w") as f:
        json.dump(weapon_list_all, f, indent=2)


if __name__ == '__main__':
    _main()
