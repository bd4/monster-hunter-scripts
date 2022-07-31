#!/usr/bin/env python3

import sys
import os.path
import time
import re
import json
import lxml.etree

import requests

PART_HEADER_MAP = dict(Slash="Cut",
                       Impact="Impact",
                       Shot="Shot",
                       Fire="Fire",
                       Water="Water",
                       Ice="Ice",
                       Thunder="Thunder",
                       Dragon="Dragon")


def _td_part_id(td):
    s = td.xpath('.//text()')[0].strip()
    if s.startswith("["):
        s = s[1:2]
    return int(s)


def _td_part_break(td):
    text = td.text or ""
    text = text.strip()
    if text:
        m = re.match(r"\(x(\d+)\) (\d+)", text)
        print(text, m, m.group(1), m.group(2))
        return dict(count=int(m.group(1)), damage=int(m.group(2)))
    return dict(count=0, damage=0)

def _td_part_sever(td):
    text = td.text or ""
    text = text.strip()
    if text:
        m = re.match(r"\((\w+)\) (\d+)", text)
        return dict(type=m.group(1), damage=int(m.group(2)))
    return dict(type="", damage=0)


def get_monster_data(link):
    hit_data = {}
    base = "https://mhrise.mhrice.info"
    url = base + link
    result = requests.get(url)
    root = lxml.etree.HTML(result.content)
    sections = root.xpath("//section")
    hit_table = None
    parts_table = None
    for section in sections:
        h2 = section.xpath('h2')
        if h2 and h2[0].text:
            if hit_table is None and h2[0].text.lower().startswith("hitzone"):
                hit_table = section.xpath('.//table')[0]
            elif parts_table is None and h2[0].text.lower().startswith("parts"):
                parts_table = section.xpath('.//table')[0]
    #pp("hit_table", hit_table)
    #pp("tr", hit_table.xpath('thead/tr'))
    header_cells = hit_table.xpath('thead/tr/th')
    header_names = [th.text for th in header_cells]
    #print("names", header_names)
    rows = hit_table.xpath('tbody/tr')
    part_id_name_map = {}
    for row in rows:
        if 'invalid' in row.attrib.get('class', ""):
            continue
        #pp("tr", row)
        cols = dict(zip(header_names, row.xpath('td')))
        name_td = cols["Name"]
        #pp("name_td", name_td)
        name_en_span = name_td.xpath('.//span[@lang="en"]/span')
        if not name_en_span:
            continue
        name = name_en_span[0].text
        #pp("part", cols["Part"].xpath('.//text()'))
        part_id = _td_part_id(cols["Part"])
        part_id_name_map[part_id] = name
        hit_data[name] = {}
        for k in PART_HEADER_MAP.keys():
            hit_data[name][PART_HEADER_MAP[k]] = int(cols[k].text)
    #print(hit_data)

    return hit_data

    # add break/sever data
    header_cells = parts_table.xpath('thead/tr/th')
    header_names = [th.text for th in header_cells]
    #print(header_names)
    rows = parts_table.xpath('tbody/tr')
    breaks = []
    for row in rows:
        if 'invalid' in row.attrib.get('class', ""):
            continue
        cols = dict(zip(header_names, row.xpath('td')))
        part_id = _td_part_id(cols["Part"])
        part_name = part_id_name_map[part_id]
        hit_data[part_name]["_stagger"] = int(cols["Stagger"].text)
        part_break = cols["Break"].text or ""
        part_sever = cols["Sever"].text or ""
        part_break = part_break.strip()
        part_sever = part_sever.strip()
        hit_data[part_name]["_break"] = _td_part_break(cols["Break"])
        hit_data[part_name]["_sever"] = _td_part_sever(cols["Sever"])
        if part_break or part_sever:
            breaks.append(part_name)

    hit_data["_breaks"] = breaks
    return hit_data


def pp(name, e):
    if isinstance(e, list):
        for i, ei in enumerate(e):
            pp(name + "[" + str(i) + "]", ei)
    else:
        print(name, e.tag)
        print(lxml.etree.tostring(e, pretty_print=True))


def get_monster_list():
    result = requests.get("https://mhrise.mhrice.info/monster.html")
    root = lxml.etree.HTML(result.content)
    monster_li = root.xpath('//ul[@id="slist-monster"]//li')
    monsters = []
    for li in monster_li:
        name = li.xpath('.//span[@lang="en"]/span')[0].text
        link = li.xpath('a')[0].attrib['href']
        monsters.append(dict(name=name, link=link))
    return monsters


def _main():
    outdir = sys.argv[1]
    monster_list = get_monster_list()
    with open(os.path.join(outdir, "monster_list.json"), "w") as f:
        json.dump(monster_list, f, indent=2)

    monster_hitboxes = {}
    for m in monster_list:
        print(m["name"])
        try:
            monster_hitboxes[m["name"]] = get_monster_data(m["link"])
        except Exception as e:
            print("ERR: failed to parse hitzones for ", m["name"])
            print(repr(e), str(e))
        time.sleep(0.5)

    with open(os.path.join(outdir, "monster_hitboxes.json"), "w") as f:
        json.dump(monster_hitboxes, f, indent=2)


if __name__ == '__main__':
    _main()
