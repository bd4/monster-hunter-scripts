#!/usr/bin/env python3

import sys
import os.path
import time
import re
import json
from pprint import pprint
from collections import defaultdict
import lxml.etree
import urllib.parse

import requests

import _pathfix

from mhapi.util import WEAPON_TYPES

MAX_PER_TYPE = 100000

def pp(name, e):
    if isinstance(e, list):
        for i, ei in enumerate(e):
            pp(name + "[" + str(i) + "]", ei)
    else:
        print(name, e.tag)
        print(lxml.etree.tostring(e, pretty_print=True))


def parse_sharpness(value_span):
    bar_span = value_span.xpath('.//span[@class="mh-sharpness-bar"]')[0]
    sharp_spans = bar_span.xpath('.//span')
    i = 0
    last_color_num = -1
    values = []
    values_plus = []
    for sharp_span in sharp_spans:
        # <span class="mh-sharpness mh-sharpness-color-0" style="left:0%;width:47.5%;"></span>
        attr_style = sharp_span.attrib["style"]
        attr_class = sharp_span.attrib["class"]
        classes = attr_class.split()
        half = False
        for class_name in classes:
            if class_name.startswith("mh-sharpness-color-"):
                color_num = int(class_name[-1])
            if class_name == "mh-sharpness-half":
                half = True
        styles = attr_style.split(";")
        for s in styles:
            s = s.strip()
            if not s:
                continue
            parts = s.split(":")
            if parts[0] == "width":
                value = int(2*float(parts[1].rstrip("%")))
                break
        if value == 0:
            continue
        if half:
            if not values_plus:
                values_plus = list(values)
            if color_num == last_color_num:
                values_plus[-1] += value
            else:
                values_plus.append(value)
        else:
            # fill in missing colors, if any
            while i < color_num:
                values.append(0)
                i += 1
            values.append(value)
        i += 1
        last_color_num = color_num
    return values, values_plus


def _map_element(e):
    if e == "Bomb":
        return "Blast"
    if e == "Paralyze":
        return "Paralysis"
    return e


def get_rampage_slots(name):
    names = [name]
    if name.endswith("+"):
        names.append(name[:-1] + " +")
    if '"' in name:
        names.append(name.replace('"', ''))
    for name in names:
        url = ("https://monsterhunterrise.wiki.fextralife.com/"
               + urllib.parse.quote(name))
        result = requests.get(url)
        if result.status_code == 200:
            break
    if result.status_code == 404:
        print("WARN: failed to get rampage slots", name)
        return []
    root = lxml.etree.HTML(result.content)

    slot_imgs = root.xpath('//div[@class="infobox"]//tbody//img')
    for img in slot_imgs:
        title = img.attrib.get("title")
        if title is None:
            title = img.attrib.get("alt")
        if title and "rampage" in title and "icon" in title:
            parts = re.split(r"[_ ]", title)
            level = int(parts[2])
            return [level]
    return []


def get_weapon_details(wtype, name, link):
    data = dict(wtype=wtype, name=name)
    url = "https://mhrise.mhrice.info" + link
    result = requests.get(url)
    root = lxml.etree.HTML(result.content)

    icon_div = root.xpath('//div[@class="mh-title-icon"]/div[@class="mh-colored-icon"]/div')[0]
    rarity_class = icon_div.attrib["class"]
    data["rarity"] = int(rarity_class.split("-")[-1])

    stat_div = root.xpath('//div[@class="mh-kvlist"]')[0]
    kvlist = stat_div.xpath('.//p[@class="mh-kv"]')
    for kv in kvlist:
        spans = kv.xpath('span')
        key = spans[0].text.strip().lower()
        if key in set(["attack", "affinity", "defense"]):
            value = spans[1].text
            value = value.rstrip("%")
            data[key.lower()] = int(value)
        elif key == "element":
            value_spans = spans[1].xpath("span")
            value = value_spans[0].text.strip()
            if value:
                parts = value.split()
                if parts[0] == "None":
                    data["element"] = None
                    data["element_attack"] = None
                else:
                    data["element"] = _map_element(parts[0])
                    data["element_attack"] = int(parts[1])
            if len(value_spans) > 1:
                value = value_spans[1].text.strip()
                parts = value.split()
                data["element_2"] = _map_element(parts[0])
                data["element_2_attack"] = int(parts[1])
            else:
                data["element_2"] = None
                data["element_2_attack"] = None
        elif key == "slot":
            # <img alt="A level-2 slot" class="mh-slot" src="/resources/slot_1.png">
            # <img alt="A level-4 slot" class="mh-slot-large" src="/resources/slot_3.png">
            slots = []
            value_span = spans[1]
            slot_imgs = value_span.xpath('.//span[@class="mh-slot-outer"]/img')
            for slot_img in slot_imgs:
                src = slot_img.attrib["src"]
                m = re.match(r".*/slot_(\d+)\.png", src)
                if m:
                    svalue = int(m.group(1)) + 1
                    slots.append(svalue)
            data["slots"] = slots
        elif key == "rampage slot":
            slots = []
            value_span = spans[1]
            slot_imgs = value_span.xpath('.//span[@class="mh-slot-outer"]/img')
            for slot_img in slot_imgs:
                src = slot_img.attrib["src"]
                m = re.match(r".*/slot_(\d+).png", src)
                if m:
                    svalue = int(m.group(1)) + 1
                    slots.append(svalue)
            data["rampage_slots"] = slots
        elif key == "sharpness":
            value_span = spans[1]
            sharp, sharp_plus = parse_sharpness(value_span)
            data["sharpness"] = sharp
            data["sharpness_plus"] = sharp_plus
        elif key == "bottle":
            value = spans[1].text.strip()
            if wtype == "Charge Blade":
                key = "phial"
                if value == "Power":
                    value = "Impact"
                if value == "StrongElement":
                    value = "Element"
            if wtype == "Switch Axe":
                key = "phial"
                parts = value.split()
                value = parts[0]
                if value == "StrongElement":
                    value = "Element"
                if value == "DownStamina":
                    value = "Exhaust"
                phial_num = int(parts[1])
                if phial_num > 0:
                    data["phial_value"] = phial_num
            data[key] = value
        elif key == "type":
            value = spans[1].text.strip()
            parts = value.split()
            value = parts[0]
            if len(parts) > 1:
                level = int(parts[1])
                data["shelling_level"] = level
            if wtype == "Gunlance":
                key = "shelling_type"
            if value == "Radial":
                value = "Long"
            elif value == "Diffusion":
                value = "Wide"
            data[key] = value
        elif key == "insect level":
            value = spans[1].text.strip()
            data["bug_level"] = int(value)

    sections = root.xpath("//section")
    craft_table = None
    for section in sections:
        h2 = section.xpath("h2/text()")
        if h2 and h2[0] == "Crafting":
            craft_table = section.xpath("div/table/tbody")[0]
            break
    if craft_table is not None:
        rows = craft_table.xpath("tr")
        for row in rows:
            cells = row.findall("td")
            craft_type = cells[0].text.strip()
            if craft_type.startswith("Forge"):
                zenny, comps = get_components(cells)
                data["creation_cost"] = zenny
                data["create_components"] = comps
            elif craft_type.startswith("Upgrade"):
                zenny, comps = get_components(cells)
                data["upgrade_cost"] = zenny
                data["upgrade_components"] = comps

    data["rampage_slots"] = get_rampage_slots(name)

    return data


def get_components(cells):
    zenny = int(cells[1].text.rstrip("z"))
    cmat_text = cells[2].text
    components = {}
    if cmat_text != "-":
        cmat_name = cells[2].xpath('.//span[@lang="en"]/span')[0].text
        cmat_points_string = cells[2].xpath("span")[0].tail
        cmat_points = int(cmat_points_string.split(" ")[0])
        components[cmat_name] = cmat_points
    li_mats = cells[3].xpath("ul/li")
    for li in li_mats:
        count = int(li.text.strip().rstrip("x"))
        name = li.xpath('.//span[@lang="en"]/span')[0].text
        components[name] = count
    return (zenny, components)


def get_rice_id(link):
    # /weapon/GreatSword_026.html
    fname_base, _ = os.path.splitext(os.path.basename(link))
    _, tail = fname_base.rsplit("_", maxsplit=1)
    return int(tail)


def get_weapon_list(wtype, id_offset):
    if wtype == "Sword and Shield":
        ftype = "short_sword"
    elif wtype == "Hunting Horn":
        ftype = "horn"
    elif wtype == "Gunlance":
        ftype = "gun_lance"
    elif wtype == "Switch Axe":
        ftype = "slash_axe"
    elif wtype == "Charge Blade":
        ftype = "charge_axe"
    else:
        ftype = wtype.lower().replace(" ", "_")
    list_fname = ftype + ".html"
    result = requests.get("https://mhrise.mhrice.info/weapon/" + list_fname)
    root = lxml.etree.HTML(result.content)
    weapon_tree_li = root.xpath('//div[@class="mh-weapon-tree"]//li')
    weapons = []
    seen = set()
    for li in weapon_tree_li:
        listack = [li]
        name_stack = [None]
        while listack:
            current_li = listack.pop()
            parent_name = name_stack.pop()

            a = current_li.xpath('a[@class="mh-icon-text"]')[0]
            sublists = current_li.xpath('ul/li')

            name = a.xpath('.//span[@lang="en"]/span')[0].text
            link = a.attrib['href']

            name_stack.extend([name] * len(sublists))
            listack.extend(sublists)

            if link in seen:
                print("WARN: Duplicate ", name, link)
                continue
            seen.add(link)

            id_ = get_rice_id(link) + id_offset
            final = (len(sublists) == 0)
            wdata = dict(name=name, link=link, _id=id_, parent_name=parent_name, final=final)
            weapons.append(wdata)

    return weapons


def test_details():
    tests = [
        ("Great Sword", "Sinister Shadowblade+", "/weapon/GreatSword_403.html"),
        ("Great Sword", "Redwing Claymore I", "/weapon/GreatSword_068.html"),
        ("Great Sword", "Defender Great Sword I", "/weapon/GreatSword_132.html"),
        ("Great Sword", "Kamura Warrior Cleaver", "/weapon/GreatSword_300.html"),
        ("Dual Blades", "Blood Wind Skards+", "/weapon/DualBlades_319.html"),
        ("Switch Axe", "Arzuros Jubilax", "/weapon/SlashAxe_323.html"),
        ("Switch Axe", "Leave-Taker+", "/weapon/SlashAxe_307.html"),
        ("Insect Glaive", "Fine Kamura Glaive", "/weapon/InsectGlaive_302.html"),
    ]
    for t in tests:
        print(t)
        d = get_weapon_details(*t)
        pprint(d)
        print()


def _main():
    weapons_type_name_map = defaultdict(dict)
    weapons_data = []

    outdir = sys.argv[1]
    outfile = os.path.join(outdir, "weapon_list.json")
    if os.path.exists(outfile):
        print("Loading existing data from ", outfile)
        with open(outfile) as f:
            old_data = json.load(f)
            for d in old_data:
                wtype_name_map = weapons_type_name_map[d["wtype"]]
                if d["name"] in wtype_name_map:
                    print("Removing duplicate ", d["wtype"], d["name"])
                    continue
                wtype_name_map[d["name"]] = d
                old_slots = d["rampage_slots"]
                new_slots = get_rampage_slots(d["name"])
                if new_slots != old_slots:
                    print(d["name"], old_slots, "=>", new_slots)
                    d["rampage_slots"] = new_slots
                    time.sleep(0.1)

    for itype, wtype in enumerate(WEAPON_TYPES):
        wtype_name_map = weapons_type_name_map[wtype]
        weapons = get_weapon_list(wtype, (itype+1) * MAX_PER_TYPE)
        if not weapons:
            print("WARN: no weapons of type", wtype)
            continue
        name_id_map = {}
        for w in weapons:
            # always re-calculate IDs
            name_id_map[w["name"]] = w["_id"]
            if w["parent_name"]:
                w["parent_id"] = name_id_map[w["parent_name"]]
            else:
                w["parent_id"] = None
            data = wtype_name_map.get(w["name"])
            if data is not None:
                print("UP ", wtype, w["_id"], w["name"], w["link"])
                data.update(w)
                weapons_data.append(data)
                continue
            print("ADD", wtype, w["_id"], w["name"], w["link"])
            data = get_weapon_details(wtype, w["name"], w["link"])
            data.update(w)
            weapons_data.append(data)
            time.sleep(0.5)

    with open(os.path.join(outdir, "weapon_list.json"), "w") as f:
        json.dump(weapons_data, f, indent=2)


if __name__ == '__main__':
    #test_details()
    _main()
