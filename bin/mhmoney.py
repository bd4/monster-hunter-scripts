#!/usr/bin/env python
"""
Script to find the most lucrative monster parts to farm for money.
"""

import codecs
import urllib
import os.path

import _pathfix

from mhapi.db import MHDB
from mhapi import rewards



ITEM_TYPES = "Bone Bug Flesh Ore Sac/Fluid".split()


def print_top_items(db):
    items = db.get_items(ITEM_TYPES)
    ev = dict()
    strats = dict()
    for item in items:
        trade = db.get_wyporium_trade(item.id)
        if trade is not None:
            ev[item.id] = 0
            continue

        if item.sell == "":
            item.sell = 0
        else:
            item.sell = int(item.sell)

        ir = rewards.ItemRewards(db, item)
        strat = ir.get_best_strat()
        if strat is None:
            ev[item.id] = 0
        else:
            ev[item.id] = strat.ev
            strats[item.id] = strat

    def item_value(i):
        return i.sell * ev[i.id] / 100.0

    items.sort(key=item_value, reverse=True)
    for item in items:
        value = item_value(item)
        if value < 10000:
            break
        print "    %-20s % 7.f % 6d (% 5.f)" % \
            (item.name, value, int(item.sell), ev[item.id])


if __name__ == '__main__':
    db = MHDB()
    print_top_items(db)
