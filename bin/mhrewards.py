#!/usr/bin/env python3

import _pathfix

from mhapi.db import MHDB
from mhapi import rewards
from mhapi.util import get_utf8_writer


def print_rewards(item_name):
    out = get_utf8_writer(sys.stdout)
    err_out = get_utf8_writer(sys.stderr)

    db = MHDB(_pathfix.db_path)

    # TODO: implement fuzzy search like in mhrewards using difflib
    #item_names = db.get_item_names(rewards.ITEM_TYPES)

    item_row = rewards.find_item(db, item_name, err_out)
    if item_row is None:
        sys.exit(os.EX_DATAERR)
    ir = rewards.ItemRewards(db, item_row)
    ir.print_all(out)


_ITEM_NAME_SPECIAL = {
    "welldonesteak":	"Well-done Steak",
    "lrgelderdragonbone":	"Lrg ElderDragon Bone",
    "highqualitypelt":	"High-quality Pelt",
    "kingsfrill":   	"King's Frill",
    "btetsucabrahardclaw":	"B.TetsucabraHardclaw",
    "heartstoppingbeak":	"Heart-stopping Beak",
    "dsqueenconcentrate":	"D.S.QueenConcentrate",
    "dahrenstone":  	"Dah'renstone",
    "championsweapon":	"Champion's Weapon",
    "championsarmor":	"Champion's Armor",
    "popeyedgoldfish":	"Pop-eyed Goldfish",
    "100mwantedposter":	"100m+ Wanted Poster",
    "goddesssmelody":	"Goddess's Melody",
    "goddesssembrace":	"Goddess's Embrace",
    "capcommhspissue":	"Capcom MH Sp. Issue",
    "goddesssfire": 	"Goddess's Fire",
    "huntersticket":	"Hunter's Ticket",
    "herosseal":    	"Hero's Seal",
    "thetaleofpoogie":	"The Tale of Poogie",
    "goddesssgrace":	"Goddess's Grace",
    "conquerorsseal":	"Conqueror's Seal",
    "conquerorssealg":	"Conqueror's Seal G",
    "questersticket":	"Quester's Ticket",
    "instructorsticket":"Instructor's Ticket",
    "veticket":         "VE Ticket",
    "vedeluxeticket":	"VE Deluxe Ticket",
    "vebronzeticket":	"VE Bronze Ticket",
    "vesilverticket":	"VE Silver Ticket",
    "vegoldenticket":	"VE Golden Ticket",
    "vecosmicticket":	"VE Cosmic Ticket",
}


def item_name_key(item_name):
    return item_name.translate(None, " .-'+").lower()


def canonical_item_name(item_name):
    key = item_name_key(item_name)
    if key in _ITEM_NAME_SPECIAL:
        return _ITEM_NAME_SPECIAL[key]
    else:
        return " ".join(item_name.lower().split()).title()


if __name__ == '__main__':
    import sys
    import os
    import os.path

    if len(sys.argv) != 2:
        print(("Usage: %s 'item name'" % sys.argv[0]))
        sys.exit(os.EX_USAGE)

    item_name = canonical_item_name(sys.argv[1])

    print_rewards(item_name)
